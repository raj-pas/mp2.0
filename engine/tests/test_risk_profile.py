"""Parity tests for engine/risk_profile.py vs v36 mockup methodology §1+§2."""

from __future__ import annotations

import pytest
from engine.risk_profile import (
    Q2_SCORE_BY_CHOICE,
    Q4_SCORE_BY_CHOICE,
    RiskProfileInput,
    compute_anchor,
    compute_capacity,
    compute_risk_profile,
    compute_tolerance,
    descriptor_for_score,
    descriptor_to_score_1_5,
    score_1_5_to_descriptor,
)


class TestHayesWorkedExample:
    """Methodology §1 Hayes household: Q1=5, Q2=B, Q3=1 stressor, Q4=B.

    Expected per the mockup methodology section: T=45, C=50, profile=Balanced,
    anchor=22.5. With canon-aligned vocab (locked decision #5), the profile
    label is unchanged ("Balanced" in both vocabularies).
    """

    def test_tolerance_45(self) -> None:
        # 0.5 * (5 * 10) + 0.3 * 50 + 0.2 * (1 * 25) = 25 + 15 + 5 = 45
        assert compute_tolerance(q1=5, q2="B", q3_count=1) == pytest.approx(45.0)

    def test_capacity_50(self) -> None:
        assert compute_capacity(q4="B") == pytest.approx(50.0)

    def test_anchor_22_5(self) -> None:
        assert compute_anchor(tolerance=45.0, capacity=50.0) == pytest.approx(22.5)

    def test_full_profile(self) -> None:
        result = compute_risk_profile(
            RiskProfileInput(q1=5, q2="B", q3=["career"], q4="B"),
        )
        assert result.tolerance_score == pytest.approx(45.0)
        assert result.capacity_score == pytest.approx(50.0)
        assert result.tolerance_descriptor == "Balanced"
        assert result.capacity_descriptor == "Balanced"
        assert result.household_descriptor == "Balanced"
        assert result.score_1_5 == 3  # Balanced
        assert result.anchor == pytest.approx(22.5)
        assert result.flags == []


class TestDescriptorBoundaries:
    """0-100 → 5-band canon descriptor mapping."""

    @pytest.mark.parametrize(
        "score, expected",
        [
            (0, "Cautious"),
            (10, "Cautious"),
            (20, "Cautious"),  # Inclusive upper bound
            (21, "Conservative-balanced"),
            (40, "Conservative-balanced"),
            (41, "Balanced"),
            (60, "Balanced"),
            (61, "Balanced-growth"),
            (80, "Balanced-growth"),
            (81, "Growth-oriented"),
            (100, "Growth-oriented"),
        ],
    )
    def test_descriptor_thresholds(self, score: int, expected: str) -> None:
        assert descriptor_for_score(score) == expected


class TestCanonScoreMapping:
    @pytest.mark.parametrize(
        "descriptor, score",
        [
            ("Cautious", 1),
            ("Conservative-balanced", 2),
            ("Balanced", 3),
            ("Balanced-growth", 4),
            ("Growth-oriented", 5),
        ],
    )
    def test_descriptor_to_score(self, descriptor: str, score: int) -> None:
        assert descriptor_to_score_1_5(descriptor) == score
        assert score_1_5_to_descriptor(score) == descriptor


class TestHouseholdBucketIsMin:
    """household_bucket = min(T_bucket, C_bucket) (mockup methodology §1)."""

    def test_min_when_capacity_lower(self) -> None:
        # T=80 (Balanced-growth, rank 4), C=20 (Cautious, rank 1) → min=Cautious
        result = compute_risk_profile(
            # Q1=10 (q1_score=100), Q2=D (q2_score=90), Q3=4 (q3_score=100)
            # T = 0.5*100 + 0.3*90 + 0.2*100 = 50 + 27 + 20 = 97 → Growth-oriented
            # Use a profile that gets T=80: Q1=10, Q2=B (50), Q3=2 → 50+15+10=75
            # Adjust: Q1=10, Q2=C (70), Q3=1 → 50+21+5 = 76 → Balanced-growth
            # For exact T=80: 0.5*100 + 0.3*70 + 0.2*45 = 50+21+9=80; q3_count=1.8 NA
            # Use approximate: Q1=10, Q2=C, Q3=2 → 50+21+10 = 81 → Growth-oriented
            # Just use a clearly higher T:
            RiskProfileInput(q1=10, q2="C", q3=["biz", "moved"], q4="A"),
        )
        # T = 0.5*100 + 0.3*70 + 0.2*50 = 50 + 21 + 10 = 81 → Growth-oriented (5)
        # C = 10 → Cautious (1)
        # min(5, 1) = 1 → Cautious
        assert result.tolerance_descriptor == "Growth-oriented"
        assert result.capacity_descriptor == "Cautious"
        assert result.household_descriptor == "Cautious"
        assert result.score_1_5 == 1

    def test_min_when_tolerance_lower(self) -> None:
        # Q1=0, Q2=A, Q3=0 → T=0+3+0=3 → Cautious
        # Q4=D → C=90 → Growth-oriented
        result = compute_risk_profile(
            RiskProfileInput(q1=0, q2="A", q3=[], q4="D"),
        )
        # T = 0.5*0 + 0.3*10 + 0.2*0 = 3 → Cautious
        # C = 90 → Growth-oriented
        assert result.tolerance_descriptor == "Cautious"
        assert result.capacity_descriptor == "Growth-oriented"
        assert result.household_descriptor == "Cautious"
        assert result.score_1_5 == 1


class TestConsistencyFlags:
    def test_high_tolerance_with_anxious_response_flagged(self) -> None:
        # Q1>=7 + Q2=A is contradictory.
        result = compute_risk_profile(
            RiskProfileInput(q1=8, q2="A", q3=[], q4="C"),
        )
        assert "tolerance_contradiction" in result.flags

    def test_no_flag_when_consistent(self) -> None:
        result = compute_risk_profile(
            RiskProfileInput(q1=5, q2="B", q3=["career"], q4="B"),
        )
        assert result.flags == []


class TestInputValidation:
    def test_q1_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="q1"):
            compute_tolerance(q1=11, q2="B", q3_count=1)
        with pytest.raises(ValueError, match="q1"):
            compute_tolerance(q1=-1, q2="B", q3_count=1)

    def test_q2_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="q2"):
            compute_tolerance(q1=5, q2="E", q3_count=1)

    def test_q3_count_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="q3_count"):
            compute_tolerance(q1=5, q2="B", q3_count=-1)

    def test_q3_count_above_max_raises(self) -> None:
        with pytest.raises(ValueError, match="q3_count"):
            compute_tolerance(q1=5, q2="B", q3_count=10)

    def test_q4_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="q4"):
            compute_capacity(q4="Z")

    def test_q3_truncated_to_max(self) -> None:
        """Stressor list longer than Q3_MAX_STRESSORS is capped, not rejected."""

        result = compute_risk_profile(
            RiskProfileInput(
                q1=5,
                q2="B",
                # 5 stressors but max is 4
                q3=["a", "b", "c", "d", "e"],
                q4="B",
            ),
        )
        # T should match q3_count=4: 0.5*50 + 0.3*50 + 0.2*100 = 25+15+20 = 60
        assert result.tolerance_score == pytest.approx(60.0)


class TestConfigurableConstants:
    """Ensures named constants exist and are addressable for Lori-driven tuning."""

    def test_q2_choices_complete(self) -> None:
        assert set(Q2_SCORE_BY_CHOICE.keys()) == {"A", "B", "C", "D"}

    def test_q4_choices_complete(self) -> None:
        assert set(Q4_SCORE_BY_CHOICE.keys()) == {"A", "B", "C", "D"}
