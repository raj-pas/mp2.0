"""Full advisor-lifecycle integration test for the auto-trigger path
(per locked decision #96).

Walks every (synchronously-fired) auto-trigger sequentially against a
single household and asserts that the cumulative DB invariants hold:

  - PortfolioRun rows grow monotonically (strict-increase OR REUSED;
    never decrease, never duplicate same-signature).
  - PortfolioRunEvent chain is monotonic GENERATED / REGENERATED_AFTER_DECLINE
    / REUSED — no orphaned event types in normal flow.
  - AuditEvent count for `portfolio_run_*` actions grows by exactly
    one per trigger fire (`portfolio_run_generated` or
    `portfolio_run_reused`; typed-skip path is exercised by
    test_auto_portfolio_generation.py separately).
  - No IntegrityError under sequential load (every transaction commits
    cleanly; helper-managed atomic per locked #81).
  - Final state is internally consistent: hash chain unique per signature;
    audit metadata.source captures the trigger that produced it.

Per locked #96: this catches sequential cross-trigger interactions that
the 8 isolated-trigger tests in test_auto_portfolio_generation.py miss.

Locked decisions exercised:
  - #14 (8 trigger points; this test mixes direct-helper + API-endpoint
    invocations to cover both the wizard/override/realignment surface
    and the lower-level helpers)
  - #16 (single canonical action: portfolio_run_generated /
    portfolio_run_reused; source captured in metadata)
  - #74 (sync inline: every API trigger call returns AFTER the
    PortfolioRun has been written; no on_commit race)
  - #81 (helper-managed atomic; sequential calls never deadlock)
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.db import IntegrityError
from django.urls import reverse
from rest_framework.test import APIClient
from web.api import models
from web.api.views import (
    _trigger_and_audit,
    _trigger_portfolio_generation,
)
from web.audit.models import AuditEvent

User = get_user_model()


def _bootstrap_full_demo() -> models.Household:
    """Reset state with seed_default_cma + load_synthetic_personas.

    load_synthetic_personas auto-seeds an initial PortfolioRun via
    `_trigger_portfolio_generation(source='synthetic_load')` per A5
    (sub-session #3). Lifecycle test STARTS from this seeded state.
    """
    call_command("seed_default_cma", "--force")
    call_command("load_synthetic_personas")
    return models.Household.objects.get(external_id="hh_sandra_mike_chen")


def _advisor_user() -> User:
    """Idempotent advisor for sequential trigger fires.

    Synthetic Sandra/Mike is owner-less (Phase A) so any advisor in the
    `advisor` group can mutate it via the API endpoints.
    """
    user, _ = User.objects.get_or_create(
        username="advisor@example.com",
        defaults={"email": "advisor@example.com"},
    )
    user.set_password("pw")
    user.save()
    group, _ = Group.objects.get_or_create(name="advisor")
    user.groups.add(group)
    return user


def _authenticated_client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _portfolio_audit_count(household: models.Household) -> int:
    """Count canonical portfolio-trigger AuditEvent rows for the household.

    Mirrors locked #16: each trigger fire emits exactly ONE of:
      - portfolio_run_generated (engine ran; new row)
      - portfolio_run_reused    (signature match; existing row reused)
    Scoped by household_id (in metadata) since `entity_id` for
    `portfolio_run_*` events is the run external_id, not the household.
    """
    return AuditEvent.objects.filter(
        action__in=("portfolio_run_generated", "portfolio_run_reused"),
        metadata__household_id=household.external_id,
    ).count()


@pytest.mark.django_db
def test_full_advisor_lifecycle_emits_canonical_audits_at_each_trigger() -> None:
    """End-to-end advisor lifecycle on Sandra/Mike (locked #96).

    Walk:
      1. wizard_commit baseline (auto-seeded by load_synthetic_personas).
      2. Re-fire helper with same signature → REUSED.
      3. Realignment via API → link allocations change → fresh signature
         → GENERATED.
      4. Override via API → trigger fires but signature unchanged → REUSED.
         (NOTE: GoalRiskOverride creation does NOT mutate
         `committed_construction_snapshot` because the snapshot reads
         `goal.goal_risk_score` directly; the override is a parallel
         append-only record. The integration test pins that the override
         endpoint DOES fire `_trigger_and_audit(source="override")` —
         which produces a portfolio_run_reused audit on the realignment
         run — even though the signature is unchanged.)
      5. Mutate household_risk_score + helper-direct → fresh GENERATED.
      6. Re-fire same signature → REUSED.

    Assert at each step:
      - PortfolioRun count grows monotonically (or REUSED).
      - PortfolioRunEvent chain is monotonic GENERATED/REUSED.
      - AuditEvent count for portfolio_run_generated/reused grows by
        exactly 1 per trigger fire.
      - No IntegrityError under sequential load.
    """
    hh = _bootstrap_full_demo()
    user = _advisor_user()
    client = _authenticated_client(user)

    # ---- Step 1: baseline state from auto-seed (synthetic_load) -----
    initial_runs = models.PortfolioRun.objects.filter(household=hh).count()
    assert initial_runs == 1, (
        f"Expected exactly 1 auto-seed run from load_synthetic_personas; "
        f"got {initial_runs}. Sub-session #3 A5 contract violated."
    )
    initial_audits = _portfolio_audit_count(hh)
    assert initial_audits == 1, (
        f"Expected 1 portfolio_run_generated audit from auto-seed; got {initial_audits}."
    )

    # GENERATED PortfolioRunEvent on the seeded run.
    seeded_run = models.PortfolioRun.objects.filter(household=hh).first()
    assert seeded_run is not None
    seed_events = models.PortfolioRunEvent.objects.filter(
        portfolio_run=seeded_run,
        event_type=models.PortfolioRunEvent.EventType.GENERATED,
    )
    assert seed_events.count() == 1, "Auto-seed must emit exactly 1 GENERATED event"

    run_count = initial_runs
    audit_count = initial_audits

    # ---- Step 2: same-signature re-fire → REUSED -------------------
    try:
        result_2 = _trigger_portfolio_generation(hh, user, source="wizard_commit")
    except IntegrityError as exc:
        pytest.fail(f"Sequential same-signature re-fire raised IntegrityError: {exc}")
    assert result_2.pk == seeded_run.pk, "Same-signature must REUSE existing run"
    run_count_after_2 = models.PortfolioRun.objects.filter(household=hh).count()
    assert run_count_after_2 == run_count, "REUSED path must NOT create a new row"
    audit_count_after_2 = _portfolio_audit_count(hh)
    assert audit_count_after_2 == audit_count + 1, (
        f"REUSED path must emit exactly 1 portfolio_run_reused audit; "
        f"audit count went {audit_count} → {audit_count_after_2}"
    )
    audit_count = audit_count_after_2
    # REUSED PortfolioRunEvent appended on the existing run.
    reused_events = models.PortfolioRunEvent.objects.filter(
        portfolio_run=seeded_run,
        event_type=models.PortfolioRunEvent.EventType.REUSED,
    )
    assert reused_events.count() >= 1, "Same-signature re-fire must emit REUSED event"

    # ---- Step 3: realignment via API → fresh signature → GENERATED -
    # Sandra/Mike's goal_ski_cabin uses joint_tfsa($80k) + non_reg($40k);
    # rebalance to (60k retirement / 90k ski) on tfsa + (78k emma / 30k
    # ski) on non-reg. Link allocations change → input_hash → fresh
    # signature.
    response_3 = client.post(
        reverse("household-realignment", args=[hh.external_id]),
        {
            "account_goal_amounts": {
                "acct_joint_tfsa": {
                    "goal_retirement_income": "60000.00",
                    "goal_ski_cabin": "90000.00",
                },
                "acct_non_registered": {
                    "goal_emma_education": "78000.00",
                    "goal_ski_cabin": "30000.00",
                },
            }
        },
        format="json",
    )
    assert response_3.status_code == 200, (
        f"Realignment endpoint failed: {response_3.status_code} {response_3.content!r}"
    )
    run_count_after_3 = models.PortfolioRun.objects.filter(household=hh).count()
    # Realignment changed link allocations → input_hash → fresh signature
    # → new run. (If realignment produced an identical signature we'd
    # see REUSED + same row count; assert STRICT increase here.)
    assert run_count_after_3 == run_count + 1, (
        f"Realignment must create new run; count {run_count} → {run_count_after_3}"
    )
    run_count = run_count_after_3
    audit_count_after_3 = _portfolio_audit_count(hh)
    assert audit_count_after_3 == audit_count + 1
    audit_count = audit_count_after_3
    realignment_run = (
        models.PortfolioRun.objects.filter(household=hh).order_by("-created_at").first()
    )
    assert realignment_run is not None
    realignment_audit = AuditEvent.objects.filter(
        action="portfolio_run_generated",
        entity_id=realignment_run.external_id,
    ).first()
    assert realignment_audit is not None
    assert realignment_audit.metadata.get("source") == "realignment"

    # ---- Step 4: override via API → audits + GENERATED -------------
    # Per fix-2026-05-04 (locked #100 real-Chrome smoke surfaced the bug):
    # `committed_construction_snapshot` and `_goal_to_engine` now consult
    # `effective_goal_risk_score(goal)` which resolves the latest
    # GoalRiskOverride. An override that changes the effective score
    # (here: score 3 system → score 5 override) produces a different
    # input_hash and a new PortfolioRun row. Pre-fix, the override was
    # invisible to the engine and REUSED was incorrectly hit; that
    # behavior was a real production bug masquerading as REUSED.
    response_4 = client.post(
        reverse("goal-risk-override-create", args=["goal_retirement_income"]),
        {
            "score_1_5": 5,
            "descriptor": "Growth-oriented",
            "rationale": (
                "Sandra/Mike lifecycle integration test — record an "
                "advisor risk override on the retirement goal."
            ),
        },
        format="json",
    )
    assert response_4.status_code == 201, (
        f"Override endpoint failed: {response_4.status_code} {response_4.content!r}"
    )
    run_count_after_4 = models.PortfolioRun.objects.filter(household=hh).count()
    # Override changes effective score → fresh input_hash → GENERATED new run.
    assert run_count_after_4 == run_count + 1, (
        f"GoalRiskOverride that changes effective score must produce a new "
        f"PortfolioRun via fresh input_hash. Run count went "
        f"{run_count} → {run_count_after_4}"
    )
    run_count = run_count_after_4
    override_run = (
        models.PortfolioRun.objects.filter(household=hh).order_by("-created_at").first()
    )
    assert override_run is not None
    audit_count_after_4 = _portfolio_audit_count(hh)
    # Override fires _trigger_and_audit(source="override") which generates a
    # new run → emits portfolio_run_generated audit (locked #16 canonical naming).
    assert audit_count_after_4 == audit_count + 1, (
        f"Override trigger must emit exactly 1 portfolio_run_generated audit; "
        f"audit count went {audit_count} → {audit_count_after_4}"
    )
    audit_count = audit_count_after_4
    override_audit = (
        AuditEvent.objects.filter(
            action="portfolio_run_generated",
            entity_id=override_run.external_id,
        )
        .order_by("-created_at")
        .first()
    )
    assert override_audit is not None, (
        "Override trigger must emit a portfolio_run_generated audit on the "
        "newly-created run (different signature from realignment run)."
    )
    assert override_audit.metadata.get("source") == "override", (
        f"Override audit metadata.source must be 'override'; got "
        f"{override_audit.metadata.get('source')!r}"
    )

    # ---- Step 5: helper-direct trigger after household_risk_score
    #              mutation → fresh signature → GENERATED ------------
    hh.refresh_from_db()
    new_hh_risk = 2 if hh.household_risk_score != 2 else 4
    hh.household_risk_score = new_hh_risk
    hh.save(update_fields=["household_risk_score"])
    result_5 = _trigger_and_audit(hh, user, source="manual")
    assert isinstance(result_5, models.PortfolioRun), (
        "Helper must return PortfolioRun on success path"
    )
    run_count_after_5 = models.PortfolioRun.objects.filter(household=hh).count()
    assert run_count_after_5 == run_count + 1
    run_count = run_count_after_5
    audit_count_after_5 = _portfolio_audit_count(hh)
    assert audit_count_after_5 == audit_count + 1
    audit_count = audit_count_after_5
    manual_audit = AuditEvent.objects.filter(
        action="portfolio_run_generated",
        entity_id=result_5.external_id,
    ).first()
    assert manual_audit is not None
    assert manual_audit.metadata.get("source") == "manual"

    # ---- Step 6: same-signature re-fire on result_5 → REUSED -------
    result_6 = _trigger_and_audit(hh, user, source="manual")
    assert isinstance(result_6, models.PortfolioRun)
    assert result_6.pk == result_5.pk, "Same-signature re-fire must REUSE result_5"
    run_count_after_6 = models.PortfolioRun.objects.filter(household=hh).count()
    assert run_count_after_6 == run_count, "REUSED must NOT add a row"
    audit_count_after_6 = _portfolio_audit_count(hh)
    assert audit_count_after_6 == audit_count + 1
    audit_count = audit_count_after_6

    # ---- Final invariants -----------------------------------------
    final_runs = models.PortfolioRun.objects.filter(household=hh).order_by("created_at")
    final_signatures = [r.run_signature for r in final_runs]
    assert len(final_signatures) == len(set(final_signatures)), (
        f"PortfolioRun signatures must be unique per row (append-only); "
        f"got duplicates in {final_signatures}"
    )
    # Six trigger fires total (1 auto-seed + 5 in this test); audit count
    # must equal 6 generated/reused events.
    assert audit_count == 6, (
        f"Expected exactly 6 portfolio_run_* audits across lifecycle; "
        f"got {audit_count}. Failed cumulative-1-per-trigger invariant."
    )
    # Run count must be 4: auto-seed (step 1) + realignment (step 3) +
    # override (step 4, fresh signature post-fix-2026-05-04) + manual
    # (step 5). Steps 2 + 6 were REUSED with no new rows.
    assert run_count == 4, (
        f"Expected 4 distinct PortfolioRuns (auto-seed + realignment + "
        f"override + manual); got {run_count}"
    )

    # PortfolioRunEvent monotonic chain: every run has at least one
    # GENERATED or REGENERATED_AFTER_DECLINE event; only the seeded
    # run has additional REUSED events from steps 2 + 6.
    for run in final_runs:
        events = models.PortfolioRunEvent.objects.filter(portfolio_run=run)
        generated_count = events.filter(
            event_type__in=(
                models.PortfolioRunEvent.EventType.GENERATED,
                models.PortfolioRunEvent.EventType.REGENERATED_AFTER_DECLINE,
            )
        ).count()
        assert generated_count == 1, (
            f"Run {run.external_id} must have exactly 1 "
            f"GENERATED/REGENERATED_AFTER_DECLINE event; got {generated_count}"
        )

    # Final hash sanity: every run has non-empty hash chain (locked #82).
    for run in final_runs:
        assert run.run_signature, f"Run {run.external_id} missing run_signature"
        assert run.input_hash, f"Run {run.external_id} missing input_hash"
        assert run.output_hash, f"Run {run.external_id} missing output_hash"
        assert run.cma_hash, f"Run {run.external_id} missing cma_hash"

    # GoalAccountLink amounts after realignment match what we sent.
    # (Defensive: catches a class of bugs where realignment fires the
    # trigger but the underlying mutation silently no-ops.)
    joint_tfsa_link_to_retirement = models.GoalAccountLink.objects.get(
        goal__external_id="goal_retirement_income",
        account__external_id="acct_joint_tfsa",
    )
    assert joint_tfsa_link_to_retirement.allocated_amount == Decimal("60000.00")
