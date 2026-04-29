from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import pytest
from engine import optimize
from engine.compliance import risk_rating
from engine.frontier import (
    build_covariance,
    compute_frontier,
    evaluate_portfolio,
    optimal_on_frontier,
    percentile_projection,
)
from engine.schemas import (
    Account,
    Allocation,
    CMASnapshot,
    FundAssumption,
    Goal,
    GoalAccountLink,
    Holding,
    Household,
    Person,
    RiskInput,
)
from engine.sleeves import STEADYHAND_PURE_SLEEVES


def test_fraser_frontier_fixture_matches_reference_math() -> None:
    data = _fraser_fixture()
    returns = [fund["expected_return"] for fund in data["funds"]]
    volatilities = [fund["volatility"] for fund in data["funds"]]
    correlation_matrix = data["correlation_matrix"]

    covariance = build_covariance(volatilities, correlation_matrix)
    frontier = compute_frontier(returns, volatilities, correlation_matrix)
    current = evaluate_portfolio(
        data["current_weights"],
        returns,
        volatilities,
        correlation_matrix,
        periods=5,
        percentile=25,
        starting_value=100_000,
    )

    assert covariance[0][0] == pytest.approx(0.01772093)
    assert len(frontier.efficient) == 71
    assert frontier.minimum_variance is not None
    assert frontier.minimum_variance.expected_return == pytest.approx(0.03)
    assert frontier.minimum_variance.volatility == pytest.approx(0.00396)
    assert current.expected_return == pytest.approx(0.0627375)
    assert current.volatility == pytest.approx(0.0910797)
    assert current.value == pytest.approx(116_833.75, abs=0.01)


def test_percentile_optimizer_selects_reference_frontier_points() -> None:
    data = _fraser_fixture()
    returns = [fund["expected_return"] for fund in data["funds"]]
    volatilities = [fund["volatility"] for fund in data["funds"]]
    frontier = compute_frontier(returns, volatilities, data["correlation_matrix"])

    risk_three = optimal_on_frontier(
        frontier.efficient,
        periods=5,
        percentile=25,
        starting_value=100_000,
    )
    risk_five = optimal_on_frontier(
        frontier.efficient,
        periods=5,
        percentile=45,
        starting_value=100_000,
    )

    assert risk_three is not None
    assert risk_five is not None
    assert risk_three.expected_return == pytest.approx(0.0600971)
    assert risk_three.volatility == pytest.approx(0.0719875)
    assert risk_three.value == pytest.approx(119_597.09, abs=0.01)
    assert risk_five.expected_return > risk_three.expected_return
    assert risk_five.volatility > risk_three.volatility


def test_percentile_projection_values_are_ordered() -> None:
    p10 = percentile_projection(
        starting_value=100_000,
        expected_return=0.05,
        volatility=0.1,
        periods=5,
        percentile=10,
    )
    p50 = percentile_projection(
        starting_value=100_000,
        expected_return=0.05,
        volatility=0.1,
        periods=5,
        percentile=50,
    )
    p90 = percentile_projection(
        starting_value=100_000,
        expected_return=0.05,
        volatility=0.1,
        periods=5,
        percentile=90,
    )

    assert p10 == pytest.approx(94_029.31, abs=0.01)
    assert p10 < p50 < p90


def test_optimize_returns_link_first_portfolio_run_payload() -> None:
    output = optimize(_household(), _cma_snapshot())

    assert output.schema_version == "engine_output.link_first.v1"
    assert output.household_id == "hh_chen"
    assert len(output.link_recommendations) == 2
    assert len(output.goal_rollups) == 2
    assert len(output.account_rollups) == 2
    assert output.household_rollup.allocated_amount == pytest.approx(728_000)
    assert output.audit_trace.model_version == "fraser_link_frontier_v1"
    assert output.audit_trace.cma_version == 1

    first = output.link_recommendations[0]
    assert first.frontier_percentile == 25
    assert sum(allocation.weight for allocation in first.allocations) == pytest.approx(1.0)
    assert first.current_comparison.missing_holdings is False
    assert first.drift_flags == ["review_rebalance"]
    assert output.warnings == ["missing_holdings", "review_rebalance"]


def test_optimize_flags_missing_current_holdings() -> None:
    household = _household()
    household.accounts[0].current_holdings = []

    output = optimize(household, _cma_snapshot())

    assert output.link_recommendations[0].current_comparison.missing_holdings is True
    assert "missing_holdings" in output.warnings


def test_compliance_risk_rating_is_deterministic() -> None:
    rating = risk_rating(
        [Allocation(sleeve_id="cash_savings", sleeve_name="Cash / Savings", weight=1.0)],
        STEADYHAND_PURE_SLEEVES,
    )

    assert rating == "low"


def _fraser_fixture() -> dict:
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures/fraser_v1.json"
    return json.loads(fixture_path.read_text())


def _cma_snapshot() -> CMASnapshot:
    data = _fraser_fixture()
    return CMASnapshot(
        id="fraser-cma-v1",
        version=1,
        source=data["source_note"],
        funds=[
            FundAssumption(
                id=fund["id"],
                name=fund["name"],
                expected_return=fund["expected_return"],
                volatility=fund["volatility"],
                optimizer_eligible=fund["optimizer_eligible"],
                is_whole_portfolio=fund["is_whole_portfolio"],
            )
            for fund in data["funds"]
        ],
        correlation_matrix=data["correlation_matrix"],
    )


def _household() -> Household:
    person = Person(
        id="person_mike",
        household_id="hh_chen",
        name="Mike Chen",
        dob=date(1964, 2, 12),
        investment_knowledge="medium",
    )
    retirement = Goal(
        id="goal_retirement",
        household_id="hh_chen",
        name="Retirement income",
        target_amount=1_600_000,
        target_date=date(2030, 6, 30),
        necessity_score=5,
        current_funded_amount=620_000,
        contribution_plan={"monthly": 3500},
        account_allocations=[
            GoalAccountLink(
                goal_id="goal_retirement",
                account_id="acct_rrsp_mike",
                allocated_amount=620_000,
            )
        ],
        goal_risk_score=3,
    )
    education = Goal(
        id="goal_education",
        household_id="hh_chen",
        name="Emma education",
        target_amount=80_000,
        target_date=date(2027, 9, 1),
        necessity_score=5,
        current_funded_amount=108_000,
        contribution_plan={"monthly": 500},
        account_allocations=[
            GoalAccountLink(
                goal_id="goal_education",
                account_id="acct_resp_emma",
                allocated_amount=108_000,
            )
        ],
        goal_risk_score=1,
    )
    rrsp = Account(
        id="acct_rrsp_mike",
        household_id="hh_chen",
        owner_person_id="person_mike",
        type="RRSP",
        regulatory_objective="growth_and_income",
        regulatory_time_horizon="3-10y",
        regulatory_risk_rating="medium",
        current_value=620_000,
        current_holdings=[
            Holding(
                sleeve_id="sh_income",
                sleeve_name="SH Income",
                weight=0.4,
                market_value=248_000,
            ),
            Holding(
                sleeve_id="sh_equity",
                sleeve_name="SH Equity",
                weight=0.6,
                market_value=372_000,
            ),
        ],
    )
    resp = Account(
        id="acct_resp_emma",
        household_id="hh_chen",
        owner_person_id="person_mike",
        type="RESP",
        regulatory_objective="growth_and_income",
        regulatory_time_horizon="<3y",
        regulatory_risk_rating="low",
        current_value=108_000,
        current_holdings=[],
    )
    return Household(
        id="hh_chen",
        type="couple",
        members=[person],
        goals=[retirement, education],
        accounts=[rrsp, resp],
        household_risk_score=6,
        risk_input=RiskInput(household_score=6, goals={"goal_retirement": 3}),
        created_at=datetime(2026, 4, 28, 12, 0, 0),
        updated_at=datetime(2026, 4, 28, 12, 0, 0),
    )
