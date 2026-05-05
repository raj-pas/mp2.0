"""Public API TypedDict shapes for cross-tier (Python ↔ TS) contracts.

Per plan v20 §A1.27 + Round 14 #3 LOCKED:
  TypedDict at the DRF serializer boundary lets drf-spectacular emit a
  precise OpenAPI schema, which `npm run codegen` translates into the
  TypeScript shapes in `frontend/src/lib/api-types.ts`. This is the
  single source of truth for advisor-actionable blocker payloads — the
  hand-synchronized TS type in `frontend/src/lib/household.ts` mirrors
  the same field names + Literal codes.

Why TypedDict (not dataclass):
  - `dict[str, Any]` round-trips cleanly through DRF's renderer; no need
    for a Serializer class wrapping nested objects.
  - `NotRequired[...]` is the canonical way to model "this field is
    present only for blocker codes that target that entity" (e.g.,
    `account_id` is NOT meaningful on `no_accounts` / `no_goals` /
    `household_invalid_risk_score`).
  - `Literal[...]` on `code` and `ui_action` lets mypy + the OpenAPI
    schema enforce the closed set of advisor-facing strings (i18n
    keys + frontend `<button>` action mapping rely on this exhaustivity).

Why basis points (not Decimal):
  - Canon §6.3a forbids raw Decimal in audit metadata.
  - Basis points (1 bp = 0.0001 = 0.01%) preserve full $0.01 precision
    for `current_value` up to ~$92T without floats; advisor-facing
    formatting layer multiplies back to dollars.

Closes G11 (UUID-leak gap): the existing
`portfolio_generation_blockers_for_household` returns list[str] with
raw `account.external_id` UUIDs interpolated. The structured shape
NEVER exposes raw external_ids — `account_label` carries the
advisor-friendly humanized form ("Purpose RRSP at Steadyhand
($890K)") built by `account_helpers.advisor_account_label`.
"""

from __future__ import annotations

from typing import Literal, NotRequired, TypedDict


class PortfolioGenerationBlocker(TypedDict):
    """A single advisor-actionable reason portfolio generation cannot run.

    The 12 codes cover every branch in
    `portfolio_generation_blockers_for_household`:
      household-level    → `household_invalid_risk_score`,
                           `no_accounts`, `no_goals`
      account-level      → `purpose_account_unassigned`,
                           `purpose_account_unallocated`,
                           `purpose_account_zero_value`,
                           `purpose_account_pct_not_100`,
                           `unsupported_account_type`,
                           `missing_link_amount`,
                           `mixed_amount_pct`
      goal-level         → `goal_missing_target_date`,
                           `goal_invalid_risk_score`

    The 5 ui_actions map to advisor-friendly fix CTAs (Round 9 #11
    LOCKED — every blocker has a fix CTA, no bypass):
      assign_to_goal       → opens P13 AssignAccountModal (next pair)
      edit_account_value   → opens AccountRoute with current_value field
                             auto-focused
      set_goal_horizon     → opens GoalRoute with target_date editor
      set_household_risk   → opens HouseholdRoute risk selector
      open_review_workspace→ navigates to Review (final fallback for
                             extraction/conflict-resolution gaps)
    """

    code: Literal[
        "purpose_account_unassigned",
        "purpose_account_unallocated",
        "purpose_account_zero_value",
        "purpose_account_pct_not_100",
        "goal_missing_target_date",
        "goal_invalid_risk_score",
        "household_invalid_risk_score",
        "no_accounts",
        "no_goals",
        "unsupported_account_type",
        "missing_link_amount",
        "mixed_amount_pct",
    ]
    account_id: NotRequired[str]
    account_label: NotRequired[str]
    account_value_basis_points: NotRequired[int]
    account_unallocated_basis_points: NotRequired[int]
    goal_id: NotRequired[str]
    goal_label: NotRequired[str]
    ui_action: Literal[
        "assign_to_goal",
        "edit_account_value",
        "set_goal_horizon",
        "set_household_risk",
        "open_review_workspace",
    ]
