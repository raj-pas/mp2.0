"""Planning / spreadsheet extraction prompt module (Phase 4 tool-use).

Planning artifacts (retirement plans, cash-flow projections,
goal-funding workbooks, multi-year drawdown schedules) are typically
spreadsheet exports or richly-tabular PDFs. Extraction lifts each
named cell or row into a discrete fact. The historic failure mode
was Bedrock returning the entire workbook as a single markdown
table; this prompt explicitly forbids that shape.
"""

from __future__ import annotations

from extraction.prompts.base import compose_prompt
from extraction.schemas import ClassificationResult

PROMPT_VERSION = "planning_review_facts_v2_tooluse"


_TYPE_BODY = """\
This is a financial-planning artifact (retirement plan, cash-flow
projection, multi-year goal funding, drawdown schedule, or
spreadsheet export). Extract per-cell facts, not tables.

ABSOLUTE PROHIBITION: do NOT emit markdown tables, prose preambles,
JSON code fences, or any synthesized summary. Every fact must come
from a single named cell, row, or labeled value in the source. If
you find yourself writing a `|`-delimited row in any field, STOP.

Extraction priorities (highest first):
  1. Goal definitions -> goals[N].name + goals[N].priority +
     goals[N].time_horizon_years + goals[N].target_amount.
     For each named goal, emit one fact per attribute.
  2. Goal-account allocations -> goal_account_links[N].goal_name +
     goal_account_links[N].account_id_or_label +
     goal_account_links[N].allocated_amount. One fact per cell of
     the allocation matrix.
  3. Multi-year cash flow / drawdown projections -> emit each
     year's projected value as a SEPARATE fact:
       behavioral_notes.cash_flow.year_2027.income = 245000
       behavioral_notes.cash_flow.year_2027.outflow = 180000
     The advisor can re-classify these into goals or account
     drawdowns at review time; the engine does not consume them.
  4. Account-level current values from the planning summary ->
     accounts[N].current_value with derivation_method="extracted"
     ONLY IF the planning doc references a stated balance.
     If the planning doc references a balance from a prior
     statement, OMIT (advisor will reconcile against the actual
     statement).

Numeric discipline: dollar amounts are decimal numbers, never
strings. Years are integers. Percentages stay as decimals (0.06,
not "6%").

If the planning artifact uses scenario columns (Optimistic /
Expected / Pessimistic), emit each scenario as a separate fact path
under behavioral_notes.scenarios.<scenario_name>.<field>. Do NOT
collapse to a single value.

If a row carries an "as-of" date, emit asserted_at on that fact.
"""


def build_prompt(filename: str, classification: ClassificationResult, text: str) -> str:
    return compose_prompt(
        document_type="planning",
        type_specific_body=_TYPE_BODY,
        classification=classification,
        filename=filename,
        text=text,
        prompt_version=PROMPT_VERSION,
    )
