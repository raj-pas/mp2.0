"""Sub-session #11.1 — audit-timeline endpoint tests.

The audit-timeline endpoint surfaces append-only ``AuditEvent``
rows for a workspace. The advisor uses this to understand what
happened on a workspace (commits / approvals / fact overrides /
conflict resolutions) without needing analyst access.
"""

from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from web.api import models
from web.api.tests.test_review_ingestion import _user
from web.audit.models import AuditEvent


@pytest.mark.django_db
def test_audit_timeline_returns_events_in_chronological_order(tmp_path, settings) -> None:
    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(label="Audit ws", owner=user)
    AuditEvent.objects.create(
        actor=user.email,
        action="review_section_approved",
        entity_type="review_workspace",
        entity_id=workspace.external_id,
        metadata={"section": "household"},
    )
    AuditEvent.objects.create(
        actor=user.email,
        action="review_fact_overridden",
        entity_type="review_workspace",
        entity_id=workspace.external_id,
        metadata={"field": "people[0].date_of_birth"},
    )

    response = client.get(reverse("review-workspace-audit-timeline", args=[workspace.external_id]))

    assert response.status_code == 200
    events = response.json()["events"]
    assert len(events) == 2
    # Newest first per AuditEvent.Meta.ordering
    assert events[0]["action"] == "review_fact_overridden"
    assert events[1]["action"] == "review_section_approved"
    # Real-PII safety: metadata flows back; the advisor is already
    # authenticated for this workspace's data.
    assert events[0]["metadata"]["field"] == "people[0].date_of_birth"


@pytest.mark.django_db
def test_audit_timeline_only_returns_events_for_this_workspace(tmp_path, settings) -> None:
    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    ws_a = models.ReviewWorkspace.objects.create(label="A", owner=user)
    ws_b = models.ReviewWorkspace.objects.create(label="B", owner=user)
    AuditEvent.objects.create(
        actor=user.email,
        action="review_section_approved",
        entity_type="review_workspace",
        entity_id=ws_a.external_id,
        metadata={"section": "household"},
    )
    AuditEvent.objects.create(
        actor=user.email,
        action="review_section_approved",
        entity_type="review_workspace",
        entity_id=ws_b.external_id,
        metadata={"section": "household"},
    )

    response = client.get(reverse("review-workspace-audit-timeline", args=[ws_a.external_id]))

    assert response.status_code == 200
    events = response.json()["events"]
    assert len(events) == 1
    assert events[0]["entity_id"] == ws_a.external_id


@pytest.mark.django_db
def test_audit_timeline_returns_empty_for_workspace_without_events(tmp_path, settings) -> None:
    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(label="Empty", owner=user)

    response = client.get(reverse("review-workspace-audit-timeline", args=[workspace.external_id]))

    assert response.status_code == 200
    assert response.json()["events"] == []


@pytest.mark.django_db
def test_audit_timeline_caps_at_100_events(tmp_path, settings) -> None:
    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(label="Audit ws", owner=user)
    for i in range(150):
        AuditEvent.objects.create(
            actor=user.email,
            action="review_section_approved",
            entity_type="review_workspace",
            entity_id=workspace.external_id,
            metadata={"section": f"section-{i}"},
        )

    response = client.get(reverse("review-workspace-audit-timeline", args=[workspace.external_id]))

    assert response.status_code == 200
    events = response.json()["events"]
    assert len(events) == 100
