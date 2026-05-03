"""Phase 5b.13 — Defer conflict + auto-resurface regression tests.

`POST /api/review-workspaces/<wsid>/conflicts/defer/` marks a
conflict as advisory so section approvals can proceed without
blocking on it. When NEW evidence arrives (a new ExtractedFact for
the same field), the conflict auto-undefers (re_surfaced_at) and
re-blocks until resolved. Mirrors the pattern in canon §11.4
source-priority hierarchy + locked decision (2026-05-02 — auto-
resurface).
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from web.api import models
from web.api.review_state import (
    reviewed_state_from_workspace,
    section_blockers,
)
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


def _seed_conflict(workspace) -> str:
    """Two facts on the same field from two same-class docs ⇒
    one conflict surfaces. Returns the field path of the seeded
    conflict.
    """
    kyc = _doc(workspace, filename="kyc.pdf", document_type="kyc")
    kyc2 = _doc(workspace, filename="kyc-v2.pdf", document_type="kyc")
    _fact(workspace, kyc, field="people[0].date_of_birth", value="1985-03-12")
    _fact(workspace, kyc2, field="people[0].date_of_birth", value="1985-03-15")

    workspace.reviewed_state = reviewed_state_from_workspace(workspace)
    workspace.save(update_fields=["reviewed_state"])
    return "people[0].date_of_birth"


@pytest.mark.django_db
def test_defer_conflict_marks_as_advisory_and_emits_audit() -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(label="WS", owner=user)
    field = _seed_conflict(workspace)

    response = client.post(
        reverse("review-workspace-conflict-defer", args=[workspace.external_id]),
        {"field": field, "rationale": "Decide later — need to verify with client."},
        format="json",
    )
    assert response.status_code == 200, response.content

    workspace.refresh_from_db()
    conflicts = workspace.reviewed_state.get("conflicts") or []
    target = next(c for c in conflicts if c.get("field") == field)
    assert target.get("deferred") is True
    assert target.get("deferred_by")
    assert target.get("deferred_rationale") == "Decide later — need to verify with client."
    assert target.get("re_surfaced_at") in (None, "")

    events = AuditEvent.objects.filter(action="review_conflict_deferred")
    assert events.count() == 1
    metadata = events.first().metadata
    assert metadata["field"] == field
    assert metadata["rationale_len"] > 0
    # PII discipline: rationale text must NEVER be in audit metadata.
    assert "rationale" not in metadata
    assert "Decide later" not in str(metadata)


@pytest.mark.django_db
def test_deferred_conflict_does_not_block_section_approval() -> None:
    user = _user()
    workspace = models.ReviewWorkspace.objects.create(label="WS", owner=user)
    field = _seed_conflict(workspace)
    conflicts_before = workspace.reviewed_state.get("conflicts") or []
    assert len(section_blockers(workspace.reviewed_state, "people")) > 0

    # Defer the conflict
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        reverse("review-workspace-conflict-defer", args=[workspace.external_id]),
        {"field": field, "rationale": "Defer for follow-up."},
        format="json",
    )
    assert response.status_code == 200

    workspace.refresh_from_db()
    blockers = section_blockers(workspace.reviewed_state, "people")
    # No conflict-kind blocker for the deferred field.
    assert all(
        not (b.get("kind") == "conflict" and field in (b.get("label", "")))
        for b in blockers
    )


@pytest.mark.django_db
def test_deferred_conflict_resurfaces_on_new_evidence() -> None:
    """A NEW extracted fact for a deferred field triggers
    re_surfaced_at, which restores the section-blocker effect.
    """
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(label="WS", owner=user)
    field = _seed_conflict(workspace)

    # Defer the conflict.
    client.post(
        reverse("review-workspace-conflict-defer", args=[workspace.external_id]),
        {"field": field, "rationale": "Defer for now."},
        format="json",
    )

    # New evidence arrives: a third document with a third fact on the
    # same field path. Re-running reconcile (via reviewed_state_from_workspace)
    # should auto-undefer.
    new_doc = _doc(workspace, filename="kyc-v3.pdf", document_type="kyc")
    _fact(workspace, new_doc, field=field, value="1985-03-20")
    workspace.refresh_from_db()
    fresh_state = reviewed_state_from_workspace(workspace)
    target = next(c for c in fresh_state.get("conflicts") or [] if c.get("field") == field)

    assert target.get("deferred") is True  # marker preserved
    assert target.get("re_surfaced_at")  # but resurfaced

    # Section blockers logic re-blocks once re_surfaced_at is set.
    workspace.reviewed_state = fresh_state
    workspace.save(update_fields=["reviewed_state"])
    blockers = section_blockers(workspace.reviewed_state, "people")
    assert any(b.get("kind") == "conflict" for b in blockers), (
        f"expected re-surfaced conflict to block 'people' section, "
        f"but got blockers: {blockers}"
    )


@pytest.mark.django_db
def test_deferred_conflict_no_resurface_without_new_evidence() -> None:
    """Re-running reconcile WITHOUT new facts must preserve the
    deferred state unchanged — no spurious re_surfaced_at flapping.
    """
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(label="WS", owner=user)
    field = _seed_conflict(workspace)

    client.post(
        reverse("review-workspace-conflict-defer", args=[workspace.external_id]),
        {"field": field, "rationale": "Defer."},
        format="json",
    )
    workspace.refresh_from_db()
    fresh_state = reviewed_state_from_workspace(workspace)
    target = next(c for c in fresh_state.get("conflicts") or [] if c.get("field") == field)
    assert target.get("deferred") is True
    assert target.get("re_surfaced_at") in (None, "")  # NOT resurfaced


@pytest.mark.django_db
def test_defer_conflict_validates_inputs() -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(label="WS", owner=user)
    _seed_conflict(workspace)

    # Missing field
    response = client.post(
        reverse("review-workspace-conflict-defer", args=[workspace.external_id]),
        {"field": "", "rationale": "Some rationale."},
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["code"] == "field_required"

    # Short rationale
    response = client.post(
        reverse("review-workspace-conflict-defer", args=[workspace.external_id]),
        {"field": "people[0].date_of_birth", "rationale": "x"},
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["code"] == "rationale_required"

    # Unknown field
    response = client.post(
        reverse("review-workspace-conflict-defer", args=[workspace.external_id]),
        {"field": "household.unknown_field", "rationale": "Some rationale."},
        format="json",
    )
    assert response.status_code == 404
    assert response.json()["code"] == "conflict_not_found"


@pytest.mark.django_db
def test_defer_conflict_unauthenticated_returns_403() -> None:
    workspace = models.ReviewWorkspace.objects.create(label="WS", owner=_user())
    client = APIClient()
    response = client.post(
        reverse("review-workspace-conflict-defer", args=[workspace.external_id]),
        {"field": "x", "rationale": "x"},
        format="json",
    )
    assert response.status_code in {401, 403}
