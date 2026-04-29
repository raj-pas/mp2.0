"""Link-first portfolio optimizer."""

from __future__ import annotations

from datetime import date

from engine.frontier import (
    compute_frontier,
    evaluate_portfolio,
    optimal_on_frontier,
    percentile_projection,
)
from engine.schemas import (
    Allocation,
    AllocationDelta,
    CMASnapshot,
    Constraints,
    CurrentPortfolioComparison,
    EngineOutput,
    EngineRun,
    FanChartPoint,
    Goal,
    Household,
    LinkRecommendation,
    OptimizationMethod,
    ProjectionPoint,
    Rollup,
)

MODEL_VERSION = "default_cma_link_frontier_v1"
RISK_TO_PERCENTILE = {1: 5, 2: 15, 3: 25, 4: 35, 5: 45}
DRIFT_THRESHOLD = 0.05


def optimize(
    household: Household,
    cma_snapshot: CMASnapshot,
    method: OptimizationMethod = "percentile",
    constraints: Constraints | None = None,
) -> EngineOutput:
    """Optimize every goal-account link and roll recommendations up."""

    if not household.goals:
        raise ValueError("household must include at least one goal")
    if not household.accounts:
        raise ValueError("household must include at least one account")

    constraints = constraints or Constraints()
    eligible_funds = [fund for fund in cma_snapshot.funds if fund.optimizer_eligible]
    if len(eligible_funds) < 2:
        raise ValueError("cma_snapshot must include at least two optimizer-eligible funds")

    fund_index = {fund.id: index for index, fund in enumerate(cma_snapshot.funds)}
    eligible_indexes = [fund_index[fund.id] for fund in eligible_funds]
    expected_returns = [fund.expected_return for fund in eligible_funds]
    volatilities = [fund.volatility for fund in eligible_funds]
    correlation_matrix = [
        [cma_snapshot.correlation_matrix[i][j] for j in eligible_indexes] for i in eligible_indexes
    ]

    frontier = compute_frontier(expected_returns, volatilities, correlation_matrix)
    if not frontier.efficient:
        raise ValueError("No feasible efficient frontier for active CMA snapshot")

    accounts = {account.id: account for account in household.accounts}
    link_recommendations: list[LinkRecommendation] = []
    fan_chart: list[FanChartPoint] = []

    for goal in household.goals:
        for link in goal.account_allocations:
            account = accounts.get(link.account_id)
            if account is None:
                raise ValueError(f"Goal-account link references unknown account {link.account_id}")
            allocated_amount = _link_amount(
                link.allocated_amount, link.allocated_pct, account.current_value
            )
            horizon_years = _goal_horizon_years(goal)
            percentile = RISK_TO_PERCENTILE[goal.goal_risk_score]
            optimal = optimal_on_frontier(
                frontier.efficient,
                periods=horizon_years,
                percentile=percentile,
                starting_value=allocated_amount,
            )
            if optimal is None:
                raise ValueError("No optimal frontier point available")

            allocations = [
                Allocation(sleeve_id=fund.id, sleeve_name=fund.name, weight=weight)
                for fund, weight in zip(eligible_funds, optimal.weights, strict=True)
                if weight > 1e-8
            ]
            projection = _projection(
                allocated_amount=allocated_amount,
                horizon_years=horizon_years,
                percentile=percentile,
                expected_return=optimal.expected_return,
                volatility=optimal.volatility,
                optimized_value=optimal.value or 0,
            )
            comparison = _current_comparison(
                account=account,
                expected_returns=expected_returns,
                volatilities=volatilities,
                correlation_matrix=correlation_matrix,
                eligible_funds=eligible_funds,
                optimal_allocations=allocations,
                horizon_years=horizon_years,
                percentile=percentile,
                allocated_amount=allocated_amount,
            )
            drift_flags = _drift_flags(comparison)
            link_id = f"{goal.id}:{account.id}"
            advisor_summary = (
                f"{goal.name} in {account.type} uses goal risk {goal.goal_risk_score}/5 "
                f"over {horizon_years:.1f} years, optimizing the {percentile}th percentile "
                f"outcome on the active frontier."
            )
            technical_trace = {
                "link_id": link_id,
                "goal_id": goal.id,
                "account_id": account.id,
                "goal_risk_score": goal.goal_risk_score,
                "horizon_years": horizon_years,
                "allocated_amount": allocated_amount,
                "frontier_percentile": percentile,
                "selected_frontier_point": {
                    "expected_return": optimal.expected_return,
                    "volatility": optimal.volatility,
                    "projected_value": optimal.value,
                    "weights": optimal.weights,
                },
                "cma_snapshot_id": cma_snapshot.id,
                "tax_drag_version": cma_snapshot.tax_drag_version,
            }
            recommendation = LinkRecommendation(
                link_id=link_id,
                goal_id=goal.id,
                goal_name=goal.name,
                account_id=account.id,
                account_type=account.type,
                allocated_amount=allocated_amount,
                horizon_years=horizon_years,
                goal_risk_score=goal.goal_risk_score,
                frontier_percentile=percentile,
                allocations=allocations,
                expected_return=optimal.expected_return,
                volatility=optimal.volatility,
                projected_value=optimal.value or 0,
                projection=projection,
                current_comparison=comparison,
                drift_flags=drift_flags,
                advisor_summary=advisor_summary,
                technical_trace={**technical_trace, "rollup_weighting": "allocated_amount"},
            )
            link_recommendations.append(recommendation)
            fan_chart.extend(
                [
                    FanChartPoint(
                        link_id=link_id,
                        goal_id=goal.id,
                        year=point.year,
                        p10=point.p10,
                        p50=point.p50,
                        p90=point.p90,
                    )
                    for point in projection
                ]
            )

    if not link_recommendations:
        raise ValueError("household must include at least one goal-account link")

    goal_rollups = _rollups_by_goal(household.goals, link_recommendations)
    account_rollups = _rollups_by_account(household.accounts, link_recommendations)
    household_rollup = _rollup(
        id_=household.id,
        name="Household",
        recommendations=link_recommendations,
    )
    advisor_summary = (
        f"Generated {len(link_recommendations)} goal-account recommendations using "
        f"CMA snapshot {cma_snapshot.version}."
    )
    return EngineOutput(
        household_id=household.id,
        link_recommendations=link_recommendations,
        goal_rollups=goal_rollups,
        account_rollups=account_rollups,
        household_rollup=household_rollup,
        fan_chart=fan_chart,
        audit_trace=EngineRun(
            model_version=MODEL_VERSION,
            method=method,
            params={
                "risk_mapping": RISK_TO_PERCENTILE,
                "drift_threshold": DRIFT_THRESHOLD,
                "reference": "Default CMA efficient frontier v1",
            },
            cma_snapshot_id=cma_snapshot.id,
            cma_version=cma_snapshot.version,
            fund_assumptions=[fund.model_dump(mode="json") for fund in cma_snapshot.funds],
            constraints=constraints.model_dump(mode="json"),
        ),
        advisor_summary=advisor_summary,
        technical_trace={
            "model_version": MODEL_VERSION,
            "cma_snapshot_id": cma_snapshot.id,
            "cma_version": cma_snapshot.version,
            "link_count": len(link_recommendations),
            "goal_count": len(goal_rollups),
            "account_count": len(account_rollups),
        },
        warnings=_warnings(link_recommendations),
    )


def _link_amount(
    allocated_amount: float | None, allocated_pct: float | None, account_value: float
) -> float:
    if allocated_amount is not None and allocated_amount > 0:
        return allocated_amount
    if allocated_pct is not None and allocated_pct > 0 and account_value > 0:
        return allocated_pct * account_value
    raise ValueError("Every goal-account link must include allocated dollars or percentage")


def _goal_horizon_years(goal: Goal) -> float:
    days = (goal.target_date - date.today()).days
    return max(days / 365.25, 0.25)


def _projection(
    *,
    allocated_amount: float,
    horizon_years: float,
    percentile: int,
    expected_return: float,
    volatility: float,
    optimized_value: float,
) -> list[ProjectionPoint]:
    years = sorted({0, max(1, round(horizon_years / 2)), max(1, round(horizon_years))})
    points: list[ProjectionPoint] = []
    for year in years:
        periods = max(float(year), 0.0001)
        points.append(
            ProjectionPoint(
                year=year,
                p10=percentile_projection(
                    starting_value=allocated_amount,
                    expected_return=expected_return,
                    volatility=volatility,
                    periods=periods,
                    percentile=10,
                ),
                p50=percentile_projection(
                    starting_value=allocated_amount,
                    expected_return=expected_return,
                    volatility=volatility,
                    periods=periods,
                    percentile=50,
                ),
                p90=percentile_projection(
                    starting_value=allocated_amount,
                    expected_return=expected_return,
                    volatility=volatility,
                    periods=periods,
                    percentile=90,
                ),
                optimized_percentile_value=optimized_value if year == max(years) else 0,
            )
        )
    return points


def _current_comparison(
    *,
    account,
    expected_returns: list[float],
    volatilities: list[float],
    correlation_matrix: list[list[float]],
    eligible_funds,
    optimal_allocations: list[Allocation],
    horizon_years: float,
    percentile: int,
    allocated_amount: float,
) -> CurrentPortfolioComparison:
    if not account.current_holdings:
        return CurrentPortfolioComparison(missing_holdings=True)

    fund_ids = [fund.id for fund in eligible_funds]
    weights = [0.0 for _ in fund_ids]
    for holding in account.current_holdings:
        if holding.sleeve_id in fund_ids:
            weights[fund_ids.index(holding.sleeve_id)] += holding.weight

    if sum(weights) <= 0:
        return CurrentPortfolioComparison(missing_holdings=True)

    total = sum(weights)
    weights = [weight / total for weight in weights]
    current = evaluate_portfolio(
        weights,
        expected_returns,
        volatilities,
        correlation_matrix,
        periods=horizon_years,
        percentile=percentile,
        starting_value=allocated_amount,
    )
    current_allocations = [
        Allocation(sleeve_id=fund.id, sleeve_name=fund.name, weight=weight)
        for fund, weight in zip(eligible_funds, weights, strict=True)
        if weight > 1e-8
    ]
    optimal_by_id = {allocation.sleeve_id: allocation.weight for allocation in optimal_allocations}
    deltas = [
        AllocationDelta(
            sleeve_id=fund.id,
            sleeve_name=fund.name,
            weight_delta=optimal_by_id.get(fund.id, 0.0) - weight,
        )
        for fund, weight in zip(eligible_funds, weights, strict=True)
        if abs(optimal_by_id.get(fund.id, 0.0) - weight) > 1e-8
    ]
    return CurrentPortfolioComparison(
        missing_holdings=False,
        expected_return=current.expected_return,
        volatility=current.volatility,
        allocations=current_allocations,
        deltas=deltas,
    )


def _drift_flags(comparison: CurrentPortfolioComparison) -> list[str]:
    if comparison.missing_holdings:
        return ["missing_holdings"]
    if any(abs(delta.weight_delta) >= DRIFT_THRESHOLD for delta in comparison.deltas):
        return ["review_rebalance"]
    return []


def _rollups_by_goal(goals: list[Goal], recommendations: list[LinkRecommendation]) -> list[Rollup]:
    return [
        _rollup(
            id_=goal.id,
            name=goal.name,
            recommendations=[item for item in recommendations if item.goal_id == goal.id],
        )
        for goal in goals
        if any(item.goal_id == goal.id for item in recommendations)
    ]


def _rollups_by_account(accounts, recommendations: list[LinkRecommendation]) -> list[Rollup]:
    return [
        _rollup(
            id_=account.id,
            name=account.type,
            recommendations=[item for item in recommendations if item.account_id == account.id],
        )
        for account in accounts
        if any(item.account_id == account.id for item in recommendations)
    ]


def _rollup(id_: str, name: str, recommendations: list[LinkRecommendation]) -> Rollup:
    allocated_amount = sum(item.allocated_amount for item in recommendations)
    if allocated_amount <= 0:
        return Rollup(
            id=id_,
            name=name,
            allocated_amount=0,
            allocations=[],
            expected_return=0,
            volatility=0,
        )

    weights: dict[str, tuple[str, float]] = {}
    expected_return = 0.0
    volatility = 0.0
    for item in recommendations:
        share = item.allocated_amount / allocated_amount
        expected_return += item.expected_return * share
        volatility += item.volatility * share
        for allocation in item.allocations:
            label, current = weights.get(allocation.sleeve_id, (allocation.sleeve_name, 0.0))
            weights[allocation.sleeve_id] = (label, current + allocation.weight * share)

    return Rollup(
        id=id_,
        name=name,
        allocated_amount=allocated_amount,
        allocations=[
            Allocation(sleeve_id=sleeve_id, sleeve_name=label, weight=weight)
            for sleeve_id, (label, weight) in sorted(weights.items())
            if weight > 1e-8
        ],
        expected_return=expected_return,
        volatility=volatility,
    )


def _warnings(recommendations: list[LinkRecommendation]) -> list[str]:
    warnings: set[str] = set()
    for recommendation in recommendations:
        warnings.update(recommendation.drift_flags)
    return sorted(warnings)
