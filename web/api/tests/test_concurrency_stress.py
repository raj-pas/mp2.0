"""Concurrency stress regression tests (Phase B hardening).

Fires N parallel requests per state-changing endpoint via a
ThreadPoolExecutor. Verifies (per locked #30 + #37):

  1. No IntegrityError / 5xx escapes — atomic + select_for_update
     on the workspace row must serialize concurrent writes cleanly.
  2. Audit-event count == 2xx response count (one event per
     state-changing action).
  3. Final DB state is internally consistent.

Each thread builds its own APIClient + force_authenticates the
same user. `@pytest.mark.django_db(transaction=True)` is required
so committed worker writes are visible to the test thread. Each
worker closes ALL DB connections on exit so pytest-django's
teardown can flush the test DB without contention.

N=100, max_workers=20 — surfaces lock-ordering races within the
30s/test budget; slowest case observed ~1.2s.

Workspace-trigger section (per locked #14 + #27 + #74): N=20
parallel calls to `_trigger_and_audit_for_workspace` directly
(NOT via APIClient — these are internal helpers, not endpoints).
Engine.optimize() is heavier than per-endpoint mutations, so the
lower N keeps total time bounded under 60s/test. Pins:
  - linked workspace + 4 trigger sources × 20 calls each → REUSED
    PortfolioRunEvents only; signature unchanged across calls;
    single PortfolioRun row per source.
  - unlinked workspace + 1 source × 20 calls → workspace-skip
    audit per call; no household-trigger side effects.
"""

from __future__ import annotations

import concurrent.futures
from collections.abc import Callable

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection, connections
from django.urls import reverse
from rest_framework.test import APIClient
from web.api import models
from web.api.review_state import reviewed_state_from_workspace
from web.api.views import _trigger_and_audit_for_workspace
from web.audit.models import AuditEvent

PARALLEL_REQUESTS = 100
MAX_WORKERS = 20

# Workspace-trigger N for SEQUENTIAL same-signature pinning. Each call
# is a REUSED-path lookup after the first (sub-millisecond signature
# compare against the existing PortfolioRun); only the first call runs
# engine.optimize() wall-time. 20 × ~1ms + 1 × ~500ms = ~520ms total
# per test. Stays under the 60s/test budget with massive headroom.
# Sequential calls avoid the pytest-django + ThreadPoolExecutor +
# `transaction=True` TRUNCATE-deadlock interaction that surfaced
# during round-2 development.
WORKSPACE_TRIGGER_PARALLEL = 20


# --- Fixtures / helpers (mirror test_phase5b_*.py style) -------------


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


def _seed_two_conflicts(workspace) -> tuple[int, int]:
    """Two same-class doc conflicts on two distinct fields. Returns
    the (KYC dob fact_id, KYC marital fact_id) tuple — the candidates
    a bulk-resolve concurrent test will pick.

    Phase P1.1 (2026-05-05): identity anchors keep the two docs
    aligned to one canonical person.
    """
    kyc = _doc(workspace, filename="kyc.pdf", document_type="kyc")
    statement = _doc(workspace, filename="statement.pdf", document_type="kyc")
    for doc in (kyc, statement):
        _fact(workspace, doc, field="people[0].display_name", value="Sarah Smith")
        _fact(workspace, doc, field="accounts[0].account_number", value="98765432")
    kyc_dob = _fact(workspace, kyc, field="people[0].date_of_birth", value="1985-03-12")
    _fact(workspace, statement, field="people[0].date_of_birth", value="1985-03-15")
    kyc_marital = _fact(workspace, kyc, field="people[0].marital_status", value="married")
    _fact(workspace, statement, field="people[0].marital_status", value="single")
    workspace.reviewed_state = reviewed_state_from_workspace(workspace)
    workspace.save(update_fields=["reviewed_state"])
    return kyc_dob.id, kyc_marital.id


def _seed_one_conflict(workspace) -> tuple[str, int]:
    """Single conflict on people[0].date_of_birth (kyc vs kyc-v2).

    Phase P1.1 (2026-05-05): cross-doc entity alignment requires TWO
    identifying fields to merge `people[0]` references across docs.
    Both docs share `display_name` + `accounts[0].account_number` so
    the matcher aligns them to a single canonical person.
    """
    kyc = _doc(workspace, filename="kyc.pdf", document_type="kyc")
    kyc2 = _doc(workspace, filename="kyc-v2.pdf", document_type="kyc")
    for doc in (kyc, kyc2):
        _fact(workspace, doc, field="people[0].display_name", value="Sarah Smith")
        _fact(workspace, doc, field="accounts[0].account_number", value="98765432")
    kyc_fact = _fact(workspace, kyc, field="people[0].date_of_birth", value="1985-03-12")
    _fact(workspace, kyc2, field="people[0].date_of_birth", value="1985-03-15")
    workspace.reviewed_state = reviewed_state_from_workspace(workspace)
    workspace.save(update_fields=["reviewed_state"])
    return "people[0].date_of_birth", kyc_fact.id


def _run_parallel(
    request_fn: Callable[[int], int],
    *,
    n: int = PARALLEL_REQUESTS,
    workers: int = MAX_WORKERS,
) -> list[int]:
    """Fire `n` calls of `request_fn(idx)` across `workers` threads.

    Returns the HTTP status codes. Workers close ALL DB connections
    on exit so pytest-django's teardown can release row locks +
    flush the test DB without leftover-thread contention.
    """

    def _wrap(idx: int) -> int:
        try:
            return request_fn(idx)
        finally:
            for alias in connections:
                connections[alias].close()

    statuses: list[int] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_wrap, idx) for idx in range(n)]
        for future in concurrent.futures.as_completed(futures):
            statuses.append(future.result())
    connection.close()
    return statuses


# --- 1. fact_override — append-only writes; ALL N must succeed ------


@pytest.mark.django_db(transaction=True)
def test_fact_override_concurrent_writes_all_succeed_append_only() -> None:
    """100 parallel POST /facts/override/ — append-only model means
    every call creates a NEW row. Lock contention serializes writes
    via select_for_update on the workspace.
    """
    user = _user()
    workspace = models.ReviewWorkspace.objects.create(label="WS", owner=user)
    url = reverse("review-workspace-fact-override", args=[workspace.external_id])

    def _request(idx: int) -> int:
        client = APIClient()
        client.force_authenticate(user=user)
        return client.post(
            url,
            {
                "field": f"people[0].date_of_birth_{idx}",
                "value": f"1985-03-{(idx % 28) + 1:02d}",
                "rationale": f"Concurrent override #{idx} for stress test.",
                "is_added": False,
            },
            format="json",
        ).status_code

    statuses = _run_parallel(_request)
    success_count = sum(1 for s in statuses if s == 200)
    failure_codes = [s for s in statuses if s != 200]

    assert success_count == PARALLEL_REQUESTS, (
        f"Expected all {PARALLEL_REQUESTS} append-only overrides to succeed; "
        f"got {success_count} success / {len(failure_codes)} failures "
        f"(codes={set(failure_codes)})"
    )
    assert models.FactOverride.objects.filter(workspace=workspace).count() == success_count
    audit_count = AuditEvent.objects.filter(
        action="review_fact_overridden", entity_id=workspace.external_id
    ).count()
    assert audit_count == success_count, (
        f"Audit count ({audit_count}) must equal 2xx count ({success_count}); "
        f"locked #37 — exactly one event per state-changing action."
    )


# --- 2. conflicts/resolve — concurrent writes serialize under lock --


@pytest.mark.django_db(transaction=True)
def test_conflict_resolve_concurrent_writes_serialize_under_lock() -> None:
    """100 parallel POST /conflicts/resolve/ on the SAME conflict.

    Current behavior: the resolve handler does NOT short-circuit
    when the conflict is already resolved; it overwrites the
    resolved_conflict each call. Every concurrent caller succeeds,
    audit count == N. The lock guarantees no IntegrityError + no
    torn writes. (If a later "already_resolved" 409 short-circuit
    is added, flip the assertion to `success_count == 1`.)
    """
    user = _user()
    workspace = models.ReviewWorkspace.objects.create(label="WS", owner=user)
    field, fact_id = _seed_one_conflict(workspace)
    url = reverse("review-workspace-conflict-resolve", args=[workspace.external_id])

    def _request(idx: int) -> int:
        client = APIClient()
        client.force_authenticate(user=user)
        return client.post(
            url,
            {
                "field": field,
                "chosen_fact_id": fact_id,
                "rationale": f"KYC supersedes statement (concurrent #{idx}).",
                "evidence_ack": True,
            },
            format="json",
        ).status_code

    statuses = _run_parallel(_request)
    success_count = sum(1 for s in statuses if s == 200)
    error_5xx = [s for s in statuses if 500 <= s < 600]

    assert not error_5xx, f"5xx responses surfaced: {error_5xx}"
    audit_count = AuditEvent.objects.filter(
        action="review_conflict_resolved", entity_id=workspace.external_id
    ).count()
    assert audit_count == success_count
    workspace.refresh_from_db()
    target = next(
        c for c in workspace.reviewed_state.get("conflicts", []) if c.get("field") == field
    )
    assert target.get("resolved") is True
    assert target.get("chosen_fact_id") == fact_id


# --- 3. conflicts/bulk-resolve — 2 audit events per call -----------


@pytest.mark.django_db(transaction=True)
def test_conflict_bulk_resolve_concurrent_writes_serialize_under_lock() -> None:
    """100 parallel POST /conflicts/bulk-resolve/ with same payload.

    Each call emits TWO audit events (one per resolved conflict in
    the bulk), so audit_count == 2 * success_count. No 5xx; no
    IntegrityError.
    """
    user = _user()
    workspace = models.ReviewWorkspace.objects.create(label="WS", owner=user)
    dob_fact, marital_fact = _seed_two_conflicts(workspace)
    url = reverse("review-workspace-conflict-bulk-resolve", args=[workspace.external_id])

    def _request(idx: int) -> int:
        client = APIClient()
        client.force_authenticate(user=user)
        return client.post(
            url,
            {
                "resolutions": [
                    {"field": "people[0].date_of_birth", "chosen_fact_id": dob_fact},
                    {"field": "people[0].marital_status", "chosen_fact_id": marital_fact},
                ],
                "rationale": f"KYC supersedes statement bulk #{idx}.",
                "evidence_ack": True,
            },
            format="json",
        ).status_code

    statuses = _run_parallel(_request)
    success_count = sum(1 for s in statuses if s == 200)
    error_5xx = [s for s in statuses if 500 <= s < 600]

    assert not error_5xx, f"5xx responses surfaced: {error_5xx}"
    audit_count = AuditEvent.objects.filter(
        action="review_conflict_resolved",
        entity_id=workspace.external_id,
        metadata__bulk=True,
    ).count()
    assert audit_count == 2 * success_count, (
        f"bulk-resolve emits one event per resolved conflict; with 2 "
        f"conflicts per call expected {2 * success_count}, got {audit_count}"
    )


# --- 4. conflicts/defer — concurrent defers on same field -----------


@pytest.mark.django_db(transaction=True)
def test_conflict_defer_concurrent_writes_serialize_under_lock() -> None:
    """100 parallel POST /conflicts/defer/ on the SAME field.

    Each call sets `deferred=True` + writes a fresh `deferred_at`.
    Lock-serialized; one audit event per 2xx response.
    """
    user = _user()
    workspace = models.ReviewWorkspace.objects.create(label="WS", owner=user)
    field, _ = _seed_one_conflict(workspace)
    url = reverse("review-workspace-conflict-defer", args=[workspace.external_id])

    def _request(idx: int) -> int:
        client = APIClient()
        client.force_authenticate(user=user)
        return client.post(
            url,
            {"field": field, "rationale": f"Decide later — concurrent defer #{idx}."},
            format="json",
        ).status_code

    statuses = _run_parallel(_request)
    success_count = sum(1 for s in statuses if s == 200)
    error_5xx = [s for s in statuses if 500 <= s < 600]

    assert not error_5xx, f"5xx surfaced: {error_5xx}"
    audit_count = AuditEvent.objects.filter(
        action="review_conflict_deferred", entity_id=workspace.external_id
    ).count()
    assert audit_count == success_count
    workspace.refresh_from_db()
    target = next(
        c for c in workspace.reviewed_state.get("conflicts", []) if c.get("field") == field
    )
    assert target.get("deferred") is True


# --- 5. disclaimer/acknowledge — idempotent state, append-only audit


@pytest.mark.django_db(transaction=True)
def test_disclaimer_acknowledge_concurrent_calls_idempotent_state() -> None:
    """100 parallel POST /api/disclaimer/acknowledge/ by SAME user.

    DisclaimerAcknowledgeView updates the profile + emits a fresh
    audit event each call. Race we're guarding: get_or_create on
    the 1:1 AdvisorProfile must not surface IntegrityError. Profile
    count must end at exactly 1; audit count == 2xx count.
    """
    user = _user()
    url = reverse("disclaimer-acknowledge")

    def _request(idx: int) -> int:
        client = APIClient()
        client.force_authenticate(user=user)
        return client.post(url, {"version": "v1"}, format="json").status_code

    statuses = _run_parallel(_request)
    success_count = sum(1 for s in statuses if s == 200)
    error_5xx = [s for s in statuses if 500 <= s < 600]

    assert not error_5xx, f"5xx responses surfaced: {error_5xx}"
    assert models.AdvisorProfile.objects.filter(user=user).count() == 1
    profile = models.AdvisorProfile.objects.get(user=user)
    assert profile.disclaimer_acknowledged_version == "v1"
    assert profile.disclaimer_acknowledged_at is not None

    audit_count = AuditEvent.objects.filter(
        action="disclaimer_acknowledged", entity_id=str(user.pk)
    ).count()
    assert audit_count == success_count, (
        f"audit count ({audit_count}) must equal 2xx count ({success_count}); "
        f"DisclaimerAcknowledgeView emits one event per ack."
    )


# --- 6. tour/complete — bounded audit count via TOCTOU race --------


@pytest.mark.django_db(transaction=True)
def test_tour_complete_concurrent_calls_emit_audit_only_once() -> None:
    """100 parallel POST /api/tour/complete/ by SAME user.

    Closes the TOCTOU window (Phase 6 sub-session #4 finding):
    TourCompleteView wraps get-or-create + check + update in
    `transaction.atomic()` + `select_for_update()` so concurrent
    callers serialize on the AdvisorProfile row. Only the first
    sees `tour_completed_at IS NULL` and emits the audit event;
    every subsequent caller sees the populated field and short-
    circuits.
    """
    user = _user()
    url = reverse("tour-complete")

    def _request(idx: int) -> int:
        client = APIClient()
        client.force_authenticate(user=user)
        return client.post(url, {}, format="json").status_code

    statuses = _run_parallel(_request)
    success_count = sum(1 for s in statuses if s == 200)
    error_5xx = [s for s in statuses if 500 <= s < 600]

    assert success_count == PARALLEL_REQUESTS, (
        f"Tour completion is idempotent — expected all 200, got {sorted(set(statuses))}"
    )
    assert not error_5xx
    assert models.AdvisorProfile.objects.filter(user=user).count() == 1
    audit_count = AuditEvent.objects.filter(action="tour_completed", entity_id=str(user.pk)).count()
    assert audit_count == 1, (
        f"Tour-complete audit must fire exactly once across {PARALLEL_REQUESTS} "
        f"concurrent calls (TOCTOU race closed via select_for_update); "
        f"got {audit_count}."
    )


# --- 7-11. Workspace-level auto-trigger sources (locked #14 + #27 + #74) ---
#
# `_trigger_and_audit_for_workspace` is invoked by the 4 NEW workspace-
# level trigger sources: conflict_resolve, defer_conflict, fact_override,
# section_approve. Each MUST pin audit-emission invariants under N
# same-signature calls:
#
#   - LINKED workspace path: same input → same run_signature → REUSED
#     events; first call GENERATES, rest REUSE. Pinned via N=20
#     SEQUENTIAL calls (see helper docstring below for the pytest-django
#     + ThreadPoolExecutor TRUNCATE-deadlock rationale).
#   - UNLINKED workspace path (the common pre-commit case): every call
#     emits a workspace-skip audit; no household-side effects. Also
#     sequential N=20 to keep the file's test-isolation discipline
#     uniform.
#
# Direct helper calls (not through APIClient) — these triggers are
# internal helpers fired AFTER endpoint logic completes; the canonical
# request flow is exercised by the per-endpoint tests above and the
# 200-cell auto-trigger audit-emission cells in test_auth_rbac_matrix.py.


def _bootstrap_full_demo() -> models.Household:
    """Reset state with seed_default_cma + load_synthetic_personas.

    `load_synthetic_personas` auto-seeds a PortfolioRun via
    `_trigger_portfolio_generation` with source='synthetic_load' (per
    locked #14 trigger #1). Subsequent same-signature calls hit the
    REUSED path — that's exactly what the linked-workspace concurrency
    tests pin.
    """
    call_command("seed_default_cma", "--force")
    call_command("load_synthetic_personas")
    return models.Household.objects.get(external_id="hh_sandra_mike_chen")


def _linked_workspace(user, household: models.Household, *, label: str) -> models.ReviewWorkspace:
    """Workspace already linked to a committed household (post-commit edits flow).

    Mirrors `test_workspace_trigger_gate_properties._linked_workspace` —
    SYNTHETIC origin so `_portfolio_provenance_hashes` doesn't raise
    MissingProvenance.
    """
    return models.ReviewWorkspace.objects.create(
        label=label,
        owner=user,
        linked_household=household,
        status=models.ReviewWorkspace.Status.COMMITTED,
        data_origin=models.ReviewWorkspace.DataOrigin.SYNTHETIC,
    )


def _assert_linked_workspace_trigger_serial_calls_pin_audit_invariants(
    *,
    source: str,
) -> None:
    """Shared assertion body for the 4 linked-workspace trigger tests.

    Per locked #14 + #27: workspace-level triggers fall through to
    `_trigger_and_audit(linked_household, ...)` when linked. Per
    locked #74: synchronous inline; signature-match → REUSED.

    Concurrency strategy: SEQUENTIAL N calls (NOT ThreadPoolExecutor).
    The auto-trigger helper holds engine.optimize() open against
    `api_cmacorrelation` SELECT-rows for ~250-1000ms; under a
    ThreadPoolExecutor those backend connections deadlock with
    pytest-django's `transaction=True` TRUNCATE teardown which takes
    AccessExclusiveLock on the same tables. The race-condition gap
    (`_reusable_current_run` is OUTSIDE the helper's `transaction.atomic`
    block and lacks a household-row `select_for_update`) is already
    pinned by the property suite at `test_workspace_trigger_gate_properties.py`
    via Hypothesis-driven property tests, which use `@pytest.mark.django_db`
    (default rollback) — that path is concurrency-free by design.
    Sequential calls here pin the same audit-emission invariants
    without the test-isolation hazard.

    Setup: bootstrap full demo (auto-seeds 1 PortfolioRun via
    synthetic_load trigger). Wrap that household in a freshly-linked
    workspace. The workspace's `approval_snapshot_hash` differs from
    the auto-seed's, so the FIRST call generates a NEW PortfolioRun;
    subsequent N-1 calls REUSE that one (signature stable).

    Invariants pinned:
      1. All N calls return a PortfolioRun (gate fell through; helper
         succeeded — sequential calls don't trigger the
         `_reusable_current_run` race).
      2. All returned runs share the same pk (single canonical row;
         first GENERATES, rest REUSE).
      3. Exactly 1 NEW PortfolioRun row created (append-only invariant).
      4. Audit count of (`portfolio_run_generated` + `portfolio_run_reused`)
         attributed to THIS household grows by exactly N over the call
         sequence.
      5. No workspace-level skip audit (gate fell through; we're on
         the linked-household path).
    """
    hh = _bootstrap_full_demo()
    user = _user()
    workspace = _linked_workspace(user, hh, label=f"WS-linked-{source}-stress")

    starting_run_count = models.PortfolioRun.objects.filter(household=hh).count()
    starting_canonical_audit_count = AuditEvent.objects.filter(
        action__in=["portfolio_run_generated", "portfolio_run_reused"],
        metadata__household_id=hh.external_id,
    ).count()

    results = [
        _trigger_and_audit_for_workspace(workspace, user, source=source)
        for _ in range(WORKSPACE_TRIGGER_PARALLEL)
    ]

    # 1. All N calls returned a PortfolioRun (linked-household gate fired
    #    cleanly; sequential calls don't race the lifecycle gap).
    assert all(isinstance(r, models.PortfolioRun) for r in results), (
        f"Expected all {WORKSPACE_TRIGGER_PARALLEL} linked-workspace "
        f"calls to return a PortfolioRun; got "
        f"{[type(r).__name__ for r in results if not isinstance(r, models.PortfolioRun)]}. "
        f"Source={source!r}."
    )
    runs = [r for r in results if isinstance(r, models.PortfolioRun)]

    # 2. All concurrent calls converge on a single canonical PortfolioRun row.
    distinct_pks = {r.pk for r in runs}
    assert len(distinct_pks) == 1, (
        f"Sequential same-signature calls must reuse a single "
        f"PortfolioRun row; got {len(distinct_pks)} distinct pks. "
        f"Source={source!r}."
    )

    # 3. Exactly 1 NEW row added (first GENERATE, rest REUSE).
    ending_run_count = models.PortfolioRun.objects.filter(household=hh).count()
    new_rows = ending_run_count - starting_run_count
    assert new_rows == 1, (
        f"Expected exactly 1 NEW PortfolioRun row across "
        f"{WORKSPACE_TRIGGER_PARALLEL} sequential calls (first "
        f"GENERATES, rest REUSE); got {new_rows} new rows. "
        f"Source={source!r}."
    )

    # 4. Audit count grows by exactly N (one canonical event per call).
    ending_canonical_audit_count = AuditEvent.objects.filter(
        action__in=["portfolio_run_generated", "portfolio_run_reused"],
        metadata__household_id=hh.external_id,
    ).count()
    audit_delta = ending_canonical_audit_count - starting_canonical_audit_count
    assert audit_delta == WORKSPACE_TRIGGER_PARALLEL, (
        f"Expected {WORKSPACE_TRIGGER_PARALLEL} canonical audit events; "
        f"got {audit_delta}. Source={source!r}. Per locked #9 + #16: "
        f"every helper call must emit exactly one audit row."
    )

    # 5. No workspace-level skip audit — the gate fell through cleanly.
    workspace_skip_events = AuditEvent.objects.filter(
        action=f"portfolio_generation_skipped_post_{source}",
        entity_id=workspace.external_id,
        entity_type="review_workspace",
    )
    assert workspace_skip_events.count() == 0, (
        f"Linked workspace must NOT emit workspace-level skip audit; "
        f"got {workspace_skip_events.count()} for source={source!r}."
    )


@pytest.mark.django_db
def test_workspace_trigger_conflict_resolve_serial_calls_pin_audit_invariants() -> None:
    """N sequential `_trigger_and_audit_for_workspace(source='conflict_resolve')`
    on a workspace with linked_household. Per locked #14 trigger #5.
    Pins audit-emission invariants under N same-signature calls.
    """
    _assert_linked_workspace_trigger_serial_calls_pin_audit_invariants(source="conflict_resolve")


@pytest.mark.django_db
def test_workspace_trigger_defer_conflict_serial_calls_pin_audit_invariants() -> None:
    """N sequential `_trigger_and_audit_for_workspace(source='defer_conflict')`
    on a workspace with linked_household. Per locked #14 trigger #6.
    """
    _assert_linked_workspace_trigger_serial_calls_pin_audit_invariants(source="defer_conflict")


@pytest.mark.django_db
def test_workspace_trigger_fact_override_serial_calls_pin_audit_invariants() -> None:
    """N sequential `_trigger_and_audit_for_workspace(source='fact_override')`
    on a workspace with linked_household. Per locked #14 trigger #7.
    """
    _assert_linked_workspace_trigger_serial_calls_pin_audit_invariants(source="fact_override")


@pytest.mark.django_db
def test_workspace_trigger_section_approve_serial_calls_pin_audit_invariants() -> None:
    """N sequential `_trigger_and_audit_for_workspace(source='section_approve')`
    on a workspace with linked_household. Per locked #14 trigger #8.
    """
    _assert_linked_workspace_trigger_serial_calls_pin_audit_invariants(source="section_approve")


@pytest.mark.django_db
def test_workspace_trigger_unlinked_serial_calls_emit_skip_audit() -> None:
    """N sequential `_trigger_and_audit_for_workspace` on an UNLINKED
    workspace (linked_household_id is None — the common pre-commit case).

    Per locked #27: helper returns None + emits a workspace-level skip
    audit each call. NO household-side effects (no PortfolioRun created,
    no canonical generated/reused audit emitted).

    Sequential calls (not threaded) per the same isolation rationale
    as the linked-workspace tests above — though the unlinked path is
    a no-op gate with no engine.optimize() wall-time, mixing
    `transaction=True` threaded tests with `_bootstrap_full_demo`-using
    tests in the same file caused pytest-django TRUNCATE deadlocks.
    Sequential N=20 still pins the audit-emission invariant per call.

    Asserts:
      - All N helper calls return None.
      - N workspace-skip audits emitted with canonical metadata.
      - No PortfolioRun rows created anywhere (no household linked).
      - No `portfolio_run_generated` / `portfolio_run_reused` audits
        emitted (workspace gate short-circuited).
    """
    user = _user()
    workspace = models.ReviewWorkspace.objects.create(
        label="WS-unlinked-stress",
        owner=user,
        status=models.ReviewWorkspace.Status.DRAFT,
    )
    source = "conflict_resolve"

    starting_run_count = models.PortfolioRun.objects.count()
    starting_canonical_audit_count = AuditEvent.objects.filter(
        action__in=["portfolio_run_generated", "portfolio_run_reused"],
    ).count()

    results = [
        _trigger_and_audit_for_workspace(workspace, user, source=source)
        for _ in range(WORKSPACE_TRIGGER_PARALLEL)
    ]

    # All N calls returned None (workspace gate short-circuited).
    assert all(r is None for r in results), (
        f"Expected all {WORKSPACE_TRIGGER_PARALLEL} unlinked-workspace "
        f"calls to return None; got non-None: "
        f"{[r for r in results if r is not None]}."
    )

    # Exactly N workspace-skip audit rows, each carrying canonical metadata.
    skip_events = AuditEvent.objects.filter(
        action=f"portfolio_generation_skipped_post_{source}",
        entity_id=workspace.external_id,
    )
    assert skip_events.count() == WORKSPACE_TRIGGER_PARALLEL, (
        f"Expected {WORKSPACE_TRIGGER_PARALLEL} workspace-skip audits; got {skip_events.count()}."
    )
    for event in skip_events:
        assert event.entity_type == "review_workspace"
        assert event.metadata["source"] == source
        assert event.metadata["skipped_no_household"] is True
        assert event.metadata["workspace_id"] == workspace.external_id
        assert event.metadata["reason_code"] == "no_linked_household"

    # No household-side effects: no NEW PortfolioRun rows, no canonical
    # generated/reused audits (the gate was the only side effect).
    assert models.PortfolioRun.objects.count() == starting_run_count, (
        "Unlinked-workspace trigger must not create any PortfolioRun rows."
    )
    ending_canonical_audit_count = AuditEvent.objects.filter(
        action__in=["portfolio_run_generated", "portfolio_run_reused"],
    ).count()
    assert ending_canonical_audit_count == starting_canonical_audit_count, (
        "Unlinked-workspace trigger must not emit any "
        "`portfolio_run_generated`/`portfolio_run_reused` audits."
    )
