"""v36 8-fund universe tests (locked decision #3)."""

from __future__ import annotations

import pytest
from engine.sleeves import (
    FUND_NAMES,
    SLEEVE_COLOR_HEX,
    SLEEVE_REF_POINTS,
    STEADYHAND_PURE_SLEEVES,
)


class TestEightFundUniverse:
    """All 8 v36 funds present and uniquely identified."""

    def test_eight_sleeves(self) -> None:
        assert len(STEADYHAND_PURE_SLEEVES) == 8

    def test_unique_ids(self) -> None:
        ids = [s.id for s in STEADYHAND_PURE_SLEEVES]
        assert len(ids) == len(set(ids))

    def test_includes_founders_and_builders(self) -> None:
        ids = {s.id for s in STEADYHAND_PURE_SLEEVES}
        assert "founders_fund" in ids
        assert "builders_fund" in ids


class TestSleeveRefPoints:
    """Calibration reference table at canonical risk score points."""

    def test_six_score_points(self) -> None:
        assert sorted(SLEEVE_REF_POINTS.keys()) == [5, 15, 25, 35, 45, 50]

    @pytest.mark.parametrize("score", [5, 15, 25, 35, 45, 50])
    def test_each_point_sums_to_100(self, score: int) -> None:
        mix = SLEEVE_REF_POINTS[score]
        assert sum(mix.values()) == 100, (
            f"Score {score} mix sums to {sum(mix.values())}, not 100. Mix: {mix}"
        )

    def test_each_point_has_all_eight_funds(self) -> None:
        expected_funds = {
            "SH-Sav",
            "SH-Inc",
            "SH-Eq",
            "SH-Glb",
            "SH-SC",
            "SH-GSC",
            "SH-Fnd",
            "SH-Bld",
        }
        for score, mix in SLEEVE_REF_POINTS.items():
            assert set(mix.keys()) == expected_funds, (
                f"Score {score} missing funds: {expected_funds - set(mix.keys())}"
            )

    def test_cash_decreases_with_aggression(self) -> None:
        # Higher score → less cash exposure
        cash_by_score = [(s, SLEEVE_REF_POINTS[s]["SH-Sav"]) for s in [5, 15, 25, 35, 45, 50]]
        cash_values = [c for _, c in cash_by_score]
        assert all(a >= b for a, b in zip(cash_values, cash_values[1:], strict=False))

    def test_equity_increases_with_aggression(self) -> None:
        # Higher score → more direct equity (SH-Eq + SH-Glb + SH-SC + SH-GSC)
        equity_by_score = []
        for score in [5, 15, 25, 35, 45, 50]:
            mix = SLEEVE_REF_POINTS[score]
            equity_by_score.append(mix["SH-Eq"] + mix["SH-Glb"] + mix["SH-SC"] + mix["SH-GSC"])
        assert all(a <= b for a, b in zip(equity_by_score, equity_by_score[1:], strict=False))


class TestColorAndNameCoverage:
    def test_color_hex_covers_all_eight(self) -> None:
        assert set(SLEEVE_COLOR_HEX.keys()) == {
            "SH-Sav",
            "SH-Inc",
            "SH-Eq",
            "SH-Glb",
            "SH-SC",
            "SH-GSC",
            "SH-Fnd",
            "SH-Bld",
        }
        # All values are 7-char hex strings starting with '#'.
        for fund_id, hex_value in SLEEVE_COLOR_HEX.items():
            assert hex_value.startswith("#"), f"{fund_id}: {hex_value}"
            assert len(hex_value) == 7, f"{fund_id}: {hex_value}"

    def test_fund_names_covers_all_eight(self) -> None:
        assert set(FUND_NAMES.keys()) == {
            "SH-Sav",
            "SH-Inc",
            "SH-Eq",
            "SH-Glb",
            "SH-SC",
            "SH-GSC",
            "SH-Fnd",
            "SH-Bld",
        }
        for fund_id, name in FUND_NAMES.items():
            assert name.startswith("Steadyhand "), f"{fund_id}: {name}"
