"""Wizard commit + readiness_blockers regression tests.

Pins the wiring added this session:
  1. ``WizardAccountSerializer`` accepts ``missing_holdings_confirmed``.
  2. ``WizardCommitView`` passes the flag through to ``Account.objects.create``.
  3. ``WizardCommitView`` response includes ``readiness_blockers`` so the
     frontend wizard can surface a "committed but not ready" warning toast.
  4. ``HouseholdDetailSerializer.readiness_blockers`` humanizes UUID
     ``external_id`` references with ``<account_type> (<8-char prefix>)``.

Real bug class this guards (post-tag finding 2026-05-04):
  - Eren Mikasa wizard commit with $10K of $900K allocated to a goal +
    no missing_holdings_confirmed → silent typed-skip per locked #9 →
    advisor saw cold-start UI with no signal. Surfacing readiness_blockers
    in the commit response + persistent panel + Step5 pre-flight closes
    the UX gap without breaking the locked #9 silent-skip invariant.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from web.api import models


def _client():
    User = get_user_model()
    user, _ = User.objects.get_or_create(
        username="advisor@example.com",
        defaults={"email": "advisor@example.com"},
    )
    api = APIClient()
    api.force_authenticate(user=user)
    return api


def _wizard_payload(**overrides):
    """Default minimal-valid wizard payload; tests override specific fields."""
    payload = {
        "display_name": "Wizard Readiness Test",
        "household_type": "single",
        "members": [{"name": "Solo", "dob": "1985-01-01"}],
        "risk_profile": {"q1": 5, "q2": "B", "q3": [], "q4": "B"},
        "accounts": [
            {
                "account_type": "TFSA",
                "current_value": "10000.00",
                "missing_holdings_confirmed": True,
            }
        ],
        "goals": [
            {
                "name": "Test goal",
                "target_date": "2030-01-01",
                "necessity_score": 3,
                "legs": [{"account_index": 0, "allocated_amount": "10000.00"}],
            }
        ],
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# missing_holdings_confirmed plumb-through
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_wizard_passes_missing_holdings_confirmed_true_to_account() -> None:
    response = _client().post(reverse("wizard-commit"), _wizard_payload(), format="json")
    assert response.status_code == 201
    hh = models.Household.objects.get(external_id=response.json()["household_id"])
    acct = hh.accounts.first()
    assert acct is not None
    assert acct.missing_holdings_confirmed is True


@pytest.mark.django_db
def test_wizard_defaults_missing_holdings_confirmed_to_false_when_omitted() -> None:
    """Backwards-compat: existing wizard payloads without the new field still work."""
    payload = _wizard_payload()
    # Explicitly drop the key — simulates old frontend / pre-update payload.
    del payload["accounts"][0]["missing_holdings_confirmed"]
    response = _client().post(reverse("wizard-commit"), payload, format="json")
    assert response.status_code == 201
    hh = models.Household.objects.get(external_id=response.json()["household_id"])
    acct = hh.accounts.first()
    assert acct is not None
    assert acct.missing_holdings_confirmed is False


@pytest.mark.django_db
def test_wizard_missing_holdings_confirmed_false_explicit() -> None:
    payload = _wizard_payload()
    payload["accounts"][0]["missing_holdings_confirmed"] = False
    response = _client().post(reverse("wizard-commit"), payload, format="json")
    assert response.status_code == 201
    hh = models.Household.objects.get(external_id=response.json()["household_id"])
    acct = hh.accounts.first()
    assert acct is not None
    assert acct.missing_holdings_confirmed is False


# ---------------------------------------------------------------------------
# readiness_blockers in commit response
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_wizard_commit_response_engine_ready_returns_empty_blockers() -> None:
    """Fully-aligned account + goals + missing_holdings_confirmed=true → engine-ready."""
    response = _client().post(reverse("wizard-commit"), _wizard_payload(), format="json")
    assert response.status_code == 201
    body = response.json()
    assert "readiness_blockers" in body, "Response must include readiness_blockers field"
    assert body["readiness_blockers"] == [], (
        f"Engine-ready household should have empty blockers; got {body['readiness_blockers']!r}"
    )


@pytest.mark.django_db
def test_wizard_commit_response_under_allocated_account_surfaces_blocker() -> None:
    """Account total $900K + only $10K allocated to goal → blocker surfaced.

    Mirrors the Eren Mikasa user report: $890K unallocated → engine refuses
    to generate. Frontend must see this in the commit response so the
    warning toast can fire.
    """
    payload = _wizard_payload()
    payload["accounts"][0]["current_value"] = "900000.00"
    payload["goals"][0]["legs"][0]["allocated_amount"] = "10000.00"
    response = _client().post(reverse("wizard-commit"), payload, format="json")
    assert response.status_code == 201
    body = response.json()
    blockers = body["readiness_blockers"]
    assert len(blockers) >= 1
    assert any("must be fully assigned to goals" in b for b in blockers), (
        f"Expected an under-allocation blocker; got {blockers!r}"
    )


@pytest.mark.django_db
def test_wizard_commit_response_missing_holdings_false_is_NOT_a_blocker() -> None:
    """SEMANTIC INVARIANT (verified at HEAD by deep audit this session):

    `portfolio_generation_blockers_for_household` (the household-level
    readiness function) does NOT check holdings/missing_holdings_confirmed.
    The engine optimizer handles 0-holdings accounts gracefully:
      - missing_holdings_confirmed=true  → emits `confirmed_missing_current_holdings` warning
      - missing_holdings_confirmed=false → emits `missing_current_holdings` warning
    BOTH cases produce a valid PortfolioRun.

    So this test pins: missing_holdings_confirmed=false on a fully-
    allocated account does NOT show up as a readiness blocker. The Step5
    pre-flight should not warn about it either (we removed that warning
    after the deep audit; the Step3 checkbox + label is the right
    affordance for this advisor signal).
    """
    payload = _wizard_payload()
    payload["accounts"][0]["missing_holdings_confirmed"] = False
    response = _client().post(reverse("wizard-commit"), payload, format="json")
    assert response.status_code == 201
    body = response.json()
    # No blockers — engine succeeds (just with a warning in the run output).
    assert body["readiness_blockers"] == [], (
        "missing_holdings_confirmed=false alone should NOT block; got "
        f"{body['readiness_blockers']!r}"
    )


@pytest.mark.django_db
def test_wizard_commit_with_active_cma_creates_portfolio_run() -> None:
    """END-TO-END verification: empty readiness_blockers + active CMA →
    auto-trigger ACTUALLY succeeds in creating a PortfolioRun. Empty
    blockers alone aren't sufficient (engine could still raise
    InvalidCMAUniverse or similar); this test pins the full happy path.
    """
    from django.core.management import call_command

    call_command("seed_default_cma", "--force")
    response = _client().post(reverse("wizard-commit"), _wizard_payload(), format="json")
    assert response.status_code == 201
    body = response.json()
    assert body["readiness_blockers"] == []

    hh = models.Household.objects.get(external_id=body["household_id"])
    runs = list(hh.portfolio_runs.all())
    assert len(runs) == 1, (
        f"Auto-trigger should have created exactly 1 PortfolioRun for engine-ready "
        f"wizard commit; got {len(runs)}"
    )
    output = runs[0].output
    assert output is not None
    # missing_holdings_confirmed=true → engine emits the "confirmed" warning.
    warnings = output.get("warnings", []) or []
    assert "confirmed_missing_current_holdings" in warnings, (
        f"Engine should emit confirmed_missing_current_holdings; got {warnings!r}"
    )
    # Run has at least one link recommendation
    link_recs = output.get("link_recommendations", []) or []
    assert len(link_recs) >= 1


@pytest.mark.django_db
def test_wizard_commit_with_unchecked_holdings_emits_unconfirmed_warning() -> None:
    """missing_holdings_confirmed=false → engine still creates run, just
    without the `confirmed_missing_current_holdings` warning. This pins
    the warning-semantic distinction at the engine layer.
    """
    from django.core.management import call_command

    call_command("seed_default_cma", "--force")
    payload = _wizard_payload()
    payload["accounts"][0]["missing_holdings_confirmed"] = False
    response = _client().post(reverse("wizard-commit"), payload, format="json")
    assert response.status_code == 201
    hh = models.Household.objects.get(external_id=response.json()["household_id"])
    runs = list(hh.portfolio_runs.all())
    assert len(runs) == 1
    output = runs[0].output
    warnings = output.get("warnings", []) or []
    # Engine emits the un-confirmed warning…
    assert "missing_current_holdings" in warnings
    # …but NOT the confirmed one (advisor didn't check the box).
    assert "confirmed_missing_current_holdings" not in warnings, (
        f"Engine should NOT emit confirmed_missing when checkbox unchecked; got {warnings!r}"
    )


# ---------------------------------------------------------------------------
# HouseholdDetailSerializer humanization
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_household_detail_humanizes_uuid_in_blockers() -> None:
    """`be3337bc-7d7a-43ac-...` should render as `RRSP (be3337bc)` in the
    blocker text so the advisor can identify which account each blocker
    refers to."""
    payload = _wizard_payload()
    payload["accounts"][0]["account_type"] = "RRSP"
    payload["accounts"][0]["current_value"] = "900000.00"
    payload["goals"][0]["legs"][0]["allocated_amount"] = "10000.00"
    api = _client()
    response = api.post(reverse("wizard-commit"), payload, format="json")
    assert response.status_code == 201
    household_id = response.json()["household_id"]

    detail = api.get(reverse("client-detail", args=[household_id]))
    assert detail.status_code == 200
    blockers = detail.json()["readiness_blockers"]
    assert len(blockers) >= 1
    # Humanized form should appear; raw UUID should NOT.
    has_humanized = any("RRSP (" in b for b in blockers)
    has_raw_uuid = any(
        # Match a full UUID pattern in any blocker (8-4-4-4-12 hex).
        any(len(part) == 36 and part.count("-") == 4 for part in b.split())
        for b in blockers
    )
    assert has_humanized, f"Expected 'RRSP (' substring in blockers; got {blockers!r}"
    assert not has_raw_uuid, f"Raw UUID should be humanized; got {blockers!r}"


@pytest.mark.django_db
def test_household_detail_blockers_empty_for_engine_ready_household() -> None:
    """Sandra/Mike Chen synthetic is engine-ready by construction (per A1
    fixture refresh). The serializer must return [] (not None, not error)."""
    from django.core.management import call_command

    call_command("seed_default_cma", "--force")
    call_command("load_synthetic_personas")

    api = _client()
    detail = api.get(reverse("client-detail", args=["hh_sandra_mike_chen"]))
    assert detail.status_code == 200
    body = detail.json()
    assert body["readiness_blockers"] == [], (
        f"Sandra/Mike is engine-ready; expected []; got {body['readiness_blockers']!r}"
    )


# ---------------------------------------------------------------------------
# Wizard backwards-compat: the existing audit emission still fires
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_wizard_commit_with_missing_holdings_field_still_emits_audit() -> None:
    """Regression guard: adding the new field doesn't break the existing
    `household_wizard_committed` audit event.
    """
    from web.audit.models import AuditEvent

    before = AuditEvent.objects.filter(action="household_wizard_committed").count()
    response = _client().post(reverse("wizard-commit"), _wizard_payload(), format="json")
    assert response.status_code == 201
    after = AuditEvent.objects.filter(action="household_wizard_committed").count()
    assert after - before == 1
