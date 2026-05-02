"""Link-first portfolio optimizer."""

from __future__ import annotations

import re
from datetime import date
from typing import Any  # noqa: F401  used by dict[str, Any] annotations

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
    MappingStatus,
    OptimizationMethod,
    ProjectionPoint,
    Rollup,
)

MODEL_VERSION = "default_cma_link_frontier_v2"
RISK_TO_PERCENTILE = {1: 5, 2: 15, 3: 25, 4: 35, 5: 45}
DRIFT_THRESHOLD = 0.05
MISSING_HOLDINGS_WARNING = "missing_current_holdings"
UNMAPPED_HOLDINGS_WARNING = "unmapped_current_holdings"
PARTIAL_MAPPING_WARNING = "partially_mapped_current_holdings"
CASH_PENDING_WARNING = "cash_pending_investment"
METADATA_WARNING = "fund_metadata_incomplete"


def optimize(
    household: Household,
    cma_snapshot: CMASnapshot,
    method: OptimizationMethod = "percentile",
    constraints: Constraints | None = None,
    as_of_date: date | None = None,
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
    fund_aliases = _fund_alias_map(eligible_funds)
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
    valuation_date = as_of_date or date.today()

    for goal in household.goals:
        for link in goal.account_allocations:
            account = accounts.get(link.account_id)
            if account is None:
                raise ValueError(f"Goal-account link references unknown account {link.account_id}")
            allocated_amount = _link_amount(
                link.allocated_amount, link.allocated_pct, account.current_value
            )
            horizon_years = _goal_horizon_years(goal, valuation_date)
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
                _allocation_for_fund(fund, weight)
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
                fund_aliases=fund_aliases,
                optimal_allocations=allocations,
                horizon_years=horizon_years,
                percentile=percentile,
                allocated_amount=allocated_amount,
            )
            drift_flags = _drift_flags(comparison)
            allocation_warnings = _allocation_metadata_warnings(allocations)
            recommendation_warnings = sorted(
                set(drift_flags).union(comparison.warnings).union(allocation_warnings)
            )
            link_id = link.id
            advisor_summary = (
                f"{goal.name} in {account.type} uses goal risk {goal.goal_risk_score}/5 "
                f"over {horizon_years:.1f} years, optimizing the {percentile}th percentile "
                f"outcome on the active frontier."
            )
            technical_trace = {
                "link_id": link_id,
                "link_external_id": link.id,
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
                "mapping_status": comparison.status,
                "warnings": recommendation_warnings,
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
                warnings=recommendation_warnings,
                explanation=_link_explanation(
                    goal=goal,
                    account=account,
                    percentile=percentile,
                    allocations=allocations,
                    current_comparison=comparison,
                    warnings=recommendation_warnings,
                ),
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
                "reference": "Default CMA efficient frontier v2",
                "whole_portfolio_funds": "eligible_and_mixed",
                "allocation_cap": None,
            },
            cma_snapshot_id=cma_snapshot.id,
            cma_version=cma_snapshot.version,
            fund_assumptions=[fund.model_dump(mode="json") for fund in cma_snapshot.funds],
            constraints=constraints.model_dump(mode="json"),
        ),
        advisor_summary=advisor_summary,
        technical_trace={
            "model_version": MODEL_VERSION,
            "schema_version": "engine_output.link_first.v2",
            "cma_snapshot_id": cma_snapshot.id,
            "cma_version": cma_snapshot.version,
            "as_of_date": valuation_date.isoformat(),
            "link_count": len(link_recommendations),
            "goal_count": len(goal_rollups),
            "account_count": len(account_rollups),
        },
        run_manifest={
            "schema_version": "engine_run_manifest.v2",
            "engine_output_schema": "engine_output.link_first.v2",
            "model_version": MODEL_VERSION,
            "method": method,
            "as_of_date": valuation_date.isoformat(),
            "household_id": household.id,
            "cma_snapshot_id": cma_snapshot.id,
            "cma_version": cma_snapshot.version,
            "risk_mapping": RISK_TO_PERCENTILE,
            "optimizer_eligible_fund_ids": [fund.id for fund in eligible_funds],
            "whole_portfolio_fund_ids": [
                fund.id for fund in eligible_funds if fund.is_whole_portfolio
            ],
            "goal_account_link_ids": [
                recommendation.link_id for recommendation in link_recommendations
            ],
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
    # The web layer's portfolio_generation_blockers_for_household must
    # surface a more specific blocker before reaching here. This branch
    # is a last-resort guard: if it raises, the message must give
    # enough signal that the source-of-truth check at the web layer is
    # missing. (See web/api/review_state.py
    # portfolio_generation_blockers_for_household for the explicit
    # zero/null current_value blocker.)
    if (allocated_amount is None or allocated_amount <= 0) and (
        allocated_pct is not None
        and allocated_pct > 0
        and (account_value is None or account_value <= 0)
    ):
        raise ValueError(
            "Goal-account link uses percentage but the linked account has no current "
            "value — advisor must provide an account value, archive, or delete the "
            "account before portfolio generation."
        )
    raise ValueError("Every goal-account link must include allocated dollars or percentage")


def _goal_horizon_years(goal: Goal, as_of_date: date) -> float:
    days = (goal.target_date - as_of_date).days
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
    fund_aliases: dict[str, str],
    optimal_allocations: list[Allocation],
    horizon_years: float,
    percentile: int,
    allocated_amount: float,
) -> CurrentPortfolioComparison:
    fund_ids = [fund.id for fund in eligible_funds]
    if account.cash_state != "invested" and not account.current_holdings:
        cash_index = _cash_fund_index(eligible_funds)
        if cash_index is None:
            return CurrentPortfolioComparison(
                missing_holdings=True,
                status="cash_or_pending",
                reason=(
                    "Account is marked as cash or pending investment, but no eligible "
                    "cash fund exists in the CMA universe."
                ),
                warnings=[CASH_PENDING_WARNING, MISSING_HOLDINGS_WARNING],
            )
        weights = [0.0 for _ in fund_ids]
        weights[cash_index] = 1.0
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
            _allocation_for_fund(fund, weight)
            for fund, weight in zip(eligible_funds, weights, strict=True)
            if weight > 1e-8
        ]
        return CurrentPortfolioComparison(
            missing_holdings=False,
            status="cash_or_pending",
            reason="Account is explicitly marked as cash or pending investment.",
            expected_return=current.expected_return,
            volatility=current.volatility,
            allocations=current_allocations,
            deltas=_allocation_deltas(eligible_funds, optimal_allocations, weights),
            warnings=[CASH_PENDING_WARNING],
        )

    if not account.current_holdings:
        reason = "Current holdings are not available for this account."
        warnings = [MISSING_HOLDINGS_WARNING]
        if account.missing_holdings_confirmed:
            reason = "Current holdings were explicitly confirmed as unavailable."
            warnings.append("confirmed_missing_current_holdings")
        return CurrentPortfolioComparison(
            missing_holdings=True,
            status="no_holdings",
            reason=reason,
            warnings=warnings,
        )

    weights = [0.0 for _ in fund_ids]
    diagnostics: list[dict[str, Any]] = []
    unmapped_holdings: list[dict[str, Any]] = []
    for holding in account.current_holdings:
        mapped_fund_id = fund_aliases.get(_normalize_alias(holding.sleeve_id)) or fund_aliases.get(
            _normalize_alias(holding.sleeve_name)
        )
        diagnostic = {
            "sleeve_id": holding.sleeve_id,
            "sleeve_name": holding.sleeve_name,
            "weight": holding.weight,
            "market_value": holding.market_value,
            "mapped_fund_id": mapped_fund_id,
            "mapping_status": "mapped" if mapped_fund_id else "unmapped",
        }
        diagnostics.append(diagnostic)
        if mapped_fund_id and mapped_fund_id in fund_ids:
            weights[fund_ids.index(mapped_fund_id)] += holding.weight
        else:
            unmapped_holdings.append(
                {
                    **diagnostic,
                    "reason": "No alias matched this holding to the active CMA fund universe.",
                }
            )

    if sum(weights) <= 0:
        return CurrentPortfolioComparison(
            missing_holdings=True,
            status="unmapped",
            reason="Current holdings are present but none map to the active CMA fund universe.",
            holdings_diagnostics=diagnostics,
            unmapped_holdings=unmapped_holdings,
            warnings=[UNMAPPED_HOLDINGS_WARNING],
        )

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
        _allocation_for_fund(fund, weight)
        for fund, weight in zip(eligible_funds, weights, strict=True)
        if weight > 1e-8
    ]
    status: MappingStatus = "partially_mapped" if unmapped_holdings else "mapped"
    warnings = [PARTIAL_MAPPING_WARNING] if unmapped_holdings else []
    return CurrentPortfolioComparison(
        missing_holdings=False,
        status=status,
        reason=(
            "Current holdings were partially mapped to the active CMA fund universe."
            if unmapped_holdings
            else "Current holdings mapped to the active CMA fund universe."
        ),
        expected_return=current.expected_return,
        volatility=current.volatility,
        allocations=current_allocations,
        deltas=_allocation_deltas(eligible_funds, optimal_allocations, weights),
        holdings_diagnostics=diagnostics,
        unmapped_holdings=unmapped_holdings,
        warnings=warnings,
    )


def _drift_flags(comparison: CurrentPortfolioComparison) -> list[str]:
    if comparison.missing_holdings:
        if comparison.status == "unmapped":
            return [UNMAPPED_HOLDINGS_WARNING]
        return [MISSING_HOLDINGS_WARNING]
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
        warnings.update(recommendation.warnings)
    return sorted(warnings)


def _allocation_for_fund(fund, weight: float) -> Allocation:
    return Allocation(
        sleeve_id=fund.id,
        sleeve_name=fund.name,
        weight=weight,
        fund_type="whole_portfolio" if fund.is_whole_portfolio else "building_block",
        asset_class_weights=fund.asset_class_weights,
        geography_weights=fund.geography_weights,
    )


def _allocation_deltas(
    eligible_funds,
    optimal_allocations: list[Allocation],
    current_weights: list[float],
) -> list[AllocationDelta]:
    optimal_by_id = {allocation.sleeve_id: allocation.weight for allocation in optimal_allocations}
    return [
        AllocationDelta(
            sleeve_id=fund.id,
            sleeve_name=fund.name,
            weight_delta=optimal_by_id.get(fund.id, 0.0) - weight,
        )
        for fund, weight in zip(eligible_funds, current_weights, strict=True)
        if abs(optimal_by_id.get(fund.id, 0.0) - weight) > 1e-8
    ]


def _allocation_metadata_warnings(allocations: list[Allocation]) -> list[str]:
    warnings: set[str] = set()
    for allocation in allocations:
        if not allocation.asset_class_weights or not allocation.geography_weights:
            warnings.add(METADATA_WARNING)
            if allocation.fund_type == "whole_portfolio":
                warnings.add("whole_fund_metadata_incomplete")
    return sorted(warnings)


def _link_explanation(
    *,
    goal: Goal,
    account,
    percentile: int,
    allocations: list[Allocation],
    current_comparison: CurrentPortfolioComparison,
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "risk": {
            "scale": "1-5",
            "goal_risk_score": goal.goal_risk_score,
            "frontier_percentile": percentile,
        },
        "direct_fund_weights": [
            {
                "fund_id": allocation.sleeve_id,
                "fund_name": allocation.sleeve_name,
                "weight": allocation.weight,
                "fund_type": allocation.fund_type,
            }
            for allocation in allocations
        ],
        "whole_fund_expansion": [
            {
                "fund_id": allocation.sleeve_id,
                "fund_name": allocation.sleeve_name,
                "asset_class_weights": allocation.asset_class_weights,
                "geography_weights": allocation.geography_weights,
                "metadata_complete": bool(
                    allocation.asset_class_weights and allocation.geography_weights
                ),
            }
            for allocation in allocations
            if allocation.fund_type == "whole_portfolio"
        ],
        "current_vs_ideal": {
            "account_id": account.id,
            "cash_state": account.cash_state,
            "mapping_status": current_comparison.status,
            "reason": current_comparison.reason,
            "unmapped_holdings": current_comparison.unmapped_holdings,
        },
        "warnings": warnings,
    }


def _fund_alias_map(funds) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for fund in funds:
        tokens = [fund.id, fund.name, *fund.aliases]
        for token in tokens:
            normalized = _normalize_alias(token)
            if normalized:
                aliases[normalized] = fund.id
    return aliases


def _normalize_alias(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


def _cash_fund_index(funds) -> int | None:
    for index, fund in enumerate(funds):
        normalized = _normalize_alias(f"{fund.id} {fund.name} {' '.join(fund.aliases)}")
        if "cash" in normalized or "savings" in normalized:
            return index
    return None
