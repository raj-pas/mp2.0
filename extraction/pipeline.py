from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path
from typing import Any

from extraction.classification import classify_document
from extraction.llm import (
    BedrockConfig,
    extract_text_facts_with_bedrock,
    extract_visual_facts_with_bedrock,
)
from extraction.schemas import (
    ClassificationResult,
    Confidence,
    DataOrigin,
    FactCandidate,
    ParsedDocument,
)

_CONFIDENCE_RANK: dict[Confidence, int] = {"low": 1, "medium": 2, "high": 3}
_CONFIDENCE_BY_RANK: dict[int, Confidence] = {1: "low", 2: "medium", 3: "high"}


def _cap_fact_confidence(
    facts: list[FactCandidate], classification: ClassificationResult
) -> list[FactCandidate]:
    """Cap each fact's confidence by the classification confidence + 1 tier.

    Phase 4 (PROMPT-5): a low-confidence classification cannot produce
    HIGH-confidence facts — but it CAN still produce medium-confidence
    facts. The cap is "facts cannot be more than 1 tier above the
    classification confidence":
      * HIGH classification    -> cap=high   (no cap; pass-through)
      * MEDIUM classification  -> cap=high   (no cap; pass-through)
      * LOW classification     -> cap=medium (HIGH floors to MEDIUM,
                                              MEDIUM stays MEDIUM,
                                              LOW stays LOW)

    Refined 2026-05-02 after the Seltzer KYC canary regressed 74 -> 32
    facts (with all 32 dropped to LOW because the doc was classified as
    low-confidence multi_schema_sweep). The original cap-at-rank-N
    semantics over-floored medium to low and erased meaningful signal;
    cap-at-rank-N+1 preserves the "low classification can't produce
    HIGH" guard without collapsing everything into the bottom tier.
    Idempotent: running this twice is a no-op.
    """
    cls_rank = _CONFIDENCE_RANK.get(classification.confidence, 2)
    cap_rank = min(cls_rank + 1, 3)
    capped: list[FactCandidate] = []
    for fact in facts:
        fact_rank = _CONFIDENCE_RANK.get(fact.confidence, 2)
        if fact_rank <= cap_rank:
            capped.append(fact)
            continue
        capped.append(replace(fact, confidence=_CONFIDENCE_BY_RANK[cap_rank]))
    return capped


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
            return _cap_fact_confidence(facts, classification), metadata
        facts, overflow = extract_visual_facts_with_bedrock(
            path=path,
            filename=filename,
            document_type=classification.document_type,
            classification=classification,
            extraction_run_id=extraction_run_id,
            max_pages=ocr_max_pages,
            config=bedrock_config,
        )
        return (
            _cap_fact_confidence(facts, classification),
            {**metadata, "ocr_overflow": overflow},
        )

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
