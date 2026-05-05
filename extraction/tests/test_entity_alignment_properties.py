"""Hypothesis property-based tests for `extraction.entity_alignment`.

Three load-bearing properties (sister §3.18 pattern: max_examples=10,
deadline=None, suppress_health_check=[function_scoped_fixture, too_slow]):

  1. Determinism — same fact-list input -> same canonical-index output
     regardless of input ORDER. The matcher is deterministic.

  2. No-fact-loss — every input fact lands in some canonical entity
     (alignment never DROPS facts; only re-indexes them).

  3. Identity-stable conflict-monotonicity — post-alignment count of
     STABLE-identity conflicts (date_of_birth, account_number) is <=
     pre-alignment count for any input shape. Display-name conflicts
     CAN surface when two distinct people share a strong identity
     signal (surname + DOB) and get merged — that's intended UX
     (advisor adjudicates).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from extraction.entity_alignment import align_facts
from extraction.reconciliation import conflicts_for_facts


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


# A small enumerated strategy: each "person spec" is a (doc_id, name, dob)
# triple. We then synthesize matching ExtractedFact-shaped inputs.
_NAMES = [
    "alice smith",
    "bob smith",
    "carol jones",
    "david jones",
    "evan miller",
]
_DOBS = [
    "1962-04-15",
    "1965-08-20",
    "1970-01-01",
    "1980-12-31",
    None,  # missing-DOB case for the single-field fail-safe
]
_DOC_TYPES = ["kyc", "statement", "meeting_note", "planning"]


@st.composite
def _person_specs(draw: Any) -> list[tuple[int, str, str | None, str]]:
    n = draw(st.integers(min_value=0, max_value=8))
    specs = []
    for _ in range(n):
        doc_id = draw(st.integers(min_value=1, max_value=4))
        name = draw(st.sampled_from(_NAMES))
        dob = draw(st.sampled_from(_DOBS))
        doc_type = draw(st.sampled_from(_DOC_TYPES))
        specs.append((doc_id, name, dob, doc_type))
    return specs


def _facts_from_specs(
    specs: list[tuple[int, str, str | None, str]],
) -> list[_FakeFact]:
    """Materialize one display_name fact + (when DOB present) one DOB
    fact per person spec. Each person uses local_index 0 in their doc
    by default; if a doc has multiple persons we increment the index."""
    docs: dict[int, _FakeDoc] = {}
    per_doc_indices: dict[int, int] = {}
    facts: list[_FakeFact] = []
    next_id = 1
    for doc_id, name, dob, doc_type in specs:
        doc = docs.setdefault(
            doc_id,
            _FakeDoc(id=doc_id, document_type=doc_type, original_filename=f"doc{doc_id}.pdf"),
        )
        idx = per_doc_indices.get(doc_id, 0)
        per_doc_indices[doc_id] = idx + 1
        facts.append(
            _FakeFact(
                field=f"people[{idx}].display_name",
                value=name,
                document=doc,
                document_id=doc_id,
                id=next_id,
            )
        )
        next_id += 1
        if dob is not None:
            facts.append(
                _FakeFact(
                    field=f"people[{idx}].date_of_birth",
                    value=dob,
                    document=doc,
                    document_id=doc_id,
                    id=next_id,
                )
            )
            next_id += 1
    return facts


# ---------------------------------------------------------------------------
# Property 1: determinism (order-invariance of the alignment)
# ---------------------------------------------------------------------------


@given(specs=_person_specs())
@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)
def test_alignment_is_deterministic_across_input_orders(specs) -> None:
    facts = _facts_from_specs(specs)
    if not facts:
        return  # vacuously satisfied
    rng = random.Random(0xC1A1)
    shuffled = list(facts)
    rng.shuffle(shuffled)

    alignment_a = align_facts(facts)
    alignment_b = align_facts(shuffled)

    # Compare canonical assignments PER FACT (not per mapping triple,
    # because the same triple key under shuffle still maps the same way).
    canonicals_a = {f.id: alignment_a.canonical_index_for(f) for f in facts}
    canonicals_b = {f.id: alignment_b.canonical_index_for(f) for f in facts}
    assert canonicals_a == canonicals_b
    assert alignment_a.canonical_count == alignment_b.canonical_count


# ---------------------------------------------------------------------------
# Property 2: no fact loss
# ---------------------------------------------------------------------------


@given(specs=_person_specs())
@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)
def test_alignment_loses_no_facts(specs) -> None:
    facts = _facts_from_specs(specs)
    if not facts:
        return  # vacuously satisfied

    alignment = align_facts(facts)
    # Every input fact whose field is a known prefix MUST receive a
    # canonical_index; facts whose field doesn't match a prefix pass
    # through unchanged.
    for fact in facts:
        canonical = alignment.canonical_index_for(fact)
        # Every entity-prefixed fact is mapped.
        assert canonical is not None, f"Fact {fact.field!r} dropped from alignment"

    # Re-indexer over the same input returns ALL facts (length-preserving).
    rewritten = alignment.align_facts(list(facts))
    assert len(rewritten) == len(facts)
    assert {f.id for f in rewritten} == {f.id for f in facts}


# ---------------------------------------------------------------------------
# Property 3: conflict-monotonicity
# ---------------------------------------------------------------------------


@given(specs=_person_specs())
@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)
def test_alignment_never_increases_dob_or_account_conflicts(specs) -> None:
    """Alignment never SURFACES new DOB or account-id conflicts.

    Alignment CAN surface a new ``display_name`` conflict when two
    distinct people share a strong identity signal (e.g. same surname
    + same DOB) and get merged into one canonical — that's intended UX
    (advisor adjudicates the resulting display_name disagreement). The
    Niesner father+son guard only protects against single-field merges.

    But alignment MUST NEVER increase conflict count on STABLE identity
    fields like ``date_of_birth`` (the matcher only merges when DOB is
    shared, so the merged group's DOB values are equal by construction)
    or account number / hash. Tightens the original
    "never_increases_conflict_count" property to the fields where the
    invariant actually holds; allows display_name conflicts to surface
    by design (Round-13 #2 + plan §A1.44 G1 acceptance).
    """
    facts = _facts_from_specs(specs)
    if not facts:
        return  # vacuously satisfied

    pre_conflicts = conflicts_for_facts(facts)
    alignment = align_facts(facts)
    post_conflicts = conflicts_for_facts(facts, alignment=alignment)

    # Filter to identity-stable fields; display_name surfacing is allowed.
    def _stable(conflicts: list[dict]) -> int:
        return sum(
            1 for c in conflicts if "date_of_birth" in c["field"] or "account_number" in c["field"]
        )

    assert _stable(post_conflicts) <= _stable(pre_conflicts), (
        f"Alignment increased identity-stable conflicts: "
        f"{_stable(pre_conflicts)} -> {_stable(post_conflicts)} for specs {specs!r}"
    )
