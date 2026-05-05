"""Account label helpers — canon-vocab, PII-safe display names.

Per plan v20 §A1.27 + canon §11.8.3:
  Advisor-facing strings NEVER include `account.external_id` (the
  internal UUID is not meaningful to a human reader and, on real-PII
  households, can be cross-referenced to a CRM record). The serializer-
  layer humanization at `serializers.py:188-229` substitutes UUIDs
  with `<account_type> (<8-char prefix>)`; this helper produces a
  richer canon-vocab label for the structured-blocker payload.

Format: ``Purpose <type> at Steadyhand (<compact_value>)``
        e.g., ``Purpose RRSP at Steadyhand ($890K)``

  - "Purpose" prefix when `is_held_at_purpose=True`; omitted for
    held-away accounts (engine ignores those, but a structured blocker
    on `unsupported_account_type` may still surface them).
  - "at Steadyhand" reflects the canon firm/custodian (single-tenant
    pilot scope; multi-custodian is post-pilot).
  - Compact dollar value gives the advisor a quick scale anchor;
    omitted when `current_value` is zero/null (which is itself the
    blocker condition for `purpose_account_zero_value`).
"""

from __future__ import annotations

from decimal import Decimal

from web.api import models


def _compact_dollars(value: Decimal | None) -> str:
    """Format a dollar value compactly for display labels.

    Examples:
        Decimal("890000")  -> "$890K"
        Decimal("1500000") -> "$1.5M"
        Decimal("250")     -> "$250"
        None / 0           -> "" (caller decides whether to omit)
    """
    if value is None:
        return ""
    amount = float(value)
    if amount == 0:
        return ""
    if abs(amount) >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    if abs(amount) >= 1_000:
        return f"${amount / 1_000:.0f}K"
    return f"${amount:.0f}"


def advisor_account_label(account: models.Account) -> str:
    """Produce a canon-vocab display label for an Account.

    PII-safe by construction: NEVER references `account.external_id`,
    `owner_person.external_id`, or any free-text field that could carry
    extracted client content. Inputs are limited to:
      - `account_type` (enum: RRSP / TFSA / Non-Registered / etc.)
      - `is_held_at_purpose` (bool)
      - `current_value` (numeric)

    Caller (serializer / blocker builder) is responsible for the
    Hypothesis-fuzz invariant that no external_id substring leaks
    through (test_account_external_id_never_in_advisor_account_label).
    """
    account_type = account.account_type or "Account"
    held_at_purpose = bool(account.is_held_at_purpose)
    compact_value = _compact_dollars(account.current_value)

    parts: list[str] = []
    if held_at_purpose:
        parts.append("Purpose")
    parts.append(account_type)
    if held_at_purpose:
        parts.append("at Steadyhand")
    if compact_value:
        parts.append(f"({compact_value})")

    return " ".join(parts)
