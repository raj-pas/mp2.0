"""Household risk profile composition (canon §4.2 + v36 mockup methodology).

Computes Tolerance (T), Capacity (C), household profile bucket, and the 0-50
anchor used as the starting point for goal-level risk scoring (canon §4.3a +
mockup Section 2).

Canon §9.4.2 boundary: this module imports only stdlib + pydantic + engine.*.
Canon §4.2 invariant: time horizon is NOT a component of the risk score; it
belongs in the duration framework (canon §4.3d, engine/optimizer.py).

# TODO(canon §4.6a): External holdings risk-tolerance dampener is NOT
# implemented in this rewrite. Per the 2026-04-30 plan (locked decision #11),
# the v36 mockup itself does not implement a risk-score dampener; it instead
# applies a projection-time drift penalty (mu * 0.85, sigma * 1.15 for
# external) — that lives in engine/projections.py. The canon §4.6a household
# risk-tolerance dampener requires a team-confirmed formula and is a Phase B
# work item. See docs/agent/open-questions.md "Code Drift vs Canon".
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Configurable calibration constants (locked decision #10 — adopt mockup
# defaults as named constants; Lori-driven changes are single-line edits).
# Sources: v36 mockup methodology Section 1 worked example + context pack.
# ---------------------------------------------------------------------------

# Q1 — Tolerance slider (0-10) — score = Q1 * Q1_SCORE_MULTIPLIER (0-100).
Q1_SCORE_MULTIPLIER = 10

# Q2 — Stress-response choice (A/B/C/D) → 0-100 score.
Q2_SCORE_BY_CHOICE: dict[str, int] = {"A": 10, "B": 50, "C": 70, "D": 90}

# Q3 — Stressor count (0-4 selected) — score = count * Q3_SCORE_PER_STRESSOR.
Q3_SCORE_PER_STRESSOR = 25
Q3_MAX_STRESSORS = 4

# Q4 — Capacity choice (A/B/C/D) → 0-100 score (this IS C directly).
Q4_SCORE_BY_CHOICE: dict[str, int] = {"A": 10, "B": 50, "C": 70, "D": 90}

# Tolerance composition weights (sum to 1.0).
TOLERANCE_WEIGHTS = {"q1": 0.5, "q2": 0.3, "q3": 0.2}

# Household-profile bucket thresholds on 0-100 score scale (mockup
# methodology Section 1). Edges are inclusive of the upper bound: <=20 →
# CAUTIOUS, etc. Canon-aligned descriptors per locked decision #5.
PROFILE_BUCKET_THRESHOLDS: list[tuple[int, str]] = [
    (20, "Cautious"),
    (40, "Conservative-balanced"),
    (60, "Balanced"),
    (80, "Balanced-growth"),
    (100, "Growth-oriented"),
]

# Map descriptor -> canon 1-5 score (locked decision #5 + canon §4.2).
DESCRIPTOR_TO_SCORE_1_5: dict[str, int] = {
    "Cautious": 1,
    "Conservative-balanced": 2,
    "Balanced": 3,
    "Balanced-growth": 4,
    "Growth-oriented": 5,
}

SCORE_1_5_TO_DESCRIPTOR: dict[int, str] = {v: k for k, v in DESCRIPTOR_TO_SCORE_1_5.items()}

# Anchor scale upper bound (0-50, used by goal_scoring).
ANCHOR_SCALE_MAX = 50

ProfileDescriptor = Literal[
    "Cautious",
    "Conservative-balanced",
    "Balanced",
    "Balanced-growth",
    "Growth-oriented",
]


class RiskProfileInput(BaseModel):
    """Raw Q1-Q4 inputs from the wizard or stored RiskProfile row."""

    model_config = ConfigDict(extra="forbid")

    q1: int = Field(ge=0, le=10, description="Tolerance slider 0-10")
    q2: Literal["A", "B", "C", "D"]
    q3: list[str] = Field(
        default_factory=list,
        description="Stressor codes selected (e.g., ['biz', 'moved']).",
    )
    q4: Literal["A", "B", "C", "D"]


class RiskProfileResult(BaseModel):
    """Computed household risk profile.

    Goal_50 + T/C are internal engine intermediates per locked decision #6 —
    they appear on this struct so server-side code can introspect, but the
    DRF preview endpoint serializer drops Goal_50 and exposes only
    ``score_1_5`` + ``descriptor`` to the UI.
    """

    model_config = ConfigDict(extra="forbid")

    tolerance_score: float = Field(ge=0, le=100)
    capacity_score: float = Field(ge=0, le=100)
    tolerance_descriptor: ProfileDescriptor
    capacity_descriptor: ProfileDescriptor
    household_descriptor: ProfileDescriptor
    score_1_5: int = Field(ge=1, le=5)
    anchor: float = Field(ge=0, le=ANCHOR_SCALE_MAX)
    flags: list[str] = Field(default_factory=list)


def compute_tolerance(q1: int, q2: str, q3_count: int) -> float:
    """T = 0.5*Q1_score + 0.3*Q2_score + 0.2*Q3_score (mockup methodology §1)."""

    if not 0 <= q1 <= 10:
        raise ValueError(f"q1 must be 0-10, got {q1}")
    if q2 not in Q2_SCORE_BY_CHOICE:
        raise ValueError(f"q2 must be one of {sorted(Q2_SCORE_BY_CHOICE)}, got {q2}")
    if not 0 <= q3_count <= Q3_MAX_STRESSORS:
        raise ValueError(f"q3_count must be 0-{Q3_MAX_STRESSORS}, got {q3_count}")

    q1_score = q1 * Q1_SCORE_MULTIPLIER
    q2_score = Q2_SCORE_BY_CHOICE[q2]
    q3_score = q3_count * Q3_SCORE_PER_STRESSOR

    return (
        TOLERANCE_WEIGHTS["q1"] * q1_score
        + TOLERANCE_WEIGHTS["q2"] * q2_score
        + TOLERANCE_WEIGHTS["q3"] * q3_score
    )


def compute_capacity(q4: str) -> float:
    """C = Q4_score (mockup methodology §1)."""

    if q4 not in Q4_SCORE_BY_CHOICE:
        raise ValueError(f"q4 must be one of {sorted(Q4_SCORE_BY_CHOICE)}, got {q4}")
    return float(Q4_SCORE_BY_CHOICE[q4])


def descriptor_for_score(score: float) -> ProfileDescriptor:
    """Map a 0-100 score onto a canon-aligned 5-band descriptor."""

    if not 0 <= score <= 100:
        raise ValueError(f"score must be 0-100, got {score}")
    for upper, descriptor in PROFILE_BUCKET_THRESHOLDS:
        if score <= upper:
            return descriptor  # type: ignore[return-value]
    return "Growth-oriented"


def descriptor_to_score_1_5(descriptor: str) -> int:
    """Canon 1-5 score for a descriptor (locked decision #5)."""

    if descriptor not in DESCRIPTOR_TO_SCORE_1_5:
        raise ValueError(f"unknown descriptor: {descriptor}")
    return DESCRIPTOR_TO_SCORE_1_5[descriptor]


def score_1_5_to_descriptor(score: int) -> ProfileDescriptor:
    if score not in SCORE_1_5_TO_DESCRIPTOR:
        raise ValueError(f"score must be 1-5, got {score}")
    return SCORE_1_5_TO_DESCRIPTOR[score]  # type: ignore[return-value]


def compute_anchor(tolerance: float, capacity: float) -> float:
    """anchor = min(T, C) / 2 (mockup methodology §2)."""

    if not 0 <= tolerance <= 100:
        raise ValueError(f"tolerance must be 0-100, got {tolerance}")
    if not 0 <= capacity <= 100:
        raise ValueError(f"capacity must be 0-100, got {capacity}")
    return min(tolerance, capacity) / 2


def _consistency_flags(q1: int, q2: str) -> list[str]:
    """Surface consistency contradictions per mockup wizard step 2 logic."""

    flags: list[str] = []
    # High-tolerance Q1 paired with high-anxiety Q2=A is contradictory.
    if q1 >= 7 and q2 == "A":
        flags.append("tolerance_contradiction")
    return flags


def compute_risk_profile(inputs: RiskProfileInput) -> RiskProfileResult:
    """End-to-end profile computation.

    Returns the canon 1-5 score + descriptor (advisor-visible) plus the
    anchor (used internally by goal_scoring) plus the 0-100 T/C scores
    (internal engine intermediates per locked decision #6).
    """

    q3_count = min(len(inputs.q3), Q3_MAX_STRESSORS)
    tolerance = compute_tolerance(inputs.q1, inputs.q2, q3_count)
    capacity = compute_capacity(inputs.q4)

    tolerance_descriptor = descriptor_for_score(tolerance)
    capacity_descriptor = descriptor_for_score(capacity)

    # Final household profile = the more conservative of T-bucket and C-bucket.
    tolerance_rank = descriptor_to_score_1_5(tolerance_descriptor)
    capacity_rank = descriptor_to_score_1_5(capacity_descriptor)
    household_rank = min(tolerance_rank, capacity_rank)
    household_descriptor = score_1_5_to_descriptor(household_rank)

    anchor = compute_anchor(tolerance, capacity)
    flags = _consistency_flags(inputs.q1, inputs.q2)

    return RiskProfileResult(
        tolerance_score=tolerance,
        capacity_score=capacity,
        tolerance_descriptor=tolerance_descriptor,
        capacity_descriptor=capacity_descriptor,
        household_descriptor=household_descriptor,
        score_1_5=household_rank,
        anchor=anchor,
        flags=flags,
    )
