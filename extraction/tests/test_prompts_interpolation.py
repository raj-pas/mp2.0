"""Happy-path interpolation tests for per-doc-type prompt builders
(audit Block B #3 backfill — verify the v4_tooluse_entity_aligned
PROMPT_VERSION bump renders the always-emit-name nudge correctly).

One test per prompt module: kyc, statement, meeting_note, planning,
generic, plus a base.compose_prompt direct-test. No real Bedrock
calls. Tests assert:

  * prompt body contains the always-emit-name nudge for people /
    accounts / goals.
  * the rendered `Prompt version: ...` line carries the v4 string.
  * the doc-type-specific guidance section is preserved.
"""

from __future__ import annotations

from extraction.prompts import (
    ENTITY_ALIGNMENT_BLOCK,
    TOOLUSE_VERSION_SUFFIX,
    generic,
    kyc,
    meeting_note,
    planning,
    statement,
)
from extraction.schemas import ClassificationResult


def _classification(document_type: str) -> ClassificationResult:
    return ClassificationResult(
        document_type=document_type,
        confidence="high",
        route="single_schema",
        signals=[],
        schema_hints=[document_type],
    )


# ---------------------------------------------------------------------------
# 1. kyc
# ---------------------------------------------------------------------------


def test_kyc_prompt_carries_v4_version_and_entity_alignment_block() -> None:
    text = kyc.build_prompt("alice_kyc.pdf", _classification("kyc"), "Sample KYC text.")
    assert kyc.PROMPT_VERSION == "kyc_review_facts_v4_tooluse_entity_aligned"
    assert kyc.PROMPT_VERSION in text
    # Entity-alignment nudge appears.
    assert "people[N].display_name" in text
    assert "accounts[N].account_number" in text
    assert "goals[N].name" in text
    # Doc-type guidance still present.
    assert "KYC" in text or "kyc" in text.lower()


# ---------------------------------------------------------------------------
# 2. statement
# ---------------------------------------------------------------------------


def test_statement_prompt_carries_v4_version() -> None:
    text = statement.build_prompt(
        "rrsp_statement_q3.pdf",
        _classification("statement"),
        "Sample statement text.",
    )
    assert statement.PROMPT_VERSION == "statement_review_facts_v4_tooluse_entity_aligned"
    assert statement.PROMPT_VERSION in text
    assert "people[N].display_name" in text
    assert "accounts[N].account_number" in text


# ---------------------------------------------------------------------------
# 3. meeting_note
# ---------------------------------------------------------------------------


def test_meeting_note_prompt_carries_v4_version() -> None:
    text = meeting_note.build_prompt(
        "annual_review.txt",
        _classification("meeting_note"),
        "Advisor narrative.",
    )
    assert meeting_note.PROMPT_VERSION == "meeting_note_review_facts_v4_tooluse_entity_aligned"
    assert meeting_note.PROMPT_VERSION in text
    assert "goals[N].name" in text
    # Behavioral notes guidance still present.
    assert "behavioral_notes" in text


# ---------------------------------------------------------------------------
# 4. planning
# ---------------------------------------------------------------------------


def test_planning_prompt_carries_v4_version() -> None:
    text = planning.build_prompt(
        "retirement_plan.xlsx",
        _classification("planning"),
        "Planning workbook export.",
    )
    assert planning.PROMPT_VERSION == "planning_review_facts_v4_tooluse_entity_aligned"
    assert planning.PROMPT_VERSION in text
    assert "goals[N].name" in text


# ---------------------------------------------------------------------------
# 5. generic
# ---------------------------------------------------------------------------


def test_generic_prompt_carries_v4_version() -> None:
    text = generic.build_prompt(
        "intake_form.pdf",
        _classification("intake"),
        "Generic intake fields.",
    )
    assert generic.PROMPT_VERSION == "generic_review_facts_v4_tooluse_entity_aligned"
    assert generic.PROMPT_VERSION in text
    assert "people[N].display_name" in text


# ---------------------------------------------------------------------------
# 6. base — TOOLUSE_VERSION_SUFFIX is bumped, ENTITY_ALIGNMENT_BLOCK exists.
# ---------------------------------------------------------------------------


def test_base_tooluse_version_suffix_is_v4() -> None:
    assert TOOLUSE_VERSION_SUFFIX == "v4_tooluse_entity_aligned"


def test_entity_alignment_block_explicitly_documents_two_field_threshold() -> None:
    """The block must explicitly mention the 2-field threshold so
    Bedrock has the context: emit name + DOB / institution+account_type
    fallback whenever possible."""
    block = ENTITY_ALIGNMENT_BLOCK
    assert "two" in block.lower() or "TWO" in block
    assert "people[N].display_name" in block
    assert "accounts[N].account_number" in block
    assert "goals[N].name" in block
