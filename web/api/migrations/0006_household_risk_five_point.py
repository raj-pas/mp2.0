from __future__ import annotations

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models

ALLOWED_ACCOUNT_TYPES = {
    "RRSP",
    "TFSA",
    "RESP",
    "RDSP",
    "FHSA",
    "Non-Registered",
    "LIRA",
    "RRIF",
    "Corporate",
}


def _risk_to_five(value, *, default: int = 3) -> int:
    qualitative = {
        "very_low": 1,
        "low": 2,
        "cautious": 2,
        "conservative": 2,
        "medium": 3,
        "moderate": 3,
        "balanced": 3,
        "medium_risk": 3,
        "high": 4,
        "growth": 4,
        "growth_oriented": 4,
        "very_high": 5,
    }
    if isinstance(value, str):
        normalized = "_".join(value.lower().split())
        if normalized in qualitative:
            return qualitative[normalized]
    try:
        score = int(value)
    except (TypeError, ValueError):
        score = default
    if score > 5:
        score = ((score + 1) // 2) if score <= 10 else 5
    return max(1, min(score, 5))


def _remap_state_payload(payload):
    if not isinstance(payload, dict):
        return payload
    state = dict(payload)
    household = dict(state.get("household") or {})
    risk = dict(state.get("risk") or {})
    if "household_risk_score" in household:
        household["household_risk_score"] = _risk_to_five(household["household_risk_score"])
    if "household_score" in risk:
        risk["household_score"] = _risk_to_five(risk["household_score"])
    elif "household_risk_score" in household:
        risk["household_score"] = household["household_risk_score"]
    state["household"] = household
    state["risk"] = risk

    goals = []
    for goal in state.get("goals") or []:
        if not isinstance(goal, dict):
            goals.append(goal)
            continue
        item = dict(goal)
        if "goal_risk_score" in item:
            item["goal_risk_score"] = _risk_to_five(item["goal_risk_score"])
        else:
            item["goal_risk_score"] = 3
        goals.append(item)
    state["goals"] = goals

    readiness = dict(state.get("readiness") or {})
    if "construction_ready" not in readiness:
        readiness["construction_ready"] = _construction_ready_for_state(state, readiness)
    readiness.setdefault("construction_missing", [])
    state["readiness"] = readiness
    return state


def _construction_ready_for_state(state, readiness) -> bool:
    if not readiness.get("engine_ready"):
        return False
    household = state.get("household") or {}
    risk = state.get("risk") or {}
    household_risk = risk.get("household_score", household.get("household_risk_score"))
    if _risk_to_five(household_risk) != household_risk and not isinstance(household_risk, str):
        return False
    for account in state.get("accounts") or []:
        if isinstance(account, dict) and account.get("type") not in ALLOWED_ACCOUNT_TYPES:
            return False
    for goal in state.get("goals") or []:
        if not isinstance(goal, dict):
            continue
        score = goal.get("goal_risk_score", 3)
        if _risk_to_five(score) != score and not isinstance(score, str):
            return False
    return True


def remap_household_risk_to_five(apps, schema_editor):  # noqa: ARG001
    Household = apps.get_model("api", "Household")
    Goal = apps.get_model("api", "Goal")
    ReviewWorkspace = apps.get_model("api", "ReviewWorkspace")
    ReviewedClientStateVersion = apps.get_model("api", "ReviewedClientStateVersion")
    ExtractedFact = apps.get_model("api", "ExtractedFact")

    for household in Household.objects.all().iterator():
        household.household_risk_score = _risk_to_five(household.household_risk_score)
        household.save(update_fields=["household_risk_score"])

    for goal in Goal.objects.all().iterator():
        goal.goal_risk_score = _risk_to_five(goal.goal_risk_score)
        goal.save(update_fields=["goal_risk_score"])

    for workspace in ReviewWorkspace.objects.all().iterator():
        workspace.reviewed_state = _remap_state_payload(workspace.reviewed_state)
        workspace.readiness = _remap_state_payload({"readiness": workspace.readiness})["readiness"]
        workspace.save(update_fields=["reviewed_state", "readiness"])

    for version in ReviewedClientStateVersion.objects.all().iterator():
        version.state = _remap_state_payload(version.state)
        version.readiness = _remap_state_payload({"readiness": version.readiness})["readiness"]
        version.save(update_fields=["state", "readiness"])

    for fact in ExtractedFact.objects.filter(field__icontains="risk").iterator():
        fact.value = _risk_to_five(fact.value)
        fact.save(update_fields=["value"])


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0005_account_missing_holdings_confirmed_and_more"),
    ]

    operations = [
        migrations.RunPython(remap_household_risk_to_five, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="household",
            name="household_risk_score",
            field=models.PositiveSmallIntegerField(
                default=3,
                validators=[MinValueValidator(1), MaxValueValidator(5)],
            ),
        ),
        migrations.AlterField(
            model_name="goal",
            name="goal_risk_score",
            field=models.PositiveSmallIntegerField(
                default=3,
                validators=[MinValueValidator(1), MaxValueValidator(5)],
            ),
        ),
        migrations.AddConstraint(
            model_name="household",
            constraint=models.CheckConstraint(
                condition=models.Q(household_risk_score__gte=1)
                & models.Q(household_risk_score__lte=5),
                name="household_risk_score_1_5",
            ),
        ),
        migrations.AddConstraint(
            model_name="goal",
            constraint=models.CheckConstraint(
                condition=models.Q(goal_risk_score__gte=1) & models.Q(goal_risk_score__lte=5),
                name="goal_risk_score_1_5",
            ),
        ),
    ]
