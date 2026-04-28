"""Phase 1 optimizer stub.

The implementation returns realistic-shaped deterministic output while preserving
the locked engine I/O contract. It is not yet the production optimizer.
"""

from __future__ import annotations

from datetime import date
from math import sqrt

from engine.compliance import risk_rating
from engine.schemas import (
    Allocation,
    Constraints,
    EngineOutput,
    EngineRun,
    FanChartPoint,
    Goal,
    GoalBlend,
    Household,
    OptimizationMethod,
    Sleeve,
)

MODEL_VERSION = "phase1_stub_2026_04_28"


def optimize(
    household: Household,
    sleeve_universe: list[Sleeve],
    method: OptimizationMethod = "percentile",
    constraints: Constraints | None = None,
) -> EngineOutput:
    """Return deterministic Phase 1 portfolio output for a household."""

    if not household.goals:
        raise ValueError("household must include at least one goal")
    if not sleeve_universe:
        raise ValueError("sleeve_universe must not be empty")

    constraints = constraints or Constraints()
    goal_blends: list[GoalBlend] = []
    fan_chart: list[FanChartPoint] = []

    for goal in household.goals:
        horizon = _goal_horizon_years(goal)
        allocations = _allocate_for_goal(household, goal, sleeve_universe)
        expected_return = _expected_return(allocations, sleeve_universe)
        volatility = _volatility(allocations, sleeve_universe)
        rating = risk_rating(allocations, sleeve_universe, horizon)
        percentile = _frontier_percentile(household, goal)

        goal_blends.append(
            GoalBlend(
                goal_id=goal.id,
                goal_name=goal.name,
                allocations=allocations,
                expected_return=expected_return,
                volatility=volatility,
                risk_rating=rating,
                frontier_percentile=percentile,
            )
        )
        fan_chart.extend(_fan_chart(goal, expected_return, volatility))

    household_blend = _household_blend(household.goals, goal_blends)
    account_risk_ratings = {
        account.id: risk_rating(
            _account_or_household_blend(account.current_holdings, household_blend), sleeve_universe
        )
        for account in household.accounts
    }
    household_rating = risk_rating(household_blend, sleeve_universe)

    return EngineOutput(
        household_id=household.id,
        goal_blends=goal_blends,
        household_blend=household_blend,
        fan_chart=fan_chart,
        account_risk_ratings=account_risk_ratings,
        household_risk_rating=household_rating,
        audit_trace=EngineRun(
            model_version=MODEL_VERSION,
            method=method,
            params={
                "risk_composite": (
                    "0.65 household risk + 0.35 goal risk; necessity and horizon adjusted"
                ),
                "note": "Illustrative Phase 1 optimizer stub, not production advice.",
            },
            sleeve_assumptions=[sleeve.model_dump(mode="json") for sleeve in sleeve_universe],
            constraints=constraints.model_dump(mode="json"),
        ),
        narrative_summary=(
            "Illustrative Phase 1 output: goal-specific sleeve blends were generated from "
            "household risk, goal risk, necessity, and horizon placeholders."
        ),
    )


def _goal_horizon_years(goal: Goal) -> float:
    days = (goal.target_date - date.today()).days
    return max(days / 365.25, 0.5)


def _frontier_percentile(household: Household, goal: Goal) -> int:
    composite = _risk_composite(household, goal)
    return round(5 + composite * 45)


def _risk_composite(household: Household, goal: Goal) -> float:
    household_component = (household.household_risk_score - 1) / 9
    goal_component = (goal.goal_risk_score - 1) / 4
    return _clamp(0.65 * household_component + 0.35 * goal_component, 0, 1)


def _allocate_for_goal(
    household: Household,
    goal: Goal,
    sleeve_universe: list[Sleeve],
) -> list[Allocation]:
    horizon = _goal_horizon_years(goal)
    risk = _risk_composite(household, goal)
    necessity_drag = goal.necessity_score * 0.045

    if horizon < 3:
        equity_total = _clamp(0.12 + risk * 0.2 - necessity_drag, 0.03, 0.28)
        cash_weight = _clamp(0.58 - risk * 0.12 + necessity_drag, 0.45, 0.78)
    else:
        horizon_lift = min(horizon, 20) * 0.012
        equity_total = _clamp(0.24 + risk * 0.55 + horizon_lift - necessity_drag, 0.1, 0.88)
        cash_weight = _clamp(0.22 - risk * 0.12 - horizon * 0.006 + necessity_drag, 0.04, 0.35)

    fixed_income_weight = _clamp(1 - equity_total - cash_weight, 0.08, 0.68)
    total = equity_total + fixed_income_weight + cash_weight
    equity_total /= total
    fixed_income_weight /= total
    cash_weight /= total

    weights = _empty_weights(sleeve_universe)
    _set_weight(weights, "cash_savings", cash_weight)
    _set_weight(weights, "income_fund", fixed_income_weight)

    equity_sleeves = [
        ("equity_fund", 0.46),
        ("global_equity_fund", 0.34),
        ("canadian_small_cap", 0.1),
        ("global_small_cap", 0.1),
    ]
    for sleeve_id, share in equity_sleeves:
        _set_weight(weights, sleeve_id, equity_total * share)

    return _allocations_from_weights(weights, sleeve_universe)


def _expected_return(allocations: list[Allocation], sleeve_universe: list[Sleeve]) -> float:
    sleeves = {sleeve.id: sleeve for sleeve in sleeve_universe}
    return sum(
        allocation.weight * sleeves[allocation.sleeve_id].expected_return
        for allocation in allocations
    )


def _volatility(allocations: list[Allocation], sleeve_universe: list[Sleeve]) -> float:
    sleeves = {sleeve.id: sleeve for sleeve in sleeve_universe}
    return sqrt(
        sum(
            (allocation.weight * sleeves[allocation.sleeve_id].volatility) ** 2
            for allocation in allocations
        )
    )


def _fan_chart(goal: Goal, expected_return: float, volatility: float) -> list[FanChartPoint]:
    horizon = min(max(round(_goal_horizon_years(goal)), 1), 35)
    monthly = float(goal.contribution_plan.get("monthly", 0) or 0)
    annual_contribution = monthly * 12
    points: list[FanChartPoint] = []
    starting_value = goal.current_funded_amount

    for year in range(horizon + 1):
        funded = starting_value + annual_contribution * year
        p50 = funded * ((1 + expected_return) ** year)
        spread = 1.28 * volatility * sqrt(max(year, 1))
        points.append(
            FanChartPoint(
                goal_id=goal.id,
                year=year,
                p10=max(p50 * (1 - spread), 0),
                p50=p50,
                p90=p50 * (1 + spread),
            )
        )

    return points


def _household_blend(goals: list[Goal], goal_blends: list[GoalBlend]) -> list[Allocation]:
    if not goal_blends:
        return []

    weights_by_goal = {
        goal.id: max(goal.current_funded_amount, goal.target_amount * 0.1) for goal in goals
    }
    total_goal_weight = sum(weights_by_goal.values())
    sleeve_weights: dict[str, tuple[str, float]] = {}

    for goal_blend in goal_blends:
        goal_weight = weights_by_goal[goal_blend.goal_id] / total_goal_weight
        for allocation in goal_blend.allocations:
            _, current_weight = sleeve_weights.get(
                allocation.sleeve_id, (allocation.sleeve_name, 0)
            )
            sleeve_weights[allocation.sleeve_id] = (
                allocation.sleeve_name,
                current_weight + allocation.weight * goal_weight,
            )

    return [
        Allocation(sleeve_id=sleeve_id, sleeve_name=name, weight=weight)
        for sleeve_id, (name, weight) in sorted(sleeve_weights.items())
        if weight > 0
    ]


def _account_or_household_blend(holdings, household_blend: list[Allocation]) -> list[Allocation]:
    if not holdings:
        return household_blend
    return [
        Allocation(
            sleeve_id=holding.sleeve_id, sleeve_name=holding.sleeve_name, weight=holding.weight
        )
        for holding in holdings
    ]


def _empty_weights(sleeve_universe: list[Sleeve]) -> dict[str, float]:
    return {sleeve.id: 0.0 for sleeve in sleeve_universe}


def _set_weight(weights: dict[str, float], sleeve_id: str, weight: float) -> None:
    if sleeve_id in weights:
        weights[sleeve_id] = weight


def _allocations_from_weights(
    weights: dict[str, float], sleeve_universe: list[Sleeve]
) -> list[Allocation]:
    sleeves = {sleeve.id: sleeve for sleeve in sleeve_universe}
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("allocation weights must sum to a positive value")

    return [
        Allocation(sleeve_id=sleeve_id, sleeve_name=sleeves[sleeve_id].name, weight=weight / total)
        for sleeve_id, weight in sorted(weights.items())
        if weight > 0
    ]


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))
