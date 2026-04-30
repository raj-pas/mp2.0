from __future__ import annotations

from extraction.layer3_facts import Fact
from extraction.normalization import normalize_fact_value
from extraction.reconciliation import advisor_label, field_section


def reconcile_facts(facts: list[Fact]) -> dict:
    """Build a review-ready fact summary with normalized current values and conflicts."""

    grouped: dict[str, list[Fact]] = {}
    for fact in facts:
        grouped.setdefault(fact.field, []).append(fact)
    values: dict[str, object] = {}
    conflicts: list[dict] = []
    for field, field_facts in grouped.items():
        normalized = [normalize_fact_value(field, fact.value) for fact in field_facts]
        values[field] = normalized[0]
        if len({str(value) for value in normalized}) > 1:
            conflicts.append(
                {
                    "field": field,
                    "label": advisor_label(field),
                    "section": field_section(field),
                    "values": [str(value) for value in normalized],
                    "resolved": False,
                }
            )
    return {"values": values, "conflicts": conflicts}
