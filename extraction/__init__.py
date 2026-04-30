"""Canonical extraction pipeline for MP2.0 secure review."""

from extraction.classification import classify_document
from extraction.parsers import parse_document_path
from extraction.pipeline import classify_from_parsed, extract_facts_for_document
from extraction.schemas import ClassificationResult, FactCandidate, ParsedDocument

__all__ = [
    "ClassificationResult",
    "FactCandidate",
    "ParsedDocument",
    "classify_document",
    "classify_from_parsed",
    "extract_facts_for_document",
    "parse_document_path",
]
