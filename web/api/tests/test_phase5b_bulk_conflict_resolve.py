"""Phase 5b.12 — Bulk conflict resolve regression tests.

`POST /api/review-workspaces/<wsid>/conflicts/bulk-resolve/`
applies a shared advisor judgment + rationale + evidence_ack to
multiple conflicts in one atomic transaction. One audit event
per resolved conflict (locked #37). Partial failure rolls back
the whole batch.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from web.api import models
from web.audit.models import AuditEvent


def _user() -> object:
    User = get_user_model()
    return User.objects.create_user(
        username="advisor@example.com", email="advisor@example.com", password="pw"
    )


def _doc(workspace, *, filename: str, **overrides) -> models.ReviewDocument:
    digest = (filename.encode().hex() + "0" * 64)[:64]
    defaults = dict(
        original_filename=filename,
        content_type="application/pdf",
        extension="pdf",
        file_size=1024,
        sha256=digest,
        storage_path=f"workspace_{workspace.external_id}/{filename}",
        document_type="kyc",
        status=models.ReviewDocument.Status.RECONCILED,
        processing_metadata={
            "extraction_version": "extraction.v2",
            "review_schema_version": "reviewed_client_state.v1",
        },
    )
    defaults.update(overrides)
    return models.ReviewDocument.objects.create(workspace=workspace, **defaults)


def _fact(workspace, document, *, field, value, confidence="medium"):
    return models.ExtractedFact.objects.create(
        workspace=workspace,
        document=document,
        field=field,
        value=value,
        confidence=confidence,
        derivation_method="extracted",
        source_location="page 1",
        source_page=1,
        evidence_quote="evidence here",
        extraction_run_id="run-test",
    )


def _seed_two_conflicts(workspace) -> tuple[int, int]:
    """Two conflicting fields with two candidates each. Returns the
    (chosen_fact_id_for_dob, chosen_fact_id_for_marital) tuple — KYC
    candidate fact IDs that the bulk endpoint picks.
    """
    kyc = _doc(workspace, filename="kyc.pdf", document_type="kyc")
    statement = _doc(workspace, filename="statement.pdf", document_type="statement")

    kyc_dob = _fact(
        workspace, kyc, field="people[0].date_of_birth", value="1985-03-12", confidence="high"
    )
    _fact(workspace, statement, field="people[0].date_of_birth", value="1985-03-15")

    kyc_marital = _fact(
        workspace, kyc, field="people[0].marital_status", value="married", confidence="high"
    )
    _fact(workspace, statement, field="people[0].marital_status", value="single")

    # Pre-compute reviewed_state with conflicts so the resolve endpoint
    # has the conflicts list to iterate over.
    from web.api.review_state import reviewed_state_from_workspace

    workspace.reviewed_state = reviewed_state_from_workspace(workspace)
    workspace.save(update_fields=["reviewed_state"])
    return kyc_dob.id, kyc_marital.id


@pytest.mark.django_db
def test_bulk_resolve_applies_to_multiple_conflicts() -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(label="WS", owner=user)
    dob_fact_id, marital_fact_id = _seed_two_conflicts(workspace)

    response = client.post(
        reverse("review-workspace-conflict-bulk-resolve", args=[workspace.external_id]),
        {
            "resolutions": [
                {"field": "people[0].date_of_birth", "chosen_fact_id": dob_fact_id},
                {"field": "people[0].marital_status", "chosen_fact_id": marital_fact_id},
            ],
            "rationale": "KYC supersedes statement for Person 0.",
            "evidence_ack": True,
        },
        format="json",
    )
    assert response.status_code == 200, response.content
    body = response.json()
    assert body["resolved_count"] == 2

    # Each resolved conflict gets its own audit event.
    events = AuditEvent.objects.filter(action="review_conflict_resolved").order_by("id")
    assert events.count() == 2
    fields = sorted(e.metadata["field"] for e in events)
    assert fields == ["people[0].date_of_birth", "people[0].marital_status"]
    for e in events:
        assert e.metadata["bulk"] is True
        assert e.metadata["bulk_count"] == 2


@pytest.mark.django_db
def test_bulk_resolve_rolls_back_on_partial_failure() -> None:
    """If ANY resolution validation fails, the WHOLE batch rolls
    back — no half-resolved conflicts left behind.
    """
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(label="WS", owner=user)
    dob_fact_id, _ = _seed_two_conflicts(workspace)

    response = client.post(
        reverse("review-workspace-conflict-bulk-resolve", args=[workspace.external_id]),
        {
            "resolutions": [
                {"field": "people[0].date_of_birth", "chosen_fact_id": dob_fact_id},
                # Invalid: chosen_fact_id is a fact NOT in this workspace.
                {"field": "people[0].marital_status", "chosen_fact_id": 999_999},
            ],
            "rationale": "Should not partially apply.",
            "evidence_ack": True,
        },
        format="json",
    )
    # Either 400 (chosen_fact_not_in_workspace) or 404 if the lookup
    # cascaded — but never 200 with one resolved + one not. The DB
    # state must show NEITHER conflict resolved.
    assert response.status_code in {400, 404}
    workspace.refresh_from_db()
    conflicts = workspace.reviewed_state.get("conflicts", [])
    for conflict in conflicts:
        assert conflict.get("resolved") is not True

    # No audit events emitted (we record AFTER the atomic block; if the
    # 4xx returned mid-loop, the block aborted and the for-loop never
    # got to the record_event calls).
    events = AuditEvent.objects.filter(action="review_conflict_resolved")
    assert events.count() == 0


@pytest.mark.django_db
def test_bulk_resolve_validates_inputs() -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(label="WS", owner=user)

    # Missing rationale
    response = client.post(
        reverse("review-workspace-conflict-bulk-resolve", args=[workspace.external_id]),
        {
            "resolutions": [{"field": "x", "chosen_fact_id": 1}],
            "rationale": "x",  # < 4 chars
            "evidence_ack": True,
        },
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["code"] == "rationale_required"

    # Missing evidence_ack
    response = client.post(
        reverse("review-workspace-conflict-bulk-resolve", args=[workspace.external_id]),
        {
            "resolutions": [{"field": "x", "chosen_fact_id": 1}],
            "rationale": "rationale here",
            "evidence_ack": False,
        },
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["code"] == "evidence_ack_required"

    # Empty resolutions
    response = client.post(
        reverse("review-workspace-conflict-bulk-resolve", args=[workspace.external_id]),
        {
            "resolutions": [],
            "rationale": "rationale here",
            "evidence_ack": True,
        },
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["code"] == "resolutions_required"


@pytest.mark.django_db
def test_bulk_resolve_unauthenticated_returns_403() -> None:
    workspace = models.ReviewWorkspace.objects.create(label="WS", owner=_user())
    client = APIClient()
    response = client.post(
        reverse("review-workspace-conflict-bulk-resolve", args=[workspace.external_id]),
        {"resolutions": [], "rationale": "x", "evidence_ack": True},
        format="json",
    )
    assert response.status_code in {401, 403}
