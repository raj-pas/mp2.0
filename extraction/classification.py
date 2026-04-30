from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any

from extraction.schemas import ClassificationResult, Confidence

FILENAME_HINTS: dict[str, str] = {
    "kyc": "kyc",
    "know your client": "kyc",
    "risk profile": "kyc",
    "profile": "kyc",
    "statement": "statement",
    "holdings": "statement",
    "portfolio": "statement",
    "plan": "planning",
    "planning": "planning",
    "projection": "planning",
    "cash flow": "planning",
    "net worth": "planning",
    "croesus": "crm_export",
    "crm": "crm_export",
    "intake": "intake",
    "meeting": "meeting_note",
    "note": "meeting_note",
    "call": "meeting_note",
    "dob": "identity",
    "address": "identity",
}

CONTENT_HINTS: dict[str, list[str]] = {
    "kyc": [
        r"\bknow your client\b",
        r"\brisk tolerance\b",
        r"\binvestment knowledge\b",
        r"\binvestment objective\b",
        r"\btime horizon\b",
    ],
    "statement": [
        r"\baccount statement\b",
        r"\bholdings?\b",
        r"\bmarket value\b",
        r"\bbook value\b",
        r"\brrsp\b|\btfsa\b|\bfhsa\b|\blira\b|\bresp\b|\brrif\b",
        r"\bsecurity\b.*\bquantity\b",
    ],
    "planning": [
        r"\bretirement\b",
        r"\bprojection\b",
        r"\bnet worth\b",
        r"\bcash flow\b",
        r"\bgoal\b",
        r"\bhorizon\b",
    ],
    "crm_export": [
        r"\bclient id\b",
        r"\bcrm\b",
        r"\bcroesus\b",
        r"\bportal username\b",
        r"\bia code\b",
    ],
    "meeting_note": [
        r"\bmeeting notes?\b",
        r"\bdiscussed\b",
        r"\bfollow[- ]?up\b",
        r"\baction items?\b",
        r"\bcall with\b",
    ],
    "identity": [
        r"\bdate of birth\b",
        r"\bdob\b",
        r"\baddress\b",
        r"\bpostal code\b",
        r"\bdriver'?s licence\b",
    ],
}

SCHEMA_HINTS: dict[str, list[str]] = {
    "kyc": ["identity", "risk", "account_kyc"],
    "statement": ["accounts", "holdings"],
    "planning": ["goals", "cash_flow", "household"],
    "crm_export": ["identity", "household", "accounts"],
    "meeting_note": ["meeting_facts", "behavioral_context", "goals"],
    "identity": ["identity"],
    "spreadsheet": ["table_sweep", "accounts", "planning"],
    "generic_financial": ["generic_financial_sweep"],
    "unknown": ["generic_financial_sweep"],
}


def classify_document(
    filename: str,
    extension: str,
    *,
    text: str = "",
    parse_metadata: dict[str, Any] | None = None,
) -> ClassificationResult:
    """Classify with filename, extension, parser metadata, and content signals."""

    normalized_extension = extension.lower()
    lowered_name = Path(filename).name.lower().replace("_", " ").replace("-", " ")
    scores: Counter[str] = Counter()
    signals: list[str] = []

    for hint, document_type in FILENAME_HINTS.items():
        if hint in lowered_name:
            scores[document_type] += 3
            signals.append(f"filename:{hint}")

    sample = " ".join(text.lower().split())[:12000]
    for document_type, patterns in CONTENT_HINTS.items():
        for pattern in patterns:
            if re.search(pattern, sample):
                scores[document_type] += 2
                signals.append(f"content:{document_type}:{pattern}")

    metadata = parse_metadata or {}
    if normalized_extension in {".xlsx", ".csv"}:
        scores["spreadsheet"] += 2
        signals.append("extension:spreadsheet")
        sheet_names = " ".join(str(name).lower() for name in metadata.get("sheet_names", []))
        if any(token in sheet_names for token in ("planning", "projection", "cash", "net worth")):
            scores["planning"] += 2
            signals.append("sheet:planning")
        if any(token in sheet_names for token in ("holding", "account", "portfolio")):
            scores["statement"] += 2
            signals.append("sheet:account")

    if normalized_extension in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
        scores["image"] += 1
        signals.append("extension:image")

    if not scores:
        fallback = (
            "generic_financial"
            if normalized_extension in {".pdf", ".docx", ".xlsx", ".csv", ".txt", ".md"}
            else "unknown"
        )
        return ClassificationResult(
            document_type=fallback,
            confidence="low",
            route="fallback",
            signals=signals or ["no_strong_signal"],
            schema_hints=SCHEMA_HINTS.get(fallback, ["generic_financial_sweep"]),
        )

    best_type, best_score = scores.most_common(1)[0]
    top_scores = [score for _, score in scores.most_common()]
    tied_or_close = len(top_scores) > 1 and top_scores[1] >= best_score - 1
    confidence: Confidence = "high" if best_score >= 5 and not tied_or_close else "medium"
    if best_score <= 2 or tied_or_close:
        confidence = "low"

    route = "adaptive"
    schema_hints = list(SCHEMA_HINTS.get(best_type, []))
    if confidence == "low":
        route = "multi_schema_sweep"
        schema_hints = sorted({*schema_hints, "generic_financial_sweep"})

    return ClassificationResult(
        document_type=best_type,
        confidence=confidence,
        route=route,
        signals=signals,
        schema_hints=schema_hints,
    )
