"""Phase P2.1 — re-open committed household flow tests (plan v20 §A1.30).

Round-trip integration: re-open a committed household, modify a fact,
re-commit; assert household.external_id unchanged + member/account/goal
counts updated + 2+ ``review_state_committed`` audit events on the
same entity. Plus boundary cases per §A1.50:

  - Cannot re-open while another open workspace exists (409).
  - Soft-undo forbidden on reopen workspaces (403 with code).
  - Reopen workspace seeded with committed reviewed_state.
  - Re-open + re-commit emits >= 3 audit events
    (review_workspace_reopened + review_state_committed +
    portfolio_generation_post_review_commit).
"""

from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from web.api import models
from web.api.review_state import readiness_for_state
from web.api.tests.test_review_ingestion import (
    _approve_required_sections,
    _engine_ready_state,
    _user,
)
from web.audit.models import AuditEvent


def _commit_workspace(client: APIClient, user) -> models.ReviewWorkspace:
    """Helper: commit a workspace and return it (post-commit). Mirrors
    the test_uncommit.py pattern used across phase tests."""
    workspace = models.ReviewWorkspace.objects.create(label="Initial review", owner=user)
    workspace.reviewed_state = _engine_ready_state()
    workspace.readiness = readiness_for_state(workspace.reviewed_state).__dict__
    workspace.save()
    _approve_required_sections(workspace, user)
    response = client.post(reverse("review-workspace-commit", args=[workspace.external_id]), {})
    assert response.status_code == 200, response.content
    workspace.refresh_from_db()
    return workspace


@pytest.mark.django_db
def test_reopen_round_trip_preserves_household_identity(tmp_path, settings) -> None:
    """G2 round-trip — household.external_id unchanged across re-commit."""
    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    from django.core.management import call_command

    call_command("seed_default_cma")
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)

    workspace = _commit_workspace(client, user)
    household = workspace.linked_household
    assert household is not None
    original_external_id = household.external_id
    original_member_count = household.members.count()

    # Re-open the committed household.
    response = client.post(reverse("client-reopen", args=[household.external_id]), {})
    assert response.status_code == 200, response.content
    body = response.json()
    assert "workspace" in body
    reopen_workspace_id = body["workspace"]["external_id"]
    reopen_workspace = models.ReviewWorkspace.objects.get(external_id=reopen_workspace_id)
    assert reopen_workspace.source_household_id == household.pk
    assert reopen_workspace.status == models.ReviewWorkspace.Status.REVIEW_READY

    # Modify a fact in the reviewed_state — add a second household member.
    new_state = dict(reopen_workspace.reviewed_state)
    new_state["people"] = [
        *new_state.get("people", []),
        {"id": "person_added", "name": "Added Person", "age": 30},
    ]
    reopen_workspace.reviewed_state = new_state
    reopen_workspace.readiness = readiness_for_state(new_state).__dict__
    reopen_workspace.save()

    # Re-commit — UPSERT must preserve the source household.
    recommit = client.post(
        reverse("review-workspace-commit", args=[reopen_workspace.external_id]), {}
    )
    assert recommit.status_code == 200, recommit.content

    household.refresh_from_db()
    assert household.external_id == original_external_id, (
        "Household external_id changed across re-commit — UPSERT broke."
    )
    # Member count should reflect the new state's member list.
    assert household.members.count() >= 1
    expected_members = len(new_state["people"])
    assert (
        household.members.count() != original_member_count
        or expected_members == original_member_count
    )

    # 2+ review_state_committed audit events on this household entity.
    commit_events = AuditEvent.objects.filter(
        action="review_state_committed",
        metadata__household_id=household.external_id,
    )
    assert commit_events.count() >= 2, (
        f"Expected >= 2 review_state_committed events on household, got {commit_events.count()}"
    )


@pytest.mark.django_db
def test_cannot_reopen_while_another_open_workspace_exists(tmp_path, settings) -> None:
    """409 conflict per §A1.14 #4 — only one open reopen workspace per household."""
    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    from django.core.management import call_command

    call_command("seed_default_cma")
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)

    workspace = _commit_workspace(client, user)
    household = workspace.linked_household

    first = client.post(reverse("client-reopen", args=[household.external_id]), {})
    assert first.status_code == 200, first.content

    # Second attempt while the first is still open → 409.
    second = client.post(reverse("client-reopen", args=[household.external_id]), {})
    assert second.status_code == 409, second.content
    assert second.json().get("code") == "reopen_conflict"


@pytest.mark.django_db
def test_soft_undo_forbidden_on_reopen_workspace(tmp_path, settings) -> None:
    """Uncommit on a reopen workspace returns 403 with structured code."""
    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    from django.core.management import call_command

    call_command("seed_default_cma")
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)

    workspace = _commit_workspace(client, user)
    household = workspace.linked_household

    response = client.post(reverse("client-reopen", args=[household.external_id]), {})
    reopen_workspace_id = response.json()["workspace"]["external_id"]
    reopen_workspace = models.ReviewWorkspace.objects.get(external_id=reopen_workspace_id)

    # Even if we force-commit it (via test setup), uncommit must be blocked.
    reopen_workspace.status = models.ReviewWorkspace.Status.COMMITTED
    reopen_workspace.linked_household = household
    reopen_workspace.save()

    uncommit = client.post(
        reverse("review-workspace-uncommit", args=[reopen_workspace.external_id]), {}
    )
    assert uncommit.status_code == 403, uncommit.content
    assert uncommit.json().get("code") == "soft_undo_forbidden_on_reopen"


@pytest.mark.django_db
def test_reopen_emits_at_least_three_audit_events_on_recommit(tmp_path, settings) -> None:
    """Re-open + re-commit emits review_workspace_reopened + review_state_committed
    + (typed-skip or generated) portfolio audit per locked #74. Expect >= 3."""
    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    from django.core.management import call_command

    call_command("seed_default_cma")
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)

    workspace = _commit_workspace(client, user)
    household = workspace.linked_household
    pre_count = AuditEvent.objects.count()

    response = client.post(reverse("client-reopen", args=[household.external_id]), {})
    reopen_workspace_id = response.json()["workspace"]["external_id"]
    reopen_workspace = models.ReviewWorkspace.objects.get(external_id=reopen_workspace_id)

    recommit = client.post(
        reverse("review-workspace-commit", args=[reopen_workspace.external_id]), {}
    )
    assert recommit.status_code == 200, recommit.content

    delta = AuditEvent.objects.count() - pre_count
    assert delta >= 3, (
        f"Re-open + re-commit should emit >= 3 audit events; saw {delta}. "
        "Expected: review_workspace_reopened + review_state_committed + "
        "portfolio_generation_post_review_commit_(skipped|failed|generated)."
    )

    # The reopen-specific event must be present + carry source_household_id.
    reopen_event = AuditEvent.objects.filter(action="review_workspace_reopened").first()
    assert reopen_event is not None
    assert reopen_event.metadata.get("source_household_id") == household.external_id


@pytest.mark.django_db
def test_reopen_workspace_seeded_with_committed_reviewed_state(tmp_path, settings) -> None:
    """The new workspace's reviewed_state mirrors the household's
    members/accounts/goals/links — composer round-trips losslessly."""
    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    from django.core.management import call_command

    call_command("seed_default_cma")
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)

    workspace = _commit_workspace(client, user)
    household = workspace.linked_household
    assert household is not None

    response = client.post(reverse("client-reopen", args=[household.external_id]), {})
    assert response.status_code == 200, response.content
    reopen_workspace_id = response.json()["workspace"]["external_id"]
    reopen_workspace = models.ReviewWorkspace.objects.get(external_id=reopen_workspace_id)

    state = reopen_workspace.reviewed_state
    assert state["household"]["display_name"] == household.display_name
    assert len(state["people"]) == household.members.count()
    assert len(state["accounts"]) == household.accounts.count()
    assert len(state["goals"]) == household.goals.count()

    # Section approvals seeded as APPROVED so the advisor lands ready
    # to upload + commit without re-approving everything.
    approvals = list(reopen_workspace.section_approvals.all())
    assert len(approvals) == 6
    assert all(a.status == models.SectionApproval.Status.APPROVED for a in approvals)


@pytest.mark.django_db
def test_reopen_workspaces_hidden_from_main_review_queue(tmp_path, settings) -> None:
    """ReviewWorkspaceListCreateView excludes reopen workspaces from
    the main /api/review-workspaces/ feed (they live separately in the
    HouseholdRoute action sub-bar / Commits sub-tab)."""
    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    from django.core.management import call_command

    call_command("seed_default_cma")
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)

    workspace = _commit_workspace(client, user)
    household = workspace.linked_household
    response = client.post(reverse("client-reopen", args=[household.external_id]), {})
    assert response.status_code == 200, response.content
    reopen_workspace_id = response.json()["workspace"]["external_id"]

    listing = client.get(reverse("review-workspace-list"))
    assert listing.status_code == 200
    listed_ids = {w["external_id"] for w in listing.json()}
    assert reopen_workspace_id not in listed_ids, (
        "Reopen workspaces must not surface in the main review queue."
    )
