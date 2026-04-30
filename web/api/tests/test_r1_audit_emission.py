"""Centralized audit-event emission regression suite (locked decision #37).

For each state-changing R1 endpoint, asserts exactly one AuditEvent of
the expected ``action`` is created. Catches accidental dropped audit
writes — a canon §9.4.6 ("second most important rule") violation that
individual endpoint tests might miss if they don't explicitly check
audit emission.

The Phase R1 audit event taxonomy (matches wizard_views.py):
- ``household_wizard_committed``
- ``realignment_applied``
- ``household_snapshot_created`` (fires per snapshot create — including
  the implicit snapshots that realignment + restore generate)
- ``household_snapshot_restored``
- ``goal_risk_override_created``
- ``external_holdings_updated``
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework.test import APIClient
from web.api import models
from web.audit.models import AuditEvent


def _authenticated_client(
    *, email: str = "advisor@example.com", role: str = "advisor"
) -> APIClient:
    User = get_user_model()
    user = User.objects.filter(username=email).first()
    if user is None:
        user = User.objects.create_user(username=email, email=email, password="pw")
    group, _ = Group.objects.get_or_create(name=role)
    user.groups.add(group)
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _seeded_household() -> models.Household:
    User = get_user_model()
    advisor = User.objects.filter(username="advisor@example.com").first()
    if advisor is None:
        advisor = User.objects.create_user(
            username="advisor@example.com",
            email="advisor@example.com",
            password="pw",
        )
    household = models.Household.objects.create(
        external_id="hh_audit_r1",
        display_name="Audit Test Household",
        household_type="couple",
        household_risk_score=3,
        owner=advisor,
    )
    models.Person.objects.create(
        external_id="p_audit_r1",
        household=household,
        name="Audit Person",
        dob=date(1980, 1, 1),
    )
    account = models.Account.objects.create(
        external_id="a_audit_r1",
        household=household,
        account_type="RRSP",
        regulatory_objective="growth_and_income",
        regulatory_time_horizon="3-10y",
        regulatory_risk_rating="medium",
        current_value=Decimal("100000.00"),
    )
    goal = models.Goal.objects.create(
        external_id="g_audit_r1",
        household=household,
        name="Retirement",
        target_date=date.today() + timedelta(days=365 * 20),
        necessity_score=4,
        goal_risk_score=3,
    )
    models.GoalAccountLink.objects.create(
        external_id="gal_audit_r1",
        goal=goal,
        account=account,
        allocated_amount=Decimal("100000.00"),
    )
    return household


def _assert_audit_event(action: str, *, count: int = 1, scope: str = "") -> None:
    """Assertion helper for the audit-event regression contract."""

    qs = AuditEvent.objects.filter(action=action)
    actual = qs.count()
    recent_actions = list(AuditEvent.objects.order_by("-id").values_list("action", flat=True)[:10])
    assert actual == count, (
        f"Expected exactly {count} AuditEvent(s) with action={action} "
        f"(scope={scope or 'global'}), got {actual}. All recent: {recent_actions}"
    )


# ---------------------------------------------------------------------------
# Wizard commit
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_wizard_commit_emits_household_wizard_committed_event() -> None:
    client = _authenticated_client()
    payload = {
        "display_name": "Wizard Audit",
        "household_type": "single",
        "members": [{"name": "Solo", "dob": "1985-01-01"}],
        "risk_profile": {"q1": 5, "q2": "B", "q3": [], "q4": "B"},
        "accounts": [{"account_type": "TFSA", "current_value": "10000.00"}],
        "goals": [
            {
                "name": "Goal",
                "target_date": "2030-01-01",
                "necessity_score": 3,
                "legs": [{"account_index": 0, "allocated_amount": "10000.00"}],
            }
        ],
    }
    response = client.post(reverse("wizard-commit"), payload, format="json")
    assert response.status_code == 201
    _assert_audit_event("household_wizard_committed", count=1, scope="wizard")


# ---------------------------------------------------------------------------
# Goal risk override
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_goal_override_emits_goal_risk_override_created() -> None:
    _seeded_household()
    client = _authenticated_client()
    response = client.post(
        reverse("goal-risk-override-create", args=["g_audit_r1"]),
        {
            "score_1_5": 4,
            "descriptor": "Balanced-growth",
            "rationale": "Client explicitly requested more growth exposure.",
        },
        format="json",
    )
    assert response.status_code == 201
    _assert_audit_event("goal_risk_override_created", count=1, scope="override")


@pytest.mark.django_db
def test_goal_override_two_creates_two_events() -> None:
    _seeded_household()
    client = _authenticated_client()
    rationales = [
        "First rationale that meets the minimum length.",
        "Second rationale, advisor revised the score.",
    ]
    for rationale in rationales:
        response = client.post(
            reverse("goal-risk-override-create", args=["g_audit_r1"]),
            {
                "score_1_5": 2,
                "descriptor": "Conservative-balanced",
                "rationale": rationale,
            },
            format="json",
        )
        assert response.status_code == 201
    _assert_audit_event("goal_risk_override_created", count=2, scope="override")


# ---------------------------------------------------------------------------
# Realignment + snapshots
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_realignment_emits_realignment_and_snapshot_events() -> None:
    household = _seeded_household()
    # Add a second goal so realignment is meaningful
    goal2 = models.Goal.objects.create(
        external_id="g_audit_r1_house",
        household=household,
        name="House",
        target_date=date.today() + timedelta(days=365 * 5),
        necessity_score=3,
        goal_risk_score=2,
    )
    account = household.accounts.get(external_id="a_audit_r1")
    models.GoalAccountLink.objects.create(
        external_id="gal_audit_r1_2",
        goal=goal2,
        account=account,
        allocated_amount=Decimal("0.00"),
    )

    client = _authenticated_client()
    response = client.post(
        reverse("household-realignment", args=[household.external_id]),
        {
            "account_goal_amounts": {
                "a_audit_r1": {
                    "g_audit_r1": "60000.00",
                    "g_audit_r1_house": "40000.00",
                }
            }
        },
        format="json",
    )
    assert response.status_code == 200
    _assert_audit_event("realignment_applied", count=1, scope="realignment")
    # Realignment creates 2 snapshots (before + after)
    _assert_audit_event("household_snapshot_created", count=2, scope="realignment-snapshots")


@pytest.mark.django_db
def test_snapshot_restore_emits_restore_event() -> None:
    household = _seeded_household()
    User = get_user_model()
    user = User.objects.get(username="advisor@example.com")
    snapshot = models.HouseholdSnapshot.objects.create(
        household=household,
        triggered_by="realignment",
        label="prior state",
        snapshot={"accounts": [], "goals": []},
        summary={},
        created_by=user,
    )

    client = _authenticated_client()
    response = client.post(
        reverse("household-snapshot-restore", args=[household.external_id, snapshot.id]),
    )
    assert response.status_code == 201
    _assert_audit_event("household_snapshot_restored", count=1, scope="snapshot-restore")
    # Restore creates 1 new snapshot tagged 'restore'
    _assert_audit_event("household_snapshot_created", count=1, scope="restore-snapshot")


# ---------------------------------------------------------------------------
# External holdings CRUD
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_external_holding_create_update_delete_each_emit_event() -> None:
    household = _seeded_household()
    client = _authenticated_client()

    # Create
    create_response = client.post(
        reverse("external-holdings-list", args=[household.external_id]),
        {
            "value": "10000.00",
            "equity_pct": "60.00",
            "fixed_income_pct": "30.00",
            "cash_pct": "5.00",
            "real_assets_pct": "5.00",
        },
        format="json",
    )
    assert create_response.status_code == 201
    holding_id = create_response.json()["id"]

    # Update
    update_response = client.patch(
        reverse("external-holdings-detail", args=[household.external_id, holding_id]),
        {
            "value": "12000.00",
            "equity_pct": "70.00",
            "fixed_income_pct": "20.00",
            "cash_pct": "5.00",
            "real_assets_pct": "5.00",
        },
        format="json",
    )
    assert update_response.status_code == 200

    # Delete
    delete_response = client.delete(
        reverse("external-holdings-detail", args=[household.external_id, holding_id]),
    )
    assert delete_response.status_code == 204

    # Each fires one external_holdings_updated event
    _assert_audit_event(
        "external_holdings_updated",
        count=3,
        scope="external-CRUD",
    )


# ---------------------------------------------------------------------------
# Read-only preview endpoints emit NO audit events (locked decision #37)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_read_only_preview_endpoints_emit_no_audit_events() -> None:
    """Locked decision #37: 'Preview endpoints (read-only computations) do
    not emit audit events.'"""

    starting_count = AuditEvent.objects.count()
    client = _authenticated_client()
    client.post(
        reverse("preview-risk-profile"),
        {"q1": 5, "q2": "B", "q3": [], "q4": "B"},
        format="json",
    )
    client.post(
        reverse("preview-sleeve-mix"),
        {"score_1_5": 3},
        format="json",
    )
    client.post(
        reverse("preview-projection"),
        {
            "start": 100000,
            "score_1_5": 3,
            "horizon_years": 10,
            "tier": "want",
        },
        format="json",
    )
    assert AuditEvent.objects.count() == starting_count
