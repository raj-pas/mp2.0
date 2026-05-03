"""Statement / account extraction prompt module (Phase 4 tool-use).

Statements are structured tabular artifacts: account header with
holder + account number + account type, then a holdings table with
symbol/units/market_value/percentage rows. Extraction lifts each
holdings row as an individual fact; the table itself is never
re-emitted as markdown.
"""

from __future__ import annotations

from extraction.prompts.base import compose_prompt
from extraction.schemas import ClassificationResult

PROMPT_VERSION = "statement_review_facts_v3_tooluse"

CANONICAL_FIELDS = [
    "accounts[*].account_type",
    "accounts[*].current_value",
    "accounts[*].account_number",
    "accounts[*].holdings",
    "accounts[*].missing_holdings_confirmed",
]


_TYPE_BODY = """\
This is an account statement (brokerage, registered, or non-
registered). Extract one fact per stated value; do not return tables.

Extraction priorities (highest first):
  1. Account number -> accounts[N].account_number (raw; system
     hashes for display).
  2. Account type -> accounts[N].account_type. Map to canonical
     enum: rrsp | tfsa | rrif | non_registered | resp | lira |
     lrif | other. Use other for unfamiliar account-type strings;
     OMIT if no type is stated.
  3. Current value / total market value -> accounts[N].current_value
     as a decimal dollar amount. Use the most recent statement-date
     total (not the prior-period column).
  4. Holdings (per row of the holdings table) -> emit each as one
     fact under accounts[N].holdings[M] with object value. Required
     keys per holding object: symbol, units, market_value. Optional
     keys: cost_basis, asset_class, currency, issuer, position_pct.
     If the statement reports zero or missing holdings for a cash-
     only account, emit accounts[N].missing_holdings_confirmed=true
     with derivation_method="extracted" only if the statement says
     so explicitly; otherwise OMIT.
  5. Statement date -> emit as asserted_at on each fact (ISO date).
     If multiple as-of dates appear (e.g. trade-date vs settle-date),
     prefer the as-of date in the report header.

Numeric discipline: emit all dollar amounts as numbers (not strings).
Currency: assume CAD unless the statement explicitly tags a non-CAD
holding. If currency is non-CAD, include "currency" inside the
holdings[].value object.

Account-holder names belong on people[N], not on accounts[N]. If
the statement lists a single holder, emit people[0].display_name.
For joint accounts, emit people[0] and people[1] in document order.

Do NOT compute totals, percentages, or differences across rows; emit
only what is printed. Do NOT emit markdown tables in any field.
"""


def build_prompt(filename: str, classification: ClassificationResult, text: str) -> str:
    return compose_prompt(
        document_type="statement",
        type_specific_body=_TYPE_BODY,
        classification=classification,
        filename=filename,
        text=text,
        prompt_version=PROMPT_VERSION,
    )
