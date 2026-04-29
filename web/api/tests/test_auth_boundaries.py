from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from web.api import models

PROTECTED_DENIED = {401, 403}


@pytest.mark.django_db
def test_client_api_requires_authentication() -> None:
    household = _household("shared_household")
    client = APIClient()

    responses = [
        client.get(reverse("client-list")),
        client.get(reverse("client-detail", args=[household.external_id])),
        client.post(reverse("generate-portfolio", args=[household.external_id]), {}),
    ]

    assert {response.status_code for response in responses} <= PROTECTED_DENIED


@pytest.mark.django_db
def test_review_api_requires_authentication(tmp_path, settings) -> None:
    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    owner = _user("owner@example.com")
    workspace = models.ReviewWorkspace.objects.create(label="Owned review", owner=owner)
    client = APIClient()

    responses = [
        client.get(reverse("review-workspace-list")),
        client.get(reverse("review-workspace-detail", args=[workspace.external_id])),
        client.post(reverse("review-workspace-upload", args=[workspace.external_id]), {}),
    ]

    assert {response.status_code for response in responses} <= PROTECTED_DENIED


@pytest.mark.django_db
def test_authenticated_client_list_is_scoped_to_user_or_shared_households() -> None:
    advisor = _user("advisor@example.com")
    other_advisor = _user("other@example.com")
    shared = _household("shared_household")
    owned = _household("owned_household", owner=advisor)
    other = _household("other_household", owner=other_advisor)
    client = APIClient()
    client.force_authenticate(user=advisor)

    list_response = client.get(reverse("client-list"))
    visible_ids = {item["id"] for item in list_response.json()}

    assert list_response.status_code == 200
    assert shared.external_id in visible_ids
    assert owned.external_id in visible_ids
    assert other.external_id not in visible_ids
    assert client.get(reverse("client-detail", args=[owned.external_id])).status_code == 200
    assert client.get(reverse("client-detail", args=[other.external_id])).status_code == 404


@pytest.mark.django_db
def test_review_commit_creates_user_owned_household(tmp_path, settings) -> None:
    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    advisor = _user("advisor@example.com")
    client = APIClient()
    client.force_authenticate(user=advisor)
    workspace = models.ReviewWorkspace.objects.create(label="Ready review", owner=advisor)
    workspace.reviewed_state = _engine_ready_state()
    workspace.readiness = {
        "engine_ready": True,
        "kyc_compliance_ready": True,
        "missing": [],
    }
    workspace.save()

    response = client.post(reverse("review-workspace-commit", args=[workspace.external_id]), {})

    assert response.status_code == 200
    household = models.Household.objects.get(external_id=response.json()["household_id"])
    assert household.owner == advisor


@pytest.mark.django_db
def test_review_commit_cannot_link_another_users_household(tmp_path, settings) -> None:
    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    advisor = _user("advisor@example.com")
    other_advisor = _user("other@example.com")
    other_household = _household("other_household", owner=other_advisor)
    client = APIClient()
    client.force_authenticate(user=advisor)
    workspace = models.ReviewWorkspace.objects.create(label="Ready review", owner=advisor)
    workspace.reviewed_state = _engine_ready_state()
    workspace.readiness = {
        "engine_ready": True,
        "kyc_compliance_ready": True,
        "missing": [],
    }
    workspace.save()

    response = client.post(
        reverse("review-workspace-commit", args=[workspace.external_id]),
        {"household_id": other_household.external_id},
        format="json",
    )

    assert response.status_code == 404


def _user(email: str):
    User = get_user_model()
    return User.objects.create_user(username=email, email=email, password="pw")


def _household(external_id: str, *, owner=None) -> models.Household:
    return models.Household.objects.create(
        external_id=external_id,
        owner=owner,
        display_name=external_id.replace("_", " ").title(),
        household_type="single",
        household_risk_score=3,
    )


def _engine_ready_state() -> dict:
    return {
        "schema_version": "reviewed_client_state.v1",
        "household": {
            "display_name": "Ready Household",
            "household_type": "couple",
            "household_risk_score": 3,
        },
        "people": [{"id": "person_ready_auth", "name": "Ready Client", "age": 62}],
        "accounts": [
            {
                "id": "acct_ready_auth",
                "type": "RRSP",
                "current_value": 100000,
                "missing_holdings_confirmed": True,
            }
        ],
        "goals": [{"id": "goal_ready_auth", "name": "Retirement", "time_horizon_years": 5}],
        "goal_account_links": [
            {
                "goal_id": "goal_ready_auth",
                "account_id": "acct_ready_auth",
                "allocated_amount": 100000,
            }
        ],
        "risk": {"household_score": 3},
    }
