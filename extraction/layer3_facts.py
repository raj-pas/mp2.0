from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

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
    """Phase 1 interface stub for Claude-backed structured extraction."""

    raise NotImplementedError("Fact extraction lands in Phase 2.")
