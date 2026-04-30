from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from extraction.parsers import parse_document_path

ExtractionMethod = Literal[
    "pdf_native",
    "pdf_ocr",
    "ocr_required",
    "docx",
    "csv",
    "xlsx",
    "xml",
    "plain",
]


@dataclass(frozen=True)
class ExtractedText:
    raw_text: str
    structured_fragments: list[dict] = field(default_factory=list)
    page_or_section_markers: list[dict] = field(default_factory=list)
    source_file_id: str = ""
    extraction_method: ExtractionMethod = "plain"


def extract_text(source_file_id: str) -> ExtractedText:
    """Extract deterministic text/table content from a secured local artifact path."""

    parsed = parse_document_path(Path(source_file_id))
    return ExtractedText(
        raw_text=parsed.text,
        structured_fragments=parsed.structured_fragments,
        page_or_section_markers=[
            fragment for fragment in parsed.structured_fragments if fragment.get("page")
        ],
        source_file_id=source_file_id,
        extraction_method=parsed.method,  # type: ignore[assignment]
    )
