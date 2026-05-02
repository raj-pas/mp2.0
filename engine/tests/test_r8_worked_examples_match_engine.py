"""Regression guard: every worked-example number quoted on the R8 methodology
overlay (`frontend/src/i18n/en.json` keys ``methodology.s*.worked``) must
match what the engine actually computes at canon-aligned inputs.

If any of these tests fails, EITHER:
  (a) an engine constant drifted from canon (locked decision #5/#10) — fix
      the engine; or
  (b) the methodology copy is stale relative to the engine — fix the i18n
      string.

Either way, the methodology page must not silently lie on stage during
the 2026-05-04 demo. Locked decision #6 + canon §9.4.5 ("AI/code does
not invent financial numbers") make the engine the source of truth.

Inputs and section references are explicit in each docstring so a failure
trace points the developer directly at the i18n key needing repair.
"""

from __future__ import annotations

import pytest

from engine.goal_scoring import effective_score_and_descriptor
from engine.moves import compute_rebalance_moves
from engine.projections import (
    BUCKET_REPRESENTATIVE_SCORE,
    equity_from_score,
    mu_current,
    mu_ideal,
)
from engine.risk_profile import RiskProfileInput, compute_risk_profile


# ---------------------------------------------------------------------------
# Section 1 — Household risk profile
# ---------------------------------------------------------------------------


def test_s1_hayes_household_profile_is_balanced_canon_score_3() -> None:
    """methodology.s1.worked: Q1=5, Q2=B, Q3=[career], Q4=B → T=45, C=50,
    household = Balanced (canon 3).
    """

    result = compute_risk_profile(
        RiskProfileInput(q1=5, q2="B", q3=["career"], q4="B")
    )

    assert result.tolerance_score == 45.0
    assert result.capacity_score == 50.0
    assert result.household_descriptor == "Balanced"
    assert result.score_1_5 == 3


# ---------------------------------------------------------------------------
# Section 2 — Anchor
# ---------------------------------------------------------------------------


def test_s2_hayes_anchor_is_22_5() -> None:
    """methodology.s2.worked: anchor = min(45, 50) / 2 = 22.5."""

    result = compute_risk_profile(
        RiskProfileInput(q1=5, q2="B", q3=["career"], q4="B")
    )

    assert result.anchor == 22.5


# ---------------------------------------------------------------------------
# Section 3 — Goal-level risk score (Hayes Retirement Goal)
# ---------------------------------------------------------------------------


def test_s3_hayes_retirement_resolves_to_conservative_balanced_score_2() -> None:
    """methodology.s3.worked pins: anchor 22.5, Need tier (-10), 47% of AUM
    (size_shift = -2), 32-year horizon, no override.

    Engine math: Goal_50 = 22.5 + (-10) + (-2) = 10.5; bucket(10.5) =
    Conservative-balanced (score 2). Horizon 32y maps to Growth-oriented
    cap (no effective bind). System descriptor = Conservative-balanced.

    The shipped i18n string used to say "Cautious (score 1)" — that was
    arithmetically wrong. Score 1 (Cautious) requires Goal_50 <= 10, which
    needs anchor <= 22.0. The Hayes household's correct anchor is 22.5.
    """

    resolved = effective_score_and_descriptor(
        anchor=22.5,
        necessity_score=5,  # Need
        goal_amount=47_000.0,
        household_aum=100_000.0,  # 47% share
        horizon_years=32.0,
        override=None,
    )

    assert resolved.score_1_5 == 2
    assert resolved.descriptor == "Conservative-balanced"
    assert resolved.system_descriptor == "Conservative-balanced"
    assert resolved.is_overridden is False
    assert resolved.is_horizon_cap_binding is False
    assert resolved.derivation == {
        "anchor": 22.5,
        "imp_shift": -10,
        "size_shift": -2,
    }


# ---------------------------------------------------------------------------
# Section 6 — Sleeve mix (calibration curve at canon-bucket midpoint)
# ---------------------------------------------------------------------------


def test_s6_canon_balanced_equity_pct_is_49_at_bucket_midpoint() -> None:
    """methodology.s6.worked: at canon Balanced (score 3) the calibration
    curve maps to ~49% equity, NOT the 56% previously quoted.

    Per locked decision #6, advisor-visible numbers must reference the
    canon-bucket midpoint (BUCKET_REPRESENTATIVE_SCORE[3] = 25.0), never
    the internal Goal_50. equity_from_score(25) = 0.05 + (24/49) * 0.90 =
    0.4908. The 56% number in the prior copy corresponded to an internal
    Goal_50 ~= 29 — meaningful for engineers but not advisor-facing.
    """

    rep_score = BUCKET_REPRESENTATIVE_SCORE[3]
    assert rep_score == 25.0

    equity_at_canon_balanced = equity_from_score(rep_score)
    assert equity_at_canon_balanced == pytest.approx(0.4908, rel=1e-3)
    assert round(equity_at_canon_balanced * 100) == 49


def test_s6_equity_curve_at_all_canon_buckets_for_calibration_table() -> None:
    """Belt-and-braces: assert the canon-rep equity for every bucket so a
    later refactor of the equity curve fails this test loudly. Expected:
    Cautious 12%, Conservative-balanced 31%, Balanced 49%, Balanced-growth
    67%, Growth-oriented 86%.
    """

    expected_pct = {1: 12, 2: 31, 3: 49, 4: 67, 5: 86}
    for canon_score, expected in expected_pct.items():
        rep = BUCKET_REPRESENTATIVE_SCORE[canon_score]
        eq = equity_from_score(rep)
        assert round(eq * 100) == expected, (
            f"canon score {canon_score} (rep={rep}) → equity={eq:.4f}, "
            f"expected ~{expected}%"
        )


# ---------------------------------------------------------------------------
# Section 7 — Lognormal projections (Thompson Retirement)
# ---------------------------------------------------------------------------


def test_s7_thompson_balanced_growth_mu_ideal_is_about_6pct() -> None:
    """methodology.s7.worked: at canon Balanced-growth (score 4) the
    representative continuous score is 35.

    Engine math:
      equity = 0.05 + (34/49) * 0.90 = 0.6745
      mu_ideal = 0.030 + 0.6745 * 0.045 = 0.0604

    The prior i18n claimed "0.030 + 0.74 × 0.045 ≈ 5.8%" — both the
    equity number (0.74 vs 0.6745) and the arithmetic (0.74 × 0.045 +
    0.030 = 0.0633 ≠ 5.8%) were wrong.
    """

    rep_score = BUCKET_REPRESENTATIVE_SCORE[4]
    assert rep_score == 35.0

    eq = equity_from_score(rep_score)
    assert eq == pytest.approx(0.6745, rel=1e-3)

    mu_id = mu_ideal(rep_score)
    assert mu_id == pytest.approx(0.0604, rel=1e-3)


def test_s7_thompson_mu_current_internal_and_external_branches_split_correctly() -> None:
    """methodology.s7 detail: external holdings carry mu × 0.85; internal
    Steadyhand off-target sleeves carry mu × 0.92. The two are per-holding
    binary, never weighted-blended.

    Engine math at canon Balanced-growth (rep=35):
      mu_current_internal = 0.0604 * 0.92 ≈ 0.0556
      mu_current_external = 0.0604 * 0.85 ≈ 0.0513

    The prior i18n claimed "with 30% external: 5.8% × 0.92 ≈ 5.34%" — that
    confused the two penalty branches AND used a weighted-blend framing
    that locked decision #11 explicitly forbids.
    """

    rep_score = BUCKET_REPRESENTATIVE_SCORE[4]

    mu_int = mu_current(rep_score, is_external=False)
    mu_ext = mu_current(rep_score, is_external=True)

    # Engine returns 0.0555 internal / 0.0513 external — display-rounded to
    # 5.5%/5.1% on stage. Tolerance accommodates the rounding spread.
    assert mu_int == pytest.approx(0.0555, rel=2e-3)
    assert mu_ext == pytest.approx(0.0513, rel=2e-3)

    # Internal penalty must be weaker than external (less drift drag for SH).
    assert mu_int > mu_ext


# ---------------------------------------------------------------------------
# Section 8 — Rebalancing moves (Choi Education)
# ---------------------------------------------------------------------------


def test_s8_choi_education_moves_balanced_at_3200() -> None:
    """methodology.s8.worked: $80,000 goal, 4-pp shortfall in Steadyhand
    Equity, 4-pp surplus in Steadyhand Savings → ±$3,200 swap with clean
    $100 rounding and zero residual.
    """

    result = compute_rebalance_moves(
        current_pct={"sh_equity": 0.46, "sh_savings": 0.54},
        ideal_pct={"sh_equity": 0.50, "sh_savings": 0.50},
        goal_total_dollars=80_000.0,
    )

    assert result.total_buy == 3200.0
    assert result.total_sell == 3200.0
    assert result.total_buy == result.total_sell, (
        "Buys/sells must balance exactly (canon §8.10 invariant)"
    )

    buys = sorted([m for m in result.moves if m.action == "buy"], key=lambda m: m.fund_id)
    sells = sorted(
        [m for m in result.moves if m.action == "sell"], key=lambda m: m.fund_id
    )
    assert len(buys) == 1
    assert len(sells) == 1
    assert buys[0].fund_id == "sh_equity"
    assert buys[0].amount == 3200.0
    assert sells[0].fund_id == "sh_savings"
    assert sells[0].amount == 3200.0
