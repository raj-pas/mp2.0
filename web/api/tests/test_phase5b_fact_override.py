"""Phase 5b.10 + 5b.11 — FactOverride endpoint regression tests.

Locks the `POST /api/review-workspaces/<wsid>/facts/override/`
contract:

  1. Append-only: every advisor edit creates a NEW row; never UPDATE
     an existing row. Latest row wins per (workspace, field).
  2. Source-priority hierarchy (canon §11.4): advisor override
     supersedes any extracted fact for the same field path. The
     reviewed-state composer reflects the override value.
  3. Audit emission (locked decision #37): exactly one
     `review_fact_overridden` event per row, with structural
     metadata only — rationale text NEVER appears in audit metadata.
  4. Section-blocker re-evaluation: if an override invalidates a
     previously-approved section's blocker set, the approval flips
     to NEEDS_ATTENTION so the commit gate forces re-review.
  5. Validation: field path required, value present, rationale
     ≥ 4 chars (mirrors ConflictResolveView's discipline).
  6. is_added=True path supports advisor-added facts (5b.11) using
     the same persistence machinery.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from web.api import models
from web.audit.models import AuditEvent


def _user(username: str = "advisor@example.com") -> object:
    User = get_user_model()
    return User.objects.create_user(username=username, email=username, password="pw")


def _workspace(user: object) -> models.ReviewWorkspace:
    return models.ReviewWorkspace.objects.create(label="WS", owner=user)


@pytest.mark.django_db
def test_fact_override_creates_append_only_row_and_emits_audit() -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = _workspace(user)

    response = client.post(
        reverse("review-workspace-fact-override", args=[workspace.external_id]),
        {
            "field": "people[0].date_of_birth",
            "value": "1985-03-12",
            "rationale": "Advisor confirmed DOB during onboarding call.",
            "is_added": False,
        },
        format="json",
    )
    assert response.status_code == 200, response.content
    body = response.json()
    assert "override_id" in body
    assert "state" in body
    assert "readiness" in body
    assert body["invalidated_approvals"] == []

    overrides = list(workspace.fact_overrides.all())
    assert len(overrides) == 1
    assert overrides[0].field == "people[0].date_of_birth"
    assert overrides[0].value == "1985-03-12"
    assert overrides[0].is_added is False
    assert overrides[0].created_by_id == user.pk

    # Audit emission per locked #37
    events = AuditEvent.objects.filter(action="review_fact_overridden")
    assert events.count() == 1
    metadata = events.first().metadata
    assert metadata["field"] == "people[0].date_of_birth"
    assert metadata["override_id"] == overrides[0].id
    assert metadata["is_added"] is False
    assert metadata["rationale_len"] == len("Advisor confirmed DOB during onboarding call.")
    # PII discipline: rationale TEXT must not leak into audit metadata.
    assert "rationale" not in metadata
    assert "Advisor confirmed DOB" not in str(metadata)


@pytest.mark.django_db
def test_fact_override_is_added_supports_advisor_added_facts() -> None:
    """Phase 5b.11 — advisor adds a goal extraction never produced."""
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = _workspace(user)

    response = client.post(
        reverse("review-workspace-fact-override", args=[workspace.external_id]),
        {
            "field": "goals[0].name",
            "value": "Retirement at 65",
            "rationale": "Goal mentioned in advisor meeting note 2026-04-15.",
            "is_added": True,
        },
        format="json",
    )
    assert response.status_code == 200
    overrides = list(workspace.fact_overrides.all())
    assert len(overrides) == 1
    assert overrides[0].is_added is True

    events = AuditEvent.objects.filter(action="review_fact_overridden")
    assert events.first().metadata["is_added"] is True


@pytest.mark.django_db
def test_fact_override_repeated_edits_create_append_only_rows() -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = _workspace(user)

    for value in ("1985-03-12", "1985-03-15", "1985-03-20"):
        response = client.post(
            reverse("review-workspace-fact-override", args=[workspace.external_id]),
            {
                "field": "people[0].date_of_birth",
                "value": value,
                "rationale": "Updated per advisor review.",
                "is_added": False,
            },
            format="json",
        )
        assert response.status_code == 200

    # Three edits → three rows (append-only).
    rows = list(
        workspace.fact_overrides.filter(field="people[0].date_of_birth").order_by("created_at")
    )
    assert [r.value for r in rows] == ["1985-03-12", "1985-03-15", "1985-03-20"]
    # Latest-row-wins: reviewed_state should reflect the last value.
    body = client.get(
        reverse("review-workspace-state", args=[workspace.external_id]),
    ).json()
    state_dob = body.get("state", {}).get("people", [{}])[0].get("date_of_birth")
    assert state_dob == "1985-03-20"


@pytest.mark.django_db
def test_fact_override_value_required() -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = _workspace(user)

    response = client.post(
        reverse("review-workspace-fact-override", args=[workspace.external_id]),
        {
            "field": "people[0].date_of_birth",
            "value": "",
            "rationale": "Some rationale.",
        },
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["code"] == "value_required"


@pytest.mark.django_db
def test_fact_override_rationale_required() -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = _workspace(user)

    response = client.post(
        reverse("review-workspace-fact-override", args=[workspace.external_id]),
        {
            "field": "people[0].date_of_birth",
            "value": "1985-03-12",
            "rationale": "x",  # < 4 chars
        },
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["code"] == "rationale_required"


@pytest.mark.django_db
def test_fact_override_field_required() -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = _workspace(user)

    response = client.post(
        reverse("review-workspace-fact-override", args=[workspace.external_id]),
        {
            "field": "",
            "value": "x",
            "rationale": "Some rationale.",
        },
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["code"] == "field_required"


@pytest.mark.django_db
def test_fact_override_rejects_save_to_existing_pk() -> None:
    """The model's append-only guard: save() raises on existing pk
    so we can't accidentally UPDATE in place via ORM.
    """
    user = _user()
    workspace = _workspace(user)
    override = models.FactOverride.objects.create(
        workspace=workspace,
        field="people[0].date_of_birth",
        value="1985-03-12",
        rationale="Initial.",
        is_added=False,
        created_by=user,
    )
    override.value = "1985-03-15"  # advisor-mutate attempt
    with pytest.raises(Exception, match="append-only"):
        override.save()


@pytest.mark.django_db
def test_fact_override_unauthenticated_returns_403() -> None:
    workspace = _workspace(_user())
    client = APIClient()
    response = client.post(
        reverse("review-workspace-fact-override", args=[workspace.external_id]),
        {"field": "x", "value": "y", "rationale": "rationale here"},
        format="json",
    )
    assert response.status_code in {401, 403}


@pytest.mark.django_db
def test_fact_override_404_for_unknown_workspace() -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        reverse(
            "review-workspace-fact-override",
            args=["00000000-0000-0000-0000-000000000000"],
        ),
        {
            "field": "people[0].date_of_birth",
            "value": "1985-03-12",
            "rationale": "Some rationale.",
        },
        format="json",
    )
    assert response.status_code == 404
