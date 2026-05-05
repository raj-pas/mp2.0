"""Phase 9.3 — evidence-quote validator tests.

Three layers:
  1. ``validate_fact_evidence_quote`` unit cases (extracted facts pass
     through; inferred facts gated; punctuation-tolerant overlap).
  2. ``filter_inferred_facts_by_evidence`` returns (kept, dropped)
     tuples that respect the threshold.
  3. Prompt-level: PROMPT_VERSION strings bumped to v3 across all
     per-type modules (Phase 9 calibration marker).
"""

from __future__ import annotations

from extraction.schemas import FactCandidate
from extraction.validation import (
    EVIDENCE_OVERLAP_THRESHOLD,
    filter_inferred_facts_by_evidence,
    validate_fact_evidence_quote,
)


def _fact(
    *,
    field: str = "people[0].display_name",
    value: object = "x",
    derivation_method: str = "inferred",
    evidence_quote: str = "",
    confidence: str = "medium",
) -> FactCandidate:
    return FactCandidate(
        field=field,
        value=value,
        confidence=confidence,
        derivation_method=derivation_method,
        source_location="",
        evidence_quote=evidence_quote,
        extraction_run_id="test-run",
    )


# ---------------------------------------------------------------------------
# 1. validate_fact_evidence_quote
# ---------------------------------------------------------------------------


class TestValidateFactEvidenceQuote:
    def test_extracted_fact_always_passes(self) -> None:
        fact = _fact(derivation_method="extracted", evidence_quote="anything")
        assert validate_fact_evidence_quote(fact, "completely unrelated text") is True

    def test_extracted_with_empty_quote_passes(self) -> None:
        fact = _fact(derivation_method="extracted", evidence_quote="")
        assert validate_fact_evidence_quote(fact, "source") is True

    def test_inferred_with_empty_quote_fails(self) -> None:
        fact = _fact(derivation_method="inferred", evidence_quote="")
        assert validate_fact_evidence_quote(fact, "source") is False

    def test_inferred_with_empty_source_passes(self) -> None:
        # Vision-path facts have empty parsed_text — quote is anchored
        # by the model's own OCR; we cannot character-match.
        fact = _fact(derivation_method="inferred", evidence_quote="quote")
        assert validate_fact_evidence_quote(fact, "") is True

    def test_inferred_with_substring_match_passes(self) -> None:
        source = "Account Holders / Primary: Jennifer Niesner DOB 1962-04-15 marital married"
        fact = _fact(
            derivation_method="inferred",
            evidence_quote="Jennifer Niesner DOB 1962-04-15",
        )
        assert validate_fact_evidence_quote(fact, source) is True

    def test_inferred_with_punctuation_difference_passes(self) -> None:
        source = "client age is 58 per ID review"
        fact = _fact(
            derivation_method="inferred",
            evidence_quote="Client age is 58, per ID review.",
        )
        assert validate_fact_evidence_quote(fact, source) is True

    def test_inferred_with_no_overlap_fails(self) -> None:
        source = "Account Statement Q3 2024 holdings table follows"
        fact = _fact(
            derivation_method="inferred",
            evidence_quote="hallucinated text not in source",
        )
        assert validate_fact_evidence_quote(fact, source) is False

    def test_inferred_with_partial_overlap_passes_above_threshold(self) -> None:
        source = "Per ID review: client age 58 confirmed"
        fact = _fact(
            derivation_method="inferred",
            evidence_quote="client age 58 confirmed",
        )
        assert validate_fact_evidence_quote(fact, source) is True

    def test_inferred_with_partial_overlap_fails_below_threshold(self) -> None:
        source = "client age is 58"
        # Quote shares only a few characters with source; below 60%.
        fact = _fact(
            derivation_method="inferred",
            evidence_quote="goal target retirement amount five million dollars",
        )
        assert validate_fact_evidence_quote(fact, source) is False

    def test_threshold_is_60_percent(self) -> None:
        # Sanity-check the threshold constant is what we expect.
        assert abs(EVIDENCE_OVERLAP_THRESHOLD - 0.6) < 1e-9


# ---------------------------------------------------------------------------
# 2. filter_inferred_facts_by_evidence
# ---------------------------------------------------------------------------


class TestFilterInferredFactsByEvidence:
    def test_returns_kept_and_dropped_tuples(self) -> None:
        source = "Jennifer Niesner DOB 1962-04-15"
        good = _fact(
            derivation_method="inferred",
            evidence_quote="Jennifer Niesner",
        )
        bad = _fact(
            derivation_method="inferred",
            evidence_quote="hallucinated content",
        )
        extracted = _fact(
            derivation_method="extracted",
            evidence_quote="any quote",
        )
        kept, dropped = filter_inferred_facts_by_evidence([good, bad, extracted], source)
        assert good in kept
        assert extracted in kept
        assert bad in dropped
        assert len(kept) == 2
        assert len(dropped) == 1

    def test_empty_facts_list_returns_empty_tuples(self) -> None:
        kept, dropped = filter_inferred_facts_by_evidence([], "source")
        assert kept == []
        assert dropped == []

    def test_all_extracted_facts_keep_all(self) -> None:
        facts = [
            _fact(derivation_method="extracted", evidence_quote="x"),
            _fact(derivation_method="extracted", evidence_quote="y"),
        ]
        kept, dropped = filter_inferred_facts_by_evidence(facts, "source")
        assert len(kept) == 2
        assert dropped == []


# ---------------------------------------------------------------------------
# 3. Prompt-version bump (Phase 9 calibration marker)
# ---------------------------------------------------------------------------


class TestPromptVersionsBumpedToV3:
    """Phase 9 v3 baseline; Phase P1.1 (2026-05-05) bumped to v4
    `_tooluse_entity_aligned` (locked decision). The v4 string must
    SUFFIX the original v3 marker family so the full version chain
    remains greppable across releases."""

    def test_kyc_prompt_version_is_v4_entity_aligned(self) -> None:
        from extraction.prompts.kyc import PROMPT_VERSION

        assert PROMPT_VERSION == "kyc_review_facts_v4_tooluse_entity_aligned"

    def test_statement_prompt_version_is_v4_entity_aligned(self) -> None:
        from extraction.prompts.statement import PROMPT_VERSION

        assert PROMPT_VERSION == "statement_review_facts_v4_tooluse_entity_aligned"

    def test_meeting_note_prompt_version_is_v4_entity_aligned(self) -> None:
        from extraction.prompts.meeting_note import PROMPT_VERSION

        assert PROMPT_VERSION == "meeting_note_review_facts_v4_tooluse_entity_aligned"

    def test_generic_prompt_version_is_v4_entity_aligned(self) -> None:
        from extraction.prompts.generic import PROMPT_VERSION

        assert PROMPT_VERSION == "generic_review_facts_v4_tooluse_entity_aligned"

    def test_planning_prompt_version_is_v4_entity_aligned(self) -> None:
        from extraction.prompts.planning import PROMPT_VERSION

        assert PROMPT_VERSION == "planning_review_facts_v4_tooluse_entity_aligned"

    def test_base_no_fabrication_block_includes_strong_signal_section(self) -> None:
        from extraction.prompts.base import NO_FABRICATION_BLOCK

        # Phase 9.1 calibration marker.
        assert "STRONG signal" in NO_FABRICATION_BLOCK
        assert "EXTRACT eagerly" in NO_FABRICATION_BLOCK
        assert "SOFT inference" in NO_FABRICATION_BLOCK
        # Forbidden-inversion list is preserved.
        assert "FORBIDDEN inversion" in NO_FABRICATION_BLOCK
        # 9.3 evidence-quote validator nudge propagates.
        assert "evidence_quote" in NO_FABRICATION_BLOCK
