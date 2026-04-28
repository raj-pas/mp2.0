from datetime import date, datetime

import pytest
from engine import STEADYHAND_PURE_SLEEVES, optimize
from engine.compliance import risk_rating
from engine.schemas import (
    Account,
    Allocation,
    Goal,
    GoalAccountLink,
    Holding,
    Household,
    Person,
    RiskInput,
)


def test_optimize_returns_realistic_shape() -> None:
    household = _household()

    output = optimize(household, STEADYHAND_PURE_SLEEVES)

    assert output.household_id == "hh_chen"
    assert len(output.goal_blends) == 2
    assert output.household_blend
    assert output.fan_chart
    assert output.household_risk_rating in {"low", "medium", "high"}
    assert output.audit_trace.model_version.startswith("phase1_stub")


def test_allocation_weights_sum_to_one_per_goal() -> None:
    output = optimize(_household(), STEADYHAND_PURE_SLEEVES)

    for blend in output.goal_blends:
        assert sum(allocation.weight for allocation in blend.allocations) == pytest.approx(1.0)


def test_compliance_risk_rating_is_deterministic() -> None:
    rating = risk_rating(
        [Allocation(sleeve_id="cash_savings", sleeve_name="Cash / Savings", weight=1.0)],
        STEADYHAND_PURE_SLEEVES,
    )

    assert rating == "low"


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
        current_funded_amount=1_050_000,
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
        current_funded_amount=68_000,
        contribution_plan={"monthly": 500},
        account_allocations=[],
        goal_risk_score=1,
    )
    account = Account(
        id="acct_rrsp_mike",
        household_id="hh_chen",
        owner_person_id="person_mike",
        type="RRSP",
        regulatory_objective="growth_and_income",
        regulatory_time_horizon="3-10y",
        regulatory_risk_rating="medium",
        current_holdings=[
            Holding(
                sleeve_id="income_fund",
                sleeve_name="Income Fund",
                weight=0.4,
                market_value=248_000,
            ),
            Holding(
                sleeve_id="equity_fund",
                sleeve_name="Equity Fund",
                weight=0.6,
                market_value=372_000,
            ),
        ],
    )
    return Household(
        id="hh_chen",
        type="couple",
        members=[person],
        goals=[retirement, education],
        accounts=[account],
        household_risk_score=6,
        risk_input=RiskInput(household_score=6, goals={"goal_retirement": 3, "goal_education": 1}),
        created_at=datetime(2026, 4, 28, 12, 0, 0),
        updated_at=datetime(2026, 4, 28, 12, 0, 0),
    )
