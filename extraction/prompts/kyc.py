"""KYC/profile extraction prompt module (Phase 4 tool-use).

KYC documents are structured forms (regulatory disclosure pages,
account-opening packets, profile updates). Extraction lifts named
fields from labeled positions; nothing is inferred from prose. The
single highest extraction-error class historically has been
fabricated values for unselected/blank checkbox fields -- the
prompt explicitly anchors that behavior.
"""

from __future__ import annotations

from extraction.prompts.base import compose_prompt
from extraction.schemas import ClassificationResult

PROMPT_VERSION = "kyc_review_facts_v2_tooluse"

CANONICAL_FIELDS = [
    "people[*].display_name",
    "people[*].date_of_birth",
    "people[*].age",
    "people[*].marital_status",
    "people[*].investment_knowledge",
    "accounts[*].regulatory_objective",
    "accounts[*].regulatory_time_horizon",
    "accounts[*].regulatory_risk_rating",
    "risk.household_score",
]


_TYPE_BODY = """\
This is a KYC / regulatory profile document. Lift named field values
from labeled positions only; do not interpret prose.

Extraction priorities (highest first):
  1. Named individuals -> people[N].display_name + date_of_birth + age.
     Use ISO YYYY-MM-DD for dates; integers for age.
  2. Marital status -> people[N].marital_status. Allowed values are
     single | married | common_law | divorced | widowed | separated.
     OMIT if no checkbox is selected. Do not default to "single".
  3. Investment knowledge -> people[N].investment_knowledge with
     values none | low | medium | high. OMIT if not stated.
  4. Account-level regulatory disclosures (PER ACCOUNT, not household-
     wide unless the form is single-account):
       accounts[N].regulatory_objective: safety | income |
         balanced_income_growth | growth | aggressive_growth.
       accounts[N].regulatory_time_horizon: short | medium | long.
         Range conversions: 0-3y -> short, 3-9y -> medium, 9y+ -> long.
         If the document uses different bands, OMIT.
       accounts[N].regulatory_risk_rating: low | low_medium | medium |
         medium_high | high. OMIT for unselected.
  5. Risk score -> risk.household_score on the 1-5 canon scale ONLY.
     If the document uses a 1-10 scale, OMIT and surface the source
     phrase in evidence_quote on a behavioral_notes.* field.

Capitalization: emit lowercase enum values exactly as listed above.
The downstream engine adapter normalizes case; emitting "Growth" or
"GROWTH" is a defect.

Behavioral context (risk tolerance narrative, investment horizon
discussion, etc.) should land under behavioral_notes.* paths and is
NOT an engine input. Do not coerce narrative into the regulatory_*
fields.

Account numbers, SIN, and tax IDs: include the raw value; the
application hashes + redacts before display. Do not partially
redact in your output.
"""


def build_prompt(filename: str, classification: ClassificationResult, text: str) -> str:
    return compose_prompt(
        document_type="kyc",
        type_specific_body=_TYPE_BODY,
        classification=classification,
        filename=filename,
        text=text,
        prompt_version=PROMPT_VERSION,
    )
