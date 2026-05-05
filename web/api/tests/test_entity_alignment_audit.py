"""Hypothesis property test: P1.1 `entities_reconciled` audit metadata
contains no PII / fact-text / account-number patterns regardless of
the random fact payload that flows through reconcile_workspace.

Mirrors the sister-locked invariant pattern from
`web/api/tests/test_status_audit_invariants.py` (sister §3.18:
max_examples=10, deadline=None, suppress_health_check=[
function_scoped_fixture, too_slow]).

Real-PII discipline (canon §11.8.3): the `entities_reconciled` audit
metadata MUST contain only counts + UUIDs + reason codes — never raw
display names, account numbers, DOBs, or any string lifted from the
incoming fact payload.
"""

from __future__ import annotations

import json
import re
import uuid

import pytest
from django.contrib.auth import get_user_model
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from web.api import models
from web.api.review_processing import reconcile_workspace
from web.audit.models import AuditEvent

User = get_user_model()


# Reused PII grep heuristics (sister pattern): SIN format + 10+ contiguous
# digits flag potential leakage of identity / account numbers.
_SIN_PATTERN = re.compile(r"\b\d{3}[-\s]?\d{3}[-\s]?\d{3}\b")
_LONG_DIGIT_PATTERN = re.compile(r"\b\d{10,}\b")


@pytest.fixture
def review_workspace_factory(transactional_db):
    """Factory yielding a fresh ReviewWorkspace + ReviewDocument per
    Hypothesis example. AuditEvent rows are immutable (Postgres
    trigger), so we ALSO scope every audit lookup by the workspace's
    UUID `external_id` to keep cross-example isolation."""

    def _make() -> tuple[models.ReviewWorkspace, models.ReviewDocument]:
        user, _ = User.objects.get_or_create(
            username=f"entity_alignment_audit_{uuid.uuid4().hex[:8]}@example.com",
            defaults={
                "email": f"entity_alignment_audit_{uuid.uuid4().hex[:8]}@example.com",
            },
        )
        workspace = models.ReviewWorkspace.objects.create(
            label="Audit invariant workspace",
            owner=user,
            data_origin=models.ReviewWorkspace.DataOrigin.SYNTHETIC,
            status=models.ReviewWorkspace.Status.REVIEW_READY,
        )
        document = models.ReviewDocument.objects.create(
            workspace=workspace,
            original_filename="audit_invariant.pdf",
            sha256=uuid.uuid4().hex + uuid.uuid4().hex,
            document_type="kyc",
            status=models.ReviewDocument.Status.FACTS_EXTRACTED,
        )
        return workspace, document

    return _make


@pytest.mark.django_db(transaction=True)
@given(
    # ASCII letters + space only for `name_payload` — distinct from
    # the legitimate UUID hex content of `source_workspace_id` so a
    # pure substring assertion is sound. Real-PII names ARE letter-
    # space dominant; this is the actual leakage class we're guarding.
    name_payload=st.text(
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll"),
            whitelist_characters=" -",
        ),
        min_size=5,
        max_size=80,
    ),
    # Account numbers are long digit strings; minimum 10 ensures the
    # `_LONG_DIGIT_PATTERN` regex would fire on a leak.
    account_number_payload=st.text(
        alphabet=st.characters(whitelist_categories=("Nd",)),
        min_size=10,
        max_size=16,
    ),
)
@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)
def test_entities_reconciled_audit_metadata_no_pii(
    review_workspace_factory, name_payload, account_number_payload
) -> None:
    # Fresh workspace per example -> cross-example isolation without
    # mutating the immutable audit table.
    workspace, document = review_workspace_factory()

    # Inject Hypothesis payloads as fact VALUES — these MUST NOT leak
    # into audit metadata.
    extraction_run_id = f"hypo-{uuid.uuid4().hex[:8]}"
    models.ExtractedFact.objects.create(
        workspace=workspace,
        document=document,
        field="people[0].display_name",
        value=name_payload,
        confidence="high",
        derivation_method="extracted",
        evidence_quote="",
        extraction_run_id=extraction_run_id,
    )
    models.ExtractedFact.objects.create(
        workspace=workspace,
        document=document,
        field="accounts[0].account_number",
        value=account_number_payload,
        confidence="high",
        derivation_method="extracted",
        evidence_quote="",
        extraction_run_id=extraction_run_id,
    )

    reconcile_workspace(workspace)

    audit = (
        AuditEvent.objects.filter(
            action="entities_reconciled", entity_id=str(workspace.external_id)
        )
        .order_by("-created_at")
        .first()
    )
    assert audit is not None, "P1.1 reconcile must emit `entities_reconciled` audit row"

    # Scan only the NON-source_workspace_id payload — the UUID we
    # legitimately emit will of course appear once, and Hypothesis
    # could generate digit-prefix names that incidentally substring
    # against the hex UUID. We strip that single field from scan scope
    # to keep the leak detector focused on actual PII vectors.
    leakage_scope = {k: v for k, v in audit.metadata.items() if k != "source_workspace_id"}
    metadata_json = json.dumps(leakage_scope, default=str)

    # Hypothesis-injected values MUST NOT appear in audit metadata
    # outside the source_workspace_id field.
    assert name_payload not in metadata_json, (
        f"Name payload {name_payload!r} leaked into audit metadata: {metadata_json!r}"
    )
    assert account_number_payload not in metadata_json, (
        f"Account-number payload {account_number_payload!r} leaked: {metadata_json!r}"
    )

    # Generic PII heuristics (sister pattern).
    assert not _SIN_PATTERN.search(metadata_json), (
        f"SIN-pattern leaked into audit metadata: {metadata_json!r}"
    )
    assert not _LONG_DIGIT_PATTERN.search(metadata_json), (
        f"Long-digit (potential account-number) pattern leaked: {metadata_json!r}"
    )

    # Locked schema fields (P1.1 §A1.23) MUST be present.
    assert "old_canonical_count" in audit.metadata
    assert "new_canonical_count" in audit.metadata
    assert "source_workspace_id" in audit.metadata
    assert "prompt_version" in audit.metadata
    # prompt_version is the suffix only — counts + UUID + version string only.
    assert audit.metadata["prompt_version"] == "v4_tooluse_entity_aligned"
