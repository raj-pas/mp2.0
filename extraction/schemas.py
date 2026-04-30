from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

Confidence = Literal["high", "medium", "low"]
DerivationMethod = Literal["extracted", "inferred", "defaulted"]
DataOrigin = Literal["synthetic", "real_derived"]

SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".csv",
    ".txt",
    ".md",
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
}

SYSTEM_FILENAMES = {".ds_store", "thumbs.db"}

DOCUMENT_TYPES = {
    "kyc",
    "statement",
    "planning",
    "crm_export",
    "intake",
    "meeting_note",
    "identity",
    "spreadsheet",
    "image",
    "generic_financial",
    "unknown",
}


@dataclass(frozen=True)
class ParsedDocument:
    text: str
    method: str
    metadata: dict[str, Any] = field(default_factory=dict)
    structured_fragments: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class ClassificationResult:
    document_type: str
    confidence: Confidence
    route: str
    signals: list[str] = field(default_factory=list)
    schema_hints: list[str] = field(default_factory=list)

    def as_metadata(self) -> dict[str, Any]:
        return {
            "document_type": self.document_type,
            "confidence": self.confidence,
            "route": self.route,
            "signals": self.signals,
            "schema_hints": self.schema_hints,
        }


class BedrockFact(BaseModel):
    field: str = Field(min_length=1)
    value: Any
    confidence: Confidence = "medium"
    derivation_method: DerivationMethod = "extracted"
    source_location: str = ""
    source_page: int | None = None
    evidence_quote: str = ""
    asserted_at: str | None = None


class BedrockFactsPayload(BaseModel):
    facts: list[BedrockFact] = Field(default_factory=list)


@dataclass(frozen=True)
class FactCandidate:
    field: str
    value: Any
    confidence: Confidence
    derivation_method: DerivationMethod
    source_location: str = ""
    source_page: int | None = None
    evidence_quote: str = ""
    asserted_at: str | None = None
    extraction_run_id: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "value": self.value,
            "confidence": self.confidence,
            "derivation_method": self.derivation_method,
            "source_location": self.source_location,
            "source_page": self.source_page,
            "evidence_quote": self.evidence_quote,
            "asserted_at": self.asserted_at,
            "extraction_run_id": self.extraction_run_id,
        }
