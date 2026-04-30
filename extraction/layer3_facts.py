from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

from extraction.classification import classify_document
from extraction.pipeline import heuristic_facts
from extraction.schemas import FactCandidate

Confidence = Literal["high", "medium", "low"]
DerivationMethod = Literal["extracted", "inferred", "defaulted"]


@dataclass(frozen=True)
class Fact:
    field: str
    value: object
    asserted_at: date | None
    superseded_by: str | None
    confidence: Confidence
    derivation_method: DerivationMethod
    source_quote: str
    source_doc_id: str
    source_location: str
    extraction_run_id: str


def extract_facts(raw_text: str) -> list[Fact]:
    """Extract synthetic/local heuristic facts from text.

    Real-derived Bedrock extraction is called through `extraction.pipeline` with
    an explicit Bedrock config so provider routing remains fail-closed.
    """

    classification = classify_document("text-input.txt", ".txt", text=raw_text)
    candidates = heuristic_facts(
        filename="text-input.txt",
        document_type=classification.document_type,
        text=raw_text,
        extraction_run_id="heuristic:manual",
    )
    return [_candidate_to_fact(candidate) for candidate in candidates]


def _candidate_to_fact(candidate: FactCandidate) -> Fact:
    asserted_at = date.fromisoformat(candidate.asserted_at) if candidate.asserted_at else None
    return Fact(
        field=candidate.field,
        value=candidate.value,
        asserted_at=asserted_at,
        superseded_by=None,
        confidence=candidate.confidence,
        derivation_method=candidate.derivation_method,
        source_quote=candidate.evidence_quote,
        source_doc_id="",
        source_location=candidate.source_location,
        extraction_run_id=candidate.extraction_run_id,
    )
