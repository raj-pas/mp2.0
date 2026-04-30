"""Parity tests for engine/goal_scoring.py vs v36 mockup methodology §3-5."""

from __future__ import annotations

import pytest
from engine.goal_scoring import (
    GOAL_50_BUCKET_THRESHOLDS,
    HORIZON_CAP_THRESHOLDS,
    IMP_SHIFT,
    NECESSITY_TO_TIER,
    SIZE_SHIFT_TABLE,
    GoalRiskOverride,
    compute_goal_50,
    effective_score_and_descriptor,
    goal_50_to_descriptor,
    horizon_cap_descriptor,
    imp_shift_for_tier,
    size_shift_for_pct,
    tier_for_necessity,
)


class TestHayesRetirementWorkedExample:
    """Mockup methodology §3 Hayes Retirement: anchor=18, Need-tier, 47% size,
    horizon=32y. Expected: Goal_50=6 (internal), uncapped=Cautious,
    horizon_cap=Growth-oriented, system=Cautious, effective=Cautious.
    Canon-relabeled per locked decision #5: 'Conservative' becomes 'Cautious'.
    """

    def test_internal_goal_50_is_6(self) -> None:
        # 18 + (-10 Need) + (-2 size in 20-50% band) = 6
        goal_50 = compute_goal_50(
            anchor=18.0,
            tier="need",
            goal_amount=82.0,
            household_aum=175.0,
        )
        assert goal_50 == pytest.approx(6.0)

    def test_full_resolution(self) -> None:
        result = effective_score_and_descriptor(
            anchor=18.0,
            necessity_score=5,  # Need
            goal_amount=82.0,
            household_aum=175.0,
            horizon_years=32.0,
        )
        # Goal_50 = 6 → uncapped Cautious (canon)
        # horizon_cap = Growth-oriented (>20y)
        # system = min(Cautious, Growth-oriented) = Cautious
        assert result.uncapped_descriptor == "Cautious"
        assert result.horizon_cap_descriptor == "Growth-oriented"
        assert result.system_descriptor == "Cautious"
        assert result.descriptor == "Cautious"
        assert result.score_1_5 == 1
        assert result.is_horizon_cap_binding is False  # uncapped already conservative
        assert result.is_overridden is False
        assert result.derivation == {
            "anchor": 18.0,
            "imp_shift": -10,
            "size_shift": -2,
        }


class TestChoiTravelWorkedExample:
    """Mockup methodology §6 Choi Travel: anchor=25, Want-tier, +3 size shift,
    horizon=8y. Expected: Goal_50=28 (internal), uncapped=Balanced,
    horizon_cap=Balanced (6-10y), system=Balanced.
    """

    def test_internal_goal_50_is_28(self) -> None:
        # anchor=25 + 0 (Want) + 3 (size 5-10%) = 28
        # To get +3 size shift: pct in [0.05, 0.10) — use goal=$80k, aum=$1000k → 8%
        goal_50 = compute_goal_50(
            anchor=25.0,
            tier="want",
            goal_amount=80.0,
            household_aum=1000.0,
        )
        assert goal_50 == pytest.approx(28.0)

    def test_full_resolution(self) -> None:
        result = effective_score_and_descriptor(
            anchor=25.0,
            necessity_score=3,  # Want
            goal_amount=80.0,
            household_aum=1000.0,
            horizon_years=8.0,
        )
        assert result.uncapped_descriptor == "Balanced"
        assert result.horizon_cap_descriptor == "Balanced"
        assert result.system_descriptor == "Balanced"
        assert result.descriptor == "Balanced"
        assert result.score_1_5 == 3


class TestHorizonCapBinding:
    """Mockup §4 Hayes Home goal: horizon=3y → cap=Conservative-balanced
    (canon for 3-5y band). If Goal_50 → Balanced or higher, cap binds.
    """

    def test_short_horizon_caps_aggressive_score(self) -> None:
        # anchor=40 + 8 (Wish) + 6 (very small) = 54 → clipped to 50 → Growth-oriented
        # horizon=2y → cap=Cautious (<3y band)
        result = effective_score_and_descriptor(
            anchor=40.0,
            necessity_score=1,  # Wish
            goal_amount=10.0,
            household_aum=1000.0,
            horizon_years=2.0,
        )
        assert result.uncapped_descriptor == "Growth-oriented"
        assert result.horizon_cap_descriptor == "Cautious"
        assert result.system_descriptor == "Cautious"
        assert result.is_horizon_cap_binding is True

    def test_long_horizon_no_cap_binding(self) -> None:
        # Hayes Retirement again — horizon-cap doesn't bind
        result = effective_score_and_descriptor(
            anchor=18.0,
            necessity_score=5,
            goal_amount=82.0,
            household_aum=175.0,
            horizon_years=32.0,
        )
        assert result.is_horizon_cap_binding is False


class TestOverrideFlow:
    """Locked decision #6: override operates on canon 1-5 + descriptor."""

    def test_override_wins_over_system(self) -> None:
        result = effective_score_and_descriptor(
            anchor=18.0,
            necessity_score=5,
            goal_amount=82.0,
            household_aum=175.0,
            horizon_years=32.0,
            override=GoalRiskOverride(
                score_1_5=4,
                descriptor="Balanced-growth",
                rationale="Client explicitly requested more aggressive blend "
                "after recent inheritance discussion.",
            ),
        )
        assert result.descriptor == "Balanced-growth"
        assert result.score_1_5 == 4
        assert result.is_overridden is True
        # System descriptor still surfaced for transparency
        assert result.system_descriptor == "Cautious"

    def test_override_inconsistent_score_descriptor_rejected(self) -> None:
        with pytest.raises(ValueError, match="disagree"):
            effective_score_and_descriptor(
                anchor=18.0,
                necessity_score=5,
                goal_amount=82.0,
                household_aum=175.0,
                horizon_years=32.0,
                override=GoalRiskOverride(
                    score_1_5=3,  # Balanced
                    descriptor="Growth-oriented",  # Mismatch
                    rationale="Some rationale that is at least 10 chars.",
                ),
            )

    def test_override_rationale_too_short_rejected(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            GoalRiskOverride(
                score_1_5=3,
                descriptor="Balanced",
                rationale="too short",
            )


class TestTierMapping:
    @pytest.mark.parametrize(
        "necessity, tier",
        [
            (5, "need"),
            (4, "need"),
            (3, "want"),
            (2, "wish"),
            (1, "wish"),
            (None, "unsure"),
        ],
    )
    def test_necessity_to_tier(self, necessity: int | None, tier: str) -> None:
        assert tier_for_necessity(necessity) == tier
        assert NECESSITY_TO_TIER[necessity] == tier

    def test_invalid_necessity_raises(self) -> None:
        with pytest.raises(ValueError):
            tier_for_necessity(7)


class TestImpShift:
    @pytest.mark.parametrize(
        "tier, expected",
        [("need", -10), ("want", 0), ("wish", 8), ("unsure", 0)],
    )
    def test_shifts(self, tier: str, expected: int) -> None:
        assert imp_shift_for_tier(tier) == expected  # type: ignore[arg-type]
        assert IMP_SHIFT[tier] == expected


class TestSizeShift:
    @pytest.mark.parametrize(
        "pct, expected",
        [
            (0.55, -6),  # >= 50%
            (0.50, -6),
            (0.30, -2),  # 20-50%
            (0.20, -2),
            (0.15, 0),  # 10-20%
            (0.10, 0),
            (0.07, 3),  # 5-10%
            (0.05, 3),
            (0.02, 6),  # <5%
            (0.0, 6),
        ],
    )
    def test_size_shift_thresholds(self, pct: float, expected: int) -> None:
        assert size_shift_for_pct(pct) == expected

    def test_negative_pct_rejected(self) -> None:
        with pytest.raises(ValueError):
            size_shift_for_pct(-0.1)


class TestGoal50Buckets:
    @pytest.mark.parametrize(
        "goal_50, expected",
        [
            (1.0, "Cautious"),
            (10.0, "Cautious"),
            (10.5, "Conservative-balanced"),
            (20.0, "Conservative-balanced"),
            (20.1, "Balanced"),
            (30.0, "Balanced"),
            (30.5, "Balanced-growth"),
            (40.0, "Balanced-growth"),
            (40.1, "Growth-oriented"),
            (50.0, "Growth-oriented"),
        ],
    )
    def test_descriptor_thresholds(self, goal_50: float, expected: str) -> None:
        assert goal_50_to_descriptor(goal_50) == expected


class TestHorizonCapBuckets:
    @pytest.mark.parametrize(
        "years, expected",
        [
            (0.5, "Cautious"),  # <3y
            (2.0, "Cautious"),
            (3.0, "Conservative-balanced"),  # 3-5y
            (5.0, "Conservative-balanced"),
            (6.0, "Balanced"),  # 6-10y
            (10.0, "Balanced"),
            (11.0, "Balanced-growth"),  # 11-20y
            (20.0, "Balanced-growth"),
            (21.0, "Growth-oriented"),  # >20y
            (50.0, "Growth-oriented"),
        ],
    )
    def test_horizon_thresholds(self, years: float, expected: str) -> None:
        assert horizon_cap_descriptor(years) == expected


class TestClampingAndEdgeCases:
    def test_goal_50_clamped_below_1(self) -> None:
        # anchor=1, Need (-10), <5% (+6) → 1 - 10 + 6 = -3 → clipped to 1
        result = compute_goal_50(
            anchor=1.0,
            tier="need",
            goal_amount=10.0,
            household_aum=1000.0,
        )
        assert result == pytest.approx(1.0)

    def test_goal_50_clamped_above_50(self) -> None:
        # anchor=50, Wish (+8), <5% (+6) → 64 → clipped to 50
        result = compute_goal_50(
            anchor=50.0,
            tier="wish",
            goal_amount=10.0,
            household_aum=1000.0,
        )
        assert result == pytest.approx(50.0)

    def test_zero_household_aum_rejected(self) -> None:
        with pytest.raises(ValueError, match="household_aum"):
            compute_goal_50(
                anchor=20.0,
                tier="want",
                goal_amount=10.0,
                household_aum=0.0,
            )


class TestConfigurableConstants:
    """Locked decision #10: constants are configurable for Lori-driven tuning."""

    def test_size_shift_table_descending(self) -> None:
        thresholds = [t for t, _ in SIZE_SHIFT_TABLE]
        assert thresholds == sorted(thresholds, reverse=True)

    def test_goal_50_thresholds_ascending(self) -> None:
        thresholds = [t for t, _ in GOAL_50_BUCKET_THRESHOLDS]
        assert thresholds == sorted(thresholds)

    def test_horizon_thresholds_ascending(self) -> None:
        thresholds = [t for t, _ in HORIZON_CAP_THRESHOLDS]
        assert thresholds == sorted(thresholds)
