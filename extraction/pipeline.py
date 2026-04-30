from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from extraction.classification import classify_document
from extraction.llm import (
    BedrockConfig,
    extract_text_facts_with_bedrock,
    extract_visual_facts_with_bedrock,
)
from extraction.schemas import ClassificationResult, DataOrigin, FactCandidate, ParsedDocument


def extract_facts_for_document(
    *,
    path: Path,
    filename: str,
    data_origin: DataOrigin,
    parsed: ParsedDocument,
    classification: ClassificationResult,
    text_max_chars: int,
    ocr_max_pages: int,
    bedrock_config: BedrockConfig | None = None,
) -> tuple[list[FactCandidate], dict[str, Any]]:
    extraction_run_id = f"{classification.document_type}:{classification.route}:{int(time.time())}"
    metadata = {
        "extraction_run_id": extraction_run_id,
        "prompt_route": classification.route,
        "schema_hints": classification.schema_hints,
    }

    if data_origin == "real_derived":
        if bedrock_config is None:
            raise RuntimeError("Real-derived extraction requires Bedrock configuration.")
        if parsed.text.strip():
            facts = extract_text_facts_with_bedrock(
                filename=filename,
                document_type=classification.document_type,
                classification=classification,
                text=parsed.text,
                extraction_run_id=extraction_run_id,
                max_chars=text_max_chars,
                config=bedrock_config,
            )
            return facts, metadata
        facts, overflow = extract_visual_facts_with_bedrock(
            path=path,
            filename=filename,
            document_type=classification.document_type,
            classification=classification,
            extraction_run_id=extraction_run_id,
            max_pages=ocr_max_pages,
            config=bedrock_config,
        )
        return facts, {**metadata, "ocr_overflow": overflow}

    return heuristic_facts(
        filename=filename,
        document_type=classification.document_type,
        text=parsed.text,
        extraction_run_id=extraction_run_id,
    ), metadata


def heuristic_facts(
    *,
    filename: str,
    document_type: str,
    text: str,
    extraction_run_id: str,
) -> list[FactCandidate]:
    facts: list[FactCandidate] = []
    stripped = " ".join(text.split())
    if stripped:
        facts.append(
            FactCandidate(
                field="document.summary",
                value=stripped[:500],
                confidence="low",
                derivation_method="extracted",
                source_location="document",
                evidence_quote=stripped[:240],
                extraction_run_id=extraction_run_id,
            )
        )
    if document_type == "statement":
        facts.append(
            FactCandidate(
                field="accounts",
                value=[
                    {
                        "id": "review_account_1",
                        "type": "Non-Registered",
                        "current_value": 0,
                        "missing_holdings_confirmed": True,
                    }
                ],
                confidence="low",
                derivation_method="inferred",
                source_location="filename",
                evidence_quote=filename,
                extraction_run_id=extraction_run_id,
            )
        )
    if document_type in {"crm_export", "identity"}:
        display_name = Path(filename).stem.replace("_", " ").replace("-", " ")
        facts.append(
            FactCandidate(
                field="household.display_name",
                value=display_name,
                confidence="low",
                derivation_method="inferred",
                source_location="filename",
                evidence_quote=filename,
                extraction_run_id=extraction_run_id,
            )
        )
    return facts


def classify_from_parsed(
    filename: str, extension: str, parsed: ParsedDocument
) -> ClassificationResult:
    return classify_document(
        filename,
        extension,
        text=parsed.text,
        parse_metadata=parsed.metadata,
    )
