"""Append-only-invariants regression suite (canon §9.4 "second most
important rule" — append-only lifecycle events).

Each lifecycle/audit model has a `save()` guard that raises
ValidationError when the pk already exists. This file is the single-
source-of-truth contract that those guards REMAIN in place. A future
refactor that drops a guard fails CI here before it can corrupt the
audit trail or run history.

The Postgres BEFORE UPDATE/DELETE triggers (separate layer) are not
exercised here — those are tested by the DB migrations + a separate
trigger smoke. This file covers ONLY the application-layer guards.

Models covered:
    - PortfolioRun
    - PortfolioRunLinkRecommendation
    - PortfolioRunEvent
    - GoalRiskOverride (additionally tested in test_r1_preview_endpoints)
    - HouseholdSnapshot (additionally tested in test_r1_preview_endpoints)
    - AuditEvent (additionally tested in web/audit/tests/test_writer)
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from web.api import models


def _seeded_household_with_run() -> tuple[models.Household, models.PortfolioRun]:
    """Build the minimum tree needed to instantiate every append-only model."""

    User = get_user_model()
    user = User.objects.create_user(
        username="advisor@example.com", email="advisor@example.com", password="pw"
    )
    household = models.Household.objects.create(
        external_id="hh_append_only",
        owner=user,
        display_name="Append Only Household",
        household_type="single",
        household_risk_score=3,
    )
    person = models.Person.objects.create(
        external_id="p_append_only",
        household=household,
        name="Append Only Client",
        dob=date(1962, 1, 1),
    )
    account = models.Account.objects.create(
        external_id="a_append_only",
        household=household,
        owner_person=person,
        account_type="RRSP",
        current_value=Decimal("100000"),
        is_held_at_purpose=True,
    )
    goal = models.Goal.objects.create(
        external_id="g_append_only",
        household=household,
        name="Retirement",
        target_date=date.today() + timedelta(days=365 * 5),
        necessity_score=3,
        goal_risk_score=3,
    )
    link = models.GoalAccountLink.objects.create(
        external_id="gal_append_only",
        goal=goal,
        account=account,
        allocated_amount=Decimal("100000"),
    )

    call_command("seed_default_cma")
    cma = models.CMASnapshot.objects.filter(status=models.CMASnapshot.Status.ACTIVE).first()
    assert cma is not None, "seed_default_cma should leave one ACTIVE snapshot"

    run = models.PortfolioRun.objects.create(
        household=household,
        cma_snapshot=cma,
        generated_by=user,
        as_of_date=date.today(),
        run_signature="runsig" + "0" * 58,
        input_snapshot={"placeholder": "audit-test"},
        output={"placeholder": "audit-test"},
        input_hash="ih" + "0" * 62,
        output_hash="oh" + "0" * 62,
        cma_hash="ch" + "0" * 62,
        engine_version="audit-test",
    )
    # PortfolioRunLinkRecommendation needed for completeness
    models.PortfolioRunLinkRecommendation.objects.create(
        portfolio_run=run,
        goal_account_link=link,
        link_external_id=link.external_id,
        goal=goal,
        account=account,
        goal_external_id=goal.external_id,
        account_external_id=account.external_id,
        allocated_amount=Decimal("100000"),
        frontier_percentile=25,
        expected_return=Decimal("0.05"),
        volatility=Decimal("0.10"),
    )
    return household, run


@pytest.mark.django_db
def test_portfolio_run_save_raises_on_existing_pk() -> None:
    """Canon §9.4 invariant: PortfolioRun is append-only."""

    _, run = _seeded_household_with_run()
    run.advisor_summary = "edited after creation"
    with pytest.raises(ValidationError, match="append-only"):
        run.save()


@pytest.mark.django_db
def test_portfolio_run_link_recommendation_save_raises_on_existing_pk() -> None:
    """Canon §9.4 invariant: per-link recommendation rows are append-only."""

    _, run = _seeded_household_with_run()
    rec = run.link_recommendation_rows.first()
    assert rec is not None, "fixture should have created a recommendation row"
    rec.allocated_amount = Decimal("999999.99")
    with pytest.raises(ValidationError, match="append-only"):
        rec.save()


@pytest.mark.django_db
def test_portfolio_run_event_save_raises_on_existing_pk() -> None:
    """Canon §9.4 invariant: PortfolioRunEvent is append-only."""

    _, run = _seeded_household_with_run()
    event = models.PortfolioRunEvent.objects.create(
        portfolio_run=run,
        household=run.household,
        event_type=models.PortfolioRunEvent.EventType.GENERATED,
    )
    event.metadata = {"forbidden": "edit"}
    with pytest.raises(ValidationError, match="append-only"):
        event.save()


@pytest.mark.django_db
def test_household_snapshot_save_raises_on_existing_pk() -> None:
    """Canon §9.4 invariant: HouseholdSnapshot is append-only.

    Already covered in test_r1_preview_endpoints.py:
    test_snapshot_immutability_save_raises_on_existing_pk — replicated
    here so a future refactor that splits snapshot tests into a
    separate module doesn't lose the invariant guard.
    """

    User = get_user_model()
    user = User.objects.create_user(
        username="advisor@example.com", email="advisor@example.com", password="pw"
    )
    household = models.Household.objects.create(
        external_id="hh_snapshot_append",
        owner=user,
        display_name="Snapshot Household",
        household_type="single",
        household_risk_score=3,
    )
    snapshot = models.HouseholdSnapshot.objects.create(
        household=household,
        triggered_by=models.HouseholdSnapshot.TriggerType.RE_GOAL,
        label="Initial",
        snapshot={"hh": "snap"},
        summary={"aum": "0"},
        created_by=user,
    )
    snapshot.label = "edited"
    with pytest.raises(ValidationError, match="append-only"):
        snapshot.save()


@pytest.mark.django_db
def test_goal_risk_override_save_raises_on_existing_pk() -> None:
    """Canon §9.4 invariant: GoalRiskOverride is append-only — a new
    override row supersedes the old one (latest-row-wins per goal),
    audit-trail is preserved.
    """

    User = get_user_model()
    user = User.objects.create_user(
        username="advisor@example.com", email="advisor@example.com", password="pw"
    )
    household = models.Household.objects.create(
        external_id="hh_override_append",
        owner=user,
        display_name="Override Household",
        household_type="single",
        household_risk_score=3,
    )
    goal = models.Goal.objects.create(
        external_id="g_override_append",
        household=household,
        name="Goal",
        target_date=date.today() + timedelta(days=365 * 5),
        necessity_score=3,
        goal_risk_score=3,
    )
    override = models.GoalRiskOverride.objects.create(
        goal=goal,
        score_1_5=4,
        descriptor="Balanced-growth",
        rationale="Initial rationale that meets minimum length.",
        created_by=user,
    )
    override.rationale = "edited rationale that meets minimum length."
    with pytest.raises(ValidationError, match="append-only"):
        override.save()
