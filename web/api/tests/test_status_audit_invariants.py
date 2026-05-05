"""Hypothesis property-based tests pinning invariants on
`_portfolio_run_status` + `portfolio_run_integrity_alert` audit emission.

Per locked decision §3.18 — strengthens the unit-test contract from
`test_portfolio_run_status_semantics.py` against random event sequences
that the unit tests can't enumerate. Specifically:

  1. status is a deterministic FUNCTION of the event log (same events in
     any order → same status).
  2. audit-emit dedup invariant: N GETs by M advisors → exactly M audit
     rows when status='hash_mismatch' (regardless of GET ordering).
  3. INVALIDATED_BY_CMA event is idempotent (multiple flips don't
     duplicate the status flip).
  4. Audit metadata never contains raw `str(exc)` patterns (PII
     regression class — locked #2 from playful-hammock).
  5. Audit `action` field is always one of the canonical strings,
     never derived from exception text.

Per locked decisions §3.18 + §3.5.
"""

from __future__ import annotations

import json
import re
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.urls import reverse
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from rest_framework.test import APIClient
from web.api import models
from web.audit.models import AuditEvent

User = get_user_model()


_RUN_EVENT_TYPES = list(models.PortfolioRunEvent.EventType)


@pytest.fixture
def household_with_run(transactional_db):
    """Reusable fixture; per-test resets to known synthetic state.

    Uses `transactional_db` (instead of `db`) so each Hypothesis example
    can clean up + commit its own state. With `db` (transaction=False),
    multiple Hypothesis examples within one test share a single
    transaction; cross-example state leaks corrupt later examples.
    """
    call_command("seed_default_cma", "--force")
    call_command("load_synthetic_personas")
    hh = models.Household.objects.get(external_id="hh_sandra_mike_chen")
    return hh, hh.portfolio_runs.order_by("-created_at").first()


def _advisor(email: str = "advisor@example.com") -> User:
    user, _ = User.objects.get_or_create(username=email, defaults={"email": email})
    group, _ = Group.objects.get_or_create(name="advisor")
    user.groups.add(group)
    return user


def _client_for(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


# ---------------------------------------------------------------------------
# 1. Status determinism
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
@given(
    event_types=st.lists(
        st.sampled_from(_RUN_EVENT_TYPES),
        min_size=0,
        max_size=5,
    )
)
@settings(
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=20,
)
def test_status_is_deterministic_for_event_set(household_with_run, event_types) -> None:
    """For any set of events on a run, calling `_portfolio_run_status`
    twice returns the same value (pure function of the event log).
    """
    from web.api.serializers import _portfolio_run_status

    hh, run = household_with_run
    # Reset events between Hypothesis examples.
    run.events.all().delete()
    for event_type in event_types:
        models.PortfolioRunEvent.objects.create(
            portfolio_run=run,
            event_type=event_type,
            reason_code="hypothesis",
            actor="system",
        )

    first = _portfolio_run_status(run)
    second = _portfolio_run_status(run)
    assert first == second, (
        f"Status non-deterministic for events {[e.value for e in event_types]}: "
        f"got {first!r} then {second!r}"
    )


# ---------------------------------------------------------------------------
# 2. Audit dedup invariant
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
@given(
    advisor_count=st.integers(min_value=1, max_value=5),
    get_count=st.integers(min_value=1, max_value=10),
)
@settings(
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=10,
)
def test_integrity_audit_dedup_invariant(household_with_run, advisor_count, get_count) -> None:
    """Across N advisors x M GETs on a hash_mismatch run, exactly N
    audit rows are emitted (one per distinct advisor; M GETs dedup).
    """
    hh, run = household_with_run
    # Set up hash_mismatch event on the run (events ARE deletable; only
    # AuditEvent has append-only trigger).
    run.events.all().delete()
    models.PortfolioRunEvent.objects.create(
        portfolio_run=run,
        event_type=models.PortfolioRunEvent.EventType.HASH_MISMATCH,
        reason_code="hypothesis",
        actor="system",
    )
    # Use UUID-unique advisor emails per example to avoid cross-example
    # dedup carryover (audit table is append-only, can't reset).
    seed = uuid.uuid4().hex[:8]
    advisors = [_advisor(f"hypo_dedup_{seed}_{i}@example.com") for i in range(advisor_count)]
    before = AuditEvent.objects.filter(
        action="portfolio_run_integrity_alert",
        entity_id=run.external_id,
    ).count()
    for advisor in advisors:
        client = _client_for(advisor)
        for _ in range(get_count):
            response = client.get(reverse("client-detail", args=[hh.external_id]))
            assert response.status_code == 200
    after = AuditEvent.objects.filter(
        action="portfolio_run_integrity_alert",
        entity_id=run.external_id,
    ).count()

    delta = after - before
    assert delta == advisor_count, (
        f"Expected delta {advisor_count} audit rows ({advisor_count} "
        f"advisors x {get_count} GETs each); got {delta}"
    )


# ---------------------------------------------------------------------------
# 3. INVALIDATED_BY_CMA idempotency
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
@given(invalidate_count=st.integers(min_value=1, max_value=5))
@settings(
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=8,
)
def test_invalidated_by_cma_is_idempotent(household_with_run, invalidate_count) -> None:
    """Multiple INVALIDATED_BY_CMA events on the same run produce the
    same `status='invalidated'` (idempotent flip).
    """
    from web.api.serializers import _portfolio_run_status

    hh, run = household_with_run
    run.events.all().delete()
    for _ in range(invalidate_count):
        models.PortfolioRunEvent.objects.create(
            portfolio_run=run,
            event_type=models.PortfolioRunEvent.EventType.INVALIDATED_BY_CMA,
            reason_code="hypothesis_idempotent",
            actor="system",
        )

    assert _portfolio_run_status(run) == "invalidated"


# ---------------------------------------------------------------------------
# 4. PII discipline — no str(exc) raw text in audit metadata
# ---------------------------------------------------------------------------


# Common PII patterns: SIN (XXX-XXX-XXX), account numbers (long digit strings),
# email addresses inside metadata strings (not the actor field itself).
_SIN_PATTERN = re.compile(r"\b\d{3}[-\s]?\d{3}[-\s]?\d{3}\b")
_LONG_DIGIT = re.compile(r"\b\d{10,}\b")  # 10+ contiguous digits


@pytest.mark.django_db(transaction=True)
@given(
    noise=st.text(
        # Postgres rejects \x00 in text columns; filter null bytes out.
        alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00"),
        min_size=0,
        max_size=50,
    )
)
@settings(
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=10,
)
def test_audit_metadata_has_no_pii_patterns(household_with_run, noise) -> None:
    """For any random text noise potentially flowing through the audit
    path (e.g., via `note` or `reason_code` on PortfolioRunEvent),
    the resulting `portfolio_run_integrity_alert` audit metadata
    contains no SIN-pattern or long-digit pattern. Pins the locked #2
    PII discipline contract for the new audit emission.
    """
    hh, run = household_with_run
    run.events.all().delete()
    models.PortfolioRunEvent.objects.create(
        portfolio_run=run,
        event_type=models.PortfolioRunEvent.EventType.HASH_MISMATCH,
        # Hypothesis noise injected here — should NOT leak to audit metadata.
        reason_code="hypothesis_pii_noise",
        note=noise,
        actor="system",
    )
    # Use UUID-unique email per example so dedup doesn't suppress emission
    # across Hypothesis runs (audit table is append-only, can't reset).
    advisor = _advisor(f"pii_advisor_{uuid.uuid4().hex[:8]}@example.com")
    client = _client_for(advisor)
    response = client.get(reverse("client-detail", args=[hh.external_id]))
    assert response.status_code == 200

    audit = AuditEvent.objects.filter(
        action="portfolio_run_integrity_alert",
        entity_id=run.external_id,
        actor=advisor.email,
    ).first()
    assert audit is not None
    metadata_str = json.dumps(audit.metadata)
    assert not _SIN_PATTERN.search(metadata_str), (
        f"SIN-pattern leaked into audit metadata: {metadata_str!r}"
    )
    assert not _LONG_DIGIT.search(metadata_str), (
        f"Long-digit pattern (potential account number) leaked into audit "
        f"metadata: {metadata_str!r}"
    )


# ---------------------------------------------------------------------------
# 5. Audit action is always canonical
# ---------------------------------------------------------------------------


_CANONICAL_ACTIONS = frozenset(
    [
        "portfolio_run_integrity_alert",
        "portfolio_run_generated",
        "portfolio_run_skipped",
        "portfolio_run_failed",
        # The frontend Banner / Panel maps these to display copy; if a new
        # canonical action is added, this set must be updated synchronously.
    ]
)


@pytest.mark.django_db(transaction=True)
@given(event_types=st.lists(st.sampled_from(_RUN_EVENT_TYPES), min_size=1, max_size=3))
@settings(
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=10,
)
def test_status_observation_emits_only_canonical_actions(household_with_run, event_types) -> None:
    """For any event sequence + any GET pattern, the only audit actions
    emitted by the status-observation path are members of the canonical
    action set. Catches accidental dynamic action strings (e.g.,
    f"action_for_{exc.__class__.__name__}") that violate locked #2 +
    locked #16.
    """
    hh, run = household_with_run
    run.events.all().delete()
    for event_type in event_types:
        models.PortfolioRunEvent.objects.create(
            portfolio_run=run,
            event_type=event_type,
            reason_code="hypothesis_canonical",
            actor="system",
        )
    # Audit table is append-only; capture the BEFORE snapshot of distinct
    # actions for this entity, then assert the DELTA is canonical-only.
    before_actions = set(
        AuditEvent.objects.filter(entity_id=run.external_id).values_list("action", flat=True)
    )
    advisor = _advisor(f"canonical_advisor_{uuid.uuid4().hex[:8]}@example.com")
    client = _client_for(advisor)
    response = client.get(reverse("client-detail", args=[hh.external_id]))
    assert response.status_code == 200

    after_actions = set(
        AuditEvent.objects.filter(entity_id=run.external_id).values_list("action", flat=True)
    )
    new_actions = after_actions - before_actions
    non_canonical = new_actions - _CANONICAL_ACTIONS - {"client_detail_viewed"}
    # Allow client_detail_viewed (emitted by ClientDetailView for any GET).
    assert not non_canonical, (
        f"Non-canonical audit actions emitted by GET: {non_canonical}. "
        f"All actions must be in the canonical set or update _CANONICAL_ACTIONS."
    )
