"""Per-doc-type prompt dispatcher for MP2.0 fact extraction.

Phase 4 (2026-05-02) restructure: the unified ``fact_extraction_prompt``
in extraction/llm.py is replaced with per-doc-type ``build_prompt(...)``
functions that compose `extraction.prompts.base.SHARED_*` guardrails
with type-specific extraction guidance.

Public surface:
  - :func:`build_prompt_for(document_type)` -> per-type ``build_prompt``
  - :data:`PROMPT_VERSION_BY_TYPE` -> stable version string per type
  - :data:`FACT_EXTRACTION_TOOL` -> Bedrock tool-use schema
"""

from __future__ import annotations

from collections.abc import Callable

from extraction.prompts import generic, kyc, meeting_note, planning, statement
from extraction.prompts.base import (
    CANONICAL_FIELD_INVENTORY,
    CANONICAL_VOCABULARY_BLOCK,
    CONFIDENCE_GUIDANCE_BLOCK,
    FACT_EXTRACTION_TOOL,
    NO_FABRICATION_BLOCK,
    TOOLUSE_VERSION_SUFFIX,
    compose_prompt,
)
from extraction.prompts.classify import PROMPT_VERSION as CLASSIFY_PROMPT_VERSION
from extraction.schemas import ClassificationResult

PromptBuilder = Callable[[str, ClassificationResult, str], str]


_BUILDERS: dict[str, PromptBuilder] = {
    "kyc": kyc.build_prompt,
    "statement": statement.build_prompt,
    "meeting_note": meeting_note.build_prompt,
    "planning": planning.build_prompt,
    "spreadsheet": planning.build_prompt,
    "crm_export": generic.build_prompt,
    "intake": generic.build_prompt,
    "identity": generic.build_prompt,
    "generic_financial": generic.build_prompt,
    "unknown": generic.build_prompt,
}


PROMPT_VERSION_BY_TYPE: dict[str, str] = {
    "kyc": kyc.PROMPT_VERSION,
    "statement": statement.PROMPT_VERSION,
    "meeting_note": meeting_note.PROMPT_VERSION,
    "planning": planning.PROMPT_VERSION,
    "spreadsheet": planning.PROMPT_VERSION,
    "crm_export": generic.PROMPT_VERSION,
    "intake": generic.PROMPT_VERSION,
    "identity": generic.PROMPT_VERSION,
    "generic_financial": generic.PROMPT_VERSION,
    "unknown": CLASSIFY_PROMPT_VERSION,
}


def build_prompt_for(
    document_type: str,
    classification: ClassificationResult | None = None,
) -> PromptBuilder:
    """Return the per-doc-type prompt builder.

    Phase 4 (refined 2026-05-02 after Seltzer KYC canary): when the
    classifier signals `route == "multi_schema_sweep"` it means the
    classifier saw signals from multiple doc types and isn't sure
    which one dominates. In that case the per-type body is too
    narrow — it produces an extraction laser-focused on one doc class
    while the source actually carries fields from many. We dispatch
    to the generic sweep builder which traverses every canonical
    schema. This addresses the canary's "missing goals + household
    + goal_account_links sections" regression where a multi-schema
    KYC routed to kyc.build_prompt and Bedrock followed the narrow
    KYC body, dropping fields it would have extracted under the
    pre-Phase-4 unified prompt.

    For a clear single-class doc (route != "multi_schema_sweep"),
    the per-doc-type builder is preferred — the type-specific
    extraction body is more accurate than the broad sweep.
    """
    if classification is not None and classification.route == "multi_schema_sweep":
        return generic.build_prompt
    return _BUILDERS.get(document_type, generic.build_prompt)


__all__ = [
    "CANONICAL_FIELD_INVENTORY",
    "CANONICAL_VOCABULARY_BLOCK",
    "CONFIDENCE_GUIDANCE_BLOCK",
    "FACT_EXTRACTION_TOOL",
    "NO_FABRICATION_BLOCK",
    "PROMPT_VERSION_BY_TYPE",
    "PromptBuilder",
    "TOOLUSE_VERSION_SUFFIX",
    "build_prompt_for",
    "compose_prompt",
]
