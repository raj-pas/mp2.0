from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Any

from extraction.entity_alignment import EntityAlignment
from extraction.normalization import normalize_fact_value, normalize_key

CONFIDENCE_PRIORITY = {"high": 0, "medium": 1, "low": 2}

FIELD_LABELS = {
    "household.display_name": "Household name",
    "household.household_type": "Household type",
    "household.last_communication_date": "Last communication date",
    "risk.household_score": "Household risk score",
}

SECTION_PREFIXES = {
    "household": ("household",),
    "people": ("people", "person"),
    "accounts": ("accounts", "holdings"),
    "goals": ("goals",),
    "goal_account_mapping": ("goal_account_links", "goal_account_mapping"),
    "risk": ("risk",),
}

REQUIRED_SECTIONS = {
    "household",
    "people",
    "accounts",
    "goals",
    "goal_account_mapping",
    "risk",
}


def fact_sort_key(
    field: str, document_type: str, confidence: str, asserted_at: date | None
) -> tuple[int, int, float]:
    source_priority = source_authority(document_type, field)
    confidence_priority = CONFIDENCE_PRIORITY.get(confidence, 3)
    asserted = asserted_at or date.min
    return (source_priority, confidence_priority, -asserted.toordinal())


def source_authority(document_type: str, field: str) -> int:
    section = field_section(field)
    type_key = document_type or "unknown"
    matrix = {
        "household": {
            "crm_export": 5,
            "kyc": 10,
            "identity": 12,
            "intake": 15,
            "planning": 25,
            "meeting_note": 35,
            "statement": 40,
        },
        "people": {
            "crm_export": 5,
            "kyc": 8,
            "identity": 10,
            "intake": 18,
            "meeting_note": 35,
            "planning": 40,
            "statement": 45,
        },
        "accounts": {
            "statement": 5,
            "crm_export": 8,
            "spreadsheet": 10,
            "kyc": 20,
            "planning": 30,
            "meeting_note": 45,
        },
        "goals": {
            "planning": 5,
            "meeting_note": 8,
            "intake": 12,
            "kyc": 25,
            "statement": 45,
            "crm_export": 50,
        },
        "goal_account_mapping": {
            "planning": 8,
            "meeting_note": 12,
            "statement": 20,
            "spreadsheet": 20,
            "kyc": 40,
        },
        "risk": {
            "kyc": 5,
            "planning": 18,
            "meeting_note": 25,
            "intake": 30,
            "statement": 50,
        },
    }
    return matrix.get(section, {}).get(type_key, 90)


def field_section(field: str) -> str:
    normalized = field.replace("[", ".").lower()
    for section, prefixes in SECTION_PREFIXES.items():
        if any(normalized.startswith(prefix) for prefix in prefixes):
            return section
    return "household"


def advisor_label(field: str) -> str:
    if field in FIELD_LABELS:
        return FIELD_LABELS[field]
    normalized = field.replace("[", " ").replace("]", "").replace(".", " ")
    words = [word for word in normalized.replace("_", " ").split() if not word.isdigit()]
    return " ".join(words).strip().capitalize() or field


def current_facts_by_field(
    facts: Iterable[Any],
    *,
    alignment: EntityAlignment | None = None,
) -> dict[str, Any]:
    """Group facts to one winner per field, with optional cross-doc alignment.

    When `alignment` is provided, each fact's field is rewritten via
    `alignment.aligned_field_for(fact)` BEFORE grouping — so a
    workspace-canonical field path
    (`people[<canonical_idx>].display_name`) becomes the grouping key
    instead of the raw per-document field path. This eliminates the
    classic father+son / Alice+Bob false-conflict where two distinct
    real-world people both land at `people[0]` in their respective
    source docs.

    When `alignment` is None, behavior is unchanged from the original
    field-keyed grouping (backwards-compat for unit tests + any caller
    that hasn't yet plumbed alignment through).
    """
    grouped: dict[str, list[Any]] = {}
    for fact in facts:
        field_key = _aligned_or_raw_field(fact, alignment)
        grouped.setdefault(field_key, []).append(fact)
    current: dict[str, Any] = {}
    for field, field_facts in grouped.items():
        current[field] = sorted(
            field_facts,
            key=lambda fact: fact_sort_key(
                field,
                getattr(getattr(fact, "document", None), "document_type", "unknown"),
                getattr(fact, "confidence", "medium"),
                getattr(fact, "asserted_at", None),
            ),
        )[0]
    return current


def conflicts_for_facts(
    facts: Iterable[Any],
    *,
    alignment: EntityAlignment | None = None,
) -> list[dict[str, Any]]:
    """Conflicts for an iterable of facts, with optional cross-doc alignment.

    See `current_facts_by_field` for the alignment contract.
    """
    grouped: dict[str, list[Any]] = {}
    for fact in facts:
        field_key = _aligned_or_raw_field(fact, alignment)
        grouped.setdefault(field_key, []).append(fact)

    conflicts: list[dict[str, Any]] = []
    for field, field_facts in grouped.items():
        normalized_values = {
            str(normalize_fact_value(field, getattr(fact, "value", ""))) for fact in field_facts
        }
        if len(normalized_values) <= 1:
            continue
        section = field_section(field)
        authority_values = {
            source_authority(getattr(fact.document, "document_type", "unknown"), field)
            for fact in field_facts
        }
        same_authority = len(authority_values) == 1
        conflicts.append(
            {
                "field": field,
                "label": advisor_label(field),
                "section": section,
                "values": sorted(normalized_values),
                "count": len(field_facts),
                "fact_ids": [fact.id for fact in field_facts],
                "resolved": False,
                "required": section in REQUIRED_SECTIONS,
                "same_authority": same_authority,
                "source_types": sorted(
                    {
                        getattr(getattr(fact, "document", None), "document_type", "unknown")
                        for fact in field_facts
                    }
                ),
            }
        )
    return conflicts


def _aligned_or_raw_field(fact: Any, alignment: EntityAlignment | None) -> str:
    """Return the canonical field for a fact when alignment is provided,
    else fall back to the raw `fact.field` value."""
    raw = str(getattr(fact, "field", ""))
    if alignment is None:
        return raw
    aligned = alignment.aligned_field_for(fact)
    return aligned if aligned is not None else raw


def semantic_entity_key(prefix: str, item: dict[str, Any], index: int) -> str:
    if item.get("id"):
        return str(item["id"])
    identity_parts = [
        item.get("source_account_identifier"),
        item.get("account_number"),
        item.get("type"),
        item.get("name"),
        item.get("display_name"),
    ]
    basis = "_".join(str(part) for part in identity_parts if part)
    if not basis:
        basis = str(index)
    return f"{prefix}_{normalize_key(basis)}"
