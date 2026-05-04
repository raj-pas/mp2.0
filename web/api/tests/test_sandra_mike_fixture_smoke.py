"""Sandra/Mike Chen synthetic fixture A1 smoke tests.

Pins the post-A1 fixture contract: RiskProfile derives anchor=22.5 (per
Hayes worked example Q1=5/Q2=B/Q3=career/Q4=B), holdings use canonical
sh_* fund ids matching the active CMA, advisor disclaimer + tour are
pre-acked so the demo flow doesn't surface PilotBanner/WelcomeTour, and
engine.optimize() runs cleanly without UNMAPPED_HOLDINGS warnings on
the synthetic data.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from engine.optimizer import optimize
from web.api import models
from web.api.engine_adapter import to_engine_cma, to_engine_household


@pytest.mark.django_db
def test_sandra_mike_fixture_loads_with_risk_profile():
    call_command("load_synthetic_personas")
    hh = models.Household.objects.get(external_id="hh_sandra_mike_chen")
    rp = hh.risk_profile
    assert rp.q1 == 5
    assert rp.q2 == "B"
    assert rp.q3 == ["career"]
    assert rp.q4 == "B"
    assert float(rp.tolerance_score) == pytest.approx(45.0)
    assert float(rp.capacity_score) == pytest.approx(50.0)
    assert float(rp.anchor) == pytest.approx(22.5)
    assert rp.score_1_5 == 3
    assert rp.household_descriptor == "Balanced"
    assert rp.flags == []


@pytest.mark.django_db
def test_sandra_mike_fixture_loads_with_canonical_sh_fund_holdings():
    call_command("load_synthetic_personas")
    hh = models.Household.objects.get(external_id="hh_sandra_mike_chen")
    fund_ids: set[str] = set()
    for acct in hh.accounts.all():
        for h in acct.holdings.all():
            fund_ids.add(h.sleeve_id)
    expected = {
        "sh_builders",
        "sh_equity",
        "sh_founders",
        "sh_global_equity",
        "sh_income",
        "sh_savings",
        "sh_small_cap_equity",
    }
    assert fund_ids == expected
    assert "income_fund" not in fund_ids
    assert "equity_fund" not in fund_ids
    assert "global_equity_fund" not in fund_ids
    assert "cash_savings" not in fund_ids


@pytest.mark.django_db
def test_sandra_mike_fixture_advisor_pre_ack(settings):
    settings.MP20_LOCAL_ADMIN_EMAIL = "advisor@example.com"
    settings.MP20_LOCAL_ADMIN_PASSWORD = "test-password-not-real"
    import os

    os.environ["MP20_LOCAL_ADMIN_EMAIL"] = "advisor@example.com"
    os.environ["MP20_LOCAL_ADMIN_PASSWORD"] = "test-password-not-real"
    call_command("bootstrap_local_advisor")
    call_command("load_synthetic_personas")
    User = get_user_model()
    advisor = User.objects.get(email="advisor@example.com")
    profile = models.AdvisorProfile.objects.get(user=advisor)
    assert profile.disclaimer_acknowledged_at is not None
    assert profile.disclaimer_acknowledged_version == "v1"
    assert profile.tour_completed_at is not None


@pytest.mark.django_db
def test_sandra_mike_fixture_engine_runs_without_unmapped_warnings():
    call_command("seed_default_cma", "--force")
    call_command("load_synthetic_personas")
    hh = models.Household.objects.get(external_id="hh_sandra_mike_chen")
    snapshot = models.CMASnapshot.objects.filter(status=models.CMASnapshot.Status.ACTIVE).first()
    assert snapshot is not None, "Active CMA snapshot must exist for engine probe."

    output = optimize(to_engine_household(hh), to_engine_cma(snapshot))

    warnings_blob = " ".join(output.warnings).lower()
    assert "unmapped" not in warnings_blob, (
        f"Sandra/Mike fixture must use canonical sh_* funds; got warnings: {output.warnings}"
    )
    assert len(output.link_recommendations) >= 4
    assert output.household_rollup is not None
    assert len(output.goal_rollups) == 3  # 3 goals in fixture
