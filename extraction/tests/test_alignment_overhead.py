"""Performance budget for `extraction.entity_alignment.align_facts`.

Per §A1.46: a single workspace alignment must complete in under 100ms
on the typical Niesner-class workload (~9 docs × O(10) entities each =
~150 facts). Keeps the worker-loop reconcile responsive.

This test fabricates a 9-doc, ~140-fact workload and asserts the
median wall-clock runtime is under the budget.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from extraction.entity_alignment import align_facts


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


def _niesner_class_workload() -> list[_FakeFact]:
    """9 documents × {2 people, 3 accounts (with holdings), 2 goals} =
    ~140 facts. Names + DOBs + account numbers vary partially across
    docs to force the matcher into score comparisons."""
    facts: list[_FakeFact] = []
    next_fact_id = 1
    for doc_id in range(1, 10):
        doc = _FakeDoc(id=doc_id, document_type="kyc", original_filename=f"doc{doc_id}.pdf")
        # 2 people per doc.
        for person_idx, (name, dob) in enumerate(
            [("Alice Smith", "1962-04-15"), ("Bob Smith", "1965-08-20")]
        ):
            facts.append(
                _FakeFact(
                    id=next_fact_id,
                    field=f"people[{person_idx}].display_name",
                    value=name,
                    document=doc,
                    document_id=doc_id,
                )
            )
            next_fact_id += 1
            facts.append(
                _FakeFact(
                    id=next_fact_id,
                    field=f"people[{person_idx}].date_of_birth",
                    value=dob,
                    document=doc,
                    document_id=doc_id,
                )
            )
            next_fact_id += 1
        # 3 accounts per doc.
        for acct_idx in range(3):
            facts.append(
                _FakeFact(
                    id=next_fact_id,
                    field=f"accounts[{acct_idx}].account_number",
                    value=f"100-200-30{doc_id}-{acct_idx}",
                    document=doc,
                    document_id=doc_id,
                )
            )
            next_fact_id += 1
            facts.append(
                _FakeFact(
                    id=next_fact_id,
                    field=f"accounts[{acct_idx}].account_type",
                    value="rrsp",
                    document=doc,
                    document_id=doc_id,
                )
            )
            next_fact_id += 1
            facts.append(
                _FakeFact(
                    id=next_fact_id,
                    field=f"accounts[{acct_idx}].current_value",
                    value=42_000 + (acct_idx * 1_000),
                    document=doc,
                    document_id=doc_id,
                )
            )
            next_fact_id += 1
        # 2 goals per doc.
        for goal_idx, name in enumerate(["Retirement", "Travel"]):
            facts.append(
                _FakeFact(
                    id=next_fact_id,
                    field=f"goals[{goal_idx}].name",
                    value=name,
                    document=doc,
                    document_id=doc_id,
                )
            )
            next_fact_id += 1
    return facts


def test_align_facts_under_100ms_for_niesner_class_workload() -> None:
    facts = _niesner_class_workload()
    # Warm-up call (JIT cache, regex compile, etc.).
    align_facts(facts)
    timings: list[float] = []
    for _ in range(5):
        t0 = time.perf_counter()
        align_facts(facts)
        timings.append(time.perf_counter() - t0)
    median = sorted(timings)[len(timings) // 2]
    assert median < 0.100, (
        f"align_facts median runtime {median * 1000:.1f}ms exceeds 100ms budget "
        f"on a {len(facts)}-fact / 9-doc workload"
    )
