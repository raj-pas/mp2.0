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
"""

from __future__ import annotations

import concurrent.futures
from collections.abc import Callable

import pytest
from django.contrib.auth import get_user_model
from django.db import connection, connections
from django.urls import reverse
from rest_framework.test import APIClient
from web.api import models
from web.api.review_state import reviewed_state_from_workspace
from web.audit.models import AuditEvent

PARALLEL_REQUESTS = 100
MAX_WORKERS = 20


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
    """
    kyc = _doc(workspace, filename="kyc.pdf", document_type="kyc")
    statement = _doc(workspace, filename="statement.pdf", document_type="kyc")
    kyc_dob = _fact(workspace, kyc, field="people[0].date_of_birth", value="1985-03-12")
    _fact(workspace, statement, field="people[0].date_of_birth", value="1985-03-15")
    kyc_marital = _fact(workspace, kyc, field="people[0].marital_status", value="married")
    _fact(workspace, statement, field="people[0].marital_status", value="single")
    workspace.reviewed_state = reviewed_state_from_workspace(workspace)
    workspace.save(update_fields=["reviewed_state"])
    return kyc_dob.id, kyc_marital.id


def _seed_one_conflict(workspace) -> tuple[str, int]:
    """Single conflict on people[0].date_of_birth (kyc vs kyc-v2)."""
    kyc = _doc(workspace, filename="kyc.pdf", document_type="kyc")
    kyc2 = _doc(workspace, filename="kyc-v2.pdf", document_type="kyc")
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
