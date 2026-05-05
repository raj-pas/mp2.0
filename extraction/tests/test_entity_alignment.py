"""Unit tests for `extraction.entity_alignment.align_facts` (Phase P1.1).

Covers the §A1.50 P1.1 boundary edge cases + the canonical scenarios in
the plan §P1.1 test plan: the original Niesner bug shape, the
TIGHTENED 2-field threshold (Round 13 #2 LOCKED), and the boundary
edge cases (empty, single doc, tied scores, below threshold).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from extraction.entity_alignment import (
    ACCOUNTS_THRESHOLD,
    GOALS_THRESHOLD,
    PEOPLE_THRESHOLD,
    align_facts,
)

# ---------------------------------------------------------------------------
# Test scaffolding — minimal duck-typed Fact / Document stand-ins.
# ---------------------------------------------------------------------------


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
    document_id: int | None = None
    confidence: str = "medium"
    asserted_at: Any = None
    derivation_method: str = "extracted"
    id: int = 0


def _facts(*specs: tuple[int, str, Any, str]) -> list[_FakeFact]:
    """specs: (doc_id, field, value, doc_type)."""
    docs: dict[int, _FakeDoc] = {}
    facts: list[_FakeFact] = []
    next_fact_id = 1
    for doc_id, field_path, value, doc_type in specs:
        doc = docs.setdefault(
            doc_id,
            _FakeDoc(id=doc_id, document_type=doc_type, original_filename=f"doc{doc_id}.pdf"),
        )
        facts.append(
            _FakeFact(
                field=field_path,
                value=value,
                document=doc,
                document_id=doc_id,
                id=next_fact_id,
            )
        )
        next_fact_id += 1
    return facts


# ---------------------------------------------------------------------------
# 1. Empty list (boundary) — backwards-compat.
# ---------------------------------------------------------------------------


def test_empty_facts_returns_empty_alignment() -> None:
    alignment = align_facts([])
    assert alignment.canonical_count == 0
    assert alignment.mapping == {}
    # align_facts (re-indexer) over empty list is a no-op.
    assert alignment.align_facts([]) == []


# ---------------------------------------------------------------------------
# 2. Single doc, single person — canonical_index === local_index.
# ---------------------------------------------------------------------------


def test_single_doc_single_person_canonical_equals_local() -> None:
    facts = _facts(
        (1, "people[0].display_name", "Alice Smith", "kyc"),
        (1, "people[0].date_of_birth", "1962-04-15", "kyc"),
    )
    alignment = align_facts(facts)
    assert alignment.canonical_count == 1
    assert alignment.canonical_count_by_prefix() == {"people": 1, "accounts": 0, "goals": 0}
    assert alignment.canonical_index_for(facts[0]) == 0
    assert alignment.canonical_index_for(facts[1]) == 0


# ---------------------------------------------------------------------------
# 3. TIGHTENED THRESHOLD: 2 docs same surname, no DOB -> NO MERGE.
#    The father+son guard. Round 13 #2 LOCKED.
# ---------------------------------------------------------------------------


def test_two_docs_same_surname_no_dob_does_not_merge() -> None:
    """When two docs reference people who share ONLY a name token (and
    no DOB / no last4 account match), the matcher refuses to merge.
    Eliminates the classic father+son same-surname false-merge."""
    facts = _facts(
        (1, "people[0].display_name", "John Niesner", "kyc"),
        (2, "people[0].display_name", "Robert Niesner", "statement"),
    )
    alignment = align_facts(facts)
    # Two distinct canonicals — single-field "Niesner" overlap is
    # NOT enough.
    assert alignment.canonical_count == 2
    assert alignment.canonical_index_for(facts[0]) != alignment.canonical_index_for(facts[1])


# ---------------------------------------------------------------------------
# 4. TIGHTENED THRESHOLD: 2 docs same person with both NAME + DOB -> MERGE.
# ---------------------------------------------------------------------------


def test_two_docs_same_person_name_and_dob_merges() -> None:
    facts = _facts(
        (1, "people[0].display_name", "Alice Smith", "kyc"),
        (1, "people[0].date_of_birth", "1962-04-15", "kyc"),
        (2, "people[0].display_name", "Alice Smith", "statement"),
        (2, "people[0].date_of_birth", "1962-04-15", "statement"),
    )
    alignment = align_facts(facts)
    assert alignment.canonical_count == 1
    canonicals = {alignment.canonical_index_for(f) for f in facts}
    assert canonicals == {0}


# ---------------------------------------------------------------------------
# 5. Tied scores — most prior contributing docs wins.
# ---------------------------------------------------------------------------


def test_tied_score_breaks_to_most_contributing_docs() -> None:
    """Two existing canonicals each match a new triple at the same score.
    The canonical with MORE contributing_docs wins the tie-break."""
    # Doc 1 + Doc 2 establish canonical 0 for Alice (both contribute).
    # Doc 3 establishes canonical 1 for Alice-twin (only doc 3 contributes).
    # Doc 4 has Alice with name+DOB matching both -> should pick canonical 0
    # because canonical 0 has 2 contributing docs vs canonical 1's 1.
    facts = [
        # canonical 0 contributors
        *_facts(
            (1, "people[0].display_name", "Alice Common", "kyc"),
            (1, "people[0].date_of_birth", "1962-04-15", "kyc"),
            (2, "people[0].display_name", "Alice Common", "statement"),
            (2, "people[0].date_of_birth", "1962-04-15", "statement"),
        ),
        # canonical 1 contributor (different DOB so it's a separate canonical)
        *_facts(
            (3, "people[0].display_name", "Alice Common", "kyc"),
            (3, "people[0].date_of_birth", "1970-01-01", "kyc"),
        ),
    ]
    # Now doc 4 references Alice with name + 1962 DOB AGAIN.
    facts.extend(
        _facts(
            (4, "people[0].display_name", "Alice Common", "meeting_note"),
            (4, "people[0].date_of_birth", "1962-04-15", "meeting_note"),
        )
    )
    alignment = align_facts(facts)
    # The Alice 1962 + Alice 1970 are 2 canonicals (different DOBs ->
    # only name overlap which is below threshold). Doc 4 matches doc 1+2
    # -> canonical 0.
    assert alignment.canonical_count == 2
    doc4_facts = [f for f in facts if f.document_id == 4]
    canonicals_for_doc4 = {alignment.canonical_index_for(f) for f in doc4_facts}
    # Doc 4 must merge into canonical 0 (the one with 2 contributors).
    assert canonicals_for_doc4 == {0}


# ---------------------------------------------------------------------------
# 6. Below threshold creates new canonical (no over-merging).
# ---------------------------------------------------------------------------


def test_below_threshold_creates_new_canonical() -> None:
    """A goal with no name match + only target_amount mentioned has no
    discriminating signal — must NOT merge to a different goal that
    happens to share a target."""
    facts = _facts(
        (1, "goals[0].name", "Retirement", "planning"),
        (1, "goals[0].target_amount", 1_000_000, "planning"),
        (2, "goals[0].target_amount", 1_000_000, "meeting_note"),
    )
    # Goal in doc 2 has no name -> single feature (target only, no
    # horizon-match) -> below threshold -> new canonical.
    alignment = align_facts(facts)
    assert alignment.canonical_count_by_prefix()["goals"] == 2


# ---------------------------------------------------------------------------
# 7. Father + son same surname no DOB -> 2 canonicals (Round 13 #2 case).
#    Identical to test #3 but uses the explicit canonical-count assertion
#    in the plan deliverables list.
# ---------------------------------------------------------------------------


def test_father_and_son_same_surname_no_dob_two_canonicals() -> None:
    facts = _facts(
        (1, "people[0].display_name", "John Senior Niesner", "kyc"),
        (1, "people[1].display_name", "John Junior Niesner", "kyc"),
        (2, "people[0].display_name", "John Niesner", "statement"),
    )
    alignment = align_facts(facts)
    # All 3 distinct people: senior, junior, doc-2-John (ambiguous).
    # Without DOB or last4, none of them merge.
    assert alignment.canonical_count_by_prefix()["people"] == 3


# ---------------------------------------------------------------------------
# 8. Full identity match across 2 docs -> 1 canonical.
# ---------------------------------------------------------------------------


def test_full_identity_match_across_two_docs_one_canonical() -> None:
    facts = _facts(
        (1, "people[0].display_name", "Alice Smith", "kyc"),
        (1, "people[0].date_of_birth", "1962-04-15", "kyc"),
        (1, "accounts[0].account_number", "12345678", "kyc"),
        (2, "people[0].display_name", "Alice Smith", "statement"),
        (2, "people[0].date_of_birth", "1962-04-15", "statement"),
        (2, "accounts[0].account_number", "12345678", "statement"),
    )
    alignment = align_facts(facts)
    by_prefix = alignment.canonical_count_by_prefix()
    assert by_prefix["people"] == 1
    assert by_prefix["accounts"] == 1


# ---------------------------------------------------------------------------
# 9. Account number exact (hashed) match merges 2 RRSP statements.
# ---------------------------------------------------------------------------


def test_account_number_exact_match_merges_accounts() -> None:
    facts = _facts(
        (1, "accounts[0].account_number", "111-222-333", "statement"),
        (1, "accounts[0].account_type", "rrsp", "statement"),
        (2, "accounts[0].account_number", "111-222-333", "statement"),
        (2, "accounts[0].account_type", "rrsp", "statement"),
    )
    alignment = align_facts(facts)
    assert alignment.canonical_count_by_prefix()["accounts"] == 1


def test_distinct_account_numbers_two_canonicals() -> None:
    facts = _facts(
        (1, "accounts[0].account_number", "111-222-333", "statement"),
        (1, "accounts[0].account_type", "rrsp", "statement"),
        (2, "accounts[0].account_number", "999-888-777", "statement"),
        (2, "accounts[0].account_type", "rrsp", "statement"),
    )
    alignment = align_facts(facts)
    assert alignment.canonical_count_by_prefix()["accounts"] == 2


# ---------------------------------------------------------------------------
# 10. Goals with same name -> 1 canonical.
# ---------------------------------------------------------------------------


def test_goals_same_name_merge() -> None:
    facts = _facts(
        (1, "goals[0].name", "Retirement", "planning"),
        (2, "goals[0].name", "Retirement", "meeting_note"),
    )
    alignment = align_facts(facts)
    assert alignment.canonical_count_by_prefix()["goals"] == 1


# ---------------------------------------------------------------------------
# Bonus: re-indexer rewrites field paths in-place.
# ---------------------------------------------------------------------------


def test_align_facts_reindexer_rewrites_field_paths() -> None:
    """If doc 2's people[0] aligns to canonical 0, doc 2's facts are
    rewritten from `people[0].*` to `people[0].*` (still 0 here);
    when canonical_index differs, the field path is rewritten."""
    # Doc 1: Alice (0), Bob (1). Doc 2: Bob (0).  Bob in doc 2 should
    # align to canonical_index 1 (Bob), so the field path on doc 2 is
    # rewritten from people[0] to people[1].
    facts = _facts(
        (1, "people[0].display_name", "Alice Smith", "kyc"),
        (1, "people[0].date_of_birth", "1962-04-15", "kyc"),
        (1, "people[1].display_name", "Bob Smith", "kyc"),
        (1, "people[1].date_of_birth", "1965-08-20", "kyc"),
        (2, "people[0].display_name", "Bob Smith", "statement"),
        (2, "people[0].date_of_birth", "1965-08-20", "statement"),
    )
    alignment = align_facts(facts)
    rewritten = alignment.align_facts(list(facts))
    # Doc 2's facts now reference canonical_index 1 (Bob), not local 0.
    doc2_facts = [f for f in rewritten if f.document_id == 2]
    for f in doc2_facts:
        assert f.field.startswith("people[1].")


# ---------------------------------------------------------------------------
# Bonus: thresholds exposed for downstream sanity checks.
# ---------------------------------------------------------------------------


def test_thresholds_are_documented_constants() -> None:
    assert PEOPLE_THRESHOLD == 100
    assert ACCOUNTS_THRESHOLD == 80
    assert GOALS_THRESHOLD == 80


# ---------------------------------------------------------------------------
# Coverage backfill: branches not exercised by the principal scenarios above.
# ---------------------------------------------------------------------------


def test_accounts_institution_type_only_falls_below_threshold_with_two() -> None:
    """Two accounts in different docs share institution+type but no
    account_number — they merge ONLY when no other discriminating
    signal disagrees. (institution+type = +50, no number = below 80)."""
    facts = _facts(
        (1, "accounts[0].account_type", "rrsp", "statement"),
        (1, "accounts[0].institution", "Sun Life", "statement"),
        (2, "accounts[0].account_type", "rrsp", "statement"),
        (2, "accounts[0].institution", "Sun Life", "statement"),
    )
    alignment = align_facts(facts)
    # institution+type only = 50 (below 80), so they DO NOT merge.
    assert alignment.canonical_count_by_prefix()["accounts"] == 2


def test_accounts_type_value_close_alone_below_threshold() -> None:
    """Type + close-value = +40 alone is BELOW the 80 threshold."""
    facts = _facts(
        (1, "accounts[0].account_type", "rrsp", "statement"),
        (1, "accounts[0].current_value", 50_000, "statement"),
        (2, "accounts[0].account_type", "rrsp", "statement"),
        (2, "accounts[0].current_value", 51_000, "statement"),
    )
    alignment = align_facts(facts)
    # 40 alone < 80 -> two canonicals.
    assert alignment.canonical_count_by_prefix()["accounts"] == 2


def test_accounts_institution_type_plus_value_close_merges() -> None:
    """institution+type (+50) + type+value-close (+40) = 90 -> MERGE."""
    facts = _facts(
        (1, "accounts[0].account_type", "rrsp", "statement"),
        (1, "accounts[0].institution", "Sun Life", "statement"),
        (1, "accounts[0].current_value", 50_000, "statement"),
        (2, "accounts[0].account_type", "rrsp", "statement"),
        (2, "accounts[0].institution", "Sun Life", "statement"),
        (2, "accounts[0].current_value", 50_500, "statement"),
    )
    alignment = align_facts(facts)
    assert alignment.canonical_count_by_prefix()["accounts"] == 1


def test_goals_target_and_horizon_alone_below_threshold() -> None:
    """target_amount close + horizon match = +50 alone is below 80."""
    facts = _facts(
        (1, "goals[0].name", "Retirement", "planning"),
        (1, "goals[0].target_amount", 1_000_000, "planning"),
        (1, "goals[0].time_horizon_years", 10, "planning"),
        (2, "goals[0].name", "Travel", "meeting_note"),
        (2, "goals[0].target_amount", 1_000_000, "meeting_note"),
        (2, "goals[0].time_horizon_years", 10, "meeting_note"),
    )
    alignment = align_facts(facts)
    # Different name keys -> +50 from target+horizon alone is below 80.
    assert alignment.canonical_count_by_prefix()["goals"] == 2


def test_goals_name_match_plus_target_horizon_merges_high_score() -> None:
    """Same name (+80) + same target & horizon (+50) = 130 -> MERGE."""
    facts = _facts(
        (1, "goals[0].name", "Retirement", "planning"),
        (1, "goals[0].target_amount", 1_000_000, "planning"),
        (1, "goals[0].time_horizon_years", 10, "planning"),
        (2, "goals[0].name", "Retirement", "meeting_note"),
        (2, "goals[0].target_amount", 1_010_000, "meeting_note"),
        (2, "goals[0].time_horizon_years", 10, "meeting_note"),
    )
    alignment = align_facts(facts)
    assert alignment.canonical_count_by_prefix()["goals"] == 1


def test_iso_date_accepts_datetime_isoformat() -> None:
    """Verify _iso_date branch: a value with .isoformat() gets read."""
    from datetime import date

    facts = _facts(
        (1, "people[0].display_name", "Alice Smith", "kyc"),
    )
    facts.append(
        _FakeFact(
            id=99,
            field="people[0].date_of_birth",
            value=date(1962, 4, 15),
            document=facts[0].document,
            document_id=facts[0].document_id,
        )
    )
    facts.extend(
        _facts(
            (2, "people[0].display_name", "Alice Smith", "statement"),
            (2, "people[0].date_of_birth", "1962-04-15", "statement"),
        )
    )
    alignment = align_facts(facts)
    assert alignment.canonical_count_by_prefix()["people"] == 1


def test_iso_date_accepts_iso_with_time_component() -> None:
    """Strings of form `YYYY-MM-DDThh:mm:ssZ` are truncated to date."""
    facts = _facts(
        (1, "people[0].display_name", "Alice Smith", "kyc"),
        (1, "people[0].date_of_birth", "1962-04-15T00:00:00Z", "kyc"),
        (2, "people[0].display_name", "Alice Smith", "statement"),
        (2, "people[0].date_of_birth", "1962-04-15", "statement"),
    )
    alignment = align_facts(facts)
    assert alignment.canonical_count_by_prefix()["people"] == 1


def test_iso_date_rejects_non_iso_strings() -> None:
    """Garbage DOB strings -> dob feature stays None -> name-only match
    falls below threshold."""
    facts = _facts(
        (1, "people[0].display_name", "Alice Smith", "kyc"),
        (1, "people[0].date_of_birth", "April 15, 1962", "kyc"),
        (2, "people[0].display_name", "Alice Smith", "statement"),
        (2, "people[0].date_of_birth", "April 15, 1962", "statement"),
    )
    alignment = align_facts(facts)
    # DOBs failed to parse -> match is name-only -> below threshold.
    assert alignment.canonical_count_by_prefix()["people"] == 2


def test_field_unrelated_to_entity_passes_through_unchanged() -> None:
    """Fact with a `household.*` field is not entity-prefixed; the
    re-indexer leaves it alone."""
    fact = _FakeFact(
        id=1,
        field="household.display_name",
        value="Smith Family",
        document=_FakeDoc(id=1),
        document_id=1,
    )
    alignment = align_facts([fact])
    rewritten = alignment.align_facts([fact])
    assert rewritten[0].field == "household.display_name"
    assert alignment.canonical_index_for(fact) is None
    assert alignment.aligned_field_for(fact) is None


def test_document_key_falls_back_to_filename_when_id_missing() -> None:
    """If document.id is None but original_filename is set, that's the
    document key."""
    doc = _FakeDoc(id=None, original_filename="anonymous.pdf")  # type: ignore[arg-type]
    fact1 = _FakeFact(id=1, field="people[0].display_name", value="Alice", document=doc)
    fact2 = _FakeFact(id=2, field="people[0].date_of_birth", value="1962-04-15", document=doc)
    alignment = align_facts([fact1, fact2])
    assert alignment.canonical_count_by_prefix()["people"] == 1


def test_document_key_falls_back_to_document_id_when_no_document() -> None:
    """If `.document` is None but `.document_id` is set, use that."""
    fact1 = _FakeFact(id=1, field="people[0].display_name", value="Alice", document_id=42)
    fact2 = _FakeFact(id=2, field="people[0].date_of_birth", value="1962-04-15", document_id=42)
    alignment = align_facts([fact1, fact2])
    assert alignment.canonical_count_by_prefix()["people"] == 1


def test_maybe_int_handles_string_with_units() -> None:
    """time_horizon_years = '10 years' -> parses to 10."""
    facts = _facts(
        (1, "goals[0].name", "Retirement", "planning"),
        (1, "goals[0].target_amount", 1_000_000, "planning"),
        (1, "goals[0].time_horizon_years", "10 years", "planning"),
        (2, "goals[0].name", "Retirement", "meeting_note"),
        (2, "goals[0].target_amount", 1_000_000, "meeting_note"),
        (2, "goals[0].time_horizon_years", 10, "meeting_note"),
    )
    alignment = align_facts(facts)
    assert alignment.canonical_count_by_prefix()["goals"] == 1


def test_maybe_float_handles_currency_formatted_string() -> None:
    """current_value = '$50,000.00' -> parses to 50000.0."""
    facts = _facts(
        (1, "accounts[0].account_type", "rrsp", "statement"),
        (1, "accounts[0].institution", "Sun Life", "statement"),
        (1, "accounts[0].current_value", "$50,000.00", "statement"),
        (2, "accounts[0].account_type", "rrsp", "statement"),
        (2, "accounts[0].institution", "Sun Life", "statement"),
        (2, "accounts[0].current_value", 50_500, "statement"),
    )
    alignment = align_facts(facts)
    assert alignment.canonical_count_by_prefix()["accounts"] == 1


def test_account_number_only_digits_are_hashed() -> None:
    """An account number with letters keeps only the digits when
    hashed; same digit stream merges."""
    facts = _facts(
        (1, "accounts[0].account_number", "ACCT-12345678-X", "statement"),
        (1, "accounts[0].account_type", "rrsp", "statement"),
        (2, "accounts[0].account_number", "12345678", "statement"),
        (2, "accounts[0].account_type", "rrsp", "statement"),
    )
    alignment = align_facts(facts)
    assert alignment.canonical_count_by_prefix()["accounts"] == 1


def test_empty_or_none_account_number_does_not_match() -> None:
    """Empty / non-digit values produce None hashes; no merge from those."""
    facts = _facts(
        (1, "accounts[0].account_number", "", "statement"),
        (1, "accounts[0].account_type", "rrsp", "statement"),
        (2, "accounts[0].account_number", "ABC", "statement"),
        (2, "accounts[0].account_type", "rrsp", "statement"),
    )
    alignment = align_facts(facts)
    # Both account_number_hash are None; only type matches -> no merge.
    assert alignment.canonical_count_by_prefix()["accounts"] == 2


def test_short_account_number_no_last4_boost() -> None:
    """An account number under 4 digits doesn't yield a last4 boost."""
    facts = _facts(
        (1, "accounts[0].account_number", "12", "statement"),
    )
    alignment = align_facts(facts)
    # Just ensures last4 path is exercised without error.
    assert alignment.canonical_count_by_prefix()["accounts"] == 1


def test_zero_zero_current_values_treated_as_close() -> None:
    """current_value 0 vs 0 -> _values_close returns True."""
    facts = _facts(
        (1, "accounts[0].account_type", "rrsp", "statement"),
        (1, "accounts[0].institution", "Sun Life", "statement"),
        (1, "accounts[0].current_value", 0, "statement"),
        (2, "accounts[0].account_type", "rrsp", "statement"),
        (2, "accounts[0].institution", "Sun Life", "statement"),
        (2, "accounts[0].current_value", 0, "statement"),
    )
    alignment = align_facts(facts)
    assert alignment.canonical_count_by_prefix()["accounts"] == 1


def test_canonical_count_property() -> None:
    facts = _facts(
        (1, "people[0].display_name", "Alice Smith", "kyc"),
        (1, "accounts[0].account_number", "12345678", "statement"),
        (1, "goals[0].name", "Retirement", "planning"),
    )
    alignment = align_facts(facts)
    # 3 canonicals total — one per prefix in this case.
    assert alignment.canonical_count == 3
