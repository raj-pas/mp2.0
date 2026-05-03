"""Bedrock-based fact extraction (Phase 4 tool-use migration).

Uses Anthropic's tool-use API on Bedrock to constrain the response
shape via JSON Schema. Replaces the prior free-form JSON path that
required ``_repair_json_text`` + ``_normalize_bedrock_payload`` +
``json_payload_from_model_text`` (REPAIR-1 / REPAIR-2 closure).

Tool-use call shape:
  client.messages.create(
      model=...,
      tools=[FACT_EXTRACTION_TOOL],
      tool_choice={"type": "tool", "name": "fact_extraction"},
      messages=[{"role": "user", "content": <prompt>}],
  )

Per-doc-type prompts live in ``extraction/prompts/<doc_type>.py``;
the dispatcher ``extraction.prompts.build_prompt_for(doc_type)``
returns the right builder.

Real-PII discipline (canon §11.8.3): raw Bedrock content (text or
tool input) MAY contain extracted client values. The
``_maybe_write_bedrock_debug`` helper persists raw payloads only
inside ``MP20_SECURE_DATA_ROOT/_debug/`` and only when the
``MP20_DEBUG_BEDROCK_RESPONSES=1`` env flag is set.
"""

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

from extraction.prompts import (
    FACT_EXTRACTION_TOOL,
    PROMPT_VERSION_BY_TYPE,
    build_prompt_for,
)
from extraction.schemas import BedrockFactsPayload, ClassificationResult, FactCandidate

__all__ = [
    "DEFAULT_BEDROCK_MAX_TOKENS",
    "FACT_EXTRACTION_TOOL",
    "PROMPT_VERSION_BY_TYPE",
    "BedrockConfig",
    "BedrockExtractionError",
    "BedrockSchemaMismatchError",
    "BedrockTokenLimitError",
    "_bedrock_max_tokens",
    "bedrock_config_from_env",
    "extract_text_facts_with_bedrock",
    "extract_visual_facts_with_bedrock",
    "visual_content_blocks",
]

MAX_IMAGE_BLOCK_BYTES = 4_500_000
MAX_VISUAL_REQUEST_BYTES = 18_000_000

# Output token budget for Bedrock fact-extraction calls.
#
# Default 16384: empirically chosen during 2026-05-01 extraction-quality
# hardening. The previous default (4096) truncated mid-JSON for spreadsheet
# planning docs and large native PDFs. Tool-use migration (Phase 4) keeps
# the same budget because the tool input shape is more verbose per-fact
# than the bare JSON it replaces (each fact carries explicit field +
# value + confidence + derivation + source_location + evidence_quote +
# source_page + asserted_at), so a similar headroom is needed.
#
# Override via MP20_BEDROCK_MAX_TOKENS for ops-time tuning without code
# change (raise for very large planning docs, lower if Bedrock spend
# becomes a concern).
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


@dataclass(frozen=True)
class BedrockConfig:
    model: str
    aws_region: str
    access_key: str
    secret_key: str


# Typed extraction errors with structured `failure_code` strings that the
# worker maps onto `processing_metadata.failure_code` and the UI renders
# into actionable advisor copy. Inherit from ValueError so existing
# `except ValueError:` callers keep working without churn.
#
# Each subclass owns one diagnosable failure mode. The list below is the
# single source of truth for the failure_code vocabulary used in i18n
# keys (`review.failure_code.<code>`) and frontend rendering.
#
# Tool-use migration (Phase 4) collapsed the failure surface: the prior
# `BedrockNonJsonError` (free-form JSON couldn't be repaired) is no
# longer reachable because the API constrains the response shape. The
# class is retained for backwards compat with existing imports but is
# no longer raised by the core extraction path.


class BedrockExtractionError(ValueError):
    """Base for typed Bedrock extraction errors."""

    failure_code: str = "bedrock_unknown"


class BedrockNonJsonError(BedrockExtractionError):
    """Retained for backwards compat with the pre-tool-use code path.

    No longer raised by the core extraction path -- tool-use forces the
    response shape, so non-JSON model output cannot occur. Kept as a
    typed leaf in case ad-hoc text-mode callers (which do not exist
    today) need a stable code.
    """

    failure_code = "bedrock_non_json"


class BedrockTokenLimitError(BedrockExtractionError):
    """Bedrock response exceeded the output token budget.

    Detected by `stop_reason == "max_tokens"` on the tool-use response
    when no tool_use content block was emitted. Recovery: bump
    `MP20_BEDROCK_MAX_TOKENS`, re-classify the doc as a chunkable
    type, or route to manual-entry.
    """

    failure_code = "bedrock_token_limit"


class BedrockSchemaMismatchError(BedrockExtractionError):
    """Tool-use response did not contain a valid fact_extraction block.

    Two underlying causes:
      1. Model returned plain text instead of calling the tool (refusal,
         policy filter, or off-topic content). `stop_reason` will be
         `end_turn` or `stop_sequence`.
      2. Tool was called but `input` failed BedrockFactsPayload
         validation (rare; happens if the model emits a value that
         violates the deeper schema constraints, e.g. `confidence`
         outside the allowed enum).
    """

    failure_code = "bedrock_schema_mismatch"


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
    builder = build_prompt_for(document_type, classification)
    prompt = builder(filename, classification, text[:max_chars])
    response = client.messages.create(
        model=config.model,
        max_tokens=_bedrock_max_tokens(),
        tools=[FACT_EXTRACTION_TOOL],
        tool_choice={"type": "tool", "name": "fact_extraction"},
        messages=[{"role": "user", "content": prompt}],
    )
    return _facts_from_tool_use_response(response, extraction_run_id)


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
    builder = build_prompt_for(document_type, classification)
    prompt = builder(
        filename,
        classification,
        "Use the attached page or image content as the source.",
    )
    response = client.messages.create(
        model=config.model,
        max_tokens=_bedrock_max_tokens(),
        tools=[FACT_EXTRACTION_TOOL],
        tool_choice={"type": "tool", "name": "fact_extraction"},
        messages=[
            {
                "role": "user",
                "content": [*image_blocks, {"type": "text", "text": prompt}],
            }
        ],
    )
    return (
        _facts_from_tool_use_response(response, extraction_run_id),
        overflow,
    )


def _facts_from_tool_use_response(
    response: Any,
    extraction_run_id: str,
) -> list[FactCandidate]:
    """Extract FactCandidate list from a Bedrock tool-use response.

    Tool-use is forced via tool_choice, so a successful call carries
    exactly one tool_use content block whose .input matches
    FACT_EXTRACTION_TOOL.input_schema. Missing tool_use block is the
    error case; stop_reason disambiguates the two failure modes.
    """
    tool_use_block = None
    for block in getattr(response, "content", []) or []:
        if getattr(block, "type", None) == "tool_use":
            tool_use_block = block
            break

    if tool_use_block is None:
        # Capture the raw text for diagnostic dumping (gated by
        # MP20_DEBUG_BEDROCK_RESPONSES + MP20_SECURE_DATA_ROOT). PII risk:
        # text content may carry extracted client values.
        text_content = "".join(getattr(b, "text", "") or "" for b in (response.content or []))
        _maybe_write_bedrock_debug("no_tool_use", extraction_run_id, text_content)
        stop_reason = getattr(response, "stop_reason", None)
        if stop_reason == "max_tokens":
            raise BedrockTokenLimitError(
                "Bedrock fact_extraction call exceeded output token budget."
            )
        raise BedrockSchemaMismatchError("Bedrock did not emit a fact_extraction tool_use block.")

    raw_input = getattr(tool_use_block, "input", None)
    if not isinstance(raw_input, dict):
        _maybe_write_bedrock_debug(
            "bad_tool_input",
            extraction_run_id,
            json.dumps(raw_input, default=str)[:12000],
        )
        raise BedrockSchemaMismatchError(
            "Bedrock fact_extraction tool_use input was not a JSON object."
        )

    _maybe_write_bedrock_debug(
        "tool_input",
        extraction_run_id,
        json.dumps(raw_input, default=str)[:12000],
    )

    try:
        parsed = BedrockFactsPayload.model_validate(raw_input)
    except ValidationError as exc:
        raise BedrockSchemaMismatchError(
            "Bedrock fact_extraction tool input did not match the expected schema."
        ) from exc

    return [
        FactCandidate(
            **fact.model_dump(mode="json"),
            extraction_run_id=extraction_run_id,
        )
        for fact in parsed.facts
        if not _is_missing_fact_value(fact.value)
    ]


def _maybe_write_bedrock_debug(stage: str, extraction_run_id: str, content: str) -> None:
    """Optionally persist a raw Bedrock payload for diagnostic use.

    Gated on MP20_DEBUG_BEDROCK_RESPONSES=1. Writes only inside
    MP20_SECURE_DATA_ROOT/_debug/. Never to stdout, repo, or external
    sinks. Real-PII discipline (canon §11.8.3): contents may include
    extracted client text; treat the path as PII storage.
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


def _safe_pdf_page_image_block(page: Any) -> dict[str, Any] | None:
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
