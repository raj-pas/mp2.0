"""Phase 5b chrome tests (banner + feedback + tour + worker health).

Covers:
  * POST /api/disclaimer/acknowledge/ — version captured + audit emitted.
  * POST /api/tour/complete/ — idempotent server-side ack + audit.
  * POST /api/feedback/ — feedback row persisted + structured PII-safe.
  * GET /api/feedback/report/ — analyst-only RBAC + filters + CSV export.
  * PATCH /api/feedback/<id>/ — analyst-only triage + audit emission.
  * Session payload exposes disclaimer + tour state for FE gating.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework.test import APIClient
from web.api import models
from web.api.access import FINANCIAL_ANALYST_GROUP
from web.audit.models import AuditEvent


def _user(email: str = "advisor@example.com"):
    User = get_user_model()
    user, _ = User.objects.get_or_create(
        email=email,
        defaults={"username": email, "is_active": True},
    )
    return user


def _analyst(email: str = "analyst@example.com"):
    user = _user(email)
    group, _ = Group.objects.get_or_create(name=FINANCIAL_ANALYST_GROUP)
    user.groups.add(group)
    return user


# -----------------------------------------------------------------------
# Disclaimer ack
# -----------------------------------------------------------------------


@pytest.mark.django_db
def test_disclaimer_acknowledge_persists_version_and_emits_audit() -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("disclaimer-acknowledge")
    response = client.post(url, {"version": "v1"}, format="json")
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "v1"
    assert "acknowledged_at" in body

    profile = models.AdvisorProfile.objects.get(user=user)
    assert profile.disclaimer_acknowledged_version == "v1"
    assert profile.disclaimer_acknowledged_at is not None

    events = AuditEvent.objects.filter(
        action="disclaimer_acknowledged", entity_id=str(user.pk)
    )
    assert events.count() == 1
    metadata = events.first().metadata
    assert metadata["version"] == "v1"
    assert metadata["advisor_id"] == user.pk


@pytest.mark.django_db
def test_disclaimer_acknowledge_validates_version() -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("disclaimer-acknowledge")
    r = client.post(url, {}, format="json")
    assert r.status_code == 400 and r.json()["code"] == "version_required"
    r = client.post(url, {"version": "x" * 20}, format="json")
    assert r.status_code == 400 and r.json()["code"] == "version_too_long"


@pytest.mark.django_db
def test_session_payload_exposes_disclaimer_and_tour_state() -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(reverse("session"))
    assert response.status_code == 200
    body = response.json()
    user_block = body["user"]
    # No profile yet -> nulls / empty
    assert user_block["disclaimer_acknowledged_at"] is None
    assert user_block["disclaimer_acknowledged_version"] == ""
    assert user_block["tour_completed_at"] is None

    # After acknowledgement, the session reflects it
    client.post(reverse("disclaimer-acknowledge"), {"version": "v1"}, format="json")
    client.post(reverse("tour-complete"), {}, format="json")
    response2 = client.get(reverse("session"))
    user_block2 = response2.json()["user"]
    assert user_block2["disclaimer_acknowledged_version"] == "v1"
    assert user_block2["disclaimer_acknowledged_at"] is not None
    assert user_block2["tour_completed_at"] is not None


# -----------------------------------------------------------------------
# Tour complete
# -----------------------------------------------------------------------


@pytest.mark.django_db
def test_tour_complete_persists_and_emits_audit() -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(reverse("tour-complete"), {}, format="json")
    assert response.status_code == 200
    body = response.json()
    assert body["completed_at"]

    profile = models.AdvisorProfile.objects.get(user=user)
    assert profile.tour_completed_at is not None

    events = AuditEvent.objects.filter(
        action="tour_completed", entity_id=str(user.pk)
    )
    assert events.count() == 1


@pytest.mark.django_db
def test_tour_complete_is_idempotent_and_emits_only_once() -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)

    client.post(reverse("tour-complete"), {}, format="json")
    client.post(reverse("tour-complete"), {}, format="json")  # second call

    events = AuditEvent.objects.filter(
        action="tour_completed", entity_id=str(user.pk)
    )
    assert events.count() == 1, "second tour-complete must NOT emit an audit event"


# -----------------------------------------------------------------------
# Feedback submit
# -----------------------------------------------------------------------


@pytest.mark.django_db
def test_feedback_submit_persists_row_and_emits_audit() -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)

    payload = {
        "severity": "friction",
        "description": "The doc-drop overlay closed unexpectedly during upload.",
        "what_were_you_trying": "Uploading 3 KYC PDFs at once.",
        "route": "/review",
        "session_id": "sess-abc",
    }
    response = client.post(reverse("feedback-submit"), payload, format="json")
    assert response.status_code == 201
    feedback_id = response.json()["id"]

    feedback = models.Feedback.objects.get(pk=feedback_id)
    assert feedback.advisor == user
    assert feedback.severity == "friction"
    assert feedback.description.startswith("The doc-drop")
    assert feedback.status == "new"

    events = AuditEvent.objects.filter(
        action="feedback_submitted", entity_id=str(feedback.pk)
    )
    assert events.count() == 1


@pytest.mark.django_db
def test_feedback_submit_validates_payload() -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)

    url = reverse("feedback-submit")

    r = client.post(
        url,
        {"severity": "lol", "description": "x" * 30, "route": "/x"},
        format="json",
    )
    assert r.status_code == 400 and r.json()["code"] == "severity_invalid"

    r = client.post(
        url,
        {"severity": "friction", "description": "too short", "route": "/x"},
        format="json",
    )
    assert r.status_code == 400 and r.json()["code"] == "description_too_short"


# -----------------------------------------------------------------------
# Feedback report (analyst-only)
# -----------------------------------------------------------------------


@pytest.mark.django_db
def test_feedback_report_requires_analyst_role() -> None:
    advisor = _user()
    client = APIClient()
    client.force_authenticate(user=advisor)
    response = client.get(reverse("feedback-report"))
    assert response.status_code == 403
    assert response.json()["code"] == "analyst_required"


@pytest.mark.django_db
def test_feedback_report_filters_by_status_and_severity() -> None:
    advisor = _user("a@example.com")
    other = _user("b@example.com")
    models.Feedback.objects.create(
        advisor=advisor,
        severity="blocking",
        description="A " * 20,
        route="/r",
    )
    models.Feedback.objects.create(
        advisor=other,
        severity="friction",
        description="B " * 20,
        route="/r",
        status="closed",
    )
    analyst = _analyst()
    client = APIClient()
    client.force_authenticate(user=analyst)

    response = client.get(reverse("feedback-report"))
    assert response.status_code == 200
    rows = response.json()["rows"]
    assert len(rows) == 2

    response = client.get(
        reverse("feedback-report"), {"severity": "blocking"}
    )
    rows = response.json()["rows"]
    assert len(rows) == 1
    assert rows[0]["severity"] == "blocking"

    response = client.get(reverse("feedback-report"), {"status": "closed"})
    rows = response.json()["rows"]
    assert len(rows) == 1
    assert rows[0]["status"] == "closed"


@pytest.mark.django_db
def test_feedback_report_csv_export() -> None:
    advisor = _user()
    models.Feedback.objects.create(
        advisor=advisor,
        severity="suggestion",
        description="C " * 20,
        route="/r",
    )
    analyst = _analyst()
    client = APIClient()
    client.force_authenticate(user=analyst)

    response = client.get(reverse("feedback-report"), {"export": "csv"})
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/csv")
    text = response.content.decode()
    assert "id,advisor,severity,status" in text
    assert "suggestion" in text


# -----------------------------------------------------------------------
# Feedback update (analyst triage)
# -----------------------------------------------------------------------


@pytest.mark.django_db
def test_feedback_update_emits_audit_event() -> None:
    advisor = _user()
    feedback = models.Feedback.objects.create(
        advisor=advisor,
        severity="friction",
        description="x " * 20,
        route="/r",
    )
    analyst = _analyst()
    client = APIClient()
    client.force_authenticate(user=analyst)

    url = reverse("feedback-update", args=[feedback.pk])
    response = client.patch(
        url,
        {"status": "triaged", "ops_notes": "Re-tested; root cause known."},
        format="json",
    )
    assert response.status_code == 200
    feedback.refresh_from_db()
    assert feedback.status == "triaged"
    assert feedback.ops_notes.startswith("Re-tested")

    events = AuditEvent.objects.filter(
        action="feedback_triaged", entity_id=str(feedback.pk)
    )
    assert events.count() == 1
    metadata = events.first().metadata
    assert metadata["new_status"] == "triaged"
    assert "status" in metadata["fields_updated"]
    assert "ops_notes" in metadata["fields_updated"]


@pytest.mark.django_db
def test_feedback_update_requires_analyst_role() -> None:
    advisor = _user()
    feedback = models.Feedback.objects.create(
        advisor=advisor,
        severity="friction",
        description="x " * 20,
        route="/r",
    )
    client = APIClient()
    client.force_authenticate(user=advisor)
    url = reverse("feedback-update", args=[feedback.pk])
    response = client.patch(url, {"status": "triaged"}, format="json")
    assert response.status_code == 403
