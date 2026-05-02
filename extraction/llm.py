from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from extraction.prompts.classify import PROMPT_VERSION as CLASSIFY_PROMPT_VERSION
from extraction.prompts.kyc import PROMPT_VERSION as KYC_PROMPT_VERSION
from extraction.prompts.meeting_note import PROMPT_VERSION as MEETING_PROMPT_VERSION
from extraction.prompts.statement import PROMPT_VERSION as STATEMENT_PROMPT_VERSION
from extraction.schemas import BedrockFactsPayload, ClassificationResult, FactCandidate

MAX_IMAGE_BLOCK_BYTES = 4_500_000
MAX_VISUAL_REQUEST_BYTES = 18_000_000

# Output token budget for Bedrock fact-extraction calls.
#
# Default 16384: empirically chosen during 2026-05-01 extraction-quality
# hardening. The previous default (4096) truncated mid-JSON for spreadsheet
# planning docs and large native PDFs — Bedrock generated valid `{"facts":
# [ ... ]}` shape but ran out of output budget at ~11.7K chars, with the
# repair-retry hitting the same wall. 16384 gives ~3x headroom while
# staying well under Sonnet 4.6's per-call ceiling on Bedrock.
#
# Override via MP20_BEDROCK_MAX_TOKENS for ops-time tuning without code
# change (raise for very large planning docs, lower if Bedrock spend
# becomes a concern). Keep this as a single source of truth so all three
# call sites stay aligned.
DEFAULT_BEDROCK_MAX_TOKENS = 16384


def _bedrock_max_tokens() -> int:
    raw = os.getenv("MP20_BEDROCK_MAX_TOKENS")
    if not raw:
        return DEFAULT_BEDROCK_MAX_TOKENS
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_BEDROCK_MAX_TOKENS
    return value if value > 0 else DEFAULT_BEDROCK_MAX_TOKENS


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


# Typed extraction errors with structured `failure_code` strings that the
# worker maps onto `processing_metadata.failure_code` and the UI renders
# into actionable advisor copy. All inherit from ValueError so existing
# `except ValueError:` callers (the repair-retry path, _fail_or_retry,
# etc.) keep working without churn.
#
# Each subclass owns one diagnosable failure mode. The list below is the
# single source of truth for the failure_code vocabulary used in
# i18n keys (`review.failure_code.<code>`) and frontend rendering.


class BedrockExtractionError(ValueError):
    """Base for typed Bedrock extraction errors."""

    failure_code: str = "bedrock_unknown"


class BedrockNonJsonError(BedrockExtractionError):
    """Bedrock returned text that JSON repair couldn't recover."""

    failure_code = "bedrock_non_json"


class BedrockTokenLimitError(BedrockExtractionError):
    """Bedrock response truncated mid-output (exceeded output token budget).

    Detected when the response payload looks like it ran out of tokens
    mid-structure: unbalanced braces/brackets, ends mid-string, or ends
    with a trailing comma. This is the failure mode that drove the
    2026-05-01 max_tokens 4096→16384 fix; if it shows up again the
    surface area is now distinct from generic non-JSON errors.
    """

    failure_code = "bedrock_token_limit"


class BedrockSchemaMismatchError(BedrockExtractionError):
    """JSON parsed cleanly but didn't match the expected fact-payload schema."""

    failure_code = "bedrock_schema_mismatch"


def _looks_truncated(content: str) -> bool:
    r"""Heuristic: does this Bedrock response read as token-limit-truncated?

    Sonnet output that hits max_tokens stops mid-token, leaving the JSON
    structure unclosed. We treat a response as truncated only when the
    model *clearly started constructing JSON* and then got cut off:

      1. At least one opening brace or bracket exists (we have JSON-ish
         structure to evaluate; pure prose like "I'm sorry, I can't..."
         does not qualify — that's `bedrock_non_json` territory).
      2. AND any of:
         - bracket/brace counts unbalanced (more opens than closes), OR
         - text ends mid-value (last non-whitespace char is ``,`` or ``:``), OR
         - text doesn't end on a closing token (``}``, ``]``, or a code
           fence) — model was cut mid-word/mid-string.
    """
    stripped = content.rstrip()
    if not stripped:
        return False
    open_braces = stripped.count("{")
    close_braces = stripped.count("}")
    open_brackets = stripped.count("[")
    close_brackets = stripped.count("]")
    # Require some JSON-ish structure to have been started — otherwise
    # this is non-JSON prose, not a truncation event.
    if open_braces == 0 and open_brackets == 0:
        return False
    if open_braces > close_braces or open_brackets > close_brackets:
        return True
    if stripped[-1] in {",", ":"}:
        return True
    if not (stripped.endswith("}") or stripped.endswith("]") or stripped.endswith("```")):
        return True
    return False


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


def json_payload_from_model_text(content: str) -> Any:
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
        object_start = normalized.find("{")
        object_end = normalized.rfind("}")
        array_start = normalized.find("[")
        array_end = normalized.rfind("]")
        use_array = (
            array_start != -1
            and array_end != -1
            and (object_start == -1 or array_start < object_start)
        )
        if use_array:
            start = array_start
            end = array_end
        else:
            start = object_start
            end = object_end
        if start == -1 or end == -1 or end <= start:
            if _looks_truncated(normalized):
                raise BedrockTokenLimitError(
                    "Bedrock extraction response was truncated before JSON closed."
                ) from exc
            raise BedrockNonJsonError("Bedrock extraction did not return valid JSON.") from exc
        try:
            return json.loads(_repair_json_text(normalized[start : end + 1]))
        except json.JSONDecodeError as nested_exc:
            if _looks_truncated(normalized):
                raise BedrockTokenLimitError(
                    "Bedrock extraction response was truncated before JSON closed."
                ) from nested_exc
            raise BedrockNonJsonError(
                "Bedrock extraction did not return valid JSON."
            ) from nested_exc


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
        max_tokens=_bedrock_max_tokens(),
        messages=[{"role": "user", "content": prompt}],
    )
    return facts_from_bedrock_response(
        response,
        extraction_run_id,
        client=client,
        model=config.model,
    )


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
        max_tokens=_bedrock_max_tokens(),
        messages=[{"role": "user", "content": [*image_blocks, {"type": "text", "text": prompt}]}],
    )
    return (
        facts_from_bedrock_response(
            response,
            extraction_run_id,
            client=client,
            model=config.model,
        ),
        overflow,
    )


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


def _maybe_write_bedrock_debug(stage: str, extraction_run_id: str, content: str) -> None:
    """Optionally persist a raw Bedrock response for diagnostic use.

    Gated on MP20_DEBUG_BEDROCK_RESPONSES=1. Writes only inside
    MP20_SECURE_DATA_ROOT/_debug/. Never to stdout, repo, or external
    sinks. Real-PII discipline (canon §11.8.3): contents may include
    extracted client text; treat the path as PII storage.

    Off by default. Used to investigate JSON-parse failures during
    extraction-quality hardening — characterize whether Bedrock is
    returning markdown tables, prose preambles, truncated output, or
    schema-drifted JSON.
    """
    if os.getenv("MP20_DEBUG_BEDROCK_RESPONSES") != "1":
        return
    secure_root = os.environ.get("MP20_SECURE_DATA_ROOT")
    if not secure_root:
        return
    debug_dir = Path(secure_root) / "_debug"
    debug_dir.mkdir(parents=True, exist_ok=True)
    safe_id = re.sub(r"[^a-zA-Z0-9_-]+", "_", extraction_run_id)[:80] or "unknown"
    timestamp = int(time.time() * 1000)
    target = debug_dir / f"{safe_id}-{stage}-{timestamp}.txt"
    target.write_text(content, encoding="utf-8")


def facts_from_bedrock_response(  # noqa: ANN001
    response,
    extraction_run_id: str,
    *,
    client=None,
    model: str | None = None,
) -> list[FactCandidate]:
    content = "".join(block.text for block in response.content if hasattr(block, "text"))
    _maybe_write_bedrock_debug("first", extraction_run_id, content)
    try:
        return facts_from_model_text(content, extraction_run_id)
    except ValueError:
        if client is None or model is None:
            raise
    repair_response = client.messages.create(
        model=model,
        max_tokens=_bedrock_max_tokens(),
        messages=[
            {
                "role": "user",
                "content": (
                    "Convert the following extraction response into JSON only with shape "
                    '{"facts":[{"field":"...","value":...,"confidence":"high|medium|low",'
                    '"derivation_method":"extracted|inferred|defaulted","source_location":"...",'
                    '"source_page":null,"evidence_quote":"short quote","asserted_at":null}]}. '
                    "Drop commentary and omit facts with unknown or null values.\n\n"
                    f"Response:\n{content[:12000]}"
                ),
            }
        ],
    )
    repaired_content = "".join(
        block.text for block in repair_response.content if hasattr(block, "text")
    )
    _maybe_write_bedrock_debug("repair", extraction_run_id, repaired_content)
    return facts_from_model_text(repaired_content, extraction_run_id)


def facts_from_model_text(content: str, extraction_run_id: str) -> list[FactCandidate]:
    payload = _normalize_bedrock_payload(json_payload_from_model_text(content))
    try:
        parsed = BedrockFactsPayload.model_validate(payload)
    except ValidationError as exc:
        raise BedrockSchemaMismatchError(
            "Bedrock extraction JSON did not match the expected fact schema."
        ) from exc
    return [
        FactCandidate(
            **fact.model_dump(mode="json"),
            extraction_run_id=extraction_run_id,
        )
        for fact in parsed.facts
        if not _is_missing_fact_value(fact.value)
    ]


def _normalize_bedrock_payload(payload: Any) -> dict[str, Any]:
    if isinstance(payload, list):
        return {"facts": [_normalize_fact_item(item) for item in payload]}
    if not isinstance(payload, dict):
        raise BedrockSchemaMismatchError("Bedrock extraction did not return a JSON object.")
    facts = payload.get("facts")
    if facts is None:
        for key in ("extracted_facts", "fields", "results", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                facts = value
                break
            if isinstance(value, dict) and isinstance(value.get("facts"), list):
                facts = value["facts"]
                break
    if facts is None:
        facts = []
    return {"facts": [_normalize_fact_item(item) for item in facts if isinstance(item, dict)]}


def _normalize_fact_item(item: dict[str, Any]) -> dict[str, Any]:
    field = item.get("field") or item.get("field_path") or item.get("path") or item.get("key")
    value = item.get("value")
    if "value" not in item:
        value = item.get("raw_value", item.get("normalized_value"))
    confidence = item.get("confidence", item.get("confidence_level", "medium"))
    derivation_method = item.get("derivation_method", item.get("method", "extracted"))
    source_location = (
        item.get("source_location") or item.get("location") or item.get("source") or ""
    )
    evidence_quote = item.get("evidence_quote") or item.get("quote") or item.get("evidence") or ""
    return {
        "field": field or "",
        "value": value,
        "confidence": confidence,
        "derivation_method": derivation_method,
        "source_location": source_location,
        "source_page": item.get("source_page", item.get("page")),
        "evidence_quote": evidence_quote,
        "asserted_at": item.get("asserted_at"),
    }


def _is_missing_fact_value(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


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
    skipped_pages = 0
    total_bytes = 0
    for page in list(document)[:max_pages]:
        block = _safe_pdf_page_image_block(page)
        if block is None:
            skipped_pages += 1
            continue
        block_size = len(block["source"]["data"])
        if total_bytes + block_size > MAX_VISUAL_REQUEST_BYTES:
            skipped_pages += 1
            continue
        blocks.append(block)
        total_bytes += block_size
    overflow = {}
    if document.page_count > max_pages or skipped_pages:
        overflow = {
            "total_pages": document.page_count,
            "processed_pages": len(blocks),
            "overflow_pages": max(document.page_count - max_pages, 0) + skipped_pages,
            "status": "needs_review",
        }
    return blocks, overflow


def _safe_pdf_page_image_block(page) -> dict[str, Any] | None:  # noqa: ANN001
    import fitz

    for scale in (1.25, 1.0, 0.75, 0.5):
        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        for image_format, media_type in (("jpg", "image/jpeg"), ("png", "image/png")):
            try:
                content = pixmap.tobytes(image_format)
            except (TypeError, ValueError):
                continue
            if len(content) <= MAX_IMAGE_BLOCK_BYTES:
                return _image_block(content, media_type)
    return None


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
