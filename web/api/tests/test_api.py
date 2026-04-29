from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse
from rest_framework.test import APIClient
from web.api.models import Household
from web.audit.models import AuditEvent


@pytest.mark.django_db
def test_client_list_returns_synthetic_persona() -> None:
    call_command("load_synthetic_personas")
    client = _authenticated_client()

    response = client.get(reverse("client-list"))

    assert response.status_code == 200
    assert response.json()[0]["id"] == "hh_sandra_mike_chen"


@pytest.mark.django_db
def test_client_detail_includes_summary_financial_fields() -> None:
    call_command("load_synthetic_personas")
    client = _authenticated_client()

    response = client.get(reverse("client-detail", args=["hh_sandra_mike_chen"]))

    assert response.status_code == 200
    payload = response.json()
    assert payload["goal_count"] == 3
    assert payload["total_assets"] == 1_280_000


@pytest.mark.django_db
def test_generate_portfolio_runs_engine_and_writes_audit() -> None:
    call_command("load_synthetic_personas")
    client = _authenticated_client()

    response = client.post(reverse("generate-portfolio", args=["hh_sandra_mike_chen"]))

    assert response.status_code == 200
    payload = response.json()
    assert payload["household_id"] == "hh_sandra_mike_chen"
    assert payload["goal_blends"]
    assert AuditEvent.objects.filter(action="engine_run").exists()
    assert Household.objects.get(external_id="hh_sandra_mike_chen").last_engine_output


def _authenticated_client() -> APIClient:
    User = get_user_model()
    user = User.objects.create_user(
        username="advisor@example.com", email="advisor@example.com", password="pw"
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client
