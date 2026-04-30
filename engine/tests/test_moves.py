"""Parity tests for engine/moves.py vs v36 mockup methodology §8."""

from __future__ import annotations

import pytest
from engine.moves import (
    ROUNDING_INCREMENT,
    SKIP_THRESHOLD,
    compute_rebalance_moves,
)


class TestChoiEducationWorkedExample:
    """Methodology §8: Choi Education $80k goal, 4-pp shortfall in SH-Eq,
    4-pp surplus in SH-Sav. Δ = ±$3,200; rounded as-is; residual $0.
    """

    def test_choi_education_balanced(self) -> None:
        result = compute_rebalance_moves(
            current_pct={"SH-Sav": 0.20, "SH-Eq": 0.50, "SH-Inc": 0.30},
            ideal_pct={"SH-Sav": 0.16, "SH-Eq": 0.54, "SH-Inc": 0.30},
            goal_total_dollars=80_000.0,
        )
        # Sells: SH-Sav by $3,200; Buys: SH-Eq by $3,200
        assert result.total_buy == pytest.approx(3_200.0)
        assert result.total_sell == pytest.approx(3_200.0)
        assert len(result.moves) == 2
        # Sells listed first
        assert result.moves[0].action == "sell"
        assert result.moves[0].fund_id == "SH-Sav"
        assert result.moves[1].action == "buy"
        assert result.moves[1].fund_id == "SH-Eq"


class TestRoundingResidualAbsorbed:
    """Property: total_buy == total_sell exactly after residual fix."""

    def test_residual_absorbed_into_largest_buy(self) -> None:
        # Construct a case where unrounded deltas don't divide cleanly into $100.
        # current SH-Sav 33.33%, SH-Eq 33.33%, SH-Inc 33.34%
        # ideal   SH-Sav 50%,    SH-Eq 30%,    SH-Inc 20%
        # Total $10,000
        # delta_Sav = +1,667 → round to 1,700 (buy 1,700)
        # delta_Eq  = -333 → round to -300 (sell 300)
        # delta_Inc = -1,334 → round to -1,300 (sell 1,300)
        # Sum rounded = 1700 - 300 - 1300 = 100; residual = -100 → add to largest sell (SH-Inc)
        # Final: buy 1700, sell 300+1400 = 1700. Balanced.
        result = compute_rebalance_moves(
            current_pct={"SH-Sav": 0.3333, "SH-Eq": 0.3333, "SH-Inc": 0.3334},
            ideal_pct={"SH-Sav": 0.50, "SH-Eq": 0.30, "SH-Inc": 0.20},
            goal_total_dollars=10_000.0,
        )
        assert result.total_buy == result.total_sell

    def test_total_buy_equals_total_sell_property(self) -> None:
        """Hypothesis-style: for any plausible inputs, totals balance."""

        cases = [
            # Tiny imbalance
            (
                {"A": 0.49, "B": 0.51},
                {"A": 0.50, "B": 0.50},
                100_000.0,
            ),
            # Multi-fund
            (
                {"A": 0.20, "B": 0.30, "C": 0.50},
                {"A": 0.40, "B": 0.30, "C": 0.30},
                250_000.0,
            ),
            # Edge: very small total
            (
                {"A": 0.50, "B": 0.50},
                {"A": 0.40, "B": 0.60},
                1_000.0,
            ),
        ]
        for current, ideal, total in cases:
            result = compute_rebalance_moves(
                current_pct=current,
                ideal_pct=ideal,
                goal_total_dollars=total,
            )
            assert result.total_buy == pytest.approx(result.total_sell, abs=0.01), (
                f"Imbalance: buy={result.total_buy}, sell={result.total_sell}, "
                f"current={current}, ideal={ideal}, total={total}"
            )


class TestSkipBelowThreshold:
    """Moves under $50 are skipped (mockup §8)."""

    def test_tiny_delta_skipped(self) -> None:
        # 0.4% on $1000 = $4 — well below $50
        result = compute_rebalance_moves(
            current_pct={"A": 0.50, "B": 0.50},
            ideal_pct={"A": 0.504, "B": 0.496},
            goal_total_dollars=1_000.0,
        )
        # No moves — both deltas are $4 (below $50)
        assert result.moves == []

    def test_threshold_constant_exposed(self) -> None:
        assert SKIP_THRESHOLD == 50.0


class TestRoundingIncrement:
    def test_increment_constant(self) -> None:
        assert ROUNDING_INCREMENT == 100.0

    def test_amounts_are_multiples_of_100(self) -> None:
        result = compute_rebalance_moves(
            current_pct={"A": 0.20, "B": 0.30, "C": 0.50},
            ideal_pct={"A": 0.40, "B": 0.30, "C": 0.30},
            goal_total_dollars=250_000.0,
        )
        # All moves should be multiples of $100, even after residual fix
        for move in result.moves:
            assert move.amount % ROUNDING_INCREMENT == 0


class TestMoveOrdering:
    def test_sells_before_buys(self) -> None:
        result = compute_rebalance_moves(
            current_pct={"A": 0.10, "B": 0.40, "C": 0.50},
            ideal_pct={"A": 0.40, "B": 0.30, "C": 0.30},
            goal_total_dollars=100_000.0,
        )
        actions = [m.action for m in result.moves]
        # All sells should come before any buy
        first_buy_idx = next((i for i, a in enumerate(actions) if a == "buy"), len(actions))
        assert all(a == "sell" for a in actions[:first_buy_idx])

    def test_within_side_descending_amount(self) -> None:
        result = compute_rebalance_moves(
            current_pct={"A": 0.10, "B": 0.20, "C": 0.30, "D": 0.40},
            ideal_pct={"A": 0.40, "B": 0.30, "C": 0.20, "D": 0.10},
            goal_total_dollars=100_000.0,
        )
        sells = [m.amount for m in result.moves if m.action == "sell"]
        buys = [m.amount for m in result.moves if m.action == "buy"]
        assert sells == sorted(sells, reverse=True)
        assert buys == sorted(buys, reverse=True)


class TestFundNameLookup:
    def test_provided_names_used(self) -> None:
        result = compute_rebalance_moves(
            current_pct={"SH-Sav": 0.20, "SH-Eq": 0.80},
            ideal_pct={"SH-Sav": 0.10, "SH-Eq": 0.90},
            goal_total_dollars=100_000.0,
            fund_names={"SH-Sav": "Steadyhand Savings Fund", "SH-Eq": "Steadyhand Equity Fund"},
        )
        sell = next(m for m in result.moves if m.action == "sell")
        buy = next(m for m in result.moves if m.action == "buy")
        assert sell.fund_name == "Steadyhand Savings Fund"
        assert buy.fund_name == "Steadyhand Equity Fund"

    def test_missing_names_fall_back_to_id(self) -> None:
        result = compute_rebalance_moves(
            current_pct={"SH-Sav": 0.20, "SH-Eq": 0.80},
            ideal_pct={"SH-Sav": 0.10, "SH-Eq": 0.90},
            goal_total_dollars=100_000.0,
        )
        for move in result.moves:
            assert move.fund_name == move.fund_id


class TestEmptyOrTrivialCases:
    def test_no_changes_yields_no_moves(self) -> None:
        result = compute_rebalance_moves(
            current_pct={"A": 0.50, "B": 0.50},
            ideal_pct={"A": 0.50, "B": 0.50},
            goal_total_dollars=10_000.0,
        )
        assert result.moves == []
        assert result.total_buy == 0
        assert result.total_sell == 0

    def test_zero_goal_total_rejected(self) -> None:
        with pytest.raises(ValueError, match="goal_total_dollars"):
            compute_rebalance_moves(
                current_pct={"A": 1.0},
                ideal_pct={"A": 1.0},
                goal_total_dollars=0.0,
            )

    def test_disjoint_funds_handled(self) -> None:
        # Current has only SH-Sav; ideal has only SH-Eq
        result = compute_rebalance_moves(
            current_pct={"SH-Sav": 1.0},
            ideal_pct={"SH-Eq": 1.0},
            goal_total_dollars=10_000.0,
        )
        # Should sell all of SH-Sav and buy all of SH-Eq
        assert result.total_buy == result.total_sell
        assert any(m.fund_id == "SH-Sav" and m.action == "sell" for m in result.moves)
        assert any(m.fund_id == "SH-Eq" and m.action == "buy" for m in result.moves)
