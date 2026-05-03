from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone
from extraction.normalization import (
    bool_value as normalized_bool_value,
)
from extraction.normalization import (
    int_or_default as normalized_int_or_default,
)
from extraction.normalization import (
    json_number as normalized_json_number,
)
from extraction.normalization import (
    normalize_fact_value as canonical_normalize_fact_value,
)
from extraction.normalization import (
    normalize_key,
    risk_value_is_contract_score,
)
from extraction.normalization import (
    number as normalized_number,
)
from extraction.normalization import (
    risk_score as canonical_risk_score,
)
from extraction.reconciliation import (
    advisor_label,
    conflicts_for_facts,
    current_facts_by_field,
    fact_sort_key,
    field_section,
    semantic_entity_key,
)

from web.api import models
from web.api.access import linkable_households
from web.api.review_redaction import redact_evidence_quote
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

ALLOWED_ENGINE_ACCOUNT_TYPES = {
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


@dataclass(frozen=True)
class Readiness:
    engine_ready: bool
    construction_ready: bool
    kyc_compliance_ready: bool
    missing: list[dict[str, str]]
    construction_missing: list[dict[str, str]]


def reviewed_state_from_workspace(workspace: models.ReviewWorkspace) -> dict[str, Any]:
    current_facts = _current_facts(workspace)
    state = _empty_state()
    state["household"]["display_name"] = _value(
        current_facts, "household.display_name", workspace.label
    )
    state["household"]["household_type"] = _value(
        current_facts, "household.household_type", "couple"
    )
    state["household"]["household_risk_score"] = _risk_score(
        _value(current_facts, "risk.household_score", 3), default=3
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
    state["field_sources"] = _field_sources(workspace, current_facts)
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


def section_blockers(state: dict[str, Any], section: str) -> list[dict[str, str]]:
    readiness = readiness_for_state(state)
    blockers = [
        {"kind": "missing", "section": item["section"], "label": item["label"]}
        for item in readiness.missing
        if item["section"] == section
    ]
    for conflict in state.get("conflicts") or []:
        if conflict.get("resolved") or conflict.get("resolution"):
            continue
        field = str(conflict.get("field", ""))
        if _field_belongs_to_section(field, section):
            blockers.append(
                {
                    "kind": "conflict",
                    "section": section,
                    "label": f"Unresolved conflict: {advisor_label(field)}",
                }
            )
    for unknown in state.get("unknowns") or []:
        unknown_section = unknown.get("section") if isinstance(unknown, dict) else ""
        required = bool(unknown.get("required")) if isinstance(unknown, dict) else False
        label = (
            str(unknown.get("label") or unknown.get("field") or unknown)
            if isinstance(unknown, dict)
            else str(unknown)
        )
        if (unknown_section == section or _field_belongs_to_section(label, section)) and required:
            blockers.append(
                {"kind": "unknown", "section": section, "label": f"Required unknown: {label}"}
            )
    return blockers


def required_sections_approved(workspace: models.ReviewWorkspace) -> bool:
    approvals = {
        approval.section: approval.status for approval in workspace.section_approvals.all()
    }
    return all(
        approvals.get(section) == models.SectionApproval.Status.APPROVED
        for section in ENGINE_REQUIRED_SECTIONS
    )


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
    elif links:
        if any(
            link.get("allocated_amount") is None and link.get("allocated_pct") is None
            for link in links
        ):
            missing.append(_missing("goal_account_mapping", "Allocated dollars or percentage"))
        missing.extend(_full_assignment_blockers(accounts, links))
    if not risk.get("household_score") and not household.get("household_risk_score"):
        missing.append(_missing("risk", "Household risk input"))

    construction_missing = construction_blockers_for_state(state)
    engine_ready = not missing
    construction_ready = engine_ready and not construction_missing
    kyc_ready = bool(people and accounts)
    return Readiness(
        engine_ready=engine_ready,
        construction_ready=construction_ready,
        kyc_compliance_ready=kyc_ready,
        missing=missing,
        construction_missing=construction_missing,
    )


def construction_blockers_for_state(state: dict[str, Any]) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    household = state.get("household") or {}
    people = state.get("people") or []
    accounts = state.get("accounts") or []
    goals = state.get("goals") or []
    risk = state.get("risk") or {}

    household_risk = risk.get("household_score", household.get("household_risk_score"))
    if (
        household_risk is not None
        and household_risk != ""
        and not _risk_value_is_contract_score(household_risk)
    ):
        blockers.append(_missing("risk", "Household risk must be a 1-5 score"))
    if len(people) > 2:
        blockers.append(_missing("people", "Engine supports one or two household members"))

    for account in accounts:
        if not isinstance(account, dict):
            continue
        account_type = str(account.get("type") or "Non-Registered")
        if account_type not in ALLOWED_ENGINE_ACCOUNT_TYPES:
            blockers.append(
                _missing("accounts", f"Unsupported engine account type: {account_type}")
            )

    for goal in goals:
        if not isinstance(goal, dict):
            continue
        score = goal.get("goal_risk_score", 3)
        if not _risk_value_is_contract_score(score):
            blockers.append(_missing("goals", "Goal risk must be a 1-5 score"))

    return blockers


def validate_review_state_contract(state: dict[str, Any]) -> None:
    errors: list[str] = []
    household = state.get("household") or {}
    risk = state.get("risk") or {}
    for label, value in (
        ("household.household_risk_score", household.get("household_risk_score")),
        ("risk.household_score", risk.get("household_score")),
    ):
        if value is not None and value != "" and not _risk_value_is_contract_score(value):
            errors.append(f"{label} must be a 1-5 score.")
    for index, goal in enumerate(state.get("goals") or []):
        if not isinstance(goal, dict):
            continue
        value = goal.get("goal_risk_score")
        if value is not None and value != "" and not _risk_value_is_contract_score(value):
            errors.append(f"goals[{index}].goal_risk_score must be a 1-5 score.")
    if errors:
        raise ValueError(" ".join(errors))


def portfolio_generation_blockers_for_household(household: models.Household) -> list[str]:
    blockers: list[str] = []
    if household.household_risk_score < 1 or household.household_risk_score > 5:
        blockers.append("Household risk must be a 1-5 score.")

    accounts = list(household.accounts.all())
    if not accounts:
        blockers.append("At least one account is required before portfolio generation.")
    goals = list(household.goals.prefetch_related("account_allocations").all())
    if not goals:
        blockers.append("At least one goal is required before portfolio generation.")

    links_by_account: dict[str, list[models.GoalAccountLink]] = {
        account.external_id: [] for account in accounts if account.is_held_at_purpose
    }
    for account in accounts:
        if account.account_type not in ALLOWED_ENGINE_ACCOUNT_TYPES:
            blockers.append(
                f"Account {account.external_id} has unsupported type {account.account_type}."
            )
    for goal in goals:
        if not goal.target_date:
            blockers.append(f"Goal {goal.name} needs a target date or horizon.")
        if goal.goal_risk_score < 1 or goal.goal_risk_score > 5:
            blockers.append(f"Goal {goal.name} needs a 1-5 risk score.")
        for link in goal.account_allocations.all():
            if link.allocated_amount is None and link.allocated_pct is None:
                blockers.append("Every goal-account link needs allocated dollars or percentage.")
            if link.account.external_id in links_by_account:
                links_by_account[link.account.external_id].append(link)

    for account in accounts:
        if not account.is_held_at_purpose:
            continue
        links = links_by_account.get(account.external_id, [])
        if not links:
            blockers.append(f"Purpose account {account.external_id} must be assigned to a goal.")
            continue
        # Catalogued post-R7 real-PII bug 2: a zero/null current_value on
        # an is_held_at_purpose account with goal-links would either
        # silently pass (if links carried only allocated_pct) and then
        # crash engine.optimizer, or crash here on the abs() arithmetic.
        # Surface it as an explicit advisor-actionable blocker.
        account_value = account.current_value or Decimal("0")
        if account_value <= 0:
            blockers.append(
                f"Purpose account {account.external_id} needs a current value before "
                "portfolio generation (advisor must provide value, archive, or delete)."
            )
            continue
        if all(link.allocated_amount is not None for link in links):
            allocated = sum(link.allocated_amount for link in links)
            if abs(allocated - account.current_value) > Decimal("1.00"):
                blockers.append(
                    f"Purpose account {account.external_id} must be fully assigned to goals."
                )
        elif all(link.allocated_pct is not None for link in links):
            allocated_pct = sum(link.allocated_pct for link in links)
            if abs(allocated_pct - Decimal("1")) > Decimal("0.0001"):
                blockers.append(
                    f"Purpose account {account.external_id} goal percentages must sum to 100%."
                )
        else:
            blockers.append(
                "Do not mix dollar and percentage goal-account assignments within one account."
            )

    return blockers


def portfolio_generation_blocker_for_household(household: models.Household) -> str:
    blockers = portfolio_generation_blockers_for_household(household)
    return blockers[0] if blockers else ""


def _full_assignment_blockers(
    accounts: list[dict[str, Any]], links: list[dict[str, Any]]
) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    for account in accounts:
        if account.get("is_held_at_purpose") is False:
            continue
        account_id = str(account.get("id") or "")
        if not account_id:
            continue
        account_links = [link for link in links if str(link.get("account_id")) == account_id]
        if not account_links:
            blockers.append(_missing("goal_account_mapping", "Every Purpose account assigned"))
            continue
        account_value = _number(account.get("current_value"))
        if account_value <= 0:
            # Catalogued post-R7 real-PII bug: a zero/null current_value
            # on an is_held_at_purpose account with goal-links was being
            # silently skipped here, surviving both engine_ready and
            # construction_ready, then crashing engine.optimizer with
            # ValueError. Surface it as an explicit advisor-actionable
            # blocker so the commit gate is closed.
            label = (
                f"Purpose account needs a current value before commit (account id: {account_id})"
            )
            blockers.append(_missing("accounts", label))
            continue
        if all(link.get("allocated_amount") is not None for link in account_links):
            allocated = sum(_number(link.get("allocated_amount")) for link in account_links)
            if abs(allocated - account_value) > Decimal("1.00"):
                blockers.append(_missing("goal_account_mapping", "Full account-dollar assignment"))
        elif all(link.get("allocated_pct") is not None for link in account_links):
            allocated_pct = sum(_number(link.get("allocated_pct")) for link in account_links)
            if abs(allocated_pct - Decimal("1")) > Decimal("0.0001"):
                blockers.append(_missing("goal_account_mapping", "Full account-percent assignment"))
        else:
            blockers.append(_missing("goal_account_mapping", "Consistent assignment basis"))
    return blockers


@transaction.atomic
def create_state_version(
    workspace: models.ReviewWorkspace,
    *,
    user,
    state: dict[str, Any] | None = None,
) -> models.ReviewedClientStateVersion:
    locked_workspace = models.ReviewWorkspace.objects.select_for_update().get(pk=workspace.pk)
    state = (
        state or locked_workspace.reviewed_state or reviewed_state_from_workspace(locked_workspace)
    )
    readiness = readiness_for_state(state)
    latest_version = (
        models.ReviewedClientStateVersion.objects.filter(workspace=locked_workspace)
        .order_by("-version")
        .values_list("version", flat=True)
        .first()
    )
    next_version = (latest_version or 0) + 1
    version = models.ReviewedClientStateVersion.objects.create(
        workspace=locked_workspace,
        version=next_version,
        schema_version=REVIEW_SCHEMA_VERSION,
        state=state,
        readiness=readiness.__dict__,
        created_by=user if getattr(user, "is_authenticated", False) else None,
    )
    locked_workspace.reviewed_state = state
    locked_workspace.readiness = readiness.__dict__
    # NEVER downgrade a COMMITTED workspace. Same root cause as the
    # reconcile-after-commit race: a stale code path that calls
    # create_state_version on a committed workspace must not flip status
    # back to ENGINE_READY/REVIEW_READY. The version row itself is still
    # appended (audit / history value); only the live workspace status
    # is preserved at COMMITTED.
    update_fields = ["reviewed_state", "readiness", "updated_at"]
    if locked_workspace.status != models.ReviewWorkspace.Status.COMMITTED:
        locked_workspace.status = (
            models.ReviewWorkspace.Status.ENGINE_READY
            if readiness.engine_ready
            else models.ReviewWorkspace.Status.REVIEW_READY
        )
        update_fields.append("status")
    locked_workspace.save(update_fields=update_fields)
    workspace.reviewed_state = locked_workspace.reviewed_state
    workspace.readiness = locked_workspace.readiness
    workspace.status = locked_workspace.status
    return version


@transaction.atomic
def commit_reviewed_state(
    workspace: models.ReviewWorkspace,
    *,
    user,
    household: models.Household | None = None,
) -> models.Household:
    if workspace.status == models.ReviewWorkspace.Status.COMMITTED:
        if not workspace.linked_household:
            raise ValueError("Review workspace is committed but has no linked household.")
        if household is not None and household.pk != workspace.linked_household_id:
            raise ValueError("Review workspace is already committed to another household.")
        return workspace.linked_household

    state = workspace.reviewed_state or reviewed_state_from_workspace(workspace)
    readiness = readiness_for_state(state)
    if not readiness.engine_ready:
        raise ValueError("Reviewed state is not engine-ready.")
    if not readiness.construction_ready:
        raise ValueError("Reviewed state is not construction-ready.")
    if not required_sections_approved(workspace):
        raise ValueError("Required review sections are not approved.")

    household = household or _create_household_from_state(workspace, state, user=user)
    _merge_household_state(household, state)
    if blocker := portfolio_generation_blocker_for_household(household):
        raise ValueError(f"Committed state is not construction-ready: {blocker}")
    version = create_state_version(workspace, user=user, state=state)
    version.is_committed = True
    version.committed_household = household
    version.save(update_fields=["is_committed", "committed_household"])
    workspace.linked_household = household
    workspace.status = models.ReviewWorkspace.Status.COMMITTED
    workspace.match_candidates = []
    workspace.save(update_fields=["linked_household", "status", "match_candidates", "updated_at"])
    record_event(
        action="review_state_committed",
        entity_type="review_workspace",
        entity_id=workspace.external_id,
        actor=user.get_username() if getattr(user, "is_authenticated", False) else "system",
        metadata={"household_id": household.external_id, "version": version.version},
    )
    return household


def match_candidates(workspace: models.ReviewWorkspace) -> list[dict[str, Any]]:
    if workspace.status == models.ReviewWorkspace.Status.COMMITTED or workspace.linked_household_id:
        return []

    state = workspace.reviewed_state or reviewed_state_from_workspace(workspace)
    display_name = (state.get("household") or {}).get("display_name", "")
    people = state.get("people") or []
    candidates: list[dict[str, Any]] = []
    households = linkable_households(workspace.owner)

    for household in households.prefetch_related("members", "accounts"):
        if workspace.linked_household_id == household.pk:
            continue
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
    return current_facts_by_field(facts)


def _fact_sort_key(fact: models.ExtractedFact) -> tuple[int, int, float]:
    return fact_sort_key(
        fact.field,
        fact.document.document_type,
        fact.confidence,
        fact.asserted_at or date.min,
    )


def _value(current_facts: dict[str, models.ExtractedFact], field: str, default: Any) -> Any:
    fact = current_facts.get(field)
    return _normalize_fact_value(field, fact.value) if fact is not None else default


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
        grouped.setdefault(index, {})[name] = _normalize_fact_value(name, fact.value)
    return [grouped[index] for index in sorted(grouped)]


def _normalize_reviewed_relationships(state: dict[str, Any]) -> None:
    for index, person in enumerate(state["people"], start=1):
        person.setdefault("id", semantic_entity_key("review_person", person, index))

    for index, account in enumerate(state["accounts"], start=1):
        account.setdefault("id", semantic_entity_key("review_account", account, index))
        if "account_number" in account:
            account.setdefault("source_account_identifier", account["account_number"])

    for index, goal in enumerate(state["goals"], start=1):
        goal.setdefault("id", semantic_entity_key("review_goal", goal, index))
        goal.setdefault("goal_risk_score", 3)

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
        if "goal_id" not in link and first_goal_id:
            link["goal_id"] = first_goal_id
            link["advisor_confirmation_required"] = True
        if "account_id" not in link and first_account_id:
            link["account_id"] = first_account_id
            link["advisor_confirmation_required"] = True


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
        "field_sources": {},
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
    """Workspace conflicts enriched with per-candidate source metadata.

    Phase 5a (2026-05-02): each conflict carries a `candidates` array
    so the conflict-resolution card UI can render multi-source
    attribution (filename, doc type, confidence, derivation_method,
    redacted evidence quote) without the frontend re-querying
    extracted_facts. The candidates entry preserves the existing
    `fact_ids` array shape; consumers that only need the IDs ignore
    the new field.
    """
    facts = list(workspace.extracted_facts.select_related("document"))
    raw_conflicts = conflicts_for_facts(facts)
    facts_by_id = {fact.id: fact for fact in facts}
    enriched: list[dict[str, Any]] = []
    for conflict in raw_conflicts:
        candidates: list[dict[str, Any]] = []
        for fact_id in conflict.get("fact_ids", []):
            fact = facts_by_id.get(fact_id)
            if fact is None:
                continue
            document = fact.document
            candidates.append(
                {
                    "fact_id": fact.id,
                    "value": fact.value,
                    "confidence": fact.confidence,
                    "derivation_method": fact.derivation_method,
                    "source_document_id": document.id,
                    "source_document_filename": document.original_filename,
                    "source_document_type": document.document_type,
                    "source_location": fact.source_location,
                    "source_page": fact.source_page,
                    "redacted_evidence_quote": redact_evidence_quote(fact.evidence_quote or ""),
                    "asserted_at": fact.asserted_at.isoformat() if fact.asserted_at else None,
                }
            )
        enriched.append({**conflict, "candidates": candidates})
    return enriched


def _field_sources(
    workspace: models.ReviewWorkspace,
    current_facts: dict[str, models.ExtractedFact],
) -> dict[str, dict[str, Any]]:
    return {
        field: {
            "fact_id": fact.id,
            "field_label": advisor_label(field),
            "section": field_section(field),
            "document_id": fact.document_id,
            "document_name": fact.document.original_filename,
            "document_type": fact.document.document_type,
            "confidence": fact.confidence,
            "source_page": fact.source_page,
            "source_location": fact.source_location,
            "evidence_quote": fact.evidence_quote,
            "extraction_run_id": fact.extraction_run_id,
            "classifier_route": fact.document.processing_metadata.get("classifier", {}).get(
                "route", ""
            ),
            "schema_hints": fact.document.processing_metadata.get("classifier", {}).get(
                "schema_hints", []
            ),
        }
        for field, fact in current_facts.items()
        if fact.workspace_id == workspace.id
    }


def _missing(section: str, label: str) -> dict[str, str]:
    return {"section": section, "label": label}


def _number(value: Any) -> Decimal:
    return normalized_number(value)


def _json_number(value: Any) -> int | float:
    return normalized_json_number(value)


def _normalize_fact_value(field: str, value: Any) -> Any:
    return canonical_normalize_fact_value(field, value)


def _bool_value(value: Any) -> bool:
    return normalized_bool_value(value)


def _int_or_default(value: Any, default: int) -> int:
    return normalized_int_or_default(value, default)


def _risk_score(value: Any, *, default: int) -> int:
    return canonical_risk_score(value, default=default)


def _risk_value_is_contract_score(value: Any) -> bool:
    return risk_value_is_contract_score(value)


def _create_household_from_state(
    workspace: models.ReviewWorkspace, state: dict[str, Any], *, user
) -> models.Household:
    household = state.get("household") or {}
    return models.Household.objects.create(
        external_id=f"review_{workspace.external_id}",
        owner=user if getattr(user, "is_authenticated", False) else workspace.owner,
        display_name=household.get("display_name") or workspace.label,
        household_type=household.get("household_type") or "couple",
        household_risk_score=_risk_score(household.get("household_risk_score"), default=3),
        notes="Created from reviewed real-data workspace.",
    )


def _merge_household_state(household: models.Household, state: dict[str, Any]) -> None:
    household_state = state.get("household") or {}
    household.display_name = household_state.get("display_name") or household.display_name
    household.household_type = household_state.get("household_type") or household.household_type
    household.household_risk_score = _risk_score(
        household_state.get("household_risk_score"), default=household.household_risk_score
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
            missing_holdings_confirmed=bool(account_state.get("missing_holdings_confirmed", False)),
            cash_state=account_state.get("cash_state", models.Account.CashState.INVESTED),
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
            target_amount=(
                _number(goal_state.get("target_amount"))
                if goal_state.get("target_amount") is not None
                else None
            ),
            target_date=_target_date(goal_state),
            necessity_score=_int_or_default(goal_state.get("necessity_score"), 3),
            current_funded_amount=_number(goal_state.get("current_funded_amount")),
            contribution_plan=goal_state.get("contribution_plan") or {},
            goal_risk_score=_risk_score(goal_state.get("goal_risk_score"), default=3),
            notes=goal_state.get("notes", ""),
        )
        goals_by_id[external_id] = goal

    for link_state in state.get("goal_account_links") or []:
        goal = goals_by_id.get(str(link_state.get("goal_id")))
        account = accounts_by_id.get(str(link_state.get("account_id")))
        if not goal or not account:
            continue
        models.GoalAccountLink.objects.create(
            external_id=link_state.get("id") or models.uuid_string(),
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
    age = _int_or_default(person_state.get("age"), 60)
    return (timezone.now() - timedelta(days=round(age * 365.25))).date()


def _target_date(goal_state: dict[str, Any]) -> date:
    if target_date := goal_state.get("target_date"):
        return date.fromisoformat(str(target_date))
    horizon = _int_or_default(goal_state.get("time_horizon_years"), 5)
    return (timezone.now() + timedelta(days=round(horizon * 365.25))).date()


def _normalize(value: str) -> str:
    return normalize_key(value)


def _field_belongs_to_section(field: str, section: str) -> bool:
    return field_section(field) == section
