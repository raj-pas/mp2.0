"""Shared guardrails + tool-use schema for MP2.0 fact extraction (Phase 4).

Centralizes the cross-cutting prompt constraints that every per-doc-type
prompt module imports + composes into the user message. Bedrock tool-use
(Anthropic Messages API ``tools`` + ``tool_choice``) constrains the
response shape via JSON Schema, eliminating REPAIR-1 (free-form JSON
repair) and REPAIR-2 (alternate-key normalization) as bug classes.

Why a single guardrails module:
  * Source-of-truth for the no-fabrication rule (canon §9.4.5) — every
    doc type inherits it without copy/paste drift.
  * Source-of-truth for the canon vocab discipline (canon §6.3a) —
    prompt copy is gated by `scripts/check-vocab.sh`.
  * Source-of-truth for the FACT_EXTRACTION_TOOL JSON schema — the
    tool input shape mirrors `extraction.schemas.BedrockFact` so the
    BedrockFactsPayload validator can consume tool input directly.

Real-PII discipline (canon §11.8.3): prompt bodies never embed
client content. Document text is concatenated at call time inside
`build_prompt(...)` per doc-type module.
"""

from __future__ import annotations

from typing import Any

from extraction.schemas import ClassificationResult

# Tool-use prompt-version suffix; per-doc-type modules append to their
# own prefix (e.g. "kyc_review_facts_v4_tooluse_entity_aligned").
# Bumped to v4 in Phase P1.1 (2026-05-05) to reflect the cross-document
# entity-alignment matcher: prompts now require always-emit-name nudges
# on people[N].display_name + accounts[N].account_number (or institution
# +account_type fallback) + goals[N].name so the matcher has reliable
# identifying fields to align across documents.
TOOLUSE_VERSION_SUFFIX = "v4_tooluse_entity_aligned"


# Shared no-fabrication guidance with worked examples.
#
# Phase 9 calibration (2026-05-03): the original v2 block told Bedrock
# to "OMIT when uncertain" and Bedrock generalized "default to omission"
# — which dropped legitimate signal alongside hallucinations (Seltzer
# CS Address.pdf 12 → 8 facts, AW Address.pdf 12 → 2). The v3 block
# distinguishes STRONG document signal (extract eagerly) from SOFT
# inference (be conservative). The forbidden-inversion list still
# anchors the no-fabrication rule for ranges, aspirational language,
# and unselected checkboxes.
NO_FABRICATION_BLOCK = """\
DO NOT INVENT, ESTIMATE, OR INTERPOLATE FINANCIAL NUMBERS, NAMES, DATES,
OR ANY OTHER FIELD VALUE. If the document does not explicitly state a
value, OMIT the fact (do not include it in the facts array).

STRONG signal — EXTRACT eagerly when these patterns appear:
  - Named field labels followed by values
    (e.g. "Date of Birth: 1962-04-15", "Marital Status: married",
    "Account Number: 12345").
  - Dollar amounts in fixed table cells with header context
    (e.g. a "Market Value" column with "$42,150.00" rows).
  - ISO dates printed in headers, footers, or labeled positions
    (e.g. "Statement Date: 2024-09-30").
  - Account-holder name blocks at the top of statements / KYC docs
    (single-holder OR joint blocks; emit people[N].display_name in
    document order).
  - Holdings table rows: each row is one fact under
    accounts[N].holdings[M] with the printed symbol + units + market
    value. Do not skip rows.
  - Address blocks: emit each visible component as a separate fact
    if the doc-type-specific guidance enumerates address fields,
    OR as a single combined people[N].address quote with
    confidence="medium" if the guidance does not.
  - Goal names mentioned in narrative or labeled fields: emit
    goals[N].name with confidence="medium" even if the target_amount
    is missing (omit only target_amount in that case, not the goal).

SOFT inference — be conservative when these patterns appear:
  - Ranges or estimates ("$400k-$500k", "around 5 years", "maybe").
  - Aspirational language ("might retire by 65", "thinking about").
  - Hedged language ("around", "approximately", "roughly").
  - Inferred-from-prose synthesis (e.g. inferring household income
    from salary + spouse's stated salary).

Examples of FORBIDDEN inversion:
  - Document says "client mentioned maybe retiring in 3 years" -> OMIT
    retirement_age. The number 3 is speculative.
  - Document says "estimated household net worth $400k-$500k" -> OMIT
    net_worth. The range is not a value; if you must record it, use
    confidence="low" with the exact range quote in evidence_quote and
    let the advisor decide.
  - Document mentions an account but does not state the balance ->
    OMIT current_value for that account. Do not infer from "around"
    or "approximately" language.
  - KYC checkbox unselected -> OMIT regulatory_risk_rating; do not
    default to "medium" or any other value.
  - Document references a goal but does not state target amount ->
    include goal name with confidence="medium" or "low"; OMIT
    target_amount.

If a value appears as a range or estimate in the source, return the
exact source quote in evidence_quote with confidence="low". Never
collapse a range to a single number.

Inferred facts (derivation_method="inferred") MUST carry a verbatim
evidence_quote that supports the inference. The runtime drops
inferred facts whose evidence_quote does not appear (substring
overlap) in the source document text.
"""


CONFIDENCE_GUIDANCE_BLOCK = """\
Confidence is tied to the source class:

  - STRUCTURED documents (KYC forms, account statements, identity docs):
      "high"   if explicit + unambiguous (e.g. printed DOB, named
               account holder, dollar amount in a fixed cell).
      "medium" if inferred from structure (e.g. account type derived
               from the account-number prefix or section header).
      "low"    for estimates, ranges, or fields explicitly marked
               approximate in the document itself.

  - MEETING NOTES + advisor narrative:
      "medium" for explicit quoted advisor statements ("client wants
               $1.5M for retirement at 65").
      "low"    for speculative, aspirational, or hedged language
               ("might consider", "thinking about", "maybe in 3 years").

  - TEMPORAL facts (asserted_at):
      "high"   when the document carries a clear date stamp.
      "low"    when the date must be inferred from context.

The classifier provides an overall classification confidence; the
runtime caps each fact's confidence at the classification confidence
so a low-confidence classification can never produce high-confidence
facts.
"""


ENTITY_ALIGNMENT_BLOCK = """\
Cross-document entity alignment (P1.1, 2026-05-05):

The downstream system aligns people / accounts / goals across
DIFFERENT documents in the same workspace using identifying fields.
It treats "people[0] in doc A" and "people[0] in doc B" as the SAME
real-world person ONLY when at least TWO identifying fields overlap
(e.g. shared name token AND matching DOB). Without enough identity
signal, the system records two distinct canonical entities — which
keeps a father+son pair correctly separate, but also means missing
identity fields fragment what should have been one entity.

To support reliable alignment, ALWAYS emit the following identifier
fields whenever the document references the entity:

  - people[N].display_name      ALWAYS, for every people[N] referenced.
                                 Without a name, the matcher cannot
                                 align this person to other docs.
  - people[N].date_of_birth      Whenever printed. Strong identity
                                 signal; use ISO YYYY-MM-DD.
  - accounts[N].account_number   Preferred when printed (raw; system
                                 hashes for display). When absent,
                                 emit BOTH (institution, account_type)
                                 as a fallback identifier pair.
  - goals[N].name                ALWAYS, for every goals[N] referenced.

Do NOT invent identifiers. If a document does not state a name / DOB /
account number, OMIT — the matcher's two-field threshold is the
fail-safe.
"""


CANONICAL_VOCABULARY_BLOCK = """\
Vocabulary discipline (MP2.0 canon §6.3a + §16):

  - Use "building-block fund" (not "sleeve") in any narrative.
  - Use canon risk descriptors when describing risk in
    behavioral_notes: Cautious, Conservative-balanced, Balanced,
    Balanced-growth, Growth-oriented. Do not use low/medium/high.
  - Risk scores are 1-5 (canon scale). If the document uses a 1-10
    scale, omit and surface as evidence_quote rather than rescaling.
  - Never use "reallocation", "transfer", "move money", "rebalance"
    in extracted text fields. Use "re-goaling" if a similar concept
    appears.
"""


# Output JSON schema for the Bedrock fact_extraction tool. Mirrors the
# `extraction.schemas.BedrockFact` Pydantic model so the validator can
# consume `tool_use_block.input` directly.
#
# Keep field set in sync with BedrockFact; if BedrockFact gains a new
# field, mirror it here (and bump TOOLUSE_VERSION_SUFFIX so prompt
# version reflects the schema change).
FACT_EXTRACTION_TOOL: dict[str, Any] = {
    "name": "fact_extraction",
    "description": (
        "Emit structured advisor-review facts extracted from the client "
        "document. Use canonical MP2.0 field paths only. Omit any fact "
        "whose value is not explicitly stated in the document; do not "
        "invent or estimate values."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "facts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "field": {
                            "type": "string",
                            "description": (
                                "Canonical MP2.0 field path "
                                "(e.g. 'people[0].date_of_birth', "
                                "'accounts[0].current_value', "
                                "'risk.household_score')."
                            ),
                        },
                        "value": {
                            "description": (
                                "Extracted value. Type depends on the "
                                "field: string for names/dates, number "
                                "for amounts, integer for counts/ages, "
                                "boolean for flags."
                            ),
                        },
                        "confidence": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                        },
                        "derivation_method": {
                            "type": "string",
                            "enum": ["extracted", "inferred", "defaulted"],
                            "description": (
                                "'extracted' = lifted directly; "
                                "'inferred' = derived from doc structure; "
                                "'defaulted' = NEVER use, omit instead."
                            ),
                        },
                        "source_location": {
                            "type": "string",
                            "description": (
                                "Section, table cell, or label inside "
                                "the document where the value was "
                                "found. E.g. 'Account Holders / "
                                "Primary'."
                            ),
                        },
                        "source_page": {
                            "type": ["integer", "null"],
                        },
                        "evidence_quote": {
                            "type": "string",
                            "description": (
                                "Short verbatim source snippet (<= 240 "
                                "chars). The application redacts PII "
                                "from this field before display."
                            ),
                        },
                        "asserted_at": {
                            "type": ["string", "null"],
                            "description": (
                                "ISO-8601 date when the fact was "
                                "asserted in the document, or null if "
                                "the document does not state a date. "
                                "Used for temporal facts in meeting "
                                "notes and dated planning artifacts."
                            ),
                        },
                    },
                    "required": [
                        "field",
                        "value",
                        "confidence",
                        "derivation_method",
                        "evidence_quote",
                    ],
                },
            },
        },
        "required": ["facts"],
    },
}


# Canonical field reference exposed in every prompt so Bedrock has a
# stable list to choose from. NOT a constraint -- doc types add their
# own type-specific fields on top.
CANONICAL_FIELD_INVENTORY = """\
Canonical field paths (use exactly; do not invent new paths):

  household.display_name           # household label
  household.household_type         # individual | couple | family
  household.tax_residency          # canada-quebec | canada-non-quebec | other

  people[N].display_name           # full name as stated
  people[N].date_of_birth          # ISO YYYY-MM-DD
  people[N].age                    # integer
  people[N].marital_status         # single | married | common_law | divorced | widowed | separated
  people[N].investment_knowledge   # none | low | medium | high

  accounts[N].account_type
      # rrsp | tfsa | rrif | non_registered | resp | lira | lrif | other
  accounts[N].account_number       # raw; system hashes + redacts on display
  accounts[N].current_value        # decimal dollars
  accounts[N].holdings             # array of {symbol, units, market_value, ...}
  accounts[N].missing_holdings_confirmed   # bool; true if cash-only / no holdings
  accounts[N].regulatory_objective
      # safety | income | balanced_income_growth | growth | aggressive_growth
  accounts[N].regulatory_time_horizon      # short | medium | long
  accounts[N].regulatory_risk_rating       # low | low_medium | medium | medium_high | high

  goals[N].name                    # advisor-given goal label
  goals[N].time_horizon_years      # integer
  goals[N].target_amount           # decimal; OMIT if not stated
  goals[N].priority                # high | medium | low

  goal_account_links[N].goal_name              # exact name from goals[*].name
  goal_account_links[N].account_id_or_label    # account match label
  goal_account_links[N].allocated_amount       # decimal

  risk.household_score             # 1-5 canon scale; OMIT if doc uses 1-10

  behavioral_notes.* paths are FREE-FORM (advisor narrative). NEVER an
  engine input unless an advisor explicitly maps a behavioral note to
  a canonical field above.
"""


def compose_prompt(
    *,
    document_type: str,
    type_specific_body: str,
    classification: ClassificationResult,
    filename: str,
    text: str,
    prompt_version: str,
) -> str:
    """Compose the user message for a Bedrock tool-use fact-extraction call.

    The model is forced to call the `fact_extraction` tool via
    `tool_choice={"type": "tool", "name": "fact_extraction"}` at the
    call site (extraction/llm.py). This message body supplies the
    type-specific extraction guidance + shared guardrails; the tool
    schema constrains the response shape.
    """
    schema_hints = ", ".join(classification.schema_hints or ["generic_financial_sweep"])
    low_confidence_note = (
        "\nClassification is low-confidence; sweep across household, "
        "people, accounts, holdings, goals, goal-account links, and "
        "risk before settling on which facts to emit.\n"
        if classification.route == "multi_schema_sweep"
        else ""
    )
    return (
        "You are MP2.0 advisor-review extraction. Call the "
        "fact_extraction tool exactly once with all advisor-review "
        "facts you can extract from the document below.\n\n"
        f"=== Doc-type guidance ({document_type}) ===\n"
        f"{type_specific_body.strip()}\n\n"
        "=== No-fabrication rule (canon §9.4.5) ===\n"
        f"{NO_FABRICATION_BLOCK.strip()}\n\n"
        "=== Cross-document entity alignment ===\n"
        f"{ENTITY_ALIGNMENT_BLOCK.strip()}\n\n"
        "=== Confidence guidance ===\n"
        f"{CONFIDENCE_GUIDANCE_BLOCK.strip()}\n\n"
        "=== Vocabulary discipline ===\n"
        f"{CANONICAL_VOCABULARY_BLOCK.strip()}\n\n"
        "=== Field inventory ===\n"
        f"{CANONICAL_FIELD_INVENTORY.strip()}\n\n"
        f"=== Document context ===\n"
        f"Prompt version: {prompt_version}\n"
        f"Filename label: {filename}\n"
        f"Document type: {document_type}\n"
        f"Classifier route: {classification.route}; "
        f"confidence: {classification.confidence}; "
        f"schema hints: {schema_hints}"
        f"{low_confidence_note}\n"
        f"=== Document text ===\n{text}"
    )
