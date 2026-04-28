from __future__ import annotations

from decimal import Decimal

from engine.schemas import (
    Account,
    Goal,
    GoalAccountLink,
    Holding,
    Household,
    Person,
    RiskInput,
)

from web.api import models


def to_engine_household(household: models.Household) -> Household:
    members = [_person_to_engine(person) for person in household.members.all()]
    accounts = [_account_to_engine(account) for account in household.accounts.all()]
    goals = [_goal_to_engine(goal) for goal in household.goals.all()]
    risk_input = RiskInput(
        household_score=household.household_risk_score,
        goals={goal.id: goal.goal_risk_score for goal in goals},
    )

    return Household(
        id=household.external_id,
        type=household.household_type,
        members=members,
        goals=goals,
        accounts=accounts,
        external_assets=household.external_assets,
        household_risk_score=household.household_risk_score,
        risk_input=risk_input,
        created_at=household.created_at,
        updated_at=household.updated_at,
    )


def _person_to_engine(person: models.Person) -> Person:
    return Person(
        id=person.external_id,
        household_id=person.household.external_id,
        name=person.name,
        dob=person.dob,
        marital_status=person.marital_status,
        blended_family_flag=person.blended_family_flag,
        citizenship=person.citizenship,
        residency=person.residency,
        health_indicators=person.health_indicators,
        longevity_assumption=person.longevity_assumption,
        employment=person.employment,
        pensions=person.pensions,
        investment_knowledge=person.investment_knowledge,
        trusted_contact_person=person.trusted_contact_person,
        poa_status=person.poa_status,
        will_status=person.will_status,
        beneficiary_designations=person.beneficiary_designations,
    )


def _account_to_engine(account: models.Account) -> Account:
    return Account(
        id=account.external_id,
        household_id=account.household.external_id,
        owner_person_id=account.owner_person.external_id if account.owner_person else None,
        type=account.account_type,
        regulatory_objective=account.regulatory_objective,
        regulatory_time_horizon=account.regulatory_time_horizon,
        regulatory_risk_rating=account.regulatory_risk_rating,
        current_holdings=[
            Holding(
                sleeve_id=holding.sleeve_id,
                sleeve_name=holding.sleeve_name,
                weight=_float(holding.weight),
                market_value=_float(holding.market_value),
            )
            for holding in account.holdings.all()
        ],
        contribution_room=_float(account.contribution_room)
        if account.contribution_room is not None
        else None,
        contribution_history=account.contribution_history,
        is_held_at_purpose=account.is_held_at_purpose,
    )


def _goal_to_engine(goal: models.Goal) -> Goal:
    return Goal(
        id=goal.external_id,
        household_id=goal.household.external_id,
        name=goal.name,
        target_amount=_float(goal.target_amount),
        target_date=goal.target_date,
        necessity_score=goal.necessity_score,
        current_funded_amount=_float(goal.current_funded_amount),
        contribution_plan=goal.contribution_plan,
        account_allocations=[
            GoalAccountLink(
                goal_id=link.goal.external_id,
                account_id=link.account.external_id,
                allocated_amount=_float(link.allocated_amount)
                if link.allocated_amount is not None
                else None,
                allocated_pct=_float(link.allocated_pct)
                if link.allocated_pct is not None
                else None,
            )
            for link in goal.account_allocations.all()
        ],
        goal_risk_score=goal.goal_risk_score,
        status=goal.status,
        notes=goal.notes,
    )


def _float(value: Decimal) -> float:
    return float(value)
