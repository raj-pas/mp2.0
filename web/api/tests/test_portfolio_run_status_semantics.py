"""Pin the 5 PortfolioRun status semantics + integrity-alert audit emission
contract that Phase A1 frontend stale-state UX depends on.

The status field is a computed SerializerMethodField at
`web/api/serializers.py:_portfolio_run_status`; it returns one of:

    current / invalidated / superseded / declined / hash_mismatch

Each value drives a distinct frontend treatment per locked §3.2:

    invalidated / superseded     → StaleRunOverlay (regenerable)
    declined                     → StaleRunOverlay (regenerable; different copy)
    hash_mismatch                → IntegrityAlertOverlay (engineering-only)

For `hash_mismatch`, the serializer ALSO emits a
`portfolio_run_integrity_alert` AuditEvent on first observation per
(run, advisor) per locked §3.5. Engineering grep this audit log to
diagnose integrity violations.

These tests pin both the status semantics + the audit-emission +
dedup contract so any future serializer change can't silently break
the frontend stale-state surface.

Per locked decisions §3.2 + §3.5 + §3.18.
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


def _bootstrap() -> models.Household:
    """Reset to known synthetic state with auto-seeded PortfolioRun."""
    call_command("seed_default_cma", "--force")
    call_command("load_synthetic_personas")
    return models.Household.objects.get(external_id="hh_sandra_mike_chen")


def _advisor_client() -> tuple[APIClient, User]:
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
    return client, user


def _latest_run(hh: models.Household) -> models.PortfolioRun:
    """Return the household's most recent PortfolioRun."""
    run = hh.portfolio_runs.order_by("-created_at").first()
    assert run is not None, "Auto-seed must have produced a PortfolioRun"
    return run


# ---------------------------------------------------------------------------
# 5 status semantics (one test per status state)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_status_current_when_no_invalidating_events() -> None:
    """Fresh auto-seed run with no events → status='current'."""
    hh = _bootstrap()
    run = _latest_run(hh)
    # Sanity: no INVALIDATED_BY_CMA / HASH_MISMATCH / ADVISOR_DECLINED events.
    assert not run.events.filter(
        event_type__in=[
            models.PortfolioRunEvent.EventType.INVALIDATED_BY_CMA,
            models.PortfolioRunEvent.EventType.HASH_MISMATCH,
            models.PortfolioRunEvent.EventType.ADVISOR_DECLINED,
        ]
    ).exists()
    client, _ = _advisor_client()
    response = client.get(reverse("client-detail", args=[hh.external_id]))
    assert response.status_code == 200
    assert response.json()["latest_portfolio_run"]["status"] == "current"


@pytest.mark.django_db
def test_status_invalidated_after_cma_republish() -> None:
    """INVALIDATED_BY_CMA event → status='invalidated'.

    Mirrors the CMA-publish flow: `_record_current_run_invalidations`
    fires INVALIDATED_BY_CMA on every active run when a new CMA snapshot
    becomes ACTIVE. The frontend reads `status='invalidated'` on the
    next GET and renders `StaleRunOverlay`.
    """
    hh = _bootstrap()
    run = _latest_run(hh)
    models.PortfolioRunEvent.objects.create(
        portfolio_run=run,
        event_type=models.PortfolioRunEvent.EventType.INVALIDATED_BY_CMA,
        reason_code="new_cma_snapshot_published",
        note="Test: simulated CMA republish",
        actor="system",
    )

    client, _ = _advisor_client()
    response = client.get(reverse("client-detail", args=[hh.external_id]))
    assert response.status_code == 200
    assert response.json()["latest_portfolio_run"]["status"] == "invalidated"


@pytest.mark.django_db
def test_status_declined_after_advisor_decline() -> None:
    """ADVISOR_DECLINED event → status='declined'."""
    hh = _bootstrap()
    run = _latest_run(hh)
    models.PortfolioRunEvent.objects.create(
        portfolio_run=run,
        event_type=models.PortfolioRunEvent.EventType.ADVISOR_DECLINED,
        reason_code="not_aligned_with_kyc",
        note="Test: advisor declined the run",
        actor="advisor@example.com",
    )

    client, _ = _advisor_client()
    response = client.get(reverse("client-detail", args=[hh.external_id]))
    assert response.json()["latest_portfolio_run"]["status"] == "declined"


@pytest.mark.django_db
def test_status_hash_mismatch_when_event_present() -> None:
    """HASH_MISMATCH event → status='hash_mismatch'."""
    hh = _bootstrap()
    run = _latest_run(hh)
    models.PortfolioRunEvent.objects.create(
        portfolio_run=run,
        event_type=models.PortfolioRunEvent.EventType.HASH_MISMATCH,
        reason_code="output_hash_drift",
        note="Test: simulated integrity violation",
        actor="system",
    )

    client, _ = _advisor_client()
    response = client.get(reverse("client-detail", args=[hh.external_id]))
    assert response.json()["latest_portfolio_run"]["status"] == "hash_mismatch"


@pytest.mark.django_db
def test_status_invalidated_does_not_block_subsequent_runs() -> None:
    """Per-run invalidation; subsequent runs start at status='current'."""
    hh = _bootstrap()
    run = _latest_run(hh)
    models.PortfolioRunEvent.objects.create(
        portfolio_run=run,
        event_type=models.PortfolioRunEvent.EventType.INVALIDATED_BY_CMA,
        reason_code="new_cma_snapshot_published",
        actor="system",
    )

    # Re-publish CMA + re-trigger generation.
    from web.api.views import _trigger_portfolio_generation

    new_run = _trigger_portfolio_generation(hh, user=None, source="manual")
    assert new_run is not None
    assert new_run.id != run.id, "Helper should produce a NEW run after invalidation"

    client, _ = _advisor_client()
    response = client.get(reverse("client-detail", args=[hh.external_id]))
    body = response.json()
    # latest_portfolio_run is the NEW one; its status is 'current'.
    assert body["latest_portfolio_run"]["external_id"] == new_run.external_id
    assert body["latest_portfolio_run"]["status"] == "current"


# ---------------------------------------------------------------------------
# Integrity-alert audit emission contract (locked §3.5)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_hash_mismatch_emits_integrity_alert_audit_event() -> None:
    """First GET on a hash_mismatch run emits one AuditEvent."""
    hh = _bootstrap()
    run = _latest_run(hh)
    models.PortfolioRunEvent.objects.create(
        portfolio_run=run,
        event_type=models.PortfolioRunEvent.EventType.HASH_MISMATCH,
        reason_code="output_hash_drift",
        actor="system",
    )

    before = AuditEvent.objects.filter(action="portfolio_run_integrity_alert").count()
    client, _ = _advisor_client()
    response = client.get(reverse("client-detail", args=[hh.external_id]))
    assert response.status_code == 200
    after = AuditEvent.objects.filter(action="portfolio_run_integrity_alert").count()
    assert after - before == 1, (
        f"Exactly one portfolio_run_integrity_alert audit must be emitted "
        f"on first GET observing hash_mismatch; got delta={after - before}"
    )

    # Pin metadata shape (engineering greps this).
    audit = AuditEvent.objects.filter(action="portfolio_run_integrity_alert").latest("created_at")
    assert audit.entity_type == "portfolio_run"
    assert audit.entity_id == run.external_id
    assert audit.actor == "advisor@example.com"
    assert audit.metadata["run_external_id"] == run.external_id
    assert audit.metadata["household_id"] == hh.external_id
    assert audit.metadata["status"] == "hash_mismatch"
    assert "engine_version" in audit.metadata


@pytest.mark.django_db
def test_hash_mismatch_audit_emission_dedups_per_run_advisor() -> None:
    """Repeated GETs on same (run, advisor) emit the audit ONCE.

    Per locked §3.5 + the dedup pattern at
    `views._record_current_run_invalidations` (events.filter(...).exists()).
    Without dedup, every advisor page-load would inflate the audit table.
    """
    hh = _bootstrap()
    run = _latest_run(hh)
    models.PortfolioRunEvent.objects.create(
        portfolio_run=run,
        event_type=models.PortfolioRunEvent.EventType.HASH_MISMATCH,
        reason_code="output_hash_drift",
        actor="system",
    )

    before = AuditEvent.objects.filter(action="portfolio_run_integrity_alert").count()
    client, _ = _advisor_client()
    # Hit the endpoint 3 times — simulates multiple page loads.
    for _ in range(3):
        response = client.get(reverse("client-detail", args=[hh.external_id]))
        assert response.status_code == 200
    after = AuditEvent.objects.filter(action="portfolio_run_integrity_alert").count()

    assert after - before == 1, (
        f"Dedup violated: 3 GETs produced {after - before} audit rows. "
        f"Expected exactly 1 per (run, advisor) per locked §3.5."
    )


@pytest.mark.django_db
def test_hash_mismatch_audit_emits_per_distinct_advisor() -> None:
    """Two distinct advisors observing the same hash_mismatch run each
    emit one audit row (dedup is per-advisor, not global).
    """
    hh = _bootstrap()
    run = _latest_run(hh)
    models.PortfolioRunEvent.objects.create(
        portfolio_run=run,
        event_type=models.PortfolioRunEvent.EventType.HASH_MISMATCH,
        reason_code="output_hash_drift",
        actor="system",
    )

    # Advisor A
    advisor_a, _ = User.objects.get_or_create(
        username="advisor_a@example.com",
        defaults={"email": "advisor_a@example.com"},
    )
    group, _ = Group.objects.get_or_create(name="advisor")
    advisor_a.groups.add(group)
    client_a = APIClient()
    client_a.force_authenticate(user=advisor_a)

    # Advisor B
    advisor_b, _ = User.objects.get_or_create(
        username="advisor_b@example.com",
        defaults={"email": "advisor_b@example.com"},
    )
    advisor_b.groups.add(group)
    client_b = APIClient()
    client_b.force_authenticate(user=advisor_b)

    before = AuditEvent.objects.filter(action="portfolio_run_integrity_alert").count()
    response_a = client_a.get(reverse("client-detail", args=[hh.external_id]))
    response_b = client_b.get(reverse("client-detail", args=[hh.external_id]))
    response_a2 = client_a.get(reverse("client-detail", args=[hh.external_id]))
    after = AuditEvent.objects.filter(action="portfolio_run_integrity_alert").count()

    assert response_a.status_code == 200
    assert response_b.status_code == 200
    assert response_a2.status_code == 200
    assert after - before == 2, (
        f"Per-advisor dedup violated: 2 advisors + 1 repeat = {after - before} "
        f"audit rows; expected exactly 2 (one per distinct advisor)."
    )

    actors = set(
        AuditEvent.objects.filter(
            action="portfolio_run_integrity_alert",
            entity_id=run.external_id,
        ).values_list("actor", flat=True)
    )
    assert actors == {"advisor_a@example.com", "advisor_b@example.com"}, (
        f"Audit actors should match the 2 advisors; got {actors}"
    )
