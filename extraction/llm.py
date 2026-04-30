from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from extraction.prompts.classify import PROMPT_VERSION as CLASSIFY_PROMPT_VERSION
from extraction.prompts.kyc import PROMPT_VERSION as KYC_PROMPT_VERSION
from extraction.prompts.meeting_note import PROMPT_VERSION as MEETING_PROMPT_VERSION
from extraction.prompts.statement import PROMPT_VERSION as STATEMENT_PROMPT_VERSION
from extraction.schemas import BedrockFactsPayload, ClassificationResult, FactCandidate

PROMPT_VERSION_BY_TYPE = {
    "kyc": KYC_PROMPT_VERSION,
    "statement": STATEMENT_PROMPT_VERSION,
    "meeting_note": MEETING_PROMPT_VERSION,
    "planning": "planning_generic_v1",
    "crm_export": "crm_export_generic_v1",
    "identity": "identity_generic_v1",
    "spreadsheet": "spreadsheet_generic_v1",
    "generic_financial": "generic_financial_v1",
    "unknown": CLASSIFY_PROMPT_VERSION,
}


@dataclass(frozen=True)
class BedrockConfig:
    model: str
    aws_region: str
    access_key: str
    secret_key: str


def bedrock_config_from_env(default_region: str = "ca-central-1") -> BedrockConfig:
    missing = [
        name
        for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "BEDROCK_MODEL")
        if not os.getenv(name)
    ]
    if missing:
        raise RuntimeError(
            "Real-derived extraction requires Bedrock configuration: " + ", ".join(missing)
        )
    return BedrockConfig(
        model=os.environ["BEDROCK_MODEL"],
        aws_region=os.getenv("AWS_REGION", default_region),
        access_key=os.environ["AWS_ACCESS_KEY_ID"],
        secret_key=os.environ["AWS_SECRET_ACCESS_KEY"],
    )


def json_payload_from_model_text(content: str) -> dict[str, Any]:
    normalized = content.strip()
    normalized = re.sub(r"^```(?:json)?\s*", "", normalized)
    normalized = re.sub(r"\s*```$", "", normalized)
    try:
        return json.loads(normalized)
    except json.JSONDecodeError as exc:
        repaired = _repair_json_text(normalized)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass
        start = normalized.find("{")
        end = normalized.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Bedrock extraction did not return valid JSON.") from exc
        try:
            return json.loads(_repair_json_text(normalized[start : end + 1]))
        except json.JSONDecodeError as nested_exc:
            raise ValueError("Bedrock extraction did not return valid JSON.") from nested_exc


def extract_text_facts_with_bedrock(
    *,
    filename: str,
    document_type: str,
    classification: ClassificationResult,
    text: str,
    extraction_run_id: str,
    max_chars: int,
    config: BedrockConfig,
) -> list[FactCandidate]:
    client = _bedrock_client(config)
    prompt = fact_extraction_prompt(
        filename=filename,
        document_type=document_type,
        classification=classification,
        text=text[:max_chars],
    )
    response = client.messages.create(
        model=config.model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return facts_from_bedrock_response(response, extraction_run_id)


def extract_visual_facts_with_bedrock(
    *,
    path: Path,
    filename: str,
    document_type: str,
    classification: ClassificationResult,
    extraction_run_id: str,
    max_pages: int,
    config: BedrockConfig,
) -> tuple[list[FactCandidate], dict[str, Any]]:
    client = _bedrock_client(config)
    image_blocks, overflow = visual_content_blocks(path, max_pages=max_pages)
    if not image_blocks:
        raise ValueError(
            "Document requires OCR, but no supported visual payload could be prepared."
        )
    prompt = fact_extraction_prompt(
        filename=filename,
        document_type=document_type,
        classification=classification,
        text="Use the attached page or image content as the source.",
    )
    response = client.messages.create(
        model=config.model,
        max_tokens=4096,
        messages=[{"role": "user", "content": [*image_blocks, {"type": "text", "text": prompt}]}],
    )
    return facts_from_bedrock_response(response, extraction_run_id), overflow


def fact_extraction_prompt(
    *,
    filename: str,
    document_type: str,
    classification: ClassificationResult,
    text: str,
) -> str:
    prompt_version = PROMPT_VERSION_BY_TYPE.get(document_type, "generic_financial_v1")
    schema_hints = ", ".join(classification.schema_hints or ["generic_financial_sweep"])
    low_confidence_instruction = (
        "Classification is low-confidence, so run a multi-schema sweep across household, "
        "people, accounts, holdings, goals, goal-account mapping, and risk. "
        if classification.route == "multi_schema_sweep"
        else ""
    )
    return (
        "Extract MP2.0 advisor-review facts from this client document. Return JSON only in "
        'this shape: {"facts":[{"field":"...","value":...,"confidence":"high|medium|low",'
        '"derivation_method":"extracted|inferred|defaulted","source_location":"...",'
        '"source_page":null,"evidence_quote":"short source quote","asserted_at":null}]}. '
        "Use canonical fields such as household.display_name, household.household_type, "
        "people[0].display_name, people[0].date_of_birth, people[0].age, "
        "accounts[0].account_type, accounts[0].current_value, accounts[0].holdings, "
        "accounts[0].missing_holdings_confirmed, goals[0].name, "
        "goals[0].time_horizon_years, goal_account_links[0].goal_name, "
        "goal_account_links[0].allocated_amount, and risk.household_score. "
        "Risk scores must use the MP2.0 1-5 scale when the document provides enough "
        "context; otherwise leave them missing. Do not invent missing financial numbers. "
        "Separate factual extraction from behavioral synthesis; behavioral context belongs "
        "under behavioral_notes.* and is not an engine input unless mapped to a canonical "
        "field. For account numbers, SIN, tax IDs, and similar identifiers, include only "
        "the field name and raw value in JSON; the application will hash and redact them. "
        f"{low_confidence_instruction}"
        f"Prompt version: {prompt_version}\n"
        f"Filename label: {filename}\n"
        f"Document type: {document_type}\n"
        f"Classifier route: {classification.route}; confidence: {classification.confidence}; "
        f"schema hints: {schema_hints}\n\n"
        f"Text:\n{text}"
    )


def facts_from_bedrock_response(response, extraction_run_id: str) -> list[FactCandidate]:  # noqa: ANN001
    content = "".join(block.text for block in response.content if hasattr(block, "text"))
    payload = json_payload_from_model_text(content)
    try:
        parsed = BedrockFactsPayload.model_validate(payload)
    except ValidationError as exc:
        raise ValueError("Bedrock extraction JSON did not match the expected fact schema.") from exc
    return [
        FactCandidate(
            **fact.model_dump(mode="json"),
            extraction_run_id=extraction_run_id,
        )
        for fact in parsed.facts
    ]


def visual_content_blocks(
    path: Path, *, max_pages: int
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    extension = path.suffix.lower()
    if extension == ".pdf":
        return _pdf_page_image_blocks(path, max_pages=max_pages)
    media_type = mimetypes.guess_type(path.name)[0] or ""
    if media_type in {"image/tiff", "image/tif"}:
        raise ValueError("TIFF OCR needs conversion before Bedrock vision can process it.")
    if media_type not in {"image/png", "image/jpeg", "image/gif", "image/webp"}:
        raise ValueError(
            f"Bedrock vision OCR does not support {extension or 'this file type'} yet."
        )
    return [_image_block(path.read_bytes(), media_type)], {}


def _bedrock_client(config: BedrockConfig):
    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError("anthropic[bedrock] is required for Bedrock extraction.") from exc

    return anthropic.AnthropicBedrock(
        aws_access_key=config.access_key,
        aws_secret_key=config.secret_key,
        aws_region=config.aws_region,
    )


def _pdf_page_image_blocks(
    path: Path, *, max_pages: int
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("pymupdf is required for PDF OCR preparation.") from exc

    document = fitz.open(path)
    blocks: list[dict[str, Any]] = []
    for page in list(document)[:max_pages]:
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        blocks.append(_image_block(pixmap.tobytes("png"), "image/png"))
    overflow = {}
    if document.page_count > max_pages:
        overflow = {
            "total_pages": document.page_count,
            "processed_pages": max_pages,
            "overflow_pages": document.page_count - max_pages,
            "status": "needs_review",
        }
    return blocks, overflow


def _image_block(content: bytes, media_type: str) -> dict[str, Any]:
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": base64.b64encode(content).decode(),
        },
    }


def _repair_json_text(content: str) -> str:
    repaired = re.sub(r",(\s*[}\]])", r"\1", content)
    repaired = repaired.replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'")
    return repaired
