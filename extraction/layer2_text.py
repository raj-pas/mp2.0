from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ExtractionMethod = Literal["pdf_native", "pdf_ocr", "docx", "csv", "xml", "plain"]


@dataclass(frozen=True)
class ExtractedText:
    raw_text: str
    structured_fragments: list[dict] = field(default_factory=list)
    page_or_section_markers: list[dict] = field(default_factory=list)
    source_file_id: str = ""
    extraction_method: ExtractionMethod = "plain"


def extract_text(source_file_id: str) -> ExtractedText:
    """Phase 1 interface stub for deterministic text extraction."""

    raise NotImplementedError("Text extraction lands in Phase 2.")
