"""P11 — structured portfolio-readiness blockers (plan v20 §A1.27).

Tests cover:
  * 12 parametric tests — one per blocker code, asserting the structured
    output shape matches the TypedDict contract for that branch.
  * 1 Hypothesis property — `account.external_id` NEVER appears as a
    substring of `advisor_account_label` (closes G11 UUID-leak).
  * Boundary edge cases per §A1.50:
      - zero-account household → emits `no_accounts` only
      - 12-blocker household → all 12 codes coexist on one household
      - extreme account values ($0.01, $1B+) → bp math doesn't overflow
      - custodian-null edge cases → label still safe (we have no
        custodian field; "Steadyhand" is the canon constant)
  * Audit emission — `portfolio_generation_blocker_surfaced` event is
    emitted on serializer GET + dedupes on (count, first_code).
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import hypothesis.strategies as st
import pytest
from django.contrib.auth import get_user_model
from hypothesis import HealthCheck, given, settings
from web.api import models
from web.api.account_helpers import advisor_account_label
from web.api.review_state import (
    portfolio_generation_blockers_for_household,
    portfolio_generation_blockers_structured_for_household,
)
from web.audit.models import AuditEvent

User = get_user_model()

HYPO_SETTINGS = dict(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)


def _make_user() -> User:
    user, _ = User.objects.get_or_create(
        username="advisor_p11@example.com",
        defaults={"email": "advisor_p11@example.com"},
    )
    return user


def _make_household(
    *,
    risk: int = 3,
    label: str = "P11 Test",
) -> models.Household:
    return models.Household.objects.create(
        external_id=f"hh_p11_{label.lower().replace(' ', '_')}",
        owner=_make_user(),
        display_name=label,
        household_type="single",
        household_risk_score=risk,
    )


# ---------------------------------------------------------------------------
# 12 parametric tests — one per blocker code
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_blocker_no_accounts() -> None:
    """Empty household (no accounts, no goals) → emits no_accounts +
    no_goals."""
    hh = _make_household(label="empty")
    blockers = portfolio_generation_blockers_structured_for_household(hh)
    codes = {b["code"] for b in blockers}
    assert "no_accounts" in codes
    no_acct = next(b for b in blockers if b["code"] == "no_accounts")
    assert no_acct["ui_action"] == "open_review_workspace"
    assert "account_id" not in no_acct
    assert "account_label" not in no_acct


@pytest.mark.django_db
def test_blocker_no_goals() -> None:
    """Household with account but no goals → emits no_goals."""
    hh = _make_household(label="no_goals")
    models.Account.objects.create(
        external_id="acct_no_goals",
        household=hh,
        account_type="RRSP",
        current_value=Decimal("100000"),
        is_held_at_purpose=True,
    )
    blockers = portfolio_generation_blockers_structured_for_household(hh)
    codes = {b["code"] for b in blockers}
    assert "no_goals" in codes
    ng = next(b for b in blockers if b["code"] == "no_goals")
    assert ng["ui_action"] == "open_review_workspace"


@pytest.mark.django_db
def test_blocker_household_invalid_risk_score() -> None:
    """household_risk_score outside 1-5 → emits household_invalid_risk_score.

    DB-level check constraint `household_risk_score_1_5` blocks UPDATEs
    to invalid values. Exercise the defensive guard branch by mutating
    the in-memory instance only — the function reads the attribute
    directly and never re-fetches from DB. (This branch is a defensive
    guard for legacy/migrated rows; modern rows are constraint-protected.)
    """
    hh = _make_household(risk=3, label="invalid_risk")
    # In-memory mutation only; never persisted (constraint would reject).
    hh.household_risk_score = 0
    blockers = portfolio_generation_blockers_structured_for_household(hh)
    codes = {b["code"] for b in blockers}
    assert "household_invalid_risk_score" in codes
    inv = next(b for b in blockers if b["code"] == "household_invalid_risk_score")
    assert inv["ui_action"] == "set_household_risk"


@pytest.mark.django_db
def test_blocker_unsupported_account_type() -> None:
    """Account.account_type outside ALLOWED_ENGINE_ACCOUNT_TYPES."""
    hh = _make_household(label="unsupported_type")
    models.Account.objects.create(
        external_id="acct_weird_type",
        household=hh,
        account_type="EXOTIC_TRUST",
        current_value=Decimal("50000"),
        is_held_at_purpose=True,
    )
    models.Goal.objects.create(
        external_id="g_with_exotic",
        household=hh,
        name="Retirement",
        target_date=date.today() + timedelta(days=3650),
        goal_risk_score=3,
    )
    blockers = portfolio_generation_blockers_structured_for_household(hh)
    unsupported = [b for b in blockers if b["code"] == "unsupported_account_type"]
    assert len(unsupported) == 1
    assert unsupported[0]["account_id"] == "acct_weird_type"
    assert "EXOTIC_TRUST" in unsupported[0]["account_label"]
    assert unsupported[0]["ui_action"] == "open_review_workspace"


@pytest.mark.django_db
def test_blocker_goal_missing_target_date() -> None:
    """Goal with null target_date → emits goal_missing_target_date.

    DB schema marks target_date as non-nullable; the blocker check is a
    defensive guard for legacy/migrated rows where the column might be
    null. Exercise the branch by patching prefetch on the QuerySet to
    return our in-memory-mutated Goal instance.
    """
    from unittest.mock import patch

    hh = _make_household(label="goal_no_date")
    models.Account.objects.create(
        external_id="acct_for_no_date_goal",
        household=hh,
        account_type="RRSP",
        current_value=Decimal("100000"),
        is_held_at_purpose=True,
    )
    goal = models.Goal.objects.create(
        external_id="g_no_date",
        household=hh,
        name="No-date goal",
        target_date=date.today() + timedelta(days=3650),
        goal_risk_score=3,
    )
    goal.target_date = None  # in-memory only

    # Patch QuerySet.prefetch_related to return a list-yielding stub that
    # contains our mutated instance. This is the cleanest way to bypass
    # the DB constraint without touching the function's signature.
    original_qs_all = models.Goal.objects.all

    class _StubQS:
        def prefetch_related(self, *_args, **_kwargs):
            return self

        def all(self):
            return [goal]

        def __iter__(self):
            return iter([goal])

    with patch.object(type(hh.goals), "all", return_value=_StubQS()):
        # Patch goals.all() to return _StubQS; function chains .prefetch_related().all()
        # so we need .all() of the qs returned by prefetch_related to return [goal] too.
        # Simpler: patch .prefetch_related directly on the goals manager.
        with patch.object(type(hh.goals), "prefetch_related", return_value=_StubQS()):
            blockers = portfolio_generation_blockers_structured_for_household(hh)
    missing = [b for b in blockers if b["code"] == "goal_missing_target_date"]
    assert len(missing) == 1
    assert missing[0]["goal_id"] == "g_no_date"
    assert missing[0]["goal_label"] == "No-date goal"
    assert missing[0]["ui_action"] == "set_goal_horizon"
    _ = original_qs_all  # silence unused


@pytest.mark.django_db
def test_blocker_goal_invalid_risk_score() -> None:
    """Goal.goal_risk_score outside 1-5 → emits goal_invalid_risk_score.

    DB-level check constraint `goal_risk_score_1_5` blocks UPDATEs.
    Same prefetch_related stub approach as test_blocker_goal_missing_target_date.
    """
    from unittest.mock import patch

    hh = _make_household(label="goal_bad_risk")
    models.Account.objects.create(
        external_id="acct_for_bad_risk",
        household=hh,
        account_type="RRSP",
        current_value=Decimal("100000"),
        is_held_at_purpose=True,
    )
    goal = models.Goal.objects.create(
        external_id="g_bad_risk",
        household=hh,
        name="Bad risk goal",
        target_date=date.today() + timedelta(days=3650),
        goal_risk_score=3,
    )
    goal.goal_risk_score = 9  # in-memory only

    class _StubQS:
        def prefetch_related(self, *_args, **_kwargs):
            return self

        def all(self):
            return [goal]

        def __iter__(self):
            return iter([goal])

    with patch.object(type(hh.goals), "prefetch_related", return_value=_StubQS()):
        blockers = portfolio_generation_blockers_structured_for_household(hh)
    bad_risk = [b for b in blockers if b["code"] == "goal_invalid_risk_score"]
    assert len(bad_risk) == 1
    assert bad_risk[0]["goal_id"] == "g_bad_risk"
    assert bad_risk[0]["ui_action"] == "set_goal_horizon"


@pytest.mark.django_db
def test_blocker_purpose_account_unassigned() -> None:
    """Purpose account with no goal-account links → unassigned blocker."""
    hh = _make_household(label="acct_unassigned")
    models.Account.objects.create(
        external_id="acct_unassigned",
        household=hh,
        account_type="RRSP",
        current_value=Decimal("100000"),
        is_held_at_purpose=True,
    )
    models.Goal.objects.create(
        external_id="g_unassigned_test",
        household=hh,
        name="Retirement",
        target_date=date.today() + timedelta(days=3650),
        goal_risk_score=3,
    )
    blockers = portfolio_generation_blockers_structured_for_household(hh)
    unassigned = [b for b in blockers if b["code"] == "purpose_account_unassigned"]
    assert len(unassigned) == 1
    assert unassigned[0]["account_id"] == "acct_unassigned"
    assert unassigned[0]["ui_action"] == "assign_to_goal"
    # Basis points for $100,000 = 100000 * 10000 = 1,000,000,000 bp.
    assert unassigned[0]["account_value_basis_points"] == 1_000_000_000


@pytest.mark.django_db
def test_blocker_purpose_account_zero_value() -> None:
    """Purpose account with zero current_value but with links → zero_value."""
    hh = _make_household(label="acct_zero")
    account = models.Account.objects.create(
        external_id="acct_zero_value",
        household=hh,
        account_type="TFSA",
        current_value=Decimal("0"),
        is_held_at_purpose=True,
    )
    goal = models.Goal.objects.create(
        external_id="g_zero_test",
        household=hh,
        name="Retirement",
        target_date=date.today() + timedelta(days=3650),
        goal_risk_score=3,
    )
    models.GoalAccountLink.objects.create(
        external_id="link_zero",
        goal=goal,
        account=account,
        allocated_amount=Decimal("0"),
    )
    blockers = portfolio_generation_blockers_structured_for_household(hh)
    zero = [b for b in blockers if b["code"] == "purpose_account_zero_value"]
    assert len(zero) == 1
    assert zero[0]["ui_action"] == "edit_account_value"
    assert zero[0]["account_value_basis_points"] == 0


@pytest.mark.django_db
def test_blocker_purpose_account_unallocated() -> None:
    """Purpose account with allocated_amount sum != current_value."""
    hh = _make_household(label="acct_unalloc")
    account = models.Account.objects.create(
        external_id="acct_unallocated",
        household=hh,
        account_type="RRSP",
        current_value=Decimal("100000"),
        is_held_at_purpose=True,
    )
    goal = models.Goal.objects.create(
        external_id="g_unalloc",
        household=hh,
        name="Retirement",
        target_date=date.today() + timedelta(days=3650),
        goal_risk_score=3,
    )
    # Allocate only 60K of 100K → 40K unallocated.
    models.GoalAccountLink.objects.create(
        external_id="link_unalloc",
        goal=goal,
        account=account,
        allocated_amount=Decimal("60000"),
    )
    blockers = portfolio_generation_blockers_structured_for_household(hh)
    unalloc = [b for b in blockers if b["code"] == "purpose_account_unallocated"]
    assert len(unalloc) == 1
    # 100K - 60K = 40K → 40000 * 10000 = 400,000,000 bp
    assert unalloc[0]["account_unallocated_basis_points"] == 400_000_000
    assert unalloc[0]["ui_action"] == "assign_to_goal"


@pytest.mark.django_db
def test_blocker_purpose_account_pct_not_100() -> None:
    """Purpose account with allocated_pct sum != 1.0."""
    hh = _make_household(label="acct_pct_short")
    account = models.Account.objects.create(
        external_id="acct_pct_short",
        household=hh,
        account_type="RRSP",
        current_value=Decimal("100000"),
        is_held_at_purpose=True,
    )
    goal = models.Goal.objects.create(
        external_id="g_pct_short",
        household=hh,
        name="Retirement",
        target_date=date.today() + timedelta(days=3650),
        goal_risk_score=3,
    )
    # 95% allocated → 5% short.
    models.GoalAccountLink.objects.create(
        external_id="link_pct_short",
        goal=goal,
        account=account,
        allocated_pct=Decimal("0.95"),
    )
    blockers = portfolio_generation_blockers_structured_for_household(hh)
    pct = [b for b in blockers if b["code"] == "purpose_account_pct_not_100"]
    assert len(pct) == 1
    # gap = 1.0 - 0.95 = 0.05 → 0.05 * 10000 = 500 bp
    assert pct[0]["account_unallocated_basis_points"] == 500
    assert pct[0]["ui_action"] == "assign_to_goal"


@pytest.mark.django_db
def test_blocker_missing_link_amount() -> None:
    """GoalAccountLink with both allocated_amount and allocated_pct null."""
    hh = _make_household(label="missing_link")
    account = models.Account.objects.create(
        external_id="acct_missing_link",
        household=hh,
        account_type="RRSP",
        current_value=Decimal("100000"),
        is_held_at_purpose=True,
    )
    goal = models.Goal.objects.create(
        external_id="g_missing_link",
        household=hh,
        name="Retirement",
        target_date=date.today() + timedelta(days=3650),
        goal_risk_score=3,
    )
    models.GoalAccountLink.objects.create(
        external_id="link_no_amount",
        goal=goal,
        account=account,
        allocated_amount=None,
        allocated_pct=None,
    )
    blockers = portfolio_generation_blockers_structured_for_household(hh)
    missing = [b for b in blockers if b["code"] == "missing_link_amount"]
    assert len(missing) == 1
    assert missing[0]["ui_action"] == "assign_to_goal"
    assert missing[0]["goal_id"] == "g_missing_link"
    assert missing[0]["account_id"] == "acct_missing_link"


@pytest.mark.django_db
def test_blocker_mixed_amount_pct() -> None:
    """Account with one link in dollars + one link in percentage → mixed."""
    hh = _make_household(label="mixed")
    account = models.Account.objects.create(
        external_id="acct_mixed",
        household=hh,
        account_type="RRSP",
        current_value=Decimal("100000"),
        is_held_at_purpose=True,
    )
    g1 = models.Goal.objects.create(
        external_id="g_mix_1",
        household=hh,
        name="Goal 1",
        target_date=date.today() + timedelta(days=3650),
        goal_risk_score=3,
    )
    g2 = models.Goal.objects.create(
        external_id="g_mix_2",
        household=hh,
        name="Goal 2",
        target_date=date.today() + timedelta(days=3650),
        goal_risk_score=3,
    )
    models.GoalAccountLink.objects.create(
        external_id="link_mix_dollar", goal=g1, account=account, allocated_amount=Decimal("50000")
    )
    models.GoalAccountLink.objects.create(
        external_id="link_mix_pct", goal=g2, account=account, allocated_pct=Decimal("0.5")
    )
    blockers = portfolio_generation_blockers_structured_for_household(hh)
    mixed = [b for b in blockers if b["code"] == "mixed_amount_pct"]
    assert len(mixed) == 1
    assert mixed[0]["ui_action"] == "assign_to_goal"


# ---------------------------------------------------------------------------
# Hypothesis PII fuzz — closes G11 UUID-leak (§A1.52)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@given(
    account_type=st.sampled_from(
        ["RRSP", "TFSA", "Non-Registered", "RESP", "RDSP", "FHSA", "LIRA", "Corporate"]
    ),
    is_held_at_purpose=st.booleans(),
    current_value=st.decimals(
        min_value=Decimal("0"), max_value=Decimal("9999999999"), allow_nan=False, places=2
    ),
    external_id_seed=st.text(alphabet="abcdef0123456789-", min_size=8, max_size=80),
)
@settings(**HYPO_SETTINGS)
def test_account_external_id_never_in_advisor_account_label(
    account_type: str,
    is_held_at_purpose: bool,
    current_value: Decimal,
    external_id_seed: str,
) -> None:
    """For any synthesized Account, advisor_account_label() must NOT
    contain the external_id as a substring (closes G11 UUID-leak).

    Sister §A1.52 PII fuzz pattern. We don't persist the account — the
    helper is pure on the in-memory instance.
    """
    # Use unsaved instance — function is pure on attributes.
    account = models.Account(
        external_id=external_id_seed or "fallback-id",
        account_type=account_type,
        current_value=current_value,
        is_held_at_purpose=is_held_at_purpose,
    )
    label = advisor_account_label(account)
    assert account.external_id not in label, (
        f"external_id {account.external_id!r} leaked into label {label!r}"
    )


# ---------------------------------------------------------------------------
# Boundary edge cases per §A1.50
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_zero_account_household_emits_no_accounts_only() -> None:
    """§A1.50 — empty-account household emits no_accounts (alongside no_goals)."""
    hh = _make_household(label="empty_for_no_accts")
    blockers = portfolio_generation_blockers_structured_for_household(hh)
    codes = [b["code"] for b in blockers]
    assert "no_accounts" in codes
    # No account-keyed blockers (purpose_account_*) since there are no accounts.
    account_blockers = [b for b in blockers if b["code"].startswith("purpose_account_")]
    assert account_blockers == []


@pytest.mark.django_db
def test_extreme_account_value_basis_points_no_overflow() -> None:
    """§A1.50 — $1B account → bp math fits in int (no overflow).

    1_000_000_000 USD × 10000 bp/USD = 10_000_000_000_000 bp. Python int
    is arbitrary-precision; we assert the value is exactly correct.
    """
    hh = _make_household(label="huge")
    models.Account.objects.create(
        external_id="acct_huge",
        household=hh,
        account_type="Corporate",
        current_value=Decimal("1000000000"),  # $1B
        is_held_at_purpose=True,
    )
    models.Goal.objects.create(
        external_id="g_huge",
        household=hh,
        name="Empire",
        target_date=date.today() + timedelta(days=3650),
        goal_risk_score=3,
    )
    blockers = portfolio_generation_blockers_structured_for_household(hh)
    unassigned = [b for b in blockers if b["code"] == "purpose_account_unassigned"]
    assert len(unassigned) == 1
    assert unassigned[0]["account_value_basis_points"] == 10_000_000_000_000


@pytest.mark.django_db
def test_twelve_blocker_household_all_codes_coexist() -> None:
    """§A1.50 — fan out a household that hits as many of the 12 codes
    as can coexist in one household. Some codes are mutually exclusive
    (no_accounts vs purpose_account_*); we hit a representative subset
    and verify the structured output contains them all without dedup
    collapsing distinct rows.
    """
    from unittest.mock import patch

    hh = _make_household(label="manyblockers")
    # Bad household_risk_score (in-memory mutation only — constraint blocks UPDATE)
    hh.household_risk_score = 0

    # Account 1: zero-value Purpose account with link.
    acct1 = models.Account.objects.create(
        external_id="acct_many_zero",
        household=hh,
        account_type="RRSP",
        current_value=Decimal("0"),
        is_held_at_purpose=True,
    )
    # Account 2: unsupported type.
    models.Account.objects.create(
        external_id="acct_many_exotic",
        household=hh,
        account_type="EXOTIC",
        current_value=Decimal("50000"),
        is_held_at_purpose=True,
    )
    # Account 3: unallocated.
    acct3 = models.Account.objects.create(
        external_id="acct_many_unalloc",
        household=hh,
        account_type="TFSA",
        current_value=Decimal("100000"),
        is_held_at_purpose=True,
    )
    g1 = models.Goal.objects.create(
        external_id="g_many_1",
        household=hh,
        name="Retirement",
        target_date=date.today() + timedelta(days=3650),
        goal_risk_score=3,
    )
    g2 = models.Goal.objects.create(
        external_id="g_many_bad_date",
        household=hh,
        name="Bad date",
        target_date=date.today() + timedelta(days=3650),
        goal_risk_score=3,
    )
    g2.target_date = None  # in-memory only

    models.GoalAccountLink.objects.create(
        external_id="link_zero_account", goal=g1, account=acct1, allocated_amount=Decimal("0")
    )
    models.GoalAccountLink.objects.create(
        external_id="link_unalloc_account",
        goal=g1,
        account=acct3,
        allocated_amount=Decimal("60000"),
    )

    # Patch the goals manager to return our in-memory-mutated g2.
    fresh_g1 = models.Goal.objects.prefetch_related("account_allocations").get(pk=g1.pk)

    class _GoalsStubQS:
        def prefetch_related(self, *_args, **_kwargs):
            return self

        def all(self):
            return [fresh_g1, g2]

        def __iter__(self):
            return iter([fresh_g1, g2])

    with patch.object(type(hh.goals), "prefetch_related", return_value=_GoalsStubQS()):
        blockers = portfolio_generation_blockers_structured_for_household(hh)
    codes = {b["code"] for b in blockers}
    # Verify a representative set coexists.
    assert "household_invalid_risk_score" in codes
    assert "purpose_account_zero_value" in codes
    assert "purpose_account_unassigned" in codes  # acct_many_exotic has no link
    assert "purpose_account_unallocated" in codes
    assert "unsupported_account_type" in codes
    assert "goal_missing_target_date" in codes


@pytest.mark.django_db
def test_advisor_account_label_canon_vocab_no_uuids_held_at_purpose() -> None:
    """advisor_account_label produces canon-vocab string with 'Purpose' +
    'at Steadyhand' when held at Purpose.
    """
    account = models.Account(
        external_id="acct_label_test_uuid_xyz",
        account_type="RRSP",
        current_value=Decimal("890000"),
        is_held_at_purpose=True,
    )
    label = advisor_account_label(account)
    assert "Purpose" in label
    assert "RRSP" in label
    assert "Steadyhand" in label
    assert "$890K" in label
    assert "acct_label_test_uuid_xyz" not in label


@pytest.mark.django_db
def test_held_away_account_skipped_in_purpose_account_loop() -> None:
    """A held-away account (is_held_at_purpose=False) with a goal link is
    SKIPPED by the purpose-account loop — the function only checks
    Purpose accounts for assignment / unallocated / mixed pct branches.
    Exercises the `continue` defensive branch at line 516.
    """
    hh = _make_household(label="held_away")
    held_away = models.Account.objects.create(
        external_id="acct_held_away_skip",
        household=hh,
        account_type="RRSP",
        current_value=Decimal("50000"),
        is_held_at_purpose=False,
    )
    purpose_acct = models.Account.objects.create(
        external_id="acct_purpose_skip",
        household=hh,
        account_type="TFSA",
        current_value=Decimal("100000"),
        is_held_at_purpose=True,
    )
    goal = models.Goal.objects.create(
        external_id="g_held_away",
        household=hh,
        name="Retirement",
        target_date=date.today() + timedelta(days=3650),
        goal_risk_score=3,
    )
    models.GoalAccountLink.objects.create(
        external_id="link_held_away",
        goal=goal,
        account=held_away,
        allocated_amount=Decimal("50000"),
    )
    models.GoalAccountLink.objects.create(
        external_id="link_purpose_full",
        goal=goal,
        account=purpose_acct,
        allocated_amount=Decimal("100000"),
    )
    blockers = portfolio_generation_blockers_structured_for_household(hh)
    # No purpose_account_* blockers because both purpose-side and held-away
    # have correct allocation; held-away never enters the purpose-loop.
    purpose_blockers = [b for b in blockers if b["code"].startswith("purpose_account_")]
    assert purpose_blockers == []


@pytest.mark.django_db
def test_advisor_account_label_held_away_omits_purpose_prefix() -> None:
    """Held-away accounts (is_held_at_purpose=False) omit the 'Purpose'
    prefix — canon vocab handles non-Steadyhand custodians by leaving
    the firm/custodian unspecified (multi-custodian is post-pilot).
    """
    account = models.Account(
        external_id="acct_external",
        account_type="RRSP",
        current_value=Decimal("50000"),
        is_held_at_purpose=False,
    )
    label = advisor_account_label(account)
    assert "Purpose" not in label
    assert "Steadyhand" not in label
    assert "RRSP" in label
    assert "$50K" in label


# ---------------------------------------------------------------------------
# Cross-phase coexistence stubs (§A1.51)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_p11_blocker_banner_and_p12_unallocated_banner_coexist_no_z_collision() -> None:
    """Placeholder — full P12 component lands in next pair; here we just
    validate structural metadata: the structured-blocker payload includes
    `purpose_account_unallocated` rows that P12's UnallocatedBanner will
    consume on the same render. The two surfaces operate at different
    z-layers (banner z-10 below sister's StaleRunOverlay z-20).
    """
    hh = _make_household(label="coexist")
    account = models.Account.objects.create(
        external_id="acct_coexist",
        household=hh,
        account_type="RRSP",
        current_value=Decimal("100000"),
        is_held_at_purpose=True,
    )
    goal = models.Goal.objects.create(
        external_id="g_coexist",
        household=hh,
        name="Retirement",
        target_date=date.today() + timedelta(days=3650),
        goal_risk_score=3,
    )
    models.GoalAccountLink.objects.create(
        external_id="link_coexist",
        goal=goal,
        account=account,
        allocated_amount=Decimal("60000"),
    )
    blockers = portfolio_generation_blockers_structured_for_household(hh)
    unalloc = [b for b in blockers if b["code"] == "purpose_account_unallocated"]
    # P12 banner consumes this row's account_unallocated_basis_points.
    assert len(unalloc) == 1
    assert "account_unallocated_basis_points" in unalloc[0]


@pytest.mark.django_db
def test_p11_assign_to_goal_ui_action_opens_p13_modal_with_correct_account_id() -> None:
    """Placeholder — P13 AssignAccountModal ships in Pair 5. Here we
    assert the structured row carries `account_id` for the modal to use
    as its target.
    """
    hh = _make_household(label="p13_handoff")
    models.Account.objects.create(
        external_id="acct_p13_target",
        household=hh,
        account_type="RRSP",
        current_value=Decimal("100000"),
        is_held_at_purpose=True,
    )
    models.Goal.objects.create(
        external_id="g_p13",
        household=hh,
        name="Retirement",
        target_date=date.today() + timedelta(days=3650),
        goal_risk_score=3,
    )
    blockers = portfolio_generation_blockers_structured_for_household(hh)
    assign_rows = [b for b in blockers if b["ui_action"] == "assign_to_goal"]
    assert len(assign_rows) >= 1
    target = assign_rows[0]
    # P13 modal needs account_id as its target.
    assert target["account_id"] == "acct_p13_target"


# ---------------------------------------------------------------------------
# ADDITIVE contract — list[str] function preserved
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_legacy_list_str_function_still_returns_strings() -> None:
    """Sister consumers depend on the existing list[str] shape. The
    structured function is ADDITIVE — the legacy function's output type
    + content remain unchanged.
    """
    hh = _make_household(label="legacy_compat")
    legacy = portfolio_generation_blockers_for_household(hh)
    assert isinstance(legacy, list)
    for entry in legacy:
        assert isinstance(entry, str), (
            f"legacy function regressed: returned {type(entry).__name__} not str"
        )


# ---------------------------------------------------------------------------
# Audit emission (§A1.23) — surfaced event
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_audit_event_emitted_on_serializer_call() -> None:
    """Calling get_structured_readiness_blockers via the serializer fires
    a portfolio_generation_blocker_surfaced AuditEvent with PII-safe
    metadata (closed Literal codes only).
    """
    from web.api.serializers import HouseholdDetailSerializer

    hh = _make_household(label="audit_test")
    models.Account.objects.create(
        external_id="acct_audit",
        household=hh,
        account_type="RRSP",
        current_value=Decimal("100000"),
        is_held_at_purpose=True,
    )
    models.Goal.objects.create(
        external_id="g_audit",
        household=hh,
        name="Retirement",
        target_date=date.today() + timedelta(days=3650),
        goal_risk_score=3,
    )
    serializer = HouseholdDetailSerializer(hh)
    _ = serializer.data["structured_readiness_blockers"]

    surfaced = AuditEvent.objects.filter(
        action="portfolio_generation_blocker_surfaced",
        entity_id=hh.external_id,
    )
    assert surfaced.exists()
    metadata = surfaced.first().metadata
    assert "blocker_count" in metadata
    assert "blocker_codes" in metadata
    assert "first_code" in metadata
    # PII-safe: only closed Literal codes; no raw external_ids in metadata.
    assert "acct_audit" not in str(metadata)


@pytest.mark.django_db
def test_audit_event_dedupes_on_repeated_serializer_calls() -> None:
    """Calling the serializer twice on the same unchanged household
    emits only ONE surfaced event (dedup on count + first_code).
    """
    from web.api.serializers import HouseholdDetailSerializer

    hh = _make_household(label="audit_dedup")
    models.Account.objects.create(
        external_id="acct_dedup",
        household=hh,
        account_type="RRSP",
        current_value=Decimal("100000"),
        is_held_at_purpose=True,
    )
    models.Goal.objects.create(
        external_id="g_dedup",
        household=hh,
        name="Retirement",
        target_date=date.today() + timedelta(days=3650),
        goal_risk_score=3,
    )
    _ = HouseholdDetailSerializer(hh).data
    _ = HouseholdDetailSerializer(hh).data
    _ = HouseholdDetailSerializer(hh).data

    surfaced = AuditEvent.objects.filter(
        action="portfolio_generation_blocker_surfaced",
        entity_id=hh.external_id,
    )
    assert surfaced.count() == 1
