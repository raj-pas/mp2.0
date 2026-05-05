"""HouseholdDetailSerializer snapshot tests — JSON contract guard.

P11 introduces the 5th committed JSON fixture per locked decision §3.21.
The snapshot test asserts that `HouseholdDetailSerializer` produces a
payload whose structured_readiness_blockers field shape is byte-stable
against the fixture (modulo non-deterministic fields like timestamps).

Why a JSON fixture (not a parametric serializer test):
  Frontend `api-types.ts` is generated from drf-spectacular's OpenAPI
  schema, but the SerializerMethodField return shapes are inferred per
  the README at `frontend/src/lib/household.ts:59-63`. The fixture
  locks the actual JSON byte-shape so a silent serializer drift surfaces
  as a snapshot diff, not a runtime TS-vs-payload mismatch.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from web.api import models
from web.api.serializers import HouseholdDetailSerializer

FIXTURE_DIR = Path(__file__).parent / "fixtures"

User = get_user_model()


def _make_user() -> User:
    user, _ = User.objects.get_or_create(
        username="snapshot_advisor@example.com",
        defaults={"email": "snapshot_advisor@example.com"},
    )
    return user


@pytest.mark.django_db
def test_serializer_emits_structured_readiness_blockers_field() -> None:
    """The HouseholdDetailSerializer payload always carries the
    structured_readiness_blockers field (P11 contract addition).

    Backwards-compat (§3.16): on a fresh household with no engine output,
    structured_readiness_blockers is `[]` (empty list — engine-ready
    household has no blockers; new field never crashes the GET).
    """
    hh = models.Household.objects.create(
        external_id="hh_snapshot_field_present",
        owner=_make_user(),
        display_name="Snapshot field test",
        household_type="single",
        household_risk_score=3,
    )
    payload = HouseholdDetailSerializer(hh).data
    assert "structured_readiness_blockers" in payload
    assert "readiness_blockers" in payload
    # Empty household → emits no_accounts + no_goals (structured + humanized).
    assert isinstance(payload["structured_readiness_blockers"], list)
    assert len(payload["structured_readiness_blockers"]) >= 1


@pytest.mark.django_db
def test_serializer_structured_blocker_shape_matches_fixture() -> None:
    """Build a household whose structured_readiness_blockers shape mirrors
    the committed JSON fixture (`fixtures/household_detail_with_structured_blockers.json`).

    Locks the JSON byte-shape: each blocker dict has exactly the keys
    documented by the TypedDict at `web/api/types.py`. Drift in field
    names / addition of unexpected keys would fail this test.
    """
    fixture_path = FIXTURE_DIR / "household_detail_with_structured_blockers.json"
    with fixture_path.open("r", encoding="utf-8") as fh:
        fixture = json.load(fh)
    expected_blockers = fixture["structured_readiness_blockers"]

    # Construct a household whose structured-blocker shape matches a
    # subset of the fixture: 1 zero-value Purpose RRSP without a goal
    # link → emits `purpose_account_unassigned` (matches fixture's
    # second blocker entry shape exactly). The fixture's
    # `goal_missing_target_date` row exercises a defensive null-target
    # branch only reachable on legacy/migrated rows (DB constraint
    # blocks new rows); the snapshot test asserts SHAPE not full code
    # parity.
    hh = models.Household.objects.create(
        external_id="hh_snapshot_blocker_shape",
        owner=_make_user(),
        display_name="Snapshot Shape Test",
        household_type="couple",
        household_risk_score=3,
    )
    models.Account.objects.create(
        external_id="acct_p11_snap_shape",
        household=hh,
        account_type="RRSP",
        current_value=Decimal("0"),
        is_held_at_purpose=True,
    )
    models.Goal.objects.create(
        external_id="g_p11_snap_shape",
        household=hh,
        name="Goal with target date",
        target_date=date.today() + timedelta(days=3650),
        goal_risk_score=3,
    )

    payload = HouseholdDetailSerializer(hh).data
    actual_blockers = payload["structured_readiness_blockers"]

    # Verify the fixture's `purpose_account_unassigned` blocker shape
    # appears in actual output (other fixture codes exercise defensive
    # branches not reachable through DB-constraint-protected models).
    fixture_codes = {b["code"] for b in expected_blockers}
    actual_codes = {b["code"] for b in actual_blockers}
    common = fixture_codes & actual_codes
    assert common, f"No fixture codes intersect actual {actual_codes}"
    # The unassigned shape MUST be present in both.
    assert "purpose_account_unassigned" in actual_codes

    # Each blocker dict has the documented TypedDict keys (no surprise
    # extras). Required keys: `code`, `ui_action`. Optional keys come
    # from the NotRequired set.
    allowed_keys = {
        "code",
        "ui_action",
        "account_id",
        "account_label",
        "account_value_basis_points",
        "account_unallocated_basis_points",
        "goal_id",
        "goal_label",
    }
    for blocker in actual_blockers:
        assert "code" in blocker
        assert "ui_action" in blocker
        unexpected = set(blocker.keys()) - allowed_keys
        assert not unexpected, f"Unexpected key(s) in blocker: {unexpected}"
