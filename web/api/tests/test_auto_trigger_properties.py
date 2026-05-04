"""Hypothesis property tests — `_trigger_portfolio_generation` invariants.

Pins locked decisions #14 (8 trigger points), #74 (sync inline), #81
(helper-managed atomic), #99 (audit-trail integrity for auto-trigger).

Properties asserted:
  1. Idempotency under unchanged input — N same-signature calls produce
     1 PortfolioRun + (N-1) REUSED PortfolioRunEvents.
  2. PortfolioRun is append-only — `save()` with existing pk raises
     ValidationError (per locked append-only invariant).
  3. `run_signature` hash is deterministic across calls + DB roundtrips
     for the same (household, CMA, reviewed_state, approval_snapshot).
  4. Mutating `household_risk_score` changes signature → NEW PortfolioRun
     row (separate pk).
  5. Audit-event count matches trigger-call count over a sequence — every
     successful call emits exactly one `portfolio_run_generated` OR
     `portfolio_run_reused` audit event.

Per agent guardrails: tests using `call_command(...)` + `@pytest.mark.django_db`
+ web.api imports MUST live under `web/api/tests/` (engine purity AST gate).
"""

from __future__ import annotations

import hypothesis.strategies as st
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from hypothesis import HealthCheck, given, settings
from web.api import models
from web.api.views import _trigger_portfolio_generation
from web.audit.models import AuditEvent

User = get_user_model()

HYPO_SETTINGS = dict(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)


def _make_user() -> User:
    user, _ = User.objects.get_or_create(
        username="advisor@example.com",
        defaults={"email": "advisor@example.com"},
    )
    return user


def _bootstrap_full_demo() -> models.Household:
    """Reset state with seed_default_cma + load_synthetic_personas."""
    call_command("seed_default_cma", "--force")
    call_command("load_synthetic_personas")
    return models.Household.objects.get(external_id="hh_sandra_mike_chen")


# ---------------------------------------------------------------------------
# Property 1 — Idempotency under same input
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@given(num_calls=st.integers(min_value=2, max_value=5))
@settings(**HYPO_SETTINGS)
def test_property_same_signature_yields_reused_runs(num_calls) -> None:
    """N calls on UNCHANGED household → 1 PortfolioRun row + (N-1)
    REUSED PortfolioRunEvent rows.

    Note: load_synthetic_personas auto-seeds a PortfolioRun via
    `_trigger_portfolio_generation` with source='synthetic_load'. That
    pre-existing run is the same-signature target; subsequent calls all
    REUSED.
    """
    hh = _bootstrap_full_demo()
    user = _make_user()
    starting_run_count = models.PortfolioRun.objects.filter(household=hh).count()
    starting_reused_event_count = models.PortfolioRunEvent.objects.filter(
        household=hh,
        event_type=models.PortfolioRunEvent.EventType.REUSED,
    ).count()

    runs = [_trigger_portfolio_generation(hh, user, source="manual") for _ in range(num_calls)]

    # All returned runs are the SAME row (REUSED via run_signature match)
    assert len({r.pk for r in runs}) == 1
    # No NEW PortfolioRun rows created (auto-seed run is reused)
    assert models.PortfolioRun.objects.filter(household=hh).count() == starting_run_count
    # Each call emitted exactly one REUSED PortfolioRunEvent
    final_reused_event_count = models.PortfolioRunEvent.objects.filter(
        household=hh,
        event_type=models.PortfolioRunEvent.EventType.REUSED,
    ).count()
    assert final_reused_event_count - starting_reused_event_count == num_calls


# ---------------------------------------------------------------------------
# Property 2 — Append-only PortfolioRun.save() raises on existing pk
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_portfolio_run_save_raises_on_existing_pk() -> None:
    """Per locked append-only invariant. PortfolioRun.save() with pk set
    on an existing row must raise ValidationError.
    """
    hh = _bootstrap_full_demo()
    user = _make_user()
    run = _trigger_portfolio_generation(hh, user, source="manual")
    assert run.pk is not None
    # Re-saving the SAME row must raise — append-only guard.
    with pytest.raises(ValidationError, match="append-only"):
        run.save()
    # Mutating a field then saving must ALSO raise (attempted UPDATE on existing pk).
    run.advisor_summary = "mutated"
    with pytest.raises(ValidationError, match="append-only"):
        run.save()


# ---------------------------------------------------------------------------
# Property 3 — run_signature hash determinism
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@given(num_roundtrips=st.integers(min_value=2, max_value=4))
@settings(**HYPO_SETTINGS)
def test_property_run_signature_deterministic_for_same_inputs(num_roundtrips) -> None:
    """Same (household, CMA, reviewed_state, approval_snapshot, as_of_date)
    yields IDENTICAL run_signature across repeated calls (incl. after DB
    roundtrip via refresh_from_db()).
    """
    hh = _bootstrap_full_demo()
    user = _make_user()
    signatures: set[str] = set()
    for _ in range(num_roundtrips):
        run = _trigger_portfolio_generation(hh, user, source="manual")
        run.refresh_from_db()
        signatures.add(run.run_signature)
        # Defensive: a stable, non-empty hash.
        assert run.run_signature
        assert len(run.run_signature) >= 32  # sha256 hex prefix
    assert len(signatures) == 1, f"Same inputs must yield identical run_signature; got {signatures}"


# ---------------------------------------------------------------------------
# Property 4 — Mutating household_risk_score changes signature → new run
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@given(new_score=st.sampled_from([1, 2, 3, 4, 5]))
@settings(**HYPO_SETTINGS)
def test_property_signature_changes_on_household_mutation(new_score) -> None:
    """Different household_risk_score → different run_signature → NEW
    PortfolioRun row (different pk).

    If new_score happens to equal current score, signature won't change
    (and that's correct behavior we also verify).
    """
    hh = _bootstrap_full_demo()
    user = _make_user()
    initial_run = _trigger_portfolio_generation(hh, user, source="manual")

    # Mutate household_risk_score (canon 1-5 scale per CLAUDE.md).
    original_score = hh.household_risk_score
    hh.household_risk_score = new_score
    hh.save(update_fields=["household_risk_score"])

    next_run = _trigger_portfolio_generation(hh, user, source="manual")

    if new_score == original_score:
        # No-op mutation: same signature → REUSED.
        assert next_run.pk == initial_run.pk
        assert next_run.run_signature == initial_run.run_signature
    else:
        # Different risk profile → different reviewed_state_hash → different
        # run_signature → NEW PortfolioRun.
        assert next_run.pk != initial_run.pk
        assert next_run.run_signature != initial_run.run_signature


# ---------------------------------------------------------------------------
# Property 5 — Audit count == call count over a sequence
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@given(call_count=st.integers(min_value=3, max_value=8))
@settings(**HYPO_SETTINGS)
def test_property_audit_event_count_matches_call_count(call_count) -> None:
    """For any sequence of N successful trigger calls on an UNCHANGED
    household, AuditEvent count of (`portfolio_run_generated` +
    `portfolio_run_reused`) for THIS household increases by exactly N.
    """
    hh = _bootstrap_full_demo()
    user = _make_user()

    def _audit_count() -> int:
        # Both canonical actions emitted by the helper. Filter to this
        # household via metadata.household_id to avoid cross-test bleed.
        return AuditEvent.objects.filter(
            action__in=["portfolio_run_generated", "portfolio_run_reused"],
            metadata__household_id=hh.external_id,
        ).count()

    starting = _audit_count()
    for _ in range(call_count):
        _trigger_portfolio_generation(hh, user, source="manual")
    ending = _audit_count()

    assert ending - starting == call_count, (
        f"Expected {call_count} audit events, got {ending - starting}"
    )
