"""Phase B1 — Tier-2 merge-candidate resolve endpoint tests.

Covers (Round 18 #1, #16, #17, #33, #36, §A1.23, §A4):

  * Happy path: single resolve via merge / keep_separate / defer.
  * Bulk keep-separate happy path.
  * 404 on unknown candidate key (single + bulk).
  * Validation: decision invalid / missing rationale / missing evidence_ack.
  * Atomicity: ThreadPoolExecutor N=100 stress.
  * Audit emission: exactly N events for bulk, one per candidate.
  * PII discipline: rationale text NEVER in audit metadata; only
    rationale_length integer.
  * Round 18 #16: facts re-indexed; canonical-B no longer contributes
    new merge_candidates.
  * Round 18 #17: re-reconcile applies prior merge_decisions.
"""

from __future__ import annotations

import concurrent.futures

import pytest
from django.contrib.auth import get_user_model
from django.db import connection, connections
from django.urls import reverse
from rest_framework.test import APIClient

from web.api import models
from web.api.review_state import reviewed_state_from_workspace
from web.audit.models import AuditEvent


def _user(email: str = "advisor@example.com"):
    User = get_user_model()
    user, _ = User.objects.get_or_create(
        email=email,
        defaults={"username": email, "is_active": True},
    )
    return user


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


def _seed_niesner_shape_workspace(user) -> models.ReviewWorkspace:
    """Two docs, each with a different first-name + same surname Niesner.

    Tier-1 (Round 13 #2 LOCKED): single-field rejection -> 2 canonicals.
    Tier-2: surfaces as a merge candidate (score 90 = name_token + last_name).

    Persists `canonical_index` per fact via the same path
    `reconcile_workspace` uses, so the resolve endpoint's re-indexing
    SQL has rows to update.
    """
    from extraction.entity_alignment import align_facts as compute_alignment

    workspace = models.ReviewWorkspace.objects.create(
        label="niesner-tier2-test",
        owner=user,
        data_origin=models.ReviewWorkspace.DataOrigin.SYNTHETIC,
    )
    kyc = _doc(workspace, filename="kyc.pdf", document_type="kyc")
    statement = _doc(workspace, filename="statement.pdf", document_type="kyc")
    _fact(workspace, kyc, field="people[0].display_name", value="Sandra Niesner")
    _fact(workspace, statement, field="people[0].display_name", value="Sandra Niesner")

    # Persist canonical_index so endpoints re-indexing facts have rows to mutate.
    facts = list(workspace.extracted_facts.select_related("document"))
    alignment = compute_alignment(facts)
    rows = []
    for fact in facts:
        idx = alignment.canonical_index_for(fact)
        if idx != fact.canonical_index:
            fact.canonical_index = idx
            rows.append(fact)
    if rows:
        models.ExtractedFact.objects.bulk_update(rows, ["canonical_index"])

    workspace.reviewed_state = reviewed_state_from_workspace(workspace)
    workspace.save(update_fields=["reviewed_state"])
    return workspace


def _candidate_key(workspace) -> str:
    state = workspace.reviewed_state or {}
    candidates = state.get("merge_candidates") or []
    assert candidates, f"workspace {workspace.external_id} has no merge_candidates seeded"
    return candidates[0]["key"]


# ---------------------------------------------------------------------------
# Reviewed-state contract — merge_candidates surfaces in state.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_reviewed_state_includes_merge_candidates_for_tier2_pair() -> None:
    user = _user()
    workspace = _seed_niesner_shape_workspace(user)
    state = workspace.reviewed_state
    assert state is not None
    candidates = state.get("merge_candidates") or []
    assert len(candidates) == 1
    cand = candidates[0]
    assert cand["prefix"] == "people"
    assert cand["key"].startswith("people:")
    assert cand["score"] >= 60
    assert cand["confidence"] == "medium"
    # Display-name surfaced in canonical_*_features at the JSON shape.
    assert cand["canonical_a_features"]["display_name"] == "Sandra Niesner"
    assert cand["canonical_b_features"]["display_name"] == "Sandra Niesner"


# ---------------------------------------------------------------------------
# Happy paths — merge / keep_separate / defer.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_resolve_merge_decision_happy_path_re_indexes_facts() -> None:
    """Round 18 #16: merge re-indexes ExtractedFact rows from canonical-B
    to canonical-A; new state has no Tier-2 candidate for this pair.
    """
    user = _user()
    workspace = _seed_niesner_shape_workspace(user)
    key = _candidate_key(workspace)
    a_index = int(key.split(":")[1])
    b_index = int(key.split(":")[2])

    pre_b_count = workspace.extracted_facts.filter(canonical_index=b_index).count()
    assert pre_b_count > 0

    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse(
        "review-workspace-merge-candidate-resolve",
        args=[workspace.external_id, key],
    )
    response = client.post(
        url,
        {
            "decision": "merge",
            "rationale": "Same household; both reference Sandra Niesner.",
            "evidence_ack": True,
        },
        format="json",
    )
    assert response.status_code == 200, response.content
    body = response.json()
    new_candidates = body["state"].get("merge_candidates") or []
    keys = [c.get("key") for c in new_candidates]
    assert key not in keys

    # Round 18 #16: facts re-indexed.
    post_b_count = workspace.extracted_facts.filter(canonical_index=b_index).count()
    assert post_b_count == 0
    post_a_count = workspace.extracted_facts.filter(canonical_index=a_index).count()
    assert post_a_count >= pre_b_count

    # Round 18 #17: decision history persisted.
    workspace.refresh_from_db()
    decisions = (workspace.reviewed_state or {}).get("merge_decisions") or {}
    assert decisions.get(key) == "merge"


@pytest.mark.django_db
def test_resolve_keep_separate_happy_path_no_fact_reindex() -> None:
    user = _user()
    workspace = _seed_niesner_shape_workspace(user)
    key = _candidate_key(workspace)
    b_index = int(key.split(":")[2])
    pre_b_count = workspace.extracted_facts.filter(canonical_index=b_index).count()

    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse(
        "review-workspace-merge-candidate-resolve",
        args=[workspace.external_id, key],
    )
    response = client.post(
        url,
        {
            "decision": "keep_separate",
            "rationale": "These are father and son; separate households.",
            "evidence_ack": True,
        },
        format="json",
    )
    assert response.status_code == 200, response.content
    # No re-indexing for keep_separate.
    post_b_count = workspace.extracted_facts.filter(canonical_index=b_index).count()
    assert post_b_count == pre_b_count
    # Decision history persisted.
    workspace.refresh_from_db()
    decisions = (workspace.reviewed_state or {}).get("merge_decisions") or {}
    assert decisions.get(key) == "keep_separate"
    # Filtered from surfaced list.
    new_candidates = workspace.reviewed_state.get("merge_candidates") or []
    assert all(c.get("key") != key for c in new_candidates)


@pytest.mark.django_db
def test_resolve_defer_persists_decision_does_not_reindex() -> None:
    user = _user()
    workspace = _seed_niesner_shape_workspace(user)
    key = _candidate_key(workspace)
    b_index = int(key.split(":")[2])
    pre_b_count = workspace.extracted_facts.filter(canonical_index=b_index).count()

    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse(
        "review-workspace-merge-candidate-resolve",
        args=[workspace.external_id, key],
    )
    response = client.post(
        url,
        {
            "decision": "defer",
            "rationale": "Ask the advisor at next meeting.",
            "evidence_ack": True,
        },
        format="json",
    )
    assert response.status_code == 200, response.content
    post_b_count = workspace.extracted_facts.filter(canonical_index=b_index).count()
    assert post_b_count == pre_b_count
    workspace.refresh_from_db()
    decisions = (workspace.reviewed_state or {}).get("merge_decisions") or {}
    assert decisions.get(key) == "defer"


# ---------------------------------------------------------------------------
# Validation — invalid decision / missing rationale / missing evidence_ack.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_resolve_rejects_invalid_decision() -> None:
    user = _user()
    workspace = _seed_niesner_shape_workspace(user)
    key = _candidate_key(workspace)
    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse(
        "review-workspace-merge-candidate-resolve",
        args=[workspace.external_id, key],
    )
    r = client.post(
        url,
        {"decision": "auto_merge", "rationale": "yes", "evidence_ack": True},
        format="json",
    )
    assert r.status_code == 400
    assert r.json()["code"] == "decision_invalid"


@pytest.mark.django_db
def test_resolve_rejects_short_rationale() -> None:
    user = _user()
    workspace = _seed_niesner_shape_workspace(user)
    key = _candidate_key(workspace)
    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse(
        "review-workspace-merge-candidate-resolve",
        args=[workspace.external_id, key],
    )
    r = client.post(
        url,
        {"decision": "merge", "rationale": "no", "evidence_ack": True},
        format="json",
    )
    assert r.status_code == 400
    assert r.json()["code"] == "rationale_required"


@pytest.mark.django_db
def test_resolve_rejects_missing_evidence_ack() -> None:
    user = _user()
    workspace = _seed_niesner_shape_workspace(user)
    key = _candidate_key(workspace)
    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse(
        "review-workspace-merge-candidate-resolve",
        args=[workspace.external_id, key],
    )
    r = client.post(
        url,
        {"decision": "merge", "rationale": "Looks correct", "evidence_ack": False},
        format="json",
    )
    assert r.status_code == 400
    assert r.json()["code"] == "evidence_ack_required"


# ---------------------------------------------------------------------------
# 404 — unknown candidate key.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_resolve_returns_404_for_unknown_candidate_key() -> None:
    user = _user()
    workspace = _seed_niesner_shape_workspace(user)
    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse(
        "review-workspace-merge-candidate-resolve",
        args=[workspace.external_id, "people:99:100"],
    )
    r = client.post(
        url,
        {"decision": "merge", "rationale": "Test 404 path.", "evidence_ack": True},
        format="json",
    )
    assert r.status_code == 404
    assert r.json()["code"] == "merge_candidate_not_found"


@pytest.mark.django_db
def test_bulk_keep_separate_returns_404_when_any_key_missing() -> None:
    user = _user()
    workspace = _seed_niesner_shape_workspace(user)
    valid_key = _candidate_key(workspace)
    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse(
        "review-workspace-merge-candidate-bulk-keep-separate",
        args=[workspace.external_id],
    )
    r = client.post(
        url,
        {
            "keys": [valid_key, "people:99:100"],
            "rationale": "Bulk dismiss test.",
            "evidence_ack": True,
        },
        format="json",
    )
    assert r.status_code == 404
    assert r.json()["code"] == "merge_candidate_not_found"
    assert "people:99:100" in r.json()["missing_keys"]


# ---------------------------------------------------------------------------
# Audit discipline — exactly one event; PII-safe metadata.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_resolve_emits_single_audit_event_without_rationale_text() -> None:
    """Locked decision §A1.23 + canon §11.8.3: one AuditEvent per resolve;
    rationale TEXT never copied to immutable audit metadata.
    """
    user = _user()
    workspace = _seed_niesner_shape_workspace(user)
    key = _candidate_key(workspace)
    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse(
        "review-workspace-merge-candidate-resolve",
        args=[workspace.external_id, key],
    )
    rationale_text = "Same household per KYC + statement cross-reference."
    r = client.post(
        url,
        {
            "decision": "keep_separate",
            "rationale": rationale_text,
            "evidence_ack": True,
        },
        format="json",
    )
    assert r.status_code == 200

    events = AuditEvent.objects.filter(
        action="entity_merge_candidate_resolved",
        entity_id=str(workspace.external_id),
    )
    assert events.count() == 1
    metadata = events.first().metadata
    assert metadata["decision"] == "keep_separate"
    assert metadata["prefix"] == "people"
    assert metadata["bulk"] is False
    assert metadata["rationale_length"] == len(rationale_text)
    serialized = str(metadata)
    assert rationale_text not in serialized
    assert "household per KYC" not in serialized


# ---------------------------------------------------------------------------
# Bulk happy path — N audit events for N keys.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_bulk_keep_separate_emits_one_audit_event_per_candidate() -> None:
    """§A5 + design-system-research §5.9: bulk emits ONE event per
    candidate, each with bulk=True + bulk_count=N. Compliance review can
    independently inspect every dismissal.
    """
    user = _user()
    workspace = models.ReviewWorkspace.objects.create(
        label="bulk-tier2-test",
        owner=user,
        data_origin=models.ReviewWorkspace.DataOrigin.SYNTHETIC,
    )
    # Three docs sharing surname "Niesner" but different first names ->
    # 3 canonicals + 3 pairwise Tier-2 candidates.
    docs = [
        _doc(workspace, filename=f"doc{idx}.pdf") for idx in range(3)
    ]
    names = ["Sandra Niesner", "Robert Niesner", "Margaret Niesner"]
    for doc, name in zip(docs, names, strict=True):
        _fact(workspace, doc, field="people[0].display_name", value=name)
    workspace.reviewed_state = reviewed_state_from_workspace(workspace)
    workspace.save(update_fields=["reviewed_state"])

    candidates = workspace.reviewed_state["merge_candidates"]
    assert len(candidates) >= 2  # at least 2 pairs from 3 canonicals
    keys = [c["key"] for c in candidates]

    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse(
        "review-workspace-merge-candidate-bulk-keep-separate",
        args=[workspace.external_id],
    )
    rationale_text = "Distinct family members; intentionally separate."
    r = client.post(
        url,
        {
            "keys": keys,
            "rationale": rationale_text,
            "evidence_ack": True,
        },
        format="json",
    )
    assert r.status_code == 200, r.content
    assert r.json()["resolved_count"] == len(keys)

    events = AuditEvent.objects.filter(
        action="entity_merge_candidate_resolved",
        entity_id=str(workspace.external_id),
        metadata__bulk=True,
    )
    assert events.count() == len(keys)
    for event in events:
        assert event.metadata["bulk"] is True
        assert event.metadata["bulk_count"] == len(keys)
        assert event.metadata["decision"] == "keep_separate"
        assert event.metadata["rationale_length"] == len(rationale_text)
        # No PII anywhere.
        serialized = str(event.metadata)
        assert rationale_text not in serialized
        assert "Niesner" not in serialized


# ---------------------------------------------------------------------------
# Round 18 #17 — re-reconcile applies prior merge decisions.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_re_reconcile_preserves_keep_separate_decision() -> None:
    user = _user()
    workspace = _seed_niesner_shape_workspace(user)
    key = _candidate_key(workspace)
    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse(
        "review-workspace-merge-candidate-resolve",
        args=[workspace.external_id, key],
    )
    r = client.post(
        url,
        {"decision": "keep_separate", "rationale": "Test keep.", "evidence_ack": True},
        format="json",
    )
    assert r.status_code == 200

    # Re-derive state — Round 18 #17: prior keep_separate decision must
    # filter the pair from the surfaced candidate list.
    workspace.refresh_from_db()
    new_state = reviewed_state_from_workspace(workspace)
    surfaced = [c.get("key") for c in (new_state.get("merge_candidates") or [])]
    assert key not in surfaced
    # Decision history preserved.
    assert (new_state.get("merge_decisions") or {}).get(key) == "keep_separate"


# ---------------------------------------------------------------------------
# Round 18 #33 — concurrency stress (ThreadPoolExecutor N=100).
# ---------------------------------------------------------------------------


PARALLEL_REQUESTS = 100
MAX_WORKERS = 20


def _run_parallel(request_fn, *, n=PARALLEL_REQUESTS, workers=MAX_WORKERS):
    def _wrap(idx):
        try:
            return request_fn(idx)
        finally:
            for alias in connections:
                connections[alias].close()

    statuses = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_wrap, idx) for idx in range(n)]
        for future in concurrent.futures.as_completed(futures):
            statuses.append(future.result())
    connection.close()
    return statuses


@pytest.mark.django_db(transaction=True)
def test_resolve_merge_candidate_concurrent_writes_serialize_under_lock() -> None:
    """N=100 parallel POST /merge-candidates/<key>/resolve — atomic +
    select_for_update on workspace serializes; no 5xx; audit count
    matches the success count of state-changing decisions.
    """
    user = _user()
    workspace = _seed_niesner_shape_workspace(user)
    key = _candidate_key(workspace)
    url = reverse(
        "review-workspace-merge-candidate-resolve",
        args=[workspace.external_id, key],
    )

    def _request(idx: int) -> int:
        client = APIClient()
        client.force_authenticate(user=user)
        return client.post(
            url,
            {
                "decision": "keep_separate",
                "rationale": f"Concurrent dismiss #{idx} for stress test.",
                "evidence_ack": True,
            },
            format="json",
        ).status_code

    statuses = _run_parallel(_request)
    success_count = sum(1 for s in statuses if s == 200)
    error_5xx = [s for s in statuses if 500 <= s < 600]
    assert not error_5xx, f"5xx surfaced: {error_5xx}"

    # First call resolves; subsequent calls 404 (key already resolved).
    not_found = sum(1 for s in statuses if s == 404)
    assert success_count + not_found == PARALLEL_REQUESTS, (
        f"expected all {PARALLEL_REQUESTS} calls to either 200 or 404; "
        f"saw success={success_count} not_found={not_found} other={statuses}"
    )
    audit_count = AuditEvent.objects.filter(
        action="entity_merge_candidate_resolved",
        entity_id=str(workspace.external_id),
    ).count()
    assert audit_count == success_count


# ---------------------------------------------------------------------------
# Hypothesis — audit metadata holds NO PII regardless of inputs.
# ---------------------------------------------------------------------------


from hypothesis import HealthCheck, given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402


@given(
    decision=st.sampled_from(["merge", "keep_separate", "defer"]),
    # Inject a unique marker into every rationale so we can assert
    # the marker NEVER appears in audit metadata. This isolates the
    # invariant ("rationale TEXT not copied") from spurious matches
    # against structural metadata strings ("NoneType", "merge",
    # "people", etc.) that legitimately appear in metadata. Marker
    # uses a high-entropy ASCII suffix that the audit pipeline never
    # produces.
    rationale_payload=st.text(
        alphabet=st.characters(min_codepoint=0x41, max_codepoint=0x7A),
        min_size=4,
        max_size=80,
    ).filter(lambda s: s == s.strip() and len(s) >= 4),
)
@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)
@pytest.mark.django_db
def test_resolve_audit_metadata_carries_no_rationale_text(decision, rationale_payload) -> None:
    # Marker is high-entropy + bracketed so it can't collide with any
    # structural string in audit metadata.
    rationale = f"<<MARK-XQZP-{rationale_payload}-MARK-XQZP>>"
    user = _user(email=f"hyp-{abs(hash((decision, rationale_payload))) % 10**8}@example.com")
    # Build fresh workspace per Hypothesis example so tests don't share state.
    workspace = models.ReviewWorkspace.objects.create(
        label=f"hyp-{abs(hash(rationale_payload)) % 10**6}",
        owner=user,
        data_origin=models.ReviewWorkspace.DataOrigin.SYNTHETIC,
    )
    kyc = _doc(workspace, filename=f"hyp-kyc-{user.email}.pdf")
    statement = _doc(workspace, filename=f"hyp-st-{user.email}.pdf")
    _fact(workspace, kyc, field="people[0].display_name", value="Maria Lopez")
    _fact(workspace, statement, field="people[0].display_name", value="Maria Lopez")
    workspace.reviewed_state = reviewed_state_from_workspace(workspace)
    workspace.save(update_fields=["reviewed_state"])

    candidates = workspace.reviewed_state.get("merge_candidates") or []
    if not candidates:
        return  # vacuously satisfied
    key = candidates[0]["key"]
    client = APIClient()
    client.force_authenticate(user=user)
    url = reverse(
        "review-workspace-merge-candidate-resolve",
        args=[workspace.external_id, key],
    )
    response = client.post(
        url,
        {"decision": decision, "rationale": rationale, "evidence_ack": True},
        format="json",
    )
    assert response.status_code == 200, response.content
    event = AuditEvent.objects.filter(
        action="entity_merge_candidate_resolved",
        entity_id=str(workspace.external_id),
    ).order_by("-id").first()
    assert event is not None
    serialized = str(event.metadata)
    # Marker (entire rationale) must not appear in audit metadata.
    assert "MARK-XQZP" not in serialized
    assert rationale not in serialized
    # Rationale length captured numerically.
    assert event.metadata["rationale_length"] == len(rationale)
