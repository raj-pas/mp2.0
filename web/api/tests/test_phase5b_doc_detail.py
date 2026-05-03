"""Phase 5b.5 — per-doc detail endpoint regression tests.

Drives the slide-out DocDetailPanel (UX dimension B.1). The
endpoint returns the existing ReviewDocument shape plus a
`contributed_facts` array — the subset of workspace facts where
THIS document is the canonical source per the source-priority
hierarchy (canon §11.4). Evidence quotes are server-side redacted
via the same pipeline as the conflict-card candidates.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from web.api import models


def _user(username: str = "advisor@example.com") -> object:
    User = get_user_model()
    return User.objects.create_user(username=username, email=username, password="pw")


def _doc(workspace: models.ReviewWorkspace, **overrides) -> models.ReviewDocument:
    # Per-workspace sha256 must be unique (DB constraint). Generate
    # one from the supplied filename so multi-doc tests don't collide.
    filename = overrides.get("original_filename", "kyc.pdf")
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


def _fact(workspace, document, *, field, value, evidence="", confidence="medium"):
    return models.ExtractedFact.objects.create(
        workspace=workspace,
        document=document,
        field=field,
        value=value,
        confidence=confidence,
        derivation_method="extracted",
        source_location="page 1",
        source_page=1,
        evidence_quote=evidence,
        extraction_run_id="run-test",
    )


@pytest.mark.django_db
def test_doc_detail_returns_contributed_facts_with_redacted_evidence() -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(label="WS", owner=user)
    kyc = _doc(workspace, original_filename="kyc.pdf", document_type="kyc")
    statement = _doc(workspace, original_filename="statement.pdf", document_type="statement")

    # Two facts on KYC, one on statement. Endpoint for KYC should
    # only return KYC's contributions.
    _fact(
        workspace,
        kyc,
        field="people[0].date_of_birth",
        value="1985-03-12",
        evidence="DOB is 1985-03-12. Contact: 555-867-5309.",
        confidence="high",
    )
    _fact(
        workspace,
        kyc,
        field="people[0].marital_status",
        value="married",
        confidence="high",
    )
    _fact(
        workspace,
        statement,
        field="accounts[0].current_value",
        value=125000,
        evidence="Balance: $125,000.",
    )

    response = client.get(
        reverse("review-document-detail", args=[workspace.external_id, kyc.id]),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["original_filename"] == "kyc.pdf"
    assert "contributed_facts" in body
    fields = {row["field"] for row in body["contributed_facts"]}
    assert fields == {"people[0].date_of_birth", "people[0].marital_status"}
    # Statement's fact must NOT appear here (contributed_facts is
    # scoped to the queried document).
    assert all(row["field"] != "accounts[0].current_value" for row in body["contributed_facts"])

    dob_row = next(r for r in body["contributed_facts"] if r["field"] == "people[0].date_of_birth")
    assert dob_row["confidence"] == "high"
    assert dob_row["section"] == "people"
    assert dob_row["label"]  # human-readable, non-empty
    assert dob_row["redacted_evidence_quote"]  # redacted but present
    # Phone-pattern redaction must apply to the evidence quote so the
    # slide-out panel can't leak raw phone numbers (REDACT-1 contract).
    assert "555-867-5309" not in dob_row["redacted_evidence_quote"]
    assert "[PHONE REDACTED]" in dob_row["redacted_evidence_quote"]
    # Sort order: facts grouped by section then label alphabetically.
    sections_in_order = [row["section"] for row in body["contributed_facts"]]
    assert sections_in_order == sorted(sections_in_order)


@pytest.mark.django_db
def test_doc_detail_returns_empty_contributed_facts_for_doc_without_facts() -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(label="WS", owner=user)
    doc = _doc(workspace)

    response = client.get(
        reverse("review-document-detail", args=[workspace.external_id, doc.id]),
    )
    assert response.status_code == 200
    assert response.json()["contributed_facts"] == []


@pytest.mark.django_db
def test_doc_detail_404_when_doc_not_in_queried_workspace() -> None:
    """Doc IDs must scope to the queried workspace.

    Pilot access model (web/api/access.py:team_workspaces) is
    intentionally team-shared — any advisor with PII access sees
    every active advisor's workspaces. So User A CAN see Workspace
    B. But the doc-detail endpoint must still scope the doc lookup
    to the workspace_id in the URL — passing an unrelated doc_id
    must 404, not leak data from the foreign workspace via the
    ReviewDocument query bypass.
    """
    user_a = _user("a@example.com")
    user_b = _user("b@example.com")
    client = APIClient()
    client.force_authenticate(user=user_a)
    workspace_a = models.ReviewWorkspace.objects.create(label="A", owner=user_a)
    workspace_b = models.ReviewWorkspace.objects.create(label="B", owner=user_b)
    doc_b = _doc(workspace_b)

    # User A querying workspace_a but doc_b's id → 404 because doc_b
    # is not in workspace_a's documents.
    response = client.get(
        reverse("review-document-detail", args=[workspace_a.external_id, doc_b.id]),
    )
    assert response.status_code == 404

    # User A querying workspace_b directly with doc_b's id → 200.
    # This is the team-shared access model. If we ever tighten to
    # owner-only access, this test changes shape but the doc-detail
    # endpoint shouldn't bypass it.
    response = client.get(
        reverse("review-document-detail", args=[workspace_b.external_id, doc_b.id]),
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_doc_detail_unauthenticated_returns_403() -> None:
    workspace = models.ReviewWorkspace.objects.create(
        label="WS",
        owner=_user(),
    )
    doc = _doc(workspace)
    client = APIClient()
    response = client.get(
        reverse("review-document-detail", args=[workspace.external_id, doc.id]),
    )
    # IsAuthenticated → 403 from DRF default.
    assert response.status_code in {401, 403}
