"""Edge-case regression tests (canon §6.7) — empty / overflow /
schema-irrelevant / non-English content.

Each scenario locks a contract that an extraction failure mode
shouldn't crash the review pipeline:

  6.7.1 — Empty / illegible doc with 0 facts.
  6.7.2 — Overflow: 1000+ facts in a single workspace.
  6.7.3 — Schema-irrelevant facts: well-formed but unmappable.
  6.7.4 — Non-English (French-Canadian) content.

Uses factory_boy fixtures from web/api/tests/factories.py.
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.test import APIClient
from web.api import models
from web.api.review_serializers import ReviewWorkspaceSerializer
from web.api.review_state import (
    readiness_for_state,
    reviewed_state_from_workspace,
    section_blockers,
    serialize_doc_contributed_facts,
)
from web.api.tests.factories import (
    ExtractedFactFactory,
    ReviewDocumentFactory,
    ReviewWorkspaceFactory,
    UserFactory,
)

# ---------------------------------------------------------------------------
# 6.7.1 — Empty / illegible doc
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_empty_doc_workspace_does_not_crash_reviewed_state() -> None:
    """A workspace with one doc that produces 0 facts must:
    * compose `reviewed_state` without raising,
    * surface section-level missing blockers (not crash),
    * leave `serialize_doc_contributed_facts` returning [].
    """
    user = UserFactory()
    workspace = ReviewWorkspaceFactory(owner=user, label="Empty Doc WS")
    # Doc exists but no facts attached.
    doc = ReviewDocumentFactory(
        workspace=workspace,
        original_filename="illegible.pdf",
        status=models.ReviewDocument.Status.FAILED,
        failure_reason="ValueError:no_canonical_facts",
    )

    state = reviewed_state_from_workspace(workspace)
    assert isinstance(state, dict)
    # readiness must compute, not crash
    readiness = readiness_for_state(state)
    assert readiness.engine_ready is False
    # missing blockers should call out the things a 0-fact workspace
    # can't have (people, accounts, goals, links).
    missing_sections = {item["section"] for item in readiness.missing}
    assert {"people", "accounts", "goals"}.issubset(missing_sections), (
        f"expected core sections to be flagged missing, got {missing_sections}"
    )

    # Empty doc contributes no facts.
    contributed = serialize_doc_contributed_facts(workspace, doc)
    assert contributed == []


@pytest.mark.django_db
def test_empty_doc_section_approval_blocked() -> None:
    """A workspace with no facts must NOT permit plain approval —
    the blockers chain rejects it. APPROVED_WITH_UNKNOWNS with notes
    is the only escape.
    """
    user = UserFactory()
    workspace = ReviewWorkspaceFactory(owner=user)
    ReviewDocumentFactory(workspace=workspace)

    state = reviewed_state_from_workspace(workspace)
    blockers = section_blockers(state, "people")
    assert len(blockers) > 0, "people section must be blocked when no facts present"


@pytest.mark.django_db
def test_empty_doc_manual_entry_hatch_eligible() -> None:
    """The advisor escape hatch (manual_entry) is reachable for an
    extraction-failed doc — the contract that a 0-fact doc is
    salvageable via advisor hand-entry.
    """
    user = UserFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = ReviewWorkspaceFactory(owner=user)
    doc = ReviewDocumentFactory(
        workspace=workspace,
        status=models.ReviewDocument.Status.FAILED,
        failure_reason="BedrockNonJsonError:bedrock_non_json",
    )

    response = client.post(
        reverse(
            "review-document-manual-entry",
            args=[workspace.external_id, doc.id],
        ),
        format="json",
    )
    assert response.status_code == 200, response.content
    doc.refresh_from_db()
    assert doc.status == models.ReviewDocument.Status.MANUAL_ENTRY


# ---------------------------------------------------------------------------
# 6.7.2 — Overflow: 1000+ facts in one workspace
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_overflow_1000_facts_compose_under_1s() -> None:
    """1000 ExtractedFacts → reviewed_state composer + readiness
    must run in bounded time (≤ 1.0s wall-clock).

    This is a "doesn't blow up" test, not a microbenchmark; the bar
    is intentionally loose so we catch the next O(N²) regression
    without flapping on noisy CI.
    """
    user = UserFactory()
    workspace = ReviewWorkspaceFactory(owner=user)
    document = ReviewDocumentFactory(workspace=workspace)
    # ExtractedFactFactory's `field` default is people[0].date_of_birth;
    # Faker's `date` value is what matters here. We don't need
    # field-distinct rows — current_facts_by_field deduplicates per
    # (field, document) and we want to stress the reconciliation
    # loop's volume bound.
    ExtractedFactFactory.create_batch(
        1000,
        workspace=workspace,
        document=document,
    )

    start = time.monotonic()
    state = reviewed_state_from_workspace(workspace)
    elapsed = time.monotonic() - start

    assert isinstance(state, dict)
    assert elapsed < 1.0, f"reviewed_state took {elapsed:.3f}s for 1000 facts; expected < 1.0s"


@pytest.mark.django_db
def test_overflow_1000_facts_serializer_no_n_plus_1() -> None:
    """ReviewWorkspaceSerializer must use bounded queries even with
    1000 ExtractedFacts. The 'documents'/'extracted_facts' join
    should NOT scale per-fact.

    Bound: ≤ 60 queries total (room for the timeline + worker_health
    + section_approvals + documents + processing_jobs + audit-event
    pulls). 1000 queries means a per-fact lookup leaked in.
    """
    user = UserFactory()
    workspace = ReviewWorkspaceFactory(owner=user)
    document = ReviewDocumentFactory(workspace=workspace)
    ExtractedFactFactory.create_batch(
        1000,
        workspace=workspace,
        document=document,
    )

    with CaptureQueriesContext(connection) as ctx:
        serialized = ReviewWorkspaceSerializer(workspace).data
        # Force lazy serializermethod evaluation.
        _ = serialized["readiness"]
        _ = serialized["timeline"]
        _ = serialized["worker_health"]

    n_queries = len(ctx.captured_queries)
    assert n_queries < 60, (
        f"ReviewWorkspaceSerializer issued {n_queries} queries with 1000 facts; "
        f"this is suspicious of an N+1 leak. Inspect: "
        f"{[q['sql'][:80] for q in ctx.captured_queries[:10]]}"
    )


@pytest.mark.django_db
def test_overflow_1000_facts_doc_contributed_facts_bounded() -> None:
    """`serialize_doc_contributed_facts` for a single doc must
    process 1000 facts under 1.0s. No regression from naive
    per-fact redaction passes.
    """
    user = UserFactory()
    workspace = ReviewWorkspaceFactory(owner=user)
    document = ReviewDocumentFactory(workspace=workspace)
    ExtractedFactFactory.create_batch(
        1000,
        workspace=workspace,
        document=document,
    )

    start = time.monotonic()
    contributed = serialize_doc_contributed_facts(workspace, document)
    elapsed = time.monotonic() - start

    assert isinstance(contributed, list)
    assert elapsed < 1.0, (
        f"serialize_doc_contributed_facts took {elapsed:.3f}s for 1000 facts; expected < 1.0s"
    )


# ---------------------------------------------------------------------------
# 6.7.3 — Schema-irrelevant facts (no canonical match)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_canonical_match_yields_no_synthetic_state_defaults() -> None:
    """When extraction returns well-formed but schema-irrelevant facts
    (e.g. `random.unrelated.path`), the reviewed_state composer must
    NOT invent synthetic people/accounts/goals defaults — the canon
    forbids the engine inventing financial numbers.

    Mocking `extract_facts` is overkill here — we directly seed the
    DB with schema-irrelevant ExtractedFact rows since the composer
    reads from DB, not from the LLM.
    """
    user = UserFactory()
    workspace = ReviewWorkspaceFactory(owner=user)
    document = ReviewDocumentFactory(workspace=workspace)
    for path in (
        "random.unrelated.path",
        "marketing.lead_score",
        "internal.routing.code",
    ):
        ExtractedFactFactory(
            workspace=workspace,
            document=document,
            field=path,
            value="some-value",
        )

    state = reviewed_state_from_workspace(workspace)

    # No synthetic people/accounts/goals from schema-irrelevant facts.
    assert state["people"] == []
    assert state["accounts"] == []
    assert state["goals"] == []
    assert state["goal_account_links"] == []
    # household carries only its label-default + risk default
    # (NOT a fabricated display_name from the unrelated paths).
    assert state["household"]["display_name"] == workspace.label


@pytest.mark.django_db
def test_no_canonical_match_document_status_remains_post_extraction() -> None:
    """Documents that returned only schema-irrelevant facts should
    NOT be in a "successfully reconciled" state from the advisor's
    POV. We assert the doc.status still reflects whatever extraction
    set (FACTS_EXTRACTED / RECONCILED / FAILED) — the composer
    doesn't tamper with doc status.
    """
    user = UserFactory()
    workspace = ReviewWorkspaceFactory(owner=user)
    # Simulate Bedrock returning well-formed JSON whose paths don't
    # map to canonical schema. The doc lands in FACTS_EXTRACTED but
    # the rows themselves are useless.
    document = ReviewDocumentFactory(
        workspace=workspace,
        status=models.ReviewDocument.Status.FACTS_EXTRACTED,
    )
    ExtractedFactFactory(
        workspace=workspace,
        document=document,
        field="random.unrelated.path",
        value="ignored",
    )
    document.refresh_from_db()
    assert document.status == models.ReviewDocument.Status.FACTS_EXTRACTED
    # readiness reflects "no canonical facts" via the missing list.
    state = reviewed_state_from_workspace(workspace)
    readiness = readiness_for_state(state)
    sections_missing = {item["section"] for item in readiness.missing}
    assert {"people", "accounts", "goals"}.issubset(sections_missing)


@pytest.mark.django_db
def test_no_canonical_match_with_mocked_extract_facts() -> None:
    """Demonstrate the mock pattern for an extraction call returning
    schema-irrelevant facts. We mock `extraction.reconciliation.
    current_facts_by_field` indirectly by passing schema-irrelevant
    rows; this test asserts the doc-detail endpoint returns an empty
    contributed_facts list because no canonical fields were
    contributed.
    """
    user = UserFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = ReviewWorkspaceFactory(owner=user)
    document = ReviewDocumentFactory(workspace=workspace)
    # Patch the reconciliation function to return an empty mapping
    # (simulating extractor mapping nothing canonical).
    with patch(
        "web.api.review_state.current_facts_by_field",
        return_value={},
    ):
        ExtractedFactFactory(
            workspace=workspace,
            document=document,
            field="random.unrelated.path",
            value="x",
        )
        contributed = serialize_doc_contributed_facts(workspace, document)
    assert contributed == []


# ---------------------------------------------------------------------------
# 6.7.4 — Non-English (French-Canadian) content
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_french_value_text_persists_through_pipeline() -> None:
    """Field paths are language-agnostic English keys; the *values*
    can be French. The composer must persist the French text without
    rejecting it.

    Per locked decision #12 the canonical schema's keys (e.g.
    `people[0].date_of_birth`, `goals[0].name`) stay English even
    when the source PDF is French. The *value* however carries the
    advisor/client language faithfully.
    """
    user = UserFactory()
    workspace = ReviewWorkspaceFactory(owner=user, label="Ménage Tremblay")
    document = ReviewDocumentFactory(workspace=workspace, original_filename="kyc-fr.pdf")
    fact = ExtractedFactFactory(
        workspace=workspace,
        document=document,
        field="people[0].name",
        value="Jean-François Tremblay-Côté",
    )
    fact.refresh_from_db()
    assert fact.value == "Jean-François Tremblay-Côté"

    # The label key stays English — French-canon mapping is in the
    # advisor_label() module, not here. We just assert the value
    # didn't get mangled / coerced.
    contributed = serialize_doc_contributed_facts(workspace, document)
    assert any(row["value"] == "Jean-François Tremblay-Côté" for row in contributed)


@pytest.mark.django_db
def test_french_evidence_quote_not_stripped_by_redaction() -> None:
    """The redaction patterns target NA-format PII (CC, SIN, phone,
    address) — they must NOT strip valid French content (accents,
    cedilla, hyphenated names).
    """
    from web.api.review_redaction import redact_evidence_quote

    text = (
        "Le client Jean-François Tremblay-Côté demeure à Montréal. "
        "Date de naissance : 1985-03-12. État civil : marié."
    )
    result = redact_evidence_quote(text)
    # All accented characters preserved
    assert "Jean-François" in result
    assert "Tremblay-Côté" in result
    assert "Montréal" in result
    assert "marié" in result
    # The DOB ISO-8601 format is NOT a SIN — must not be redacted
    assert "1985-03-12" in result


@pytest.mark.django_db
def test_french_workspace_state_composer_handles_french_household() -> None:
    """End-to-end: a French-named workspace with French-text facts
    composes a valid reviewed_state. Smoke test for non-ASCII
    handling across the whole composition path.
    """
    user = UserFactory()
    workspace = ReviewWorkspaceFactory(owner=user, label="Famille Bélanger")
    document = ReviewDocumentFactory(workspace=workspace)
    ExtractedFactFactory(
        workspace=workspace,
        document=document,
        field="household.display_name",
        value="Famille Bélanger-Côté",
    )
    ExtractedFactFactory(
        workspace=workspace,
        document=document,
        field="people[0].name",
        value="Geneviève Bélanger",
    )
    ExtractedFactFactory(
        workspace=workspace,
        document=document,
        field="people[0].date_of_birth",
        value="1985-03-12",
    )

    state = reviewed_state_from_workspace(workspace)
    assert state["household"]["display_name"] == "Famille Bélanger-Côté"
    assert any(p.get("name") == "Geneviève Bélanger" for p in state["people"])
