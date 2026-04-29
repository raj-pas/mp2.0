from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from web.api import models
from web.audit.writer import record_event

REVIEW_SCHEMA_VERSION = "reviewed_client_state.v1"
ENGINE_REQUIRED_SECTIONS = [
    "household",
    "people",
    "accounts",
    "goals",
    "goal_account_mapping",
    "risk",
]

SOURCE_PRIORITY = {
    "statement": 10,
    "crm_export": 20,
    "kyc": 25,
    "planning": 30,
    "intake": 35,
    "meeting_note": 40,
    "spreadsheet": 45,
    "other": 90,
    "unknown": 100,
}


@dataclass(frozen=True)
class Readiness:
    engine_ready: bool
    kyc_compliance_ready: bool
    missing: list[dict[str, str]]


def reviewed_state_from_workspace(workspace: models.ReviewWorkspace) -> dict[str, Any]:
    current_facts = _current_facts(workspace)
    state = _empty_state()
    state["household"]["display_name"] = _value(
        current_facts, "household.display_name", workspace.label
    )
    state["household"]["household_type"] = _value(
        current_facts, "household.household_type", "couple"
    )
    state["household"]["household_risk_score"] = int(
        _value(current_facts, "risk.household_score", 3) or 3
    )

    people = _value(
        current_facts,
        "people",
        _indexed_items(current_facts, "people", {"display_name": "name", "full_name": "name"}),
    )
    accounts = _value(
        current_facts,
        "accounts",
        _indexed_items(
            current_facts,
            "accounts",
            {
                "account_type": "type",
                "account_value": "current_value",
                "market_value": "current_value",
            },
        ),
    )
    goals = _value(
        current_facts,
        "goals",
        _indexed_items(
            current_facts,
            "goals",
            {
                "goal_name": "name",
                "horizon_years": "time_horizon_years",
                "time_horizon": "time_horizon_years",
            },
        ),
    )
    links = _value(
        current_facts,
        "goal_account_links",
        _indexed_items(
            current_facts,
            "goal_account_links",
            {
                "allocated_value": "allocated_amount",
                "allocation_value": "allocated_amount",
            },
        ),
    )

    state["people"] = people if isinstance(people, list) else []
    state["accounts"] = accounts if isinstance(accounts, list) else []
    state["goals"] = goals if isinstance(goals, list) else []
    state["goal_account_links"] = links if isinstance(links, list) else []
    _normalize_reviewed_relationships(state)
    state["risk"]["household_score"] = state["household"]["household_risk_score"]
    state["source_summary"] = _source_summary(workspace)
    state["conflicts"] = _conflicts(workspace)
    state["readiness"] = readiness_for_state(state).__dict__
    return state


def apply_state_patch(state: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = _empty_state()
    merged.update(state or {})
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    merged["schema_version"] = REVIEW_SCHEMA_VERSION
    merged["readiness"] = readiness_for_state(merged).__dict__
    return merged


def readiness_for_state(state: dict[str, Any]) -> Readiness:
    missing: list[dict[str, str]] = []
    household = state.get("household") or {}
    people = state.get("people") or []
    accounts = state.get("accounts") or []
    goals = state.get("goals") or []
    links = state.get("goal_account_links") or []
    risk = state.get("risk") or {}

    if not household.get("display_name"):
        missing.append(_missing("household", "Household display name"))
    if household.get("household_type") not in {"single", "couple"}:
        missing.append(_missing("household", "Household type"))
    if not people:
        missing.append(_missing("people", "At least one household member"))
    elif not any(person.get("dob") or person.get("age") for person in people):
        missing.append(_missing("people", "At least one member DOB or age"))

    if not accounts:
        missing.append(_missing("accounts", "At least one account"))
    else:
        if not any(_number(account.get("current_value")) > 0 for account in accounts):
            missing.append(_missing("accounts", "Account current value"))
        if not any(
            account.get("holdings") or account.get("missing_holdings_confirmed")
            for account in accounts
        ):
            missing.append(_missing("accounts", "Holdings or explicit missing-holdings marker"))

    if not goals:
        missing.append(_missing("goals", "At least one goal"))
    else:
        if not any(goal.get("target_date") or goal.get("time_horizon_years") for goal in goals):
            missing.append(_missing("goals", "At least one goal time horizon"))

    if accounts and goals and not links:
        missing.append(_missing("goal_account_mapping", "Advisor-confirmed goal-account mapping"))
    if not risk.get("household_score") and not household.get("household_risk_score"):
        missing.append(_missing("risk", "Household risk input"))

    engine_ready = not missing
    kyc_ready = bool(people and accounts)
    return Readiness(
        engine_ready=engine_ready,
        kyc_compliance_ready=kyc_ready,
        missing=missing,
    )


def create_state_version(
    workspace: models.ReviewWorkspace,
    *,
    user,
    state: dict[str, Any] | None = None,
) -> models.ReviewedClientStateVersion:
    state = state or workspace.reviewed_state or reviewed_state_from_workspace(workspace)
    readiness = readiness_for_state(state)
    next_version = models.ReviewedClientStateVersion.objects.filter(workspace=workspace).count() + 1
    version = models.ReviewedClientStateVersion.objects.create(
        workspace=workspace,
        version=next_version,
        schema_version=REVIEW_SCHEMA_VERSION,
        state=state,
        readiness=readiness.__dict__,
        created_by=user if getattr(user, "is_authenticated", False) else None,
    )
    workspace.reviewed_state = state
    workspace.readiness = readiness.__dict__
    workspace.status = (
        models.ReviewWorkspace.Status.ENGINE_READY
        if readiness.engine_ready
        else models.ReviewWorkspace.Status.REVIEW_READY
    )
    workspace.save(update_fields=["reviewed_state", "readiness", "status", "updated_at"])
    return version


@transaction.atomic
def commit_reviewed_state(
    workspace: models.ReviewWorkspace,
    *,
    user,
    household: models.Household | None = None,
) -> models.Household:
    state = workspace.reviewed_state or reviewed_state_from_workspace(workspace)
    readiness = readiness_for_state(state)
    if not readiness.engine_ready:
        raise ValueError("Reviewed state is not engine-ready.")

    household = household or _create_household_from_state(workspace, state)
    _merge_household_state(household, state)
    version = create_state_version(workspace, user=user, state=state)
    version.is_committed = True
    version.committed_household = household
    version.save(update_fields=["is_committed", "committed_household"])
    workspace.linked_household = household
    workspace.status = models.ReviewWorkspace.Status.COMMITTED
    workspace.save(update_fields=["linked_household", "status", "updated_at"])
    record_event(
        action="review_state_committed",
        entity_type="review_workspace",
        entity_id=workspace.external_id,
        actor=user.get_username() if getattr(user, "is_authenticated", False) else "system",
        metadata={"household_id": household.external_id, "version": version.version},
    )
    return household


def match_candidates(workspace: models.ReviewWorkspace) -> list[dict[str, Any]]:
    state = workspace.reviewed_state or reviewed_state_from_workspace(workspace)
    display_name = (state.get("household") or {}).get("display_name", "")
    people = state.get("people") or []
    candidates: list[dict[str, Any]] = []
    for household in models.Household.objects.prefetch_related("members", "accounts").all():
        reasons: list[str] = []
        score = 0
        if display_name and _normalize(display_name) == _normalize(household.display_name):
            score += 60
            reasons.append("household name")
        member_names = {_normalize(person.name) for person in household.members.all()}
        for person in people:
            if _normalize(str(person.get("name", ""))) in member_names:
                score += 20
                reasons.append(f"member name: {person.get('name')}")
        if score:
            candidates.append(
                {
                    "household_id": household.external_id,
                    "display_name": household.display_name,
                    "confidence": min(score, 95),
                    "reasons": reasons,
                }
            )
    return sorted(candidates, key=lambda candidate: candidate["confidence"], reverse=True)[:5]


def engine_payload_from_reviewed_state(state: dict[str, Any]) -> dict[str, Any]:
    readiness = readiness_for_state(state)
    if not readiness.engine_ready:
        raise ValueError("Reviewed state is not engine-ready.")
    return state


def _current_facts(workspace: models.ReviewWorkspace) -> dict[str, models.ExtractedFact]:
    facts = list(workspace.extracted_facts.select_related("document"))
    grouped: dict[str, list[models.ExtractedFact]] = {}
    for fact in facts:
        grouped.setdefault(fact.field, []).append(fact)

    current: dict[str, models.ExtractedFact] = {}
    for field, field_facts in grouped.items():
        current[field] = sorted(field_facts, key=_fact_sort_key)[0]
    return current


def _fact_sort_key(fact: models.ExtractedFact) -> tuple[int, int, float]:
    source_priority = SOURCE_PRIORITY.get(fact.document.document_type, 100)
    confidence_priority = {"high": 0, "medium": 1, "low": 2}.get(fact.confidence, 3)
    asserted = fact.asserted_at or date.min
    return (source_priority, confidence_priority, -asserted.toordinal())


def _value(current_facts: dict[str, models.ExtractedFact], field: str, default: Any) -> Any:
    fact = current_facts.get(field)
    return fact.value if fact is not None else default


def _indexed_items(
    current_facts: dict[str, models.ExtractedFact],
    prefix: str,
    aliases: dict[str, str],
) -> list[dict[str, Any]]:
    pattern = re.compile(rf"^{re.escape(prefix)}\[(?P<index>\d+)\]\.(?P<field>.+)$")
    grouped: dict[int, dict[str, Any]] = {}
    for field, fact in current_facts.items():
        match = pattern.match(field)
        if not match:
            continue
        index = int(match.group("index"))
        name = aliases.get(match.group("field"), match.group("field"))
        grouped.setdefault(index, {})[name] = fact.value
    return [grouped[index] for index in sorted(grouped)]


def _normalize_reviewed_relationships(state: dict[str, Any]) -> None:
    for index, person in enumerate(state["people"], start=1):
        person.setdefault("id", _safe_external_id("review_person", person.get("name"), index))

    for index, account in enumerate(state["accounts"], start=1):
        account.setdefault("id", _safe_external_id("review_account", account.get("type"), index))
        if "account_number" in account:
            account.setdefault("source_account_identifier", account["account_number"])

    for index, goal in enumerate(state["goals"], start=1):
        goal.setdefault("id", _safe_external_id("review_goal", goal.get("name"), index))

    first_account_id = state["accounts"][0]["id"] if state["accounts"] else None
    first_goal_id = state["goals"][0]["id"] if state["goals"] else None
    goals_by_name = {
        _normalize(str(goal.get("name", ""))): goal["id"]
        for goal in state["goals"]
        if goal.get("name")
    }
    for link in state["goal_account_links"]:
        if "goal_id" not in link and link.get("goal_name"):
            link["goal_id"] = goals_by_name.get(_normalize(str(link["goal_name"])), first_goal_id)
        link.setdefault("goal_id", first_goal_id)
        link.setdefault("account_id", first_account_id)


def _safe_external_id(prefix: str, value: Any, index: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", str(value or "").lower()).strip("_")
    return f"{prefix}_{slug or index}"


def _empty_state() -> dict[str, Any]:
    return {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "household": {},
        "people": [],
        "accounts": [],
        "goals": [],
        "goal_account_links": [],
        "risk": {},
        "planning": {},
        "behavioral_notes": {},
        "unknowns": [],
        "conflicts": [],
        "source_summary": [],
        "readiness": {},
    }


def _source_summary(workspace: models.ReviewWorkspace) -> list[dict[str, Any]]:
    return [
        {
            "document_id": document.id,
            "filename": document.original_filename,
            "document_type": document.document_type,
            "status": document.status,
            "failure_reason": document.failure_reason,
        }
        for document in workspace.documents.all()
    ]


def _conflicts(workspace: models.ReviewWorkspace) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    grouped: dict[str, list[models.ExtractedFact]] = {}
    for fact in workspace.extracted_facts.all():
        grouped.setdefault(fact.field, []).append(fact)
    for field, facts in grouped.items():
        values = {str(fact.value) for fact in facts}
        if len(values) > 1:
            conflicts.append({"field": field, "values": sorted(values), "count": len(facts)})
    return conflicts


def _missing(section: str, label: str) -> dict[str, str]:
    return {"section": section, "label": label}


def _number(value: Any) -> Decimal:
    try:
        if value in {None, ""}:
            return Decimal("0")
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def _create_household_from_state(
    workspace: models.ReviewWorkspace, state: dict[str, Any]
) -> models.Household:
    household = state.get("household") or {}
    return models.Household.objects.create(
        external_id=f"review_{workspace.external_id}",
        display_name=household.get("display_name") or workspace.label,
        household_type=household.get("household_type") or "couple",
        household_risk_score=int(household.get("household_risk_score") or 3),
        notes="Created from reviewed real-data workspace.",
    )


def _merge_household_state(household: models.Household, state: dict[str, Any]) -> None:
    household_state = state.get("household") or {}
    household.display_name = household_state.get("display_name") or household.display_name
    household.household_type = household_state.get("household_type") or household.household_type
    household.household_risk_score = int(
        household_state.get("household_risk_score") or household.household_risk_score
    )
    household.save(
        update_fields=["display_name", "household_type", "household_risk_score", "updated_at"]
    )

    household.members.all().delete()
    household.accounts.all().delete()
    household.goals.all().delete()

    people_by_id: dict[str, models.Person] = {}
    for index, person_state in enumerate(state.get("people") or [], start=1):
        external_id = person_state.get("id") or f"{household.external_id}_person_{index}"
        person = models.Person.objects.create(
            external_id=external_id,
            household=household,
            name=person_state.get("name") or f"Household member {index}",
            dob=_dob(person_state),
            marital_status=person_state.get("marital_status", ""),
            investment_knowledge=person_state.get("investment_knowledge", "medium"),
        )
        people_by_id[external_id] = person

    accounts_by_id: dict[str, models.Account] = {}
    for index, account_state in enumerate(state.get("accounts") or [], start=1):
        external_id = account_state.get("id") or f"{household.external_id}_account_{index}"
        owner = people_by_id.get(str(account_state.get("owner_person_id") or ""))
        account = models.Account.objects.create(
            external_id=external_id,
            household=household,
            owner_person=owner,
            account_type=account_state.get("type") or "Non-Registered",
            regulatory_objective=account_state.get("regulatory_objective") or "growth_and_income",
            regulatory_time_horizon=account_state.get("regulatory_time_horizon") or "3-10y",
            regulatory_risk_rating=account_state.get("regulatory_risk_rating") or "medium",
            current_value=_number(account_state.get("current_value")),
            is_held_at_purpose=bool(account_state.get("is_held_at_purpose", True)),
        )
        accounts_by_id[external_id] = account
        for holding_index, holding_state in enumerate(account_state.get("holdings") or [], start=1):
            weight = _number(holding_state.get("weight"))
            market_value = _number(holding_state.get("market_value"))
            models.Holding.objects.create(
                account=account,
                sleeve_id=holding_state.get("sleeve_id") or f"review_holding_{holding_index}",
                sleeve_name=holding_state.get("sleeve_name") or "Reviewed holding",
                weight=weight if weight <= 1 else Decimal("0"),
                market_value=market_value,
            )

    goals_by_id: dict[str, models.Goal] = {}
    for index, goal_state in enumerate(state.get("goals") or [], start=1):
        external_id = goal_state.get("id") or f"{household.external_id}_goal_{index}"
        goal = models.Goal.objects.create(
            external_id=external_id,
            household=household,
            name=goal_state.get("name") or f"Reviewed goal {index}",
            target_amount=_number(goal_state.get("target_amount") or 1),
            target_date=_target_date(goal_state),
            necessity_score=int(goal_state.get("necessity_score") or 3),
            current_funded_amount=_number(goal_state.get("current_funded_amount")),
            contribution_plan=goal_state.get("contribution_plan") or {},
            goal_risk_score=int(goal_state.get("goal_risk_score") or 3),
            notes=goal_state.get("notes", ""),
        )
        goals_by_id[external_id] = goal

    for link_state in state.get("goal_account_links") or []:
        goal = goals_by_id.get(str(link_state.get("goal_id")))
        account = accounts_by_id.get(str(link_state.get("account_id")))
        if not goal or not account:
            continue
        models.GoalAccountLink.objects.create(
            goal=goal,
            account=account,
            allocated_amount=_number(link_state.get("allocated_amount"))
            if link_state.get("allocated_amount") is not None
            else None,
            allocated_pct=_number(link_state.get("allocated_pct"))
            if link_state.get("allocated_pct") is not None
            else None,
        )


def _dob(person_state: dict[str, Any]) -> date:
    if dob := person_state.get("dob"):
        return date.fromisoformat(str(dob))
    age = int(person_state.get("age") or 60)
    return (timezone.now() - timedelta(days=round(age * 365.25))).date()


def _target_date(goal_state: dict[str, Any]) -> date:
    if target_date := goal_state.get("target_date"):
        return date.fromisoformat(str(target_date))
    horizon = int(goal_state.get("time_horizon_years") or 5)
    return (timezone.now() + timedelta(days=round(horizon * 365.25))).date()


def _normalize(value: str) -> str:
    return " ".join(value.lower().split())
