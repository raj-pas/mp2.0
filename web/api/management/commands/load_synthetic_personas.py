from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from web.api import models


class Command(BaseCommand):
    help = "Load committed synthetic personas for local development."

    def handle(self, *args, **options):  # noqa: ANN002, ANN003
        fixture_path = (
            Path(__file__).resolve().parents[4] / "personas/sandra_mike_chen/client_state.json"
        )
        data = json.loads(fixture_path.read_text())
        with transaction.atomic():
            _load_household(data)
        self.stdout.write(self.style.SUCCESS("Loaded synthetic Sandra/Mike Chen persona."))


def _load_household(data: dict) -> None:
    models.Household.objects.filter(external_id=data["id"]).delete()
    household = models.Household.objects.create(
        external_id=data["id"],
        display_name=data["display_name"],
        household_type=data["household_type"],
        household_risk_score=data["household_risk_score"],
        external_assets=data.get("external_assets", []),
        notes=data.get("notes", ""),
    )

    people: dict[str, models.Person] = {}
    for person_data in data["members"]:
        person = models.Person.objects.create(
            external_id=person_data["id"],
            household=household,
            name=person_data["name"],
            dob=person_data["dob"],
            marital_status=person_data.get("marital_status", ""),
            blended_family_flag=person_data.get("blended_family_flag", False),
            citizenship=person_data.get("citizenship", "Canada"),
            residency=person_data.get("residency", "Canada"),
            health_indicators=person_data.get("health_indicators", {}),
            longevity_assumption=person_data.get("longevity_assumption"),
            employment=person_data.get("employment", {}),
            pensions=person_data.get("pensions", []),
            investment_knowledge=person_data.get("investment_knowledge", "medium"),
            trusted_contact_person=person_data.get("trusted_contact_person", ""),
            poa_status=person_data.get("poa_status", ""),
            will_status=person_data.get("will_status", ""),
            beneficiary_designations=person_data.get("beneficiary_designations", []),
        )
        people[person.external_id] = person

    accounts: dict[str, models.Account] = {}
    for account_data in data["accounts"]:
        account = models.Account.objects.create(
            external_id=account_data["id"],
            household=household,
            owner_person=people.get(account_data.get("owner_person_id")),
            account_type=account_data["type"],
            regulatory_objective=account_data["regulatory_objective"],
            regulatory_time_horizon=account_data["regulatory_time_horizon"],
            regulatory_risk_rating=account_data["regulatory_risk_rating"],
            current_value=account_data["current_value"],
            contribution_room=account_data.get("contribution_room"),
            contribution_history=account_data.get("contribution_history", []),
            is_held_at_purpose=account_data.get("is_held_at_purpose", True),
        )
        accounts[account.external_id] = account
        for holding_data in account_data.get("holdings", []):
            models.Holding.objects.create(
                account=account,
                sleeve_id=holding_data["sleeve_id"],
                sleeve_name=holding_data["sleeve_name"],
                weight=holding_data["weight"],
                market_value=holding_data["market_value"],
            )

    for goal_data in data["goals"]:
        goal = models.Goal.objects.create(
            external_id=goal_data["id"],
            household=household,
            name=goal_data["name"],
            target_amount=goal_data["target_amount"],
            target_date=goal_data["target_date"],
            necessity_score=goal_data["necessity_score"],
            current_funded_amount=goal_data["current_funded_amount"],
            contribution_plan=goal_data.get("contribution_plan", {}),
            goal_risk_score=goal_data["goal_risk_score"],
            status=goal_data.get("status", "watch"),
            notes=goal_data.get("notes", ""),
        )
        for link_data in goal_data.get("account_allocations", []):
            models.GoalAccountLink.objects.create(
                goal=goal,
                account=accounts[link_data["account_id"]],
                allocated_amount=link_data.get("allocated_amount"),
                allocated_pct=link_data.get("allocated_pct"),
            )
