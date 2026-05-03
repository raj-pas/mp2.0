"""Phase 4 tool-use extraction tests.

Covers the migrated Bedrock fact-extraction path:
  * FACT_EXTRACTION_TOOL schema matches BedrockFact.
  * Per-doc-type prompt modules expose build_prompt(...).
  * Per-type prompt content carries type-specific guidance.
  * Tool-use response parsing returns FactCandidate list.
  * Missing tool_use block + max_tokens stop_reason -> BedrockTokenLimitError.
  * Missing tool_use block + other stop_reason -> BedrockSchemaMismatchError.
  * Confidence floor caps fact confidence by classification confidence.
  * extract_text_facts_with_bedrock forces tool_choice + passes prompt body.
  * real_derived data_origin routes through ca-central-1.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from extraction.llm import (
    FACT_EXTRACTION_TOOL,
    PROMPT_VERSION_BY_TYPE,
    BedrockConfig,
    BedrockSchemaMismatchError,
    BedrockTokenLimitError,
    _facts_from_tool_use_response,
    extract_text_facts_with_bedrock,
)
from extraction.pipeline import _cap_fact_confidence, extract_facts_for_document
from extraction.prompts import build_prompt_for, generic, kyc, meeting_note, planning, statement
from extraction.schemas import (
    BedrockFact,
    ClassificationResult,
    FactCandidate,
    ParsedDocument,
)

# ---------------------------------------------------------------------------
# Synthetic Bedrock response shims (no SDK calls).
# ---------------------------------------------------------------------------


@dataclass
class _ToolUseBlock:
    type: str = "tool_use"
    name: str = "fact_extraction"
    input: Any = None


@dataclass
class _TextBlock:
    type: str = "text"
    text: str = ""


@dataclass
class _Response:
    content: list[Any]
    stop_reason: str = "tool_use"


def _classification(
    *, confidence: str = "high", route: str = "direct", document_type: str = "kyc"
) -> ClassificationResult:
    return ClassificationResult(
        document_type=document_type,
        confidence=confidence,  # type: ignore[arg-type]
        route=route,
        signals=[],
        schema_hints=[document_type],
    )


def _fact(field: str, value: Any = "v", confidence: str = "high") -> dict[str, Any]:
    return {
        "field": field,
        "value": value,
        "confidence": confidence,
        "derivation_method": "extracted",
        "source_location": "section",
        "source_page": None,
        "evidence_quote": "verbatim",
        "asserted_at": None,
    }


# ---------------------------------------------------------------------------
# FACT_EXTRACTION_TOOL schema invariants
# ---------------------------------------------------------------------------


def test_fact_extraction_tool_input_schema_mirrors_bedrock_fact() -> None:
    """The tool's input_schema fact-item field set must be a superset of
    BedrockFact required fields, so BedrockFactsPayload validates.
    """
    item_schema = FACT_EXTRACTION_TOOL["input_schema"]["properties"]["facts"]["items"]
    fact_keys = set(item_schema["properties"].keys())
    pydantic_required = {"field", "value", "confidence", "derivation_method", "evidence_quote"}

    assert pydantic_required.issubset(fact_keys), (
        f"FACT_EXTRACTION_TOOL must expose Bedrock-required fields; "
        f"missing: {pydantic_required - fact_keys}"
    )
    assert FACT_EXTRACTION_TOOL["name"] == "fact_extraction"
    assert FACT_EXTRACTION_TOOL["input_schema"]["required"] == ["facts"]


# ---------------------------------------------------------------------------
# Per-doc-type prompt modules
# ---------------------------------------------------------------------------


def test_each_doc_type_has_dedicated_build_prompt() -> None:
    """Phase 4.1: kyc, statement, meeting_note, planning, generic each
    expose a `build_prompt(filename, classification, text)` function.
    """
    for module in (kyc, statement, meeting_note, planning, generic):
        assert callable(module.build_prompt), f"{module.__name__} missing build_prompt"


def test_planning_prompt_forbids_markdown_tables_explicitly() -> None:
    """Planning prompt must explicitly forbid markdown tables.

    Historic failure mode: Bedrock returns the entire workbook as a
    single markdown table; tool-use kills the failure shape but the
    prompt still anchors the rule for clarity.
    """
    prompt = planning.build_prompt(
        "plan.xlsx", _classification(document_type="planning"), "doc text"
    )
    assert "markdown table" in prompt.lower() or "do not emit markdown" in prompt.lower()


def test_kyc_prompt_includes_no_fabrication_examples() -> None:
    """KYC prompt must surface the no-fabrication discipline with worked
    examples (canon §9.4.5).
    """
    prompt = kyc.build_prompt("kyc.pdf", _classification(document_type="kyc"), "doc text")
    assert "DO NOT INVENT" in prompt
    assert "OMIT" in prompt
    # KYC-specific anchor: regulatory enums use lowercase
    assert "regulatory_objective" in prompt
    assert "regulatory_risk_rating" in prompt


def test_meeting_note_prompt_uses_low_confidence_for_aspirational() -> None:
    """Meeting-note prompt must route aspirational language to low
    confidence + behavioral_notes path, not canonical engine fields.
    """
    prompt = meeting_note.build_prompt(
        "note.txt", _classification(document_type="meeting_note"), "doc text"
    )
    assert "behavioral_notes" in prompt
    assert "aspirational" in prompt.lower() or "speculative" in prompt.lower()
    assert "low" in prompt  # tier in confidence guidance


def test_prompt_version_v2_tooluse_set_per_doc_type() -> None:
    """Each per-doc-type module must carry the v2_tooluse suffix to
    distinguish from the pre-tool-use prompt versions.
    """
    expected = {
        "kyc": "kyc_review_facts_v2_tooluse",
        "statement": "statement_review_facts_v2_tooluse",
        "meeting_note": "meeting_note_review_facts_v2_tooluse",
        "planning": "planning_review_facts_v2_tooluse",
        "generic_financial": "generic_review_facts_v2_tooluse",
    }
    for doc_type, version in expected.items():
        assert PROMPT_VERSION_BY_TYPE[doc_type] == version, (
            f"{doc_type} has version {PROMPT_VERSION_BY_TYPE[doc_type]!r}; expected {version!r}"
        )


def test_build_prompt_for_returns_dispatcher_or_generic_fallback() -> None:
    """Unknown doc types fall back to generic.build_prompt."""
    builder = build_prompt_for("unknown_synthetic_type")
    assert builder is generic.build_prompt


# ---------------------------------------------------------------------------
# Tool-use response parsing
# ---------------------------------------------------------------------------


def test_facts_from_tool_use_response_extracts_facts_via_validator() -> None:
    """Happy path: tool_use block input contains valid facts; we get
    FactCandidate list with extraction_run_id stamped.
    """
    response = _Response(
        content=[
            _ToolUseBlock(
                input={
                    "facts": [_fact("people[0].display_name", "Alex"), _fact("people[0].age", 42)]
                }
            )
        ]
    )
    facts = _facts_from_tool_use_response(response, "run-id-123")
    assert len(facts) == 2
    assert all(isinstance(f, FactCandidate) for f in facts)
    assert all(f.extraction_run_id == "run-id-123" for f in facts)


def test_facts_from_tool_use_response_filters_missing_values() -> None:
    """Empty / None values are filtered out; the model can emit a fact
    with no actual value, which is the same as omitting it.
    """
    response = _Response(
        content=[
            _ToolUseBlock(
                input={
                    "facts": [
                        _fact("people[0].display_name", "Alex"),
                        _fact("people[0].age", None),
                        _fact("accounts[0].account_type", ""),
                        _fact("accounts[1].holdings", []),
                    ]
                }
            )
        ]
    )
    facts = _facts_from_tool_use_response(response, "run-id-456")
    assert len(facts) == 1
    assert facts[0].field == "people[0].display_name"


def test_facts_from_tool_use_response_raises_token_limit_on_max_tokens() -> None:
    """No tool_use block + stop_reason="max_tokens" -> BedrockTokenLimitError."""
    response = _Response(
        content=[_TextBlock(text="(model started typing but ran out of budget)")],
        stop_reason="max_tokens",
    )
    with pytest.raises(BedrockTokenLimitError) as exc_info:
        _facts_from_tool_use_response(response, "run-id")
    assert exc_info.value.failure_code == "bedrock_token_limit"


def test_facts_from_tool_use_response_raises_schema_mismatch_on_other_stop_reasons() -> None:
    """No tool_use block + non-token stop_reason -> BedrockSchemaMismatchError.

    Covers refusals, off-topic responses, content-policy filters.
    """
    for stop in ("end_turn", "stop_sequence", None):
        response = _Response(
            content=[_TextBlock(text="I cannot help with that.")],
            stop_reason=stop,  # type: ignore[arg-type]
        )
        with pytest.raises(BedrockSchemaMismatchError) as exc_info:
            _facts_from_tool_use_response(response, "run-id")
        assert exc_info.value.failure_code == "bedrock_schema_mismatch"


def test_facts_from_tool_use_response_raises_schema_mismatch_on_invalid_input() -> None:
    """Tool was called but input is not a dict -> BedrockSchemaMismatchError."""
    response = _Response(
        content=[_ToolUseBlock(input="not-a-dict")],
        stop_reason="tool_use",
    )
    with pytest.raises(BedrockSchemaMismatchError):
        _facts_from_tool_use_response(response, "run-id")


def test_facts_from_tool_use_response_raises_schema_mismatch_on_validator_failure() -> None:
    """Tool input shape doesn't validate against BedrockFactsPayload."""
    response = _Response(
        content=[_ToolUseBlock(input={"facts": "not-a-list"})],
        stop_reason="tool_use",
    )
    with pytest.raises(BedrockSchemaMismatchError):
        _facts_from_tool_use_response(response, "run-id")


# ---------------------------------------------------------------------------
# Confidence floor (PROMPT-5)
# ---------------------------------------------------------------------------


def test_classification_confidence_caps_fact_confidence() -> None:
    """A low-confidence classification floors all facts to low confidence.

    Source-priority hierarchy (canon §11.4) treats classification as the
    upper bound: if we weren't sure about the doc type, we can't have
    been sure about the facts derived from it.
    """
    facts = [
        FactCandidate(
            field=f"f{i}",
            value=i,
            confidence=conf,  # type: ignore[arg-type]
            derivation_method="extracted",
            source_location="section",
            source_page=None,
            evidence_quote="q",
            asserted_at=None,
            extraction_run_id="run",
        )
        for i, conf in enumerate(("high", "medium", "low"))
    ]
    classification = _classification(confidence="low")
    capped = _cap_fact_confidence(facts, classification)
    assert all(f.confidence == "low" for f in capped)


def test_classification_confidence_does_not_lift_low_facts_to_high() -> None:
    """High classification confidence does NOT lift low-confidence facts.

    The cap is one-directional (max only).
    """
    fact = FactCandidate(
        field="f0",
        value=0,
        confidence="low",
        derivation_method="extracted",
        source_location="section",
        source_page=None,
        evidence_quote="q",
        asserted_at=None,
        extraction_run_id="run",
    )
    classification = _classification(confidence="high")
    capped = _cap_fact_confidence([fact], classification)
    assert capped[0].confidence == "low"


def test_classification_medium_confidence_caps_high_to_medium() -> None:
    """Medium classification confidence floors high facts to medium."""
    fact = FactCandidate(
        field="f0",
        value=0,
        confidence="high",
        derivation_method="extracted",
        source_location="section",
        source_page=None,
        evidence_quote="q",
        asserted_at=None,
        extraction_run_id="run",
    )
    classification = _classification(confidence="medium")
    capped = _cap_fact_confidence([fact], classification)
    assert capped[0].confidence == "medium"


# ---------------------------------------------------------------------------
# Tool-use call shape (mock the Bedrock client)
# ---------------------------------------------------------------------------


class _FakeBedrockMessages:
    def __init__(self, response: _Response) -> None:
        self._response = response
        self.last_kwargs: dict[str, Any] = {}

    def create(self, **kwargs: Any) -> _Response:
        self.last_kwargs = kwargs
        return self._response


class _FakeBedrockClient:
    def __init__(self, response: _Response) -> None:
        self.messages = _FakeBedrockMessages(response)


def test_extract_text_facts_with_bedrock_forces_tool_choice(monkeypatch) -> None:
    """The text-extraction call must pass tools=[FACT_EXTRACTION_TOOL] +
    tool_choice={"type": "tool", "name": "fact_extraction"}.
    """
    response = _Response(
        content=[_ToolUseBlock(input={"facts": [_fact("household.display_name", "Demo")]})]
    )
    fake = _FakeBedrockClient(response)
    monkeypatch.setattr("extraction.llm._bedrock_client", lambda config: fake)

    config = BedrockConfig(
        model="global.anthropic.claude-sonnet-4-6",
        aws_region="ca-central-1",
        access_key="AKIA-test",
        secret_key="test-secret",
    )
    facts = extract_text_facts_with_bedrock(
        filename="kyc.pdf",
        document_type="kyc",
        classification=_classification(),
        text="DOB: 1980-01-01",
        extraction_run_id="run",
        max_chars=10000,
        config=config,
    )
    assert len(facts) == 1
    assert fake.messages.last_kwargs["tools"] == [FACT_EXTRACTION_TOOL]
    assert fake.messages.last_kwargs["tool_choice"] == {
        "type": "tool",
        "name": "fact_extraction",
    }
    # Prompt body must mention the doc-type-specific guidance.
    user_message = fake.messages.last_kwargs["messages"][0]["content"]
    assert "Doc-type guidance (kyc)" in user_message


# ---------------------------------------------------------------------------
# Pipeline integration: real_derived routes through Bedrock + ca-central-1
# ---------------------------------------------------------------------------


def test_extract_facts_for_document_real_derived_passes_bedrock_config(monkeypatch) -> None:
    """real_derived data_origin must call extract_text_facts_with_bedrock
    with the supplied BedrockConfig (which carries aws_region).
    """
    captured: dict[str, Any] = {}

    def _fake_extract(**kwargs: Any) -> list[FactCandidate]:
        captured.update(kwargs)
        return []

    monkeypatch.setattr("extraction.pipeline.extract_text_facts_with_bedrock", _fake_extract)

    config = BedrockConfig(
        model="global.anthropic.claude-sonnet-4-6",
        aws_region="ca-central-1",
        access_key="AKIA-test",
        secret_key="test-secret",
    )
    parsed = ParsedDocument(text="some content", method="text", metadata={})
    classification = _classification()

    facts, metadata = extract_facts_for_document(
        path=Path("/tmp/example.pdf"),
        filename="example.pdf",
        data_origin="real_derived",
        parsed=parsed,
        classification=classification,
        text_max_chars=10000,
        ocr_max_pages=4,
        bedrock_config=config,
    )
    assert facts == []
    assert captured["config"] is config
    assert captured["config"].aws_region == "ca-central-1"


def test_extract_facts_for_document_real_derived_requires_bedrock_config() -> None:
    """real_derived without bedrock_config must fail closed (REGION-1)."""
    parsed = ParsedDocument(text="some content", method="text", metadata={})
    with pytest.raises(RuntimeError, match="Real-derived"):
        extract_facts_for_document(
            path=Path("/tmp/x.pdf"),
            filename="x.pdf",
            data_origin="real_derived",
            parsed=parsed,
            classification=_classification(),
            text_max_chars=10000,
            ocr_max_pages=4,
            bedrock_config=None,
        )


# ---------------------------------------------------------------------------
# BedrockFact + tool input compatibility
# ---------------------------------------------------------------------------


def test_bedrock_fact_validator_accepts_tool_input_shape() -> None:
    """The validator that consumes tool_use_block.input MUST tolerate the
    exact shape we asked for in FACT_EXTRACTION_TOOL.input_schema. This
    pins the schema-validator round trip.
    """
    raw = _fact("people[0].date_of_birth", "1980-01-01")
    parsed = BedrockFact.model_validate(raw)
    assert parsed.field == "people[0].date_of_birth"
    assert parsed.confidence == "high"
    assert parsed.derivation_method == "extracted"
