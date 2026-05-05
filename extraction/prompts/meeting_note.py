"""Meeting-note extraction prompt module (Phase 4 tool-use).

Meeting notes are advisor narratives. They contain a small core of
explicit facts ("client retired in 2023", "household income $250k")
embedded in a much larger volume of speculative / aspirational
language. The bulk of the value belongs under behavioral_notes.* and
is NOT an engine input. Only explicit facts that match canonical
field paths leave the advisor-narrative scope.
"""

from __future__ import annotations

from extraction.prompts.base import compose_prompt
from extraction.schemas import ClassificationResult

PROMPT_VERSION = "meeting_note_review_facts_v4_tooluse_entity_aligned"


_TYPE_BODY = """\
This is an advisor meeting note / call summary. Most of the content
is narrative; only EXPLICIT facts should land on canonical field
paths.

Extraction priorities (highest first):
  1. Explicit named values -> e.g. "Sarah is 58", "joint household
     income is $245,000". Emit on canonical paths with confidence
     "medium" (advisor narrative is single-sourced).
  2. Stated dates -> use as asserted_at on the corresponding fact.
     Meeting date itself: emit as asserted_at on each fact extracted
     from the note. If the meeting date is unstated, leave asserted_at
     null.
  3. Aspirational / speculative language -> emit under
     behavioral_notes.<topic> with confidence "low". DO NOT promote
     to canonical fields.

Forbidden inversions in meeting notes:
  - "Client wants to retire by 65" -> emit
     behavioral_notes.retirement_aspiration with the verbatim quote.
     OMIT goals[N].time_horizon_years; the goal hasn't been formalized.
  - "Considering a $1M target for retirement" -> emit
     behavioral_notes.retirement_aspiration with the quote.
     OMIT goals[N].target_amount; the target is exploratory.
  - "Risk tolerance feels around 3 out of 5" -> emit
     behavioral_notes.risk_self_assessment with the quote.
     OMIT risk.household_score; that's a regulatory-disclosure field.
  - "Probably looking at a 5-7 year horizon" -> emit
     behavioral_notes.horizon_discussion with the quote.
     Do not collapse the range to a single time_horizon_years value.

Confidence:
  - High confidence is rare in meeting notes. Reserve it for
    advisor-recorded values that are clearly factual ("client age
    is 58 per ID review").
  - Default to medium for explicit advisor statements.
  - Use low for any aspirational / hedged / speculative language
    ("might", "considering", "thinking about", "around", "maybe",
    "could be", "perhaps").

Behavioral notes (free-form):
  behavioral_notes.<topic> can be ANY string; the runtime stores the
  full quote and exposes it to the advisor in review. Do not try to
  fit narrative into canonical paths -- behavioral_notes is the
  intended landing zone for narrative.
"""


def build_prompt(filename: str, classification: ClassificationResult, text: str) -> str:
    return compose_prompt(
        document_type="meeting_note",
        type_specific_body=_TYPE_BODY,
        classification=classification,
        filename=filename,
        text=text,
        prompt_version=PROMPT_VERSION,
    )
