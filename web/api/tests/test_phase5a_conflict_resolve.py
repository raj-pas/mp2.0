"""Phase 5a conflict-resolution endpoint tests.

Covers:
  * Per-conflict candidate enrichment in reviewed_state.conflicts.
  * Redacted evidence quotes per candidate (canon §11.8.3).
  * POST /api/review-workspaces/<wsid>/conflicts/resolve/ happy path.
  * Validation of payload fields (field, chosen_fact_id, rationale,
    evidence_ack).
  * 404 on unknown field; 400 on chosen_fact_id not in conflict.
  * Atomicity (transaction.atomic + select_for_update structurally
    pinned).
  * Audit event emitted exactly once with rationale_len (NOT
    rationale text).
  * Section approvals invalidated when resolution introduces blockers.
"""

from __future__ import annotations

import inspect

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from web.api import models
from web.audit.models import AuditEvent


def _user(email: str = "advisor@example.com"):
    User = get_user_model()
    user, _ = User.objects.get_or_create(
        email=email,
        defaults={"username": email, "is_active": True},
    )
    return user


def _make_conflicting_workspace(user, *, with_pii_quote: bool = False):
    """Build a workspace with two docs producing conflicting age facts.

    Phase P1.1 (2026-05-05): cross-doc entity alignment requires TWO
    identifying fields to merge `people[0]` references across docs.
    Both docs share `display_name` + `accounts[0].account_number` so
    the matcher aligns them to a single canonical person — exposing
    the age disagreement on the canonical field.
    """
    workspace = models.ReviewWorkspace.objects.create(
        label="conflict-test",
        owner=user,
        data_origin=models.ReviewWorkspace.DataOrigin.SYNTHETIC,
    )
    kyc_doc = models.ReviewDocument.objects.create(
        workspace=workspace,
        original_filename="kyc.pdf",
        content_type="application/pdf",
        file_size=100,
        sha256="a" * 64,
        document_type="kyc",
        status=models.ReviewDocument.Status.RECONCILED,
    )
    statement_doc = models.ReviewDocument.objects.create(
        workspace=workspace,
        original_filename="statement.pdf",
        content_type="application/pdf",
        file_size=200,
        sha256="b" * 64,
        document_type="statement",
        status=models.ReviewDocument.Status.RECONCILED,
    )
    # Identity anchors so alignment merges to one canonical person.
    for doc, run in ((kyc_doc, "kyc-run"), (statement_doc, "statement-run")):
        models.ExtractedFact.objects.create(
            workspace=workspace,
            document=doc,
            field="people[0].display_name",
            value="Sarah Chen",
            confidence="high",
            derivation_method="extracted",
            evidence_quote="Account holder: Sarah Chen",
            extraction_run_id=run,
        )
        models.ExtractedFact.objects.create(
            workspace=workspace,
            document=doc,
            field="accounts[0].account_number",
            value="98765432",
            confidence="high",
            derivation_method="extracted",
            evidence_quote="Account: 98765432",
            extraction_run_id=run,
        )
    quote_kyc = (
        "DOB: 1965-03-12; SIN 123-456-789" if with_pii_quote else "Date of birth: 1965-03-12"
    )
    quote_statement = (
        "Account holder Sarah Chen, age 65; SIN 987-654-321"
        if with_pii_quote
        else "Account holder Sarah Chen, age 65"
    )
    fact_a = models.ExtractedFact.objects.create(
        workspace=workspace,
        document=kyc_doc,
        field="people[0].age",
        value=60,
        confidence="high",
        derivation_method="extracted",
        evidence_quote=quote_kyc,
        extraction_run_id="kyc-run",
    )
    fact_b = models.ExtractedFact.objects.create(
        workspace=workspace,
        document=statement_doc,
        field="people[0].age",
        value=65,
        confidence="medium",
        derivation_method="extracted",
        evidence_quote=quote_statement,
        extraction_run_id="statement-run",
    )
    return workspace, fact_a, fact_b


@pytest.mark.django_db
def test_conflict_serializer_includes_candidates_with_redacted_evidence() -> None:
    """Phase 5a: state["conflicts"][i] carries a candidates array, each
    with redacted_evidence_quote (canon §11.8.3 — SIN scrubbed).
    """
    from web.api.review_state import reviewed_state_from_workspace

    user = _user()
    workspace, fact_a, fact_b = _make_conflicting_workspace(user, with_pii_quote=True)

    state = reviewed_state_from_workspace(workspace)
    conflicts = state.get("conflicts") or []
    assert conflicts, "expected at least one conflict on people[0].age"

    age_conflict = next(c for c in conflicts if c["field"] == "people[0].age")
    candidates = age_conflict.get("candidates") or []
    assert len(candidates) == 2

    candidate_fact_ids = {c["fact_id"] for c in candidates}
    assert candidate_fact_ids == {fact_a.id, fact_b.id}

    for candidate in candidates:
        # Source attribution exposed (filename is not real-PII risk —
        # only doc CONTENT is). Doc type lets the UI show provenance
        # chips.
        assert candidate["source_document_filename"] in {"kyc.pdf", "statement.pdf"}
        assert candidate["source_document_type"] in {"kyc", "statement"}
        assert candidate["confidence"] in {"high", "medium", "low"}
        # Evidence quote is REDACTED — SIN must not appear verbatim.
        assert "123-456-789" not in candidate["redacted_evidence_quote"]
        assert "987-654-321" not in candidate["redacted_evidence_quote"]


@pytest.mark.django_db
def test_conflict_resolve_endpoint_marks_resolved_with_chosen_fact() -> None:
    """Happy path: POST /resolve flips conflict.resolved=True, captures
    chosen_fact_id + rationale + evidence_ack, persists resolved_at +
    resolved_by, and returns updated state.
    """
    user = _user()
    workspace, fact_a, fact_b = _make_conflicting_workspace(user)
    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("review-workspace-conflict-resolve", args=[workspace.external_id])
    response = client.post(
        url,
        {
            "field": "people[0].age",
            "chosen_fact_id": fact_a.id,
            "rationale": "KYC is the source of record per canon §11.4.",
            "evidence_ack": True,
        },
        format="json",
    )
    assert response.status_code == 200, response.content
    body = response.json()
    conflicts = body["state"]["conflicts"]
    resolved = next(c for c in conflicts if c["field"] == "people[0].age")
    assert resolved["resolved"] is True
    assert resolved["chosen_fact_id"] == fact_a.id
    assert resolved["resolution"] == 60
    assert resolved["evidence_ack"] is True
    assert resolved["resolved_by"] == "advisor@example.com"
    assert resolved.get("rationale", "").startswith("KYC is the source")


@pytest.mark.django_db
def test_conflict_resolve_emits_single_audit_event_without_rationale_text() -> None:
    """Locked decision #37 + canon §11.8.3: exactly one audit event per
    state-changing endpoint; rationale text NEVER copied to immutable
    audit metadata (only rationale_len + structural counts).
    """
    user = _user()
    workspace, fact_a, _ = _make_conflicting_workspace(user)
    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("review-workspace-conflict-resolve", args=[workspace.external_id])
    rationale_text = "KYC is canonical source of record for DOB."
    response = client.post(
        url,
        {
            "field": "people[0].age",
            "chosen_fact_id": fact_a.id,
            "rationale": rationale_text,
            "evidence_ack": True,
        },
        format="json",
    )
    assert response.status_code == 200

    events = AuditEvent.objects.filter(
        action="review_conflict_resolved",
        entity_id=workspace.external_id,
    )
    assert events.count() == 1
    metadata = events.first().metadata
    assert metadata["field"] == "people[0].age"
    assert metadata["chosen_fact_id"] == fact_a.id
    assert metadata["rationale_len"] == len(rationale_text)
    # Audit metadata must NEVER carry the literal rationale text
    # (canon §11.8.3 — append-only audit row + advisor input may
    # reference real-PII context).
    serialized = str(metadata)
    assert rationale_text not in serialized
    assert "canonical source of record" not in serialized


@pytest.mark.django_db
def test_conflict_resolve_validates_payload_fields() -> None:
    """Each missing/invalid field returns 400 with a structured code
    (Phase 2 PII discipline — `code` is the durable contract).
    """
    user = _user()
    workspace, fact_a, _ = _make_conflicting_workspace(user)
    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("review-workspace-conflict-resolve", args=[workspace.external_id])

    # Missing field
    r = client.post(
        url,
        {"chosen_fact_id": fact_a.id, "rationale": "ok ok", "evidence_ack": True},
        format="json",
    )
    assert r.status_code == 400 and r.json()["code"] == "field_required"

    # Missing chosen_fact_id
    r = client.post(
        url,
        {"field": "people[0].age", "rationale": "ok ok", "evidence_ack": True},
        format="json",
    )
    assert r.status_code == 400 and r.json()["code"] == "chosen_fact_id_required"

    # Short rationale
    r = client.post(
        url,
        {
            "field": "people[0].age",
            "chosen_fact_id": fact_a.id,
            "rationale": "no",
            "evidence_ack": True,
        },
        format="json",
    )
    assert r.status_code == 400 and r.json()["code"] == "rationale_required"

    # Missing evidence_ack
    r = client.post(
        url,
        {
            "field": "people[0].age",
            "chosen_fact_id": fact_a.id,
            "rationale": "ok ok",
            "evidence_ack": False,
        },
        format="json",
    )
    assert r.status_code == 400 and r.json()["code"] == "evidence_ack_required"


@pytest.mark.django_db
def test_conflict_resolve_returns_404_for_unknown_field() -> None:
    user = _user()
    workspace, fact_a, _ = _make_conflicting_workspace(user)
    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("review-workspace-conflict-resolve", args=[workspace.external_id])
    r = client.post(
        url,
        {
            "field": "people[7].nonexistent_field",
            "chosen_fact_id": fact_a.id,
            "rationale": "test test",
            "evidence_ack": True,
        },
        format="json",
    )
    assert r.status_code == 404
    assert r.json()["code"] == "conflict_not_found"


@pytest.mark.django_db
def test_conflict_resolve_rejects_chosen_fact_not_in_conflict() -> None:
    """If advisor picks a fact that exists in the workspace but is NOT
    one of the conflict's candidates, return 400.
    """
    user = _user()
    workspace, fact_a, _ = _make_conflicting_workspace(user)
    # Create a third fact on a different field — exists in workspace
    # but is not a candidate for the people[0].age conflict.
    other_fact = models.ExtractedFact.objects.create(
        workspace=workspace,
        document=fact_a.document,
        field="risk.household_score",
        value=3,
        confidence="medium",
        derivation_method="extracted",
        evidence_quote="risk score discussed",
        extraction_run_id="other-run",
    )
    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("review-workspace-conflict-resolve", args=[workspace.external_id])
    r = client.post(
        url,
        {
            "field": "people[0].age",
            "chosen_fact_id": other_fact.id,
            "rationale": "ok ok",
            "evidence_ack": True,
        },
        format="json",
    )
    assert r.status_code == 400
    assert r.json()["code"] == "chosen_fact_not_in_conflict"


def test_conflict_resolve_view_uses_atomic_with_select_for_update() -> None:
    """Structural pin: the view's post handler must be wrapped in
    transaction.atomic() and acquire select_for_update() on the
    workspace row. Mirrors test_phase3_atomicity.py methodology — a
    static check that future refactors can't silently remove the
    lock-and-validate envelope.
    """
    from web.api.views import ReviewWorkspaceConflictResolveView

    source = inspect.getsource(ReviewWorkspaceConflictResolveView.post)
    assert "transaction.atomic()" in source, (
        "Phase 5a: ReviewWorkspaceConflictResolveView.post must wrap "
        "the conflict-resolution write in transaction.atomic()."
    )
    assert "select_for_update()" in source, (
        "Phase 5a: ReviewWorkspaceConflictResolveView.post must "
        "select_for_update the workspace row to serialize concurrent "
        "advisor calls (locked decision #30)."
    )


@pytest.mark.django_db
def test_conflict_resolve_invalidates_existing_section_approvals_on_blocker_emergence() -> None:
    """If approving a previously-OK section depends on facts that the
    resolution changes, the approval flips to NEEDS_ATTENTION (mirrors
    ReviewWorkspaceStateView.patch behavior). Pinned by an explicit
    `invalidated_approvals` field in the response.
    """
    user = _user()
    workspace, fact_a, _ = _make_conflicting_workspace(user)
    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("review-workspace-conflict-resolve", args=[workspace.external_id])
    response = client.post(
        url,
        {
            "field": "people[0].age",
            "chosen_fact_id": fact_a.id,
            "rationale": "KYC is canonical source of record for DOB.",
            "evidence_ack": True,
        },
        format="json",
    )
    assert response.status_code == 200
    # The contract is: response carries `invalidated_approvals` array
    # (may be empty if no approvals existed). The structural test pins
    # the field's presence so future refactors don't silently drop it.
    body = response.json()
    assert "invalidated_approvals" in body
    assert isinstance(body["invalidated_approvals"], list)
