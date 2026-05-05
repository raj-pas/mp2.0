"""Plan v20 §A1.36 (P9/P2.3) — household-scoped audit events for the
HouseholdContext "Commits" sub-tab.

Coverage:
  * Auth required (403 for unauthenticated)
  * Filters by ``kind`` query param (``commits`` default vs ``all``)
  * Pagination (page + page_size)
  * Advisor-relevant kinds only (no leakage of internal audit actions
    not in the allowlist)
  * Entity-id scoping (events for OTHER households are not returned)

Real-PII discipline (canon §11.8.3): the advisor is already
authenticated + authorized for this household via ``can_access_real_pii``.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from web.api import models
from web.audit.models import AuditEvent

User = get_user_model()


def _user() -> User:
    return User.objects.create_user(
        username="advisor_audit@example.com",
        email="advisor_audit@example.com",
        password="pw",
    )


def _household(user: User, *, suffix: str = "audit") -> models.Household:
    return models.Household.objects.create(
        external_id=f"hh_{suffix}",
        owner=user,
        display_name=f"Audit Test {suffix}",
        household_type="single",
        household_risk_score=3,
    )


@pytest.mark.django_db
def test_audit_events_requires_authentication() -> None:
    user = _user()
    household = _household(user)
    client = APIClient()
    # No force_authenticate — should be rejected
    response = client.get(reverse("client-audit-events", args=[household.external_id]))
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_audit_events_returns_review_state_committed_for_household() -> None:
    """Default ``kind=commits`` returns ``review_state_committed`` events
    matched by ``metadata.household_id`` (per how commits are emitted)."""
    user = _user()
    household = _household(user, suffix="seltzer")
    workspace = models.ReviewWorkspace.objects.create(
        label="Seltzer Audit",
        owner=user,
        linked_household=household,
    )
    AuditEvent.objects.create(
        actor=user.email,
        action="review_state_committed",
        entity_type="review_workspace",
        entity_id=workspace.external_id,
        metadata={"household_id": household.external_id, "version": 1},
    )

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(reverse("client-audit-events", args=[household.external_id]))
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["page"] == 1
    assert body["kind"] == "commits"
    assert len(body["events"]) == 1
    assert body["events"][0]["action"] == "review_state_committed"
    assert body["events"][0]["metadata"]["household_id"] == household.external_id


@pytest.mark.django_db
def test_audit_events_kind_filter_excludes_non_allowlisted_actions() -> None:
    """Events with actions outside the allowlist are filtered out, even
    when scoped to the household."""
    user = _user()
    household = _household(user, suffix="filter")
    workspace = models.ReviewWorkspace.objects.create(
        label="Filter Audit",
        owner=user,
        linked_household=household,
    )
    AuditEvent.objects.create(
        actor=user.email,
        action="review_state_committed",
        entity_type="review_workspace",
        entity_id=workspace.external_id,
        metadata={"household_id": household.external_id, "version": 1},
    )
    # An internal action that should NOT surface in the advisor feed.
    AuditEvent.objects.create(
        actor="system",
        action="session_viewed",
        entity_type="session",
        entity_id="",
        metadata={"household_id": household.external_id},
    )
    AuditEvent.objects.create(
        actor=user.email,
        action="local_login",
        entity_type="session",
        entity_id="",
        metadata={"household_id": household.external_id},
    )

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(reverse("client-audit-events", args=[household.external_id]))
    assert response.status_code == 200
    body = response.json()
    actions = {e["action"] for e in body["events"]}
    assert actions == {"review_state_committed"}, (
        f"Internal-only actions leaked into advisor feed: {actions}"
    )


@pytest.mark.django_db
def test_audit_events_paginates_at_page_size() -> None:
    """Default page-size of 50; client can request page=2."""
    user = _user()
    household = _household(user, suffix="paginate")
    workspace = models.ReviewWorkspace.objects.create(
        label="Paginate Audit",
        owner=user,
        linked_household=household,
    )
    # 75 commit events — more than one page at default 50.
    for i in range(75):
        AuditEvent.objects.create(
            actor=user.email,
            action="review_state_committed",
            entity_type="review_workspace",
            entity_id=workspace.external_id,
            metadata={"household_id": household.external_id, "version": i + 1},
        )

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(reverse("client-audit-events", args=[household.external_id]))
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 75
    assert body["page_size"] == 50
    assert len(body["events"]) == 50

    # page=2 returns the remaining 25
    response2 = client.get(reverse("client-audit-events", args=[household.external_id]) + "?page=2")
    assert response2.status_code == 200
    body2 = response2.json()
    assert body2["page"] == 2
    assert len(body2["events"]) == 25


@pytest.mark.django_db
def test_audit_events_scoped_to_target_household_only() -> None:
    """Events for OTHER households must not leak into this household's feed."""
    user = _user()
    household_a = _household(user, suffix="a")
    household_b = _household(user, suffix="b")
    workspace_a = models.ReviewWorkspace.objects.create(
        label="A", owner=user, linked_household=household_a
    )
    workspace_b = models.ReviewWorkspace.objects.create(
        label="B", owner=user, linked_household=household_b
    )
    AuditEvent.objects.create(
        actor=user.email,
        action="review_state_committed",
        entity_type="review_workspace",
        entity_id=workspace_a.external_id,
        metadata={"household_id": household_a.external_id},
    )
    AuditEvent.objects.create(
        actor=user.email,
        action="review_state_committed",
        entity_type="review_workspace",
        entity_id=workspace_b.external_id,
        metadata={"household_id": household_b.external_id},
    )

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(reverse("client-audit-events", args=[household_a.external_id]))
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    metadata_household_ids = {e["metadata"].get("household_id") for e in body["events"]}
    assert metadata_household_ids == {household_a.external_id}


@pytest.mark.django_db
def test_audit_events_kind_all_includes_portfolio_lifecycle() -> None:
    """``kind=all`` adds portfolio-generation lifecycle events to the feed."""
    user = _user()
    household = _household(user, suffix="kind_all")
    AuditEvent.objects.create(
        actor=user.email,
        action="review_state_committed",
        entity_type="review_workspace",
        entity_id="ws_x",
        metadata={"household_id": household.external_id},
    )
    AuditEvent.objects.create(
        actor=user.email,
        action="portfolio_run_declined",
        entity_type="household",
        entity_id=household.external_id,
        metadata={"household_id": household.external_id},
    )

    client = APIClient()
    client.force_authenticate(user=user)
    # commits only — should NOT include portfolio_run_declined
    response_commits = client.get(
        reverse("client-audit-events", args=[household.external_id]) + "?kind=commits"
    )
    actions_commits = {e["action"] for e in response_commits.json()["events"]}
    assert actions_commits == {"review_state_committed"}

    # all — should include both
    response_all = client.get(
        reverse("client-audit-events", args=[household.external_id]) + "?kind=all"
    )
    actions_all = {e["action"] for e in response_all.json()["events"]}
    assert actions_all == {"review_state_committed", "portfolio_run_declined"}


@pytest.mark.django_db
def test_audit_events_invalid_kind_returns_400() -> None:
    user = _user()
    household = _household(user, suffix="invalid")
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(
        reverse("client-audit-events", args=[household.external_id]) + "?kind=garbage"
    )
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_kind"


@pytest.mark.django_db
def test_audit_events_empty_state_returns_zero_results() -> None:
    """Sister §3.16 / §A1.54 — household with no audit events returns
    an empty events list without erroring."""
    user = _user()
    household = _household(user, suffix="empty")
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(reverse("client-audit-events", args=[household.external_id]))
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["events"] == []
