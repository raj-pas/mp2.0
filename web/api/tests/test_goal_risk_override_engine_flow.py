"""Regression test for the goal-risk-override → engine input flow.

Pins the fix surfaced by real-Chrome smoke 2026-05-04 (locked #100):
saved overrides round-tripped through `goal_risk_override_created` audit
+ `GoalRiskOverride` DB row, but the override never reached the engine
because `_goal_to_engine` and `committed_construction_snapshot` read
`goal.goal_risk_score` directly without consulting `active_goal_override`.
Result: identical input_hash → REUSED path → engine output reflected the
SYSTEM score, not the saved override.

The fix introduces `effective_goal_risk_score(goal)` as the single source
of truth (override.score_1_5 if present else goal.goal_risk_score) and
calls it from both adapter functions. This test asserts:

1. Helper unit semantics (override-wins vs no-override).
2. End-to-end: override that genuinely changes effective score produces
   a NEW PortfolioRun with a DIFFERENT run_signature, and the engine
   output reflects the override.
3. Edge case: override that does NOT change effective score (because
   horizon cap collapses both paths) correctly REUSES the existing run
   (no spurious regeneration; locked #74 + REUSED contract preserved).
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from web.api import models
from web.api.engine_adapter import (
    active_goal_override,
    committed_construction_snapshot,
    effective_goal_risk_score,
)
from web.api.views import _trigger_portfolio_generation

User = get_user_model()


def _make_user() -> User:
    user, _ = User.objects.get_or_create(
        username="advisor@example.com",
        defaults={"email": "advisor@example.com"},
    )
    return user


def _bootstrap() -> models.Household:
    call_command("seed_default_cma", "--force")
    call_command("load_synthetic_personas")
    return models.Household.objects.get(external_id="hh_sandra_mike_chen")


# ---------------------------------------------------------------------------
# Helper unit tests (no DB-dependent state beyond a goal + override row).
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_effective_goal_risk_score_returns_system_when_no_override():
    hh = _bootstrap()
    goal = hh.goals.get(external_id="goal_ski_cabin")
    # Ski cabin seed: system score = 4 (Balanced-growth), no override.
    assert goal.risk_overrides.count() == 0
    assert effective_goal_risk_score(goal) == goal.goal_risk_score


@pytest.mark.django_db
def test_effective_goal_risk_score_returns_override_when_present():
    hh = _bootstrap()
    goal = hh.goals.get(external_id="goal_ski_cabin")
    user = _make_user()
    models.GoalRiskOverride.objects.create(
        goal=goal,
        score_1_5=1,
        descriptor="Cautious",
        rationale="Regression test: pin override flows to engine input.",
        created_by=user,
    )
    # Override wins; system score (4) is ignored for engine input purposes.
    assert effective_goal_risk_score(goal) == 1
    # active_goal_override still works (separate path used by preview views).
    eng_override = active_goal_override(goal)
    assert eng_override is not None
    assert eng_override.score_1_5 == 1


@pytest.mark.django_db
def test_effective_goal_risk_score_returns_latest_override_when_multiple():
    """Latest-row-wins per locked decision #6 (append-only override table)."""
    hh = _bootstrap()
    goal = hh.goals.get(external_id="goal_ski_cabin")
    user = _make_user()
    models.GoalRiskOverride.objects.create(
        goal=goal,
        score_1_5=1,
        descriptor="Cautious",
        rationale="First override: too cautious initially.",
        created_by=user,
    )
    models.GoalRiskOverride.objects.create(
        goal=goal,
        score_1_5=5,
        descriptor="Growth-oriented",
        rationale="Second override: advisor revised after discussion.",
        created_by=user,
    )
    assert effective_goal_risk_score(goal) == 5


# ---------------------------------------------------------------------------
# End-to-end: snapshot + run_signature + engine output reflect override.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_committed_construction_snapshot_reflects_override():
    hh = _bootstrap()
    goal = hh.goals.get(external_id="goal_ski_cabin")
    user = _make_user()

    snapshot_pre = committed_construction_snapshot(hh)
    pre_score = next(
        g["goal_risk_score"]
        for g in snapshot_pre["goals"]
        if g["id"] == "goal_ski_cabin"
    )
    assert pre_score == goal.goal_risk_score  # system score, no override

    models.GoalRiskOverride.objects.create(
        goal=goal,
        score_1_5=1,
        descriptor="Cautious",
        rationale="Regression test: pin override flows into snapshot.",
        created_by=user,
    )
    snapshot_post = committed_construction_snapshot(hh)
    post_score = next(
        g["goal_risk_score"]
        for g in snapshot_post["goals"]
        if g["id"] == "goal_ski_cabin"
    )
    assert post_score == 1  # override-resolved
    # Goals without overrides remain unchanged in the snapshot.
    other_goals_pre = {
        g["id"]: g["goal_risk_score"]
        for g in snapshot_pre["goals"]
        if g["id"] != "goal_ski_cabin"
    }
    other_goals_post = {
        g["id"]: g["goal_risk_score"]
        for g in snapshot_post["goals"]
        if g["id"] != "goal_ski_cabin"
    }
    assert other_goals_pre == other_goals_post


@pytest.mark.django_db
def test_override_changing_effective_score_produces_new_run_signature():
    """End-to-end regression for the locked-#100 real-Chrome bug.

    Before the fix: `_trigger_portfolio_generation` ignored the override
    via `committed_construction_snapshot` reading `goal.goal_risk_score`
    directly. The input_hash matched the seed run; REUSED path returned
    the seed; the engine NEVER re-optimized with the override.

    After the fix: `effective_goal_risk_score(goal)` resolves the
    override, the snapshot reflects it, the input_hash differs, and a
    new PortfolioRun is generated.

    Ski cabin's 8-year horizon is the canonical regression case: no
    horizon-cap collapse means `MIN(override=1, cap=N)` differs from
    `MIN(system=4, cap=N)` (with cap likely 5 at 8yr → effective 1 vs 4).
    """
    hh = _bootstrap()
    user = _make_user()

    # Seed run is auto-generated by load_synthetic_personas; capture it.
    run_seed = hh.portfolio_runs.order_by("-created_at").first()
    assert run_seed is not None, (
        "load_synthetic_personas should auto-generate the initial run"
    )
    seed_signature = run_seed.run_signature

    # Save override on Ski cabin (8yr horizon → no horizon-cap collapse).
    goal = hh.goals.get(external_id="goal_ski_cabin")
    models.GoalRiskOverride.objects.create(
        goal=goal,
        score_1_5=1,
        descriptor="Cautious",
        rationale="Regression test: 8yr horizon override should produce new run.",
        created_by=user,
    )

    # Trigger regeneration. Per locked #74 this is synchronous + inline.
    run_after = _trigger_portfolio_generation(hh, user, source="override")

    # NEW PortfolioRun row (not REUSED).
    assert run_after.pk != run_seed.pk, (
        "Override that changes effective score must produce a NEW PortfolioRun"
    )
    assert run_after.run_signature != seed_signature, (
        "Override that changes effective score must produce a different "
        "run_signature; otherwise the override is invisible to the engine"
    )

    # Engine output reflects the override: ski_cabin's per-link
    # recommendation should be optimized for Cautious (low Equity), not
    # Balanced-growth (high Equity). Read the link recommendation rows.
    ski_cabin_recs = run_after.link_recommendation_rows.filter(
        goal_external_id="goal_ski_cabin"
    )
    assert ski_cabin_recs.exists(), "Ski cabin should have at least one link rec"

    # The frontier_percentile for Cautious is 5/15/25/35/45 → 5 (1=Cautious).
    # Per locked #6 risk-to-percentile mapping. Earlier runs at score=4
    # (Balanced-growth) would have percentile=35.
    for rec in ski_cabin_recs:
        assert rec.frontier_percentile == 5, (
            f"Cautious override should target P5 frontier (got {rec.frontier_percentile} "
            f"on link {rec.link_external_id}); engine input mapping likely still "
            f"reads the system score instead of the override"
        )


@pytest.mark.django_db
def test_override_at_system_score_correctly_reuses():
    """Negative-control: when the saved override matches the system score
    (effective input is byte-identical to the no-override case), REUSED
    is correct — no spurious regeneration.

    `engine.optimize()` reads the engine `Goal.goal_risk_score` field as
    the literal optimization input (no horizon-cap application; the
    horizon cap is a goal-scoring concept for display). So an override
    that equals the system score is a true no-op for the optimize path.

    This test guards against an over-eager fix that always regenerates
    on any override save, breaking the locked #74 + REUSED contract.
    """
    hh = _bootstrap()
    user = _make_user()

    run_seed = hh.portfolio_runs.order_by("-created_at").first()
    assert run_seed is not None
    seed_signature = run_seed.run_signature

    # Pick a goal where override == system_score = no-op for engine input.
    goal = hh.goals.get(external_id="goal_retirement_income")
    system_score = goal.goal_risk_score
    descriptor_for_score = {
        1: "Cautious",
        2: "Conservative-balanced",
        3: "Balanced",
        4: "Balanced-growth",
        5: "Growth-oriented",
    }[system_score]
    models.GoalRiskOverride.objects.create(
        goal=goal,
        score_1_5=system_score,
        descriptor=descriptor_for_score,
        rationale="Negative control: override matches system; engine input unchanged.",
        created_by=user,
    )

    run_after = _trigger_portfolio_generation(hh, user, source="override")

    # REUSED: same row, same signature (effective input unchanged).
    assert run_after.pk == run_seed.pk
    assert run_after.run_signature == seed_signature
