from __future__ import annotations

import json
import os
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from engine.risk_profile import RiskProfileInput, compute_risk_profile

from web.api import models

# Hardcoded to match frontend/src/lib/auth.ts DISCLAIMER_VERSION constant.
# Update both together when bumping the disclaimer text.
_DISCLAIMER_VERSION = "v1"


class Command(BaseCommand):
    help = "Load committed synthetic personas for local development."

    def handle(self, *args, **options):  # noqa: ANN002, ANN003
        fixture_path = (
            Path(__file__).resolve().parents[4] / "personas/sandra_mike_chen/client_state.json"
        )
        data = json.loads(fixture_path.read_text())
        with transaction.atomic():
            household = _load_household(data)
            _load_risk_profile(household, data)
            _load_advisor_pre_ack(self, data)
        self.stdout.write(self.style.SUCCESS("Loaded synthetic Sandra/Mike Chen persona."))

        # A5: auto-seed initial PortfolioRun for demo readiness so a fresh
        # `reset-v2-dev.sh --yes` produces a Sandra/Mike Chen state that's
        # ready to demo (Goal route + Household route immediately have
        # engine recommendations to render). Helper raises typed exceptions
        # for known states (no active CMA, kill-switch); we silent-skip.
        from web.api.error_codes import safe_exception_summary
        from web.api.views import (
            EngineKillSwitchBlocked,
            InvalidCMAUniverse,
            MissingProvenance,
            NoActiveCMASnapshot,
            ReviewedStateNotConstructionReady,
            _trigger_portfolio_generation,
        )

        household_obj = data["id"]
        from web.api import models

        try:
            household = models.Household.objects.get(external_id=household_obj)
            run = _trigger_portfolio_generation(household, user=None, source="synthetic_load")
            if run is not None:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Generated initial PortfolioRun {run.external_id[:8]} "
                        f"for {household.display_name}."
                    )
                )
        except (
            EngineKillSwitchBlocked,
            NoActiveCMASnapshot,
            InvalidCMAUniverse,
            ReviewedStateNotConstructionReady,
            MissingProvenance,
        ) as exc:
            self.stdout.write(
                self.style.WARNING(f"PortfolioRun seed skipped: {type(exc).__name__}")
            )
        except Exception as exc:  # noqa: BLE001 — never break load on engine surprise
            self.stdout.write(
                self.style.WARNING(f"PortfolioRun seed failed: {safe_exception_summary(exc)}")
            )


def _load_household(data: dict) -> models.Household:
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
            missing_holdings_confirmed=account_data.get("missing_holdings_confirmed", False),
            cash_state=account_data.get("cash_state", models.Account.CashState.INVESTED),
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

    return household


def _load_risk_profile(household: models.Household, data: dict) -> None:
    """Persist the household's RiskProfile from fixture inputs (per A1)."""
    rp_data = data.get("risk_profile")
    if rp_data is None:
        return
    rp_inputs = RiskProfileInput(
        q1=rp_data["q1"],
        q2=rp_data["q2"],
        q3=rp_data.get("q3", []),
        q4=rp_data["q4"],
    )
    rp_result = compute_risk_profile(rp_inputs)
    models.RiskProfile.objects.create(
        household=household,
        q1=rp_inputs.q1,
        q2=rp_inputs.q2,
        q3=rp_inputs.q3,
        q4=rp_inputs.q4,
        tolerance_score=rp_result.tolerance_score,
        capacity_score=rp_result.capacity_score,
        tolerance_descriptor=rp_result.tolerance_descriptor,
        capacity_descriptor=rp_result.capacity_descriptor,
        household_descriptor=rp_result.household_descriptor,
        score_1_5=rp_result.score_1_5,
        anchor=rp_result.anchor,
        flags=rp_result.flags,
    )


def _load_advisor_pre_ack(command: BaseCommand, data: dict) -> None:
    """Mark the local advisor as having pre-acked disclaimer + tour (per A1).

    Drives `load_synthetic_personas` so a fresh demo state via
    `reset-v2-dev.sh --yes` doesn't pop PilotBanner / WelcomeTour on the
    advisor's first login. Fails silently if the advisor user doesn't
    exist yet (bootstrap_local_advisor hasn't run); reset-v2-dev.sh
    invokes bootstrap before this command, so this is the normal path.
    """
    pre_ack = data.get("advisor_pre_ack") or {}
    if not (pre_ack.get("disclaimer") or pre_ack.get("tour")):
        return
    email = os.getenv("MP20_LOCAL_ADMIN_EMAIL")
    if not email:
        return
    User = get_user_model()
    try:
        advisor = User.objects.get(email=email)
    except User.DoesNotExist:
        return
    profile, _ = models.AdvisorProfile.objects.get_or_create(user=advisor)
    now = timezone.now()
    if pre_ack.get("disclaimer"):
        profile.disclaimer_acknowledged_at = now
        profile.disclaimer_acknowledged_version = _DISCLAIMER_VERSION
    if pre_ack.get("tour"):
        profile.tour_completed_at = now
    profile.save()
    command.stdout.write(
        command.style.SUCCESS(
            f"Pre-acked disclaimer ({_DISCLAIMER_VERSION}) + tour for advisor {email}."
        )
    )
