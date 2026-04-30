"""Goal-level risk scoring (canon §4.3a, §6.5 + v36 mockup methodology §3-5).

Computes Goal_50 (anchor + tier shift + size shift), applies horizon cap, and
resolves the effective bucket considering any advisor override.

**Per locked decision #6 (2026-04-30 plan):** Goal_50 is an *internal engine
intermediate* and is never returned by API endpoints or shown in UI. The
advisor-visible surface is the canon 1-5 score + canon-aligned descriptor
(Cautious / Conservative-balanced / Balanced / Balanced-growth /
Growth-oriented). All API-shaped functions in this module return
``ResolvedGoalScore`` which intentionally omits the raw 0-50 number.

Canon §9.4.2 boundary: this module imports only stdlib + pydantic + engine.*.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from engine.risk_profile import (
    ProfileDescriptor,
    descriptor_to_score_1_5,
    score_1_5_to_descriptor,
)

# ---------------------------------------------------------------------------
# Configurable calibration constants (locked decision #10).
# Lori-driven changes are single-line edits.
# ---------------------------------------------------------------------------

#: Tier-driven shift on Goal_50. Need = more conservative; Wish = more growth.
IMP_SHIFT: dict[str, int] = {
    "need": -10,
    "want": 0,
    "wish": 8,
    "unsure": 0,
}

#: Size-driven shift. Larger goals (% of household AUM) tilt more conservative.
#: Each row is ``(threshold, shift)`` where threshold is the lower bound (>=).
#: Sorted descending — first row whose threshold is met wins.
SIZE_SHIFT_TABLE: list[tuple[float, int]] = [
    (0.50, -6),
    (0.20, -2),
    (0.10, 0),
    (0.05, 3),
    (0.0, 6),
]

#: Map ``Goal.necessity_score`` (1-5) to tier label.
NECESSITY_TO_TIER: dict[int | None, str] = {
    5: "need",
    4: "need",
    3: "want",
    2: "wish",
    1: "wish",
    None: "unsure",
}

#: Goal_50 bucket thresholds (0-50 scale). Inclusive upper bounds.
#: Canon-aligned descriptors per locked decision #5.
GOAL_50_BUCKET_THRESHOLDS: list[tuple[int, str]] = [
    (10, "Cautious"),
    (20, "Conservative-balanced"),
    (30, "Balanced"),
    (40, "Balanced-growth"),
    (50, "Growth-oriented"),
]

#: Horizon cap thresholds in years. ``threshold`` is upper bound exclusive
#: in the original mockup ("<3" / "3-5" / etc.) — translated here to
#: inclusive upper edges for clarity. >20y → no effective cap.
HORIZON_CAP_THRESHOLDS: list[tuple[float, str]] = [
    (2.999, "Cautious"),
    (5.0, "Conservative-balanced"),
    (10.0, "Balanced"),
    (20.0, "Balanced-growth"),
    (float("inf"), "Growth-oriented"),
]

#: Goal_50 clamp bounds (mockup §3 formula).
GOAL_50_MIN = 1.0
GOAL_50_MAX = 50.0

Tier = Literal["need", "want", "wish", "unsure"]


class GoalRiskOverride(BaseModel):
    """Advisor override of the system-derived bucket (canon §6.5).

    Override operates exclusively on the canon 1-5 + descriptor surface
    per locked decision #6. Rationale required + audit-trailed at the API
    layer (locked decision #37).
    """

    model_config = ConfigDict(extra="forbid")

    score_1_5: int = Field(ge=1, le=5)
    descriptor: ProfileDescriptor
    rationale: str = Field(min_length=10)


class ResolvedGoalScore(BaseModel):
    """Advisor-visible output. Goal_50 intentionally omitted (locked #6)."""

    model_config = ConfigDict(extra="forbid")

    score_1_5: int = Field(ge=1, le=5)
    descriptor: ProfileDescriptor
    system_descriptor: ProfileDescriptor
    horizon_cap_descriptor: ProfileDescriptor
    uncapped_descriptor: ProfileDescriptor
    is_horizon_cap_binding: bool
    is_overridden: bool
    derivation: dict[str, float]
    """{"anchor": float, "imp_shift": int, "size_shift": int} — for explainability."""


def tier_for_necessity(necessity_score: int | None) -> Tier:
    """Map ``Goal.necessity_score`` (1-5) to tier label."""

    if necessity_score is not None and necessity_score not in NECESSITY_TO_TIER:
        raise ValueError(f"necessity_score must be 1-5 or None, got {necessity_score}")
    return NECESSITY_TO_TIER[necessity_score]  # type: ignore[return-value]


def imp_shift_for_tier(tier: Tier) -> int:
    if tier not in IMP_SHIFT:
        raise ValueError(f"tier must be one of {sorted(IMP_SHIFT)}, got {tier}")
    return IMP_SHIFT[tier]


def size_shift_for_pct(goal_pct_of_aum: float) -> int:
    """Shift derived from goal $ value as a fraction of household AUM."""

    if goal_pct_of_aum < 0:
        raise ValueError(f"goal_pct_of_aum must be >= 0, got {goal_pct_of_aum}")
    for threshold, shift in SIZE_SHIFT_TABLE:
        if goal_pct_of_aum >= threshold:
            return shift
    return SIZE_SHIFT_TABLE[-1][1]


def compute_goal_50(
    *,
    anchor: float,
    tier: Tier,
    goal_amount: float,
    household_aum: float,
) -> float:
    """Goal_50 = clip(anchor + impShift + sizeShift, 1, 50).

    INTERNAL ONLY (locked decision #6). Do not return this value in API
    responses or display in UI; use ``effective_score_and_descriptor()`` for
    advisor-facing surfaces.
    """

    if anchor < 0 or anchor > 50:
        raise ValueError(f"anchor must be 0-50, got {anchor}")
    if goal_amount < 0:
        raise ValueError(f"goal_amount must be >= 0, got {goal_amount}")
    if household_aum <= 0:
        raise ValueError(f"household_aum must be > 0, got {household_aum}")

    pct = goal_amount / household_aum
    raw = anchor + imp_shift_for_tier(tier) + size_shift_for_pct(pct)
    return max(GOAL_50_MIN, min(GOAL_50_MAX, raw))


def goal_50_to_descriptor(goal_50: float) -> ProfileDescriptor:
    """Map Goal_50 (0-50) to canon-aligned 5-band descriptor."""

    if goal_50 < 0 or goal_50 > 50:
        raise ValueError(f"goal_50 must be 0-50, got {goal_50}")
    for upper, descriptor in GOAL_50_BUCKET_THRESHOLDS:
        if goal_50 <= upper:
            return descriptor  # type: ignore[return-value]
    return "Growth-oriented"


def horizon_cap_descriptor(horizon_years: float) -> ProfileDescriptor:
    """Horizon-driven ceiling on the goal's bucket (mockup §4)."""

    if horizon_years < 0:
        raise ValueError(f"horizon_years must be >= 0, got {horizon_years}")
    for upper, descriptor in HORIZON_CAP_THRESHOLDS:
        if horizon_years <= upper:
            return descriptor  # type: ignore[return-value]
    return "Growth-oriented"


def effective_score_and_descriptor(
    *,
    anchor: float,
    necessity_score: int | None,
    goal_amount: float,
    household_aum: float,
    horizon_years: float,
    override: GoalRiskOverride | None = None,
) -> ResolvedGoalScore:
    """Resolve the effective canon 1-5 risk score for a goal.

    Pipeline:
        Goal_50 (internal) -> uncapped descriptor -> system descriptor =
        min(uncapped, horizon_cap) -> effective = override or system.
    Returns canon 1-5 + descriptor + derivation breakdown.
    """

    tier = tier_for_necessity(necessity_score)
    imp = imp_shift_for_tier(tier)
    pct = goal_amount / household_aum if household_aum > 0 else 0.0
    size = size_shift_for_pct(pct)

    goal_50 = compute_goal_50(
        anchor=anchor,
        tier=tier,
        goal_amount=goal_amount,
        household_aum=household_aum,
    )

    uncapped = goal_50_to_descriptor(goal_50)
    horizon_cap = horizon_cap_descriptor(horizon_years)

    uncapped_rank = descriptor_to_score_1_5(uncapped)
    horizon_rank = descriptor_to_score_1_5(horizon_cap)
    system_rank = min(uncapped_rank, horizon_rank)
    system_descriptor = score_1_5_to_descriptor(system_rank)

    is_horizon_cap_binding = uncapped_rank > horizon_rank

    if override is not None:
        effective_rank = override.score_1_5
        effective_descriptor = override.descriptor
        if score_1_5_to_descriptor(effective_rank) != effective_descriptor:
            raise ValueError(
                "override.score_1_5 and override.descriptor disagree: "
                f"score={effective_rank}, descriptor={effective_descriptor}"
            )
        is_overridden = True
    else:
        effective_rank = system_rank
        effective_descriptor = system_descriptor
        is_overridden = False

    return ResolvedGoalScore(
        score_1_5=effective_rank,
        descriptor=effective_descriptor,
        system_descriptor=system_descriptor,
        horizon_cap_descriptor=horizon_cap,
        uncapped_descriptor=uncapped,
        is_horizon_cap_binding=is_horizon_cap_binding,
        is_overridden=is_overridden,
        derivation={
            "anchor": anchor,
            "imp_shift": imp,
            "size_shift": size,
        },
    )
