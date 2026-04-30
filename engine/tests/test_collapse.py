"""Tests for engine/collapse.py (canon §4.3b FoF collapse logic)."""

from __future__ import annotations

import pytest
from engine.collapse import (
    DEFAULT_COLLAPSE_THRESHOLD,
    blend_asset_class_composition,
    collapse_suggestion,
    match_score,
)
from engine.schemas import FundAssumption


def _building_block(
    fund_id: str,
    name: str,
    asset_class_weights: dict[str, float],
) -> FundAssumption:
    return FundAssumption(
        id=fund_id,
        name=name,
        expected_return=0.05,
        volatility=0.10,
        is_whole_portfolio=False,
        asset_class_weights=asset_class_weights,
    )


def _whole_portfolio(
    fund_id: str,
    name: str,
    asset_class_weights: dict[str, float],
) -> FundAssumption:
    return FundAssumption(
        id=fund_id,
        name=name,
        expected_return=0.05,
        volatility=0.10,
        is_whole_portfolio=True,
        asset_class_weights=asset_class_weights,
    )


@pytest.fixture
def universe() -> list[FundAssumption]:
    return [
        _building_block("SH-Sav", "Savings", {"cash": 1.0}),
        _building_block("SH-Inc", "Income", {"fixed_income": 0.75, "equity": 0.25}),
        _building_block("SH-Eq", "Equity", {"equity": 1.0}),
        _building_block("SH-Glb", "Global Equity", {"equity": 1.0}),
        # Founders ≈ 60% equity / 40% fixed income (balanced)
        _whole_portfolio("SH-Fnd", "Founders", {"equity": 0.60, "fixed_income": 0.40}),
        # Builders ≈ 90% equity / 10% fixed income (growth-oriented)
        _whole_portfolio("SH-Bld", "Builders", {"equity": 0.90, "fixed_income": 0.10}),
    ]


class TestBlendAssetClassComposition:
    def test_pure_equity_blend(self, universe: list[FundAssumption]) -> None:
        comp = blend_asset_class_composition(blend={"SH-Eq": 1.0}, eligible_funds=universe)
        assert comp == {"equity": 1.0}

    def test_mixed_blend(self, universe: list[FundAssumption]) -> None:
        # 50% Income (75% FI / 25% Eq) + 50% Equity = 37.5% FI + 62.5% Eq
        comp = blend_asset_class_composition(
            blend={"SH-Inc": 0.5, "SH-Eq": 0.5},
            eligible_funds=universe,
        )
        assert comp["fixed_income"] == pytest.approx(0.375)
        assert comp["equity"] == pytest.approx(0.625)

    def test_zero_weight_skipped(self, universe: list[FundAssumption]) -> None:
        comp = blend_asset_class_composition(
            blend={"SH-Eq": 1.0, "SH-Sav": 0.0},
            eligible_funds=universe,
        )
        assert "cash" not in comp


class TestMatchScore:
    def test_exact_match_is_one(self, universe: list[FundAssumption]) -> None:
        # Builders is 90% Eq / 10% FI. Construct an equivalent blend.
        # SH-Eq 90% + SH-Inc proportion to hit 10% FI: SH-Inc 13.33% gives 10% FI + 3.33% Eq
        # That doesn't exactly match. Use direct equity + something with pure FI.
        # If we had a pure FI fund, blend 90% SH-Eq + 10% pure-FI = 90/10 split exactly.
        # Without one, the best match is still > threshold.
        # Use SH-Bld itself if we treat it as a building block in the blend (silly but tests math).
        # Better: test with a constructed scenario.
        builders = next(f for f in universe if f.id == "SH-Bld")
        # Blend that hits 90% Eq / 10% FI exactly: SH-Eq 86.67% + SH-Inc 13.33%
        # SH-Inc is 75% FI / 25% Eq → 13.33% × 0.75 = 10% FI; 13.33% × 0.25 = 3.33% Eq
        # Plus SH-Eq 86.67% = 86.67% Eq → total 90% Eq + 10% FI ✓
        blend = {"SH-Eq": 0.8667, "SH-Inc": 0.1333}
        score = match_score(blend=blend, whole_portfolio_fund=builders, eligible_funds=universe)
        assert score == pytest.approx(1.0, abs=0.001)

    def test_disjoint_match_is_zero(self, universe: list[FundAssumption]) -> None:
        # All-cash blend vs Builders (90% equity)
        builders = next(f for f in universe if f.id == "SH-Bld")
        blend = {"SH-Sav": 1.0}
        score = match_score(blend=blend, whole_portfolio_fund=builders, eligible_funds=universe)
        # Cash vs (Eq + FI) → fully disjoint → 0
        assert score == pytest.approx(0.0)

    def test_partial_overlap(self, universe: list[FundAssumption]) -> None:
        # Equal weight equity vs Founders 60/40
        founders = next(f for f in universe if f.id == "SH-Fnd")
        blend = {"SH-Eq": 1.0}  # 100% equity vs 60% equity / 40% FI
        score = match_score(blend=blend, whole_portfolio_fund=founders, eligible_funds=universe)
        # L1 = |100-60| + |0-40| = 80% → score = 1 - 0.4 = 0.6
        assert score == pytest.approx(0.6)

    def test_score_in_unit_interval(self, universe: list[FundAssumption]) -> None:
        founders = next(f for f in universe if f.id == "SH-Fnd")
        for blend in [
            {"SH-Sav": 1.0},
            {"SH-Eq": 0.6, "SH-Inc": 0.4},
            {"SH-Eq": 0.9, "SH-Inc": 0.1},
            {"SH-Glb": 0.3, "SH-Eq": 0.3, "SH-Inc": 0.4},
        ]:
            score = match_score(
                blend=blend,
                whole_portfolio_fund=founders,
                eligible_funds=universe,
            )
            assert 0.0 <= score <= 1.0

    def test_non_whole_portfolio_target_rejected(self, universe: list[FundAssumption]) -> None:
        eq = next(f for f in universe if f.id == "SH-Eq")
        with pytest.raises(ValueError, match="whole_portfolio"):
            match_score(
                blend={"SH-Eq": 1.0},
                whole_portfolio_fund=eq,
                eligible_funds=universe,
            )


class TestCollapseSuggestion:
    def test_high_match_returns_suggestion(self, universe: list[FundAssumption]) -> None:
        # Blend that closely matches Founders (60% Eq / 40% FI):
        # SH-Eq 50% + SH-Inc 53.33% → 0.5*1.0 + 0.5333*0.25 = 50%+13.33%=63.33% Eq;
        # 0.5333*0.75 = 40% FI. Slight equity surplus.
        blend = {"SH-Eq": 0.5, "SH-Inc": 0.5333}
        suggestion = collapse_suggestion(blend=blend, eligible_funds=universe, threshold=0.90)
        assert suggestion is not None
        assert suggestion.suggested_fund_id == "SH-Fnd"
        assert suggestion.match_score >= 0.90
        assert "SH-Eq" in suggestion.replaces
        assert "SH-Inc" in suggestion.replaces

    def test_low_match_returns_none(self, universe: list[FundAssumption]) -> None:
        # All-cash blend doesn't match any FoF
        suggestion = collapse_suggestion(
            blend={"SH-Sav": 1.0},
            eligible_funds=universe,
            threshold=0.90,
        )
        assert suggestion is None

    def test_picks_best_match(self, universe: list[FundAssumption]) -> None:
        # 90% Eq / 10% FI matches Builders (90/10) better than Founders (60/40)
        blend = {"SH-Eq": 0.8667, "SH-Inc": 0.1333}
        suggestion = collapse_suggestion(blend=blend, eligible_funds=universe, threshold=0.50)
        assert suggestion is not None
        assert suggestion.suggested_fund_id == "SH-Bld"

    def test_no_whole_portfolio_in_universe(self) -> None:
        # Universe with only building blocks → no suggestion possible
        universe = [
            _building_block("SH-Eq", "Equity", {"equity": 1.0}),
            _building_block("SH-Inc", "Income", {"fixed_income": 1.0}),
        ]
        suggestion = collapse_suggestion(
            blend={"SH-Eq": 0.5, "SH-Inc": 0.5},
            eligible_funds=universe,
        )
        assert suggestion is None

    def test_threshold_validation(self, universe: list[FundAssumption]) -> None:
        with pytest.raises(ValueError, match="threshold"):
            collapse_suggestion(
                blend={"SH-Eq": 1.0},
                eligible_funds=universe,
                threshold=1.5,
            )

    def test_default_threshold(self) -> None:
        assert DEFAULT_COLLAPSE_THRESHOLD == 0.92

    def test_replaces_excludes_zero_weights(self, universe: list[FundAssumption]) -> None:
        blend = {"SH-Eq": 0.5, "SH-Inc": 0.5333, "SH-Sav": 0.0}
        suggestion = collapse_suggestion(blend=blend, eligible_funds=universe, threshold=0.50)
        assert suggestion is not None
        assert "SH-Sav" not in suggestion.replaces
