"""Generic / fallback extraction prompt module (Phase 4 tool-use).

Used when the classifier route is "multi_schema_sweep" (low-confidence
classification) or for doc types without a dedicated module
(crm_export, intake, identity, generic_financial, unknown). Sweeps
across all canonical schemas; the per-doc-type modules are preferred
when the classifier is confident.
"""

from __future__ import annotations

from extraction.prompts.base import compose_prompt
from extraction.schemas import ClassificationResult

PROMPT_VERSION = "generic_review_facts_v2_tooluse"


_TYPE_BODY = """\
This document does not fit one of the dedicated extraction
templates (KYC, statement, meeting-note, planning). Run a multi-
schema sweep: examine the document for any explicit values matching
canonical paths, and emit only what is explicitly stated.

Sweep checklist (extract any that apply; OMIT any that do not):
  - household.display_name + household.household_type +
    household.tax_residency
  - people[N].display_name + date_of_birth + age + marital_status +
    investment_knowledge
  - accounts[N].account_type + account_number + current_value +
    holdings + missing_holdings_confirmed + regulatory_*
  - goals[N].name + time_horizon_years + target_amount + priority
  - goal_account_links[N].goal_name + account_id_or_label +
    allocated_amount
  - risk.household_score (1-5 canon scale only)

For identity documents (driver's licenses, passports, identity
verification forms): extract people[N].display_name + date_of_birth.
The application redacts identity numbers from evidence_quote on
display.

For CRM exports (advisor-system snapshots): the structure tends to
be flat key-value pairs. Map each pair to its canonical path; OMIT
internal CRM identifiers (deal IDs, lead IDs, stage names) -- those
are not engine inputs.

Confidence guidance applies as in the shared block: STRUCTURED
sources can yield "high" confidence; narrative or speculative
language is "low". When in doubt, use "medium" + verbatim
evidence_quote and let the advisor decide.

If you cannot find any extractable canonical fact, return an empty
facts array. Do NOT pad with low-confidence guesses.
"""


def build_prompt(filename: str, classification: ClassificationResult, text: str) -> str:
    return compose_prompt(
        document_type=classification.document_type or "generic_financial",
        type_specific_body=_TYPE_BODY,
        classification=classification,
        filename=filename,
        text=text,
        prompt_version=PROMPT_VERSION,
    )
