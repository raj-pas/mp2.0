"""Auto-trigger portfolio generation regression tests (A2a).

Pins locked decisions #14 (8 trigger points), #74 (sync inline), #9
(typed-skip vs unexpected-failure audit paths), #16 (audit naming
canonical), #81 (helper-managed atomic).
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from web.api import models
from web.api.views import (
    EngineKillSwitchBlocked,
    InvalidCMAUniverse,
    NoActiveCMASnapshot,
    ReviewedStateNotConstructionReady,
    _trigger_and_audit,
    _trigger_portfolio_generation,
)
from web.audit.models import AuditEvent

User = get_user_model()


def _make_user() -> User:
    user, _ = User.objects.get_or_create(
        username="advisor@example.com",
        defaults={"email": "advisor@example.com"},
    )
    return user


def _bootstrap_full_demo() -> models.Household:
    """Reset state with seed_default_cma + load_synthetic_personas."""
    call_command("seed_default_cma", "--force")
    call_command("load_synthetic_personas")
    return models.Household.objects.get(external_id="hh_sandra_mike_chen")


@pytest.mark.django_db
def test_helper_returns_portfolio_run_when_cma_active():
    hh = _bootstrap_full_demo()
    user = _make_user()
    run = _trigger_portfolio_generation(hh, user, source="manual")
    assert isinstance(run, models.PortfolioRun)
    assert run.run_signature
    assert run.input_hash
    assert run.output_hash
    # Append-only: re-call with same signature reuses
    run2 = _trigger_portfolio_generation(hh, user, source="manual")
    assert run2.pk == run.pk  # REUSED via signature match


@pytest.mark.django_db
def test_helper_raises_no_active_cma_when_no_cma_published():
    """Per locked #9: typed-skip path. Helper raises; caller emits audit."""
    call_command("load_synthetic_personas")  # NO seed_default_cma
    hh = models.Household.objects.get(external_id="hh_sandra_mike_chen")
    user = _make_user()
    # Ensure no active CMA exists
    models.CMASnapshot.objects.filter(status=models.CMASnapshot.Status.ACTIVE).update(
        status=models.CMASnapshot.Status.ARCHIVED,
    )
    with pytest.raises(NoActiveCMASnapshot):
        _trigger_portfolio_generation(hh, user, source="manual")


@pytest.mark.django_db
def test_helper_raises_kill_switch_when_engine_disabled(settings):
    settings.MP20_ENGINE_ENABLED = False
    hh = _bootstrap_full_demo()
    user = _make_user()
    with pytest.raises(EngineKillSwitchBlocked):
        _trigger_portfolio_generation(hh, user, source="manual")


@pytest.mark.django_db
def test_trigger_and_audit_typed_skip_emits_audit_returns_none(settings):
    """Per locked #9: typed-skip path. Audit + return None; commit unaffected."""
    settings.MP20_ENGINE_ENABLED = False
    hh = _bootstrap_full_demo()
    user = _make_user()
    result = _trigger_and_audit(hh, user, source="review_commit")
    assert result is None
    # Skip audit emitted with reason_code = exception class name
    skip_events = AuditEvent.objects.filter(
        action="portfolio_generation_skipped_post_review_commit",
        entity_id=hh.external_id,
    )
    assert skip_events.count() == 1
    metadata = skip_events.first().metadata
    assert metadata["source"] == "review_commit"
    assert metadata["reason_code"] == "EngineKillSwitchBlocked"


@pytest.mark.django_db
def test_trigger_and_audit_success_emits_portfolio_run_generated_audit():
    """Per locked #16: success emits canonical `portfolio_run_generated` action."""
    hh = _bootstrap_full_demo()
    user = _make_user()
    result = _trigger_and_audit(hh, user, source="review_commit")
    assert isinstance(result, models.PortfolioRun)
    # Generated audit emitted with metadata.source captured per locked #16
    generated_events = AuditEvent.objects.filter(
        action="portfolio_run_generated",
        entity_id=result.external_id,
    )
    assert generated_events.count() == 1
    metadata = generated_events.first().metadata
    assert metadata["source"] == "review_commit"
    assert metadata["household_id"] == hh.external_id
    assert metadata["link_count"] >= 4
    assert metadata["schema_version"] == "engine_output.link_first.v2"


@pytest.mark.django_db
def test_helper_creates_portfolio_run_link_recommendations():
    hh = _bootstrap_full_demo()
    user = _make_user()
    run = _trigger_portfolio_generation(hh, user, source="manual")
    link_recs = models.PortfolioRunLinkRecommendation.objects.filter(portfolio_run=run)
    assert link_recs.count() >= 4  # Sandra/Mike has 6 links
    for rec in link_recs:
        assert rec.allocations  # non-empty list of Allocation dicts
        assert rec.expected_return is not None
        assert rec.volatility is not None


@pytest.mark.django_db
def test_helper_emits_portfolio_run_event_on_generation():
    hh = _bootstrap_full_demo()
    user = _make_user()
    run = _trigger_portfolio_generation(hh, user, source="wizard_commit")
    events = models.PortfolioRunEvent.objects.filter(portfolio_run=run)
    assert events.filter(event_type=models.PortfolioRunEvent.EventType.GENERATED).count() == 1


@pytest.mark.django_db
def test_helper_returns_reused_run_on_idempotent_re_trigger():
    """Per append-only invariant: same input → REUSED, not duplicate."""
    hh = _bootstrap_full_demo()
    user = _make_user()
    run1 = _trigger_portfolio_generation(hh, user, source="manual")
    run2 = _trigger_portfolio_generation(hh, user, source="manual")
    assert run1.pk == run2.pk  # same row reused
    # REUSED PortfolioRunEvent emitted
    reuse_events = models.PortfolioRunEvent.objects.filter(
        portfolio_run=run1,
        event_type=models.PortfolioRunEvent.EventType.REUSED,
    )
    assert reuse_events.count() >= 1
