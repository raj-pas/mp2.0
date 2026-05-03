"""Hypothesis property tests — reconciliation source-priority invariants.

Drives `current_facts_by_field` + `conflicts_for_facts` with duck-typed
pyobjects (no DB) so Hypothesis can explore arbitrary fact permutations
fast.

Properties asserted:
  1. current_facts_by_field returns ONE entry per distinct field
     regardless of cross-class disagreements (canon §11.4 — losers
     drop silently).
  2. Same-class disagreements (two same-doc-type facts differing on
     value) surface as exactly one conflict per field with
     same_authority=True and len(fact_ids)>=2.
  3. Source priority is a strict ordering: the higher-authority fact
     (lower numeric value of source_authority) wins per field.
  4. The WINNING priority tuple is invariant under shuffle.
  5. field_section is a pure function of the field path — every fact
     for the same path classifies into the same section.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import hypothesis.strategies as st
from hypothesis import HealthCheck, given, settings

from extraction.reconciliation import (
    conflicts_for_facts,
    current_facts_by_field,
    field_section,
    source_authority,
)


@dataclass
class _StubDocument:
    document_type: str


@dataclass
class _StubFact:
    """Duck-typed stand-in for ExtractedFact. The reconciliation helpers
    only read .field, .value, .confidence, .document.document_type,
    .asserted_at, and .id.
    """

    id: int
    field: str
    value: Any
    confidence: str
    derivation_method: str
    document: _StubDocument
    asserted_at: date | None = None


# Restricted to STRING-typed fields so normalize_fact_value is a strip-only
# no-op — value disagreements are unambiguous. Numerically-normalized fields
# (current_value, target_amount) are exercised by the explicit anchor test.
ALL_FIELDS = [
    "people[0].date_of_birth",
    "people[0].marital_status",
    "people[1].name",
    "accounts[0].account_type",
    "accounts[1].account_type",
    "goals[0].name",
]
DOC_TYPES = ["kyc", "statement", "planning", "meeting_note", "intake", "crm_export"]
CONFIDENCES = ["high", "medium", "low"]

field_strategy = st.sampled_from(ALL_FIELDS)
doc_type_strategy = st.sampled_from(DOC_TYPES)
confidence_strategy = st.sampled_from(CONFIDENCES)
value_strategy = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=12)

HYPO_SETTINGS = dict(max_examples=50, deadline=2000, suppress_health_check=[HealthCheck.too_slow])


@st.composite
def stub_facts(draw, *, max_count: int = 12):
    n = draw(st.integers(min_value=1, max_value=max_count))
    return [
        _StubFact(
            id=i + 1,
            field=draw(field_strategy),
            value=draw(value_strategy),
            confidence=draw(confidence_strategy),
            derivation_method="extracted",
            document=_StubDocument(document_type=draw(doc_type_strategy)),
            asserted_at=None,
        )
        for i in range(n)
    ]


@given(facts=stub_facts())
@settings(**HYPO_SETTINGS)
def test_property_one_entry_per_field_in_current_facts(facts) -> None:
    """current_facts_by_field returns one entry per distinct field
    (cross-class losers drop silently).
    """
    current = current_facts_by_field(facts)
    distinct_fields = {fact.field for fact in facts}
    assert set(current.keys()) == distinct_fields
    for field, fact in current.items():
        assert fact.field == field


@given(facts=stub_facts())
@settings(**HYPO_SETTINGS)
def test_property_same_class_disagreement_surfaces_as_one_conflict(facts) -> None:
    """For each field where two SAME-doc-type facts disagree, exactly
    one conflict surfaces with len(fact_ids)>=2; same_authority=True
    when the disagreement is purely same-class.
    """
    same_class_disagreed_fields: set[str] = set()
    by_field: dict[str, list[_StubFact]] = {}
    for fact in facts:
        by_field.setdefault(fact.field, []).append(fact)
    for field, field_facts in by_field.items():
        by_doc_type: dict[str, set[Any]] = {}
        for f in field_facts:
            by_doc_type.setdefault(f.document.document_type, set()).add(str(f.value))
        for values in by_doc_type.values():
            if len(values) >= 2:
                same_class_disagreed_fields.add(field)
                break

    conflicts = conflicts_for_facts(facts)
    conflicts_by_field = {c["field"]: c for c in conflicts}

    # No duplicate conflicts for the same field.
    assert len(conflicts_by_field) == len(conflicts)

    for field in same_class_disagreed_fields:
        assert field in conflicts_by_field
        conflict = conflicts_by_field[field]
        assert len(conflict["fact_ids"]) >= 2
        # When the disagreement is purely same-class, all facts share
        # one authority value ⇒ same_authority=True.
        authority_values = {
            source_authority(f.document.document_type, field) for f in by_field[field]
        }
        if len(authority_values) == 1:
            assert conflict["same_authority"] is True


@given(facts=stub_facts())
@settings(**HYPO_SETTINGS)
def test_property_higher_authority_wins_per_field(facts) -> None:
    """The chosen fact has the LOWEST authority number (= highest
    priority) of all candidates for that field.
    """
    current = current_facts_by_field(facts)
    by_field: dict[str, list[_StubFact]] = {}
    for fact in facts:
        by_field.setdefault(fact.field, []).append(fact)

    for field, field_facts in by_field.items():
        winner_authority = source_authority(current[field].document.document_type, field)
        for candidate in field_facts:
            cand_authority = source_authority(candidate.document.document_type, field)
            assert cand_authority >= winner_authority, (
                f"field {field}: winner authority {winner_authority} > "
                f"candidate authority {cand_authority}"
            )


@given(facts=stub_facts())
@settings(**HYPO_SETTINGS)
def test_property_current_facts_winning_priority_invariant_under_shuffle(facts) -> None:
    """The WINNING priority tuple (authority, confidence) is invariant
    under shuffle.

    NOTE: the chosen fact ID may differ when multiple facts tie on the
    FULL priority tuple — sorted() is stable, so input order is the
    final tie-break. The helper does not enforce a deterministic
    final-tie-break beyond input order. In production this is masked
    by ExtractedFact.Meta.ordering (-created_at), but it is a latent
    fragility (FINDING — see report).
    """
    forward = current_facts_by_field(facts)
    reverse = current_facts_by_field(list(reversed(facts)))

    assert set(forward.keys()) == set(reverse.keys())
    for field in forward:
        f1, f2 = forward[field], reverse[field]
        a1 = source_authority(f1.document.document_type, field)
        a2 = source_authority(f2.document.document_type, field)
        assert (a1, f1.confidence) == (a2, f2.confidence)


@given(facts=stub_facts())
@settings(**HYPO_SETTINGS)
def test_property_field_section_classification_consistent(facts) -> None:
    """field_section is a pure function — every fact for the same
    field path classifies into the same section.
    """
    by_field: dict[str, set[str]] = {}
    for fact in facts:
        by_field.setdefault(fact.field, set()).add(field_section(fact.field))
    for field, sections in by_field.items():
        assert len(sections) == 1, f"{field} classifies into {sections}"


def test_source_authority_strict_order_for_known_fields() -> None:
    """Anchor: locks the matrix orientation so property tests have a
    meaningful ordering signal.
    """
    # People: kyc beats statement.
    assert source_authority("kyc", "people[0].date_of_birth") < source_authority(
        "statement", "people[0].date_of_birth"
    )
    # Accounts: statement beats kyc.
    assert source_authority("statement", "accounts[0].current_value") < source_authority(
        "kyc", "accounts[0].current_value"
    )
    # Goals: planning beats statement.
    assert source_authority("planning", "goals[0].name") < source_authority(
        "statement", "goals[0].name"
    )
