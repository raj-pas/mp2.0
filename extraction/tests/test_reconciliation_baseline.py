"""Backfill tests pinning EXISTING field-keyed grouping behavior in
`extraction.reconciliation` (audit Block B #2 — backfill BEFORE the new
alignment matcher ships, so any regression is caught by the baseline).

These tests exercise `current_facts_by_field` + `conflicts_for_facts`
WITHOUT alignment (legacy / backwards-compat code path). Phase P1.1
adds an optional `alignment=` parameter; the legacy callers (None)
must keep working unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from extraction.reconciliation import (
    advisor_label,
    conflicts_for_facts,
    current_facts_by_field,
    fact_sort_key,
    field_section,
)


@dataclass
class _FakeDoc:
    id: int
    document_type: str = "kyc"
    original_filename: str = "doc.pdf"


@dataclass
class _FakeFact:
    field: str
    value: Any
    document: _FakeDoc | None = None
    confidence: str = "medium"
    asserted_at: date | None = None
    derivation_method: str = "extracted"
    id: int = 0


# ---------------------------------------------------------------------------
# 1. current_facts_by_field — single fact passes through.
# ---------------------------------------------------------------------------


def test_current_facts_single_fact_returns_that_fact() -> None:
    fact = _FakeFact(
        id=1,
        field="household.display_name",
        value="Smith Family",
        document=_FakeDoc(id=1),
    )
    current = current_facts_by_field([fact])
    assert current == {"household.display_name": fact}


# ---------------------------------------------------------------------------
# 2. current_facts_by_field — most authoritative source wins.
# ---------------------------------------------------------------------------


def test_current_facts_most_authoritative_source_wins() -> None:
    """Per the source_authority matrix, an `accounts.*` field weighted
    most strongly to `statement` -> a statement wins over a kyc when
    they conflict on `accounts[0].current_value`."""
    statement_fact = _FakeFact(
        id=1,
        field="accounts[0].current_value",
        value=42_000,
        document=_FakeDoc(id=1, document_type="statement"),
        confidence="high",
    )
    kyc_fact = _FakeFact(
        id=2,
        field="accounts[0].current_value",
        value=40_000,
        document=_FakeDoc(id=2, document_type="kyc"),
        confidence="high",
    )
    current = current_facts_by_field([kyc_fact, statement_fact])
    assert current["accounts[0].current_value"] is statement_fact


# ---------------------------------------------------------------------------
# 3. conflicts_for_facts — same-field different-values produces a conflict.
# ---------------------------------------------------------------------------


def test_conflicts_detects_disagreement_on_same_field() -> None:
    f1 = _FakeFact(
        id=1,
        field="people[0].display_name",
        value="Alice",
        document=_FakeDoc(id=1, document_type="kyc"),
    )
    f2 = _FakeFact(
        id=2,
        field="people[0].display_name",
        value="Bob",
        document=_FakeDoc(id=2, document_type="statement"),
    )
    conflicts = conflicts_for_facts([f1, f2])
    assert len(conflicts) == 1
    conflict = conflicts[0]
    assert conflict["field"] == "people[0].display_name"
    assert conflict["section"] == "people"
    assert sorted(conflict["values"]) == ["Alice", "Bob"]
    assert conflict["count"] == 2
    assert sorted(conflict["fact_ids"]) == [1, 2]
    assert conflict["resolved"] is False
    assert conflict["required"] is True
    assert conflict["same_authority"] is False
    assert sorted(conflict["source_types"]) == ["kyc", "statement"]


# ---------------------------------------------------------------------------
# 4. conflicts_for_facts — agreement on the same field is NOT a conflict.
# ---------------------------------------------------------------------------


def test_conflicts_no_disagreement_no_conflict() -> None:
    f1 = _FakeFact(
        id=1,
        field="household.display_name",
        value="Smith",
        document=_FakeDoc(id=1, document_type="kyc"),
    )
    f2 = _FakeFact(
        id=2,
        field="household.display_name",
        value="Smith",
        document=_FakeDoc(id=2, document_type="statement"),
    )
    conflicts = conflicts_for_facts([f1, f2])
    assert conflicts == []


# ---------------------------------------------------------------------------
# 5. field_section + advisor_label — known + unknown paths.
# ---------------------------------------------------------------------------


def test_field_section_maps_known_prefixes() -> None:
    assert field_section("household.display_name") == "household"
    assert field_section("people[0].display_name") == "people"
    assert field_section("accounts[1].current_value") == "accounts"
    assert field_section("goals[0].name") == "goals"
    assert field_section("goal_account_links[0].allocated_amount") == "goal_account_mapping"
    assert field_section("risk.household_score") == "risk"


def test_field_section_falls_back_to_household_for_unknown() -> None:
    assert field_section("planning.cashflow_year_2027") == "household"


def test_advisor_label_known_field() -> None:
    assert advisor_label("household.display_name") == "Household name"


def test_advisor_label_indexed_field_strips_index() -> None:
    label = advisor_label("people[0].date_of_birth")
    # Numeric index is removed.
    assert "0" not in label.split()
    assert "date" in label.lower()


# ---------------------------------------------------------------------------
# 6. fact_sort_key — confidence + asserted_at participate in sort.
# ---------------------------------------------------------------------------


def test_fact_sort_key_orders_by_priority() -> None:
    high_recent = fact_sort_key("accounts[0].current_value", "statement", "high", date(2026, 5, 1))
    low_old = fact_sort_key("accounts[0].current_value", "statement", "low", date(2024, 1, 1))
    # Lower priority tuple sorts FIRST -> higher confidence wins.
    assert high_recent < low_old


# ---------------------------------------------------------------------------
# 7. conflicts_for_facts — same-authority detection.
# ---------------------------------------------------------------------------


def test_conflicts_same_authority_two_kyc_sources() -> None:
    f1 = _FakeFact(
        id=1,
        field="people[0].display_name",
        value="Alice",
        document=_FakeDoc(id=1, document_type="kyc"),
    )
    f2 = _FakeFact(
        id=2,
        field="people[0].display_name",
        value="Bob",
        document=_FakeDoc(id=2, document_type="kyc"),
    )
    conflicts = conflicts_for_facts([f1, f2])
    assert len(conflicts) == 1
    assert conflicts[0]["same_authority"] is True


# ---------------------------------------------------------------------------
# 8. conflicts_for_facts — empty input -> empty list (boundary).
# ---------------------------------------------------------------------------


def test_conflicts_empty_input_returns_empty_list() -> None:
    assert conflicts_for_facts([]) == []
    assert current_facts_by_field([]) == {}
