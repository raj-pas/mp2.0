"""Backwards-compat tests for pre-A2 PortfolioRun shape (locked decision #97).

A "pre-A2 PortfolioRun" is one matching the `v0.1.0-pilot` shape:
  - `engine_output.link_first.v2` schema_version on `output`
  - NO `latest_portfolio_failure` field surfaced on HouseholdDetail
    (the SerializerMethodField was added in sub-session #1; pre-A2
    households were committed before that work shipped).

`HouseholdDetailSerializer.latest_portfolio_failure` is purely
additive + null-safe: when no `portfolio_generation_*_failed`
AuditEvent exists newer than the household's latest PortfolioRun,
the field is `None`. These tests pin that contract so future
serializer changes can't silently break the pre-A2 compat surface.

Per locked #97: catches data-shape drift regressions for households
committed before sub-sessions #1-#3 shipped.

Companion: locked #101 (test_household_detail_serializer_snapshot.py)
pins the broader JSON shape; this file specifically pins the pre-A2
compat invariants on `latest_portfolio_run` + `latest_portfolio_failure`.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.urls import reverse
from rest_framework.test import APIClient
from web.api import models
from web.audit.models import AuditEvent

User = get_user_model()


def _bootstrap_full_demo() -> models.Household:
    """Reset state with seed_default_cma + load_synthetic_personas.

    Auto-seed (sub-session #3) creates an initial PortfolioRun with
    `engine_output.link_first.v2` shape — the same shape pre-A2
    advisors saw before sub-sessions #1-#3.
    """
    call_command("seed_default_cma", "--force")
    call_command("load_synthetic_personas")
    return models.Household.objects.get(external_id="hh_sandra_mike_chen")


def _advisor_client() -> APIClient:
    """Authenticated advisor (real-PII access required for ClientDetailView).

    Per access.py: advisor group → can_access_real_pii. Synthetic
    Sandra/Mike is owner-less so visible team-wide.
    """
    user, _ = User.objects.get_or_create(
        username="advisor@example.com",
        defaults={"email": "advisor@example.com"},
    )
    user.set_password("pw")
    user.save()
    group, _ = Group.objects.get_or_create(name="advisor")
    user.groups.add(group)
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_pre_a2_portfolio_run_renders_via_household_detail() -> None:
    """Households with pre-A2 PortfolioRuns must render via post-A2
    HouseholdDetailSerializer.

    Setup mirrors the exact pre-A2 sequence: bootstrap synthetic
    Sandra/Mike → engine emits a `engine_output.link_first.v2`
    PortfolioRun → no failure has been recorded.

    Asserts:
      - GET /api/clients/<hh>/ → 200
      - latest_portfolio_failure is None (no failure exists)
      - latest_portfolio_run is non-null + has the v2 shape
      - link_recommendations is non-empty
      - goal_rollups is non-empty list
      - household_rollup is dict (NOT array; matches engine schema)
    """
    hh = _bootstrap_full_demo()
    client = _advisor_client()

    response = client.get(reverse("client-detail", args=[hh.external_id]))
    assert response.status_code == 200, (
        f"ClientDetailView returned {response.status_code}: {response.content!r}"
    )
    body = response.json()

    # latest_portfolio_failure additive field MUST exist + be None.
    assert "latest_portfolio_failure" in body, (
        "Pre-A2 compat: HouseholdDetail must expose latest_portfolio_failure "
        "field (sub-session #1 additive contract)."
    )
    assert body["latest_portfolio_failure"] is None, (
        f"No failure exists for clean Sandra/Mike auto-seed; field must "
        f"be None. Got: {body['latest_portfolio_failure']!r}"
    )

    # latest_portfolio_run must be present + have v2 shape.
    assert "latest_portfolio_run" in body
    run = body["latest_portfolio_run"]
    assert run is not None, "Auto-seed produces a PortfolioRun; field must not be None"

    output = run["output"]
    assert output["schema_version"] == "engine_output.link_first.v2", (
        f"Pre-A2 contract requires engine_output.link_first.v2; got {output['schema_version']!r}"
    )
    assert isinstance(output["link_recommendations"], list)
    assert len(output["link_recommendations"]) > 0, (
        "Sandra/Mike has 6 GoalAccountLinks; link_recommendations must be non-empty"
    )
    assert isinstance(output["goal_rollups"], list)
    assert len(output["goal_rollups"]) > 0, (
        "Sandra/Mike has 3 goals; goal_rollups must be non-empty"
    )
    # household_rollup is a SINGLE object (not array). Catches drift if
    # the engine were to ever return list[Rollup] for the household.
    assert isinstance(output["household_rollup"], dict), (
        f"household_rollup must be dict (single Rollup); got "
        f"{type(output['household_rollup']).__name__}"
    )

    # account_rollups also present per engine schema (defensive).
    assert isinstance(output["account_rollups"], list)
    assert len(output["account_rollups"]) > 0


@pytest.mark.django_db
def test_household_with_failure_renders_latest_portfolio_failure(settings) -> None:
    """When a `portfolio_generation_post_<source>_failed` AuditEvent
    exists newer than the latest PortfolioRun, the HouseholdDetail
    serializer surfaces it with the canonical shape.

    Per locked #9: unexpected exceptions hit the catch-all in
    `_trigger_and_audit` + emit `portfolio_generation_post_<source>_failed`
    audit. The serializer reads that audit + exposes a 4-field dict
    so RecommendationBanner can render an inline error.

    Setup: bootstrap → delete auto-seed run → manually emit a failure
    audit (the catch-all path is exercised by integration tests
    elsewhere; here we pin the SHAPE the serializer reads).
    """
    hh = _bootstrap_full_demo()
    # Delete the auto-seed run so the failure-audit cutoff is
    # household.created_at (not run.created_at) — matches the case
    # where no run has ever generated successfully.
    models.PortfolioRun.objects.filter(household=hh).delete()

    # Manually emit a portfolio_generation_post_<source>_failed audit
    # mirroring the shape `_trigger_and_audit`'s catch-all produces.
    AuditEvent.objects.create(
        action="portfolio_generation_post_review_commit_failed",
        entity_type="household",
        entity_id=hh.external_id,
        actor="advisor@example.com",
        metadata={
            "source": "review_commit",
            "household_id": hh.external_id,
            "failure_summary": "RuntimeError: synthetic failure for shape test",
        },
    )

    client = _advisor_client()
    response = client.get(reverse("client-detail", args=[hh.external_id]))
    assert response.status_code == 200
    body = response.json()

    # latest_portfolio_run is null (we deleted the auto-seed run) +
    # latest_portfolio_failure is the canonical 4-field dict.
    assert body["latest_portfolio_run"] is None, (
        "After deleting auto-seed run, latest_portfolio_run must be null"
    )
    failure = body["latest_portfolio_failure"]
    assert failure is not None, (
        "AuditEvent newer than household.created_at exists; "
        "latest_portfolio_failure must surface it"
    )

    # Canonical shape per HouseholdDetailSerializer.get_latest_portfolio_failure:
    assert set(failure.keys()) == {
        "action",
        "reason_code",
        "exception_summary",
        "occurred_at",
    }, f"Unexpected key set in failure dict: {sorted(failure.keys())}"

    assert failure["action"] == "portfolio_generation_post_review_commit_failed"
    assert failure["reason_code"] == "review_commit"
    assert "synthetic failure for shape test" in failure["exception_summary"]
    assert failure["occurred_at"] is not None
    # ISO-8601 timestamp: must be parseable.
    from datetime import datetime

    datetime.fromisoformat(failure["occurred_at"])


# ---------------------------------------------------------------------------
# Locked decision #101 — HouseholdDetail JSON shape snapshot
# ---------------------------------------------------------------------------


_EXPECTED_TOP_LEVEL_KEYS = {
    "id",
    "display_name",
    "household_type",
    "household_risk_score",
    "goal_count",
    "total_assets",
    "external_assets",
    "notes",
    "members",
    "goals",
    "accounts",
    "latest_portfolio_run",
    "latest_portfolio_failure",
    "portfolio_runs",
}


@pytest.mark.django_db
def test_household_detail_response_shape_pinned() -> None:
    """Pin HouseholdDetail JSON shape (locked #101).

    Future field renames / type changes / removals fail this test
    BEFORE advisor sees them. Mirrors the openapi-codegen gate
    caveat per scripts/check-openapi-codegen.sh: HouseholdDetailSerializer
    has no `@extend_schema` so the codegen gate doesn't pin it; this
    test fills that gap.

    Updates require BOTH serializer commit + this expected-keys set
    + frontend type commit (3-file regression-prevention per locked #101).
    """
    hh = _bootstrap_full_demo()
    client = _advisor_client()

    response = client.get(reverse("client-detail", args=[hh.external_id]))
    assert response.status_code == 200
    body = response.json()

    actual_keys = set(body.keys())
    missing = _EXPECTED_TOP_LEVEL_KEYS - actual_keys
    extra = actual_keys - _EXPECTED_TOP_LEVEL_KEYS
    assert not missing, (
        f"HouseholdDetail missing expected keys: {sorted(missing)}. If you "
        f"intentionally removed a field, update _EXPECTED_TOP_LEVEL_KEYS + "
        f"frontend/src/lib/household.ts in the same commit (locked #101)."
    )
    assert not extra, (
        f"HouseholdDetail surfaced UNEXPECTED keys: {sorted(extra)}. If you "
        f"intentionally added a field, update _EXPECTED_TOP_LEVEL_KEYS + "
        f"frontend/src/lib/household.ts in the same commit (locked #101)."
    )

    # Type pins for top-level fields (catches type drift).
    assert isinstance(body["id"], str)
    assert isinstance(body["display_name"], str)
    assert isinstance(body["household_type"], str)
    assert isinstance(body["household_risk_score"], int)
    assert isinstance(body["goal_count"], int)
    assert isinstance(body["total_assets"], (int, float))
    assert isinstance(body["external_assets"], list)
    assert isinstance(body["notes"], str)
    assert isinstance(body["members"], list)
    assert isinstance(body["goals"], list)
    assert isinstance(body["accounts"], list)
    # latest_portfolio_run is dict|None
    assert body["latest_portfolio_run"] is None or isinstance(body["latest_portfolio_run"], dict)
    # latest_portfolio_failure is dict|None
    assert body["latest_portfolio_failure"] is None or isinstance(
        body["latest_portfolio_failure"], dict
    )
    # portfolio_runs is list (capped at 10 per get_portfolio_runs).
    assert isinstance(body["portfolio_runs"], list)
    assert len(body["portfolio_runs"]) <= 10

    # Auto-seed populates latest_portfolio_run; pin its nested top-level keys.
    assert body["latest_portfolio_run"] is not None, (
        "Auto-seed (load_synthetic_personas) must produce a PortfolioRun"
    )
    run_keys = set(body["latest_portfolio_run"].keys())
    expected_run_keys = {
        "id",
        "external_id",
        "status",
        "as_of_date",
        "cma_snapshot_id",
        "engine_version",
        "advisor_summary",
        "input_hash",
        "output_hash",
        "cma_hash",
        "reviewed_state_hash",
        "approval_snapshot_hash",
        "run_signature",
        "warnings",
        "generated_by_email",
        "created_at",
        "output",
        "technical_trace",
        "link_recommendation_rows",
        "events",
    }
    missing_run_keys = expected_run_keys - run_keys
    extra_run_keys = run_keys - expected_run_keys
    assert not missing_run_keys, f"latest_portfolio_run missing keys: {sorted(missing_run_keys)}"
    assert not extra_run_keys, (
        f"latest_portfolio_run surfaced UNEXPECTED keys: {sorted(extra_run_keys)}"
    )
