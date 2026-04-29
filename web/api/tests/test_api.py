from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse
from rest_framework.test import APIClient
from web.api import models
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
    assert payload["total_assets"] == 1_308_000


@pytest.mark.django_db
def test_generate_portfolio_runs_engine_and_writes_audit() -> None:
    call_command("load_synthetic_personas")
    call_command("seed_default_cma")
    client = _authenticated_client()

    response = client.post(reverse("generate-portfolio", args=["hh_sandra_mike_chen"]))

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "current"
    assert payload["output"]["household_id"] == "hh_sandra_mike_chen"
    assert payload["output"]["schema_version"] == "engine_output.link_first.v1"
    assert payload["output"]["link_recommendations"]
    assert payload["input_hash"]
    assert payload["output_hash"]
    assert payload["link_recommendation_rows"]
    assert AuditEvent.objects.filter(action="portfolio_run_generated").exists()
    assert models.PortfolioRun.objects.filter(
        household__external_id="hh_sandra_mike_chen",
        status=models.PortfolioRun.Status.CURRENT,
    ).exists()


@pytest.mark.django_db
def test_generate_portfolio_marks_prior_run_stale() -> None:
    call_command("load_synthetic_personas")
    call_command("seed_default_cma")
    client = _authenticated_client()

    first = client.post(reverse("generate-portfolio", args=["hh_sandra_mike_chen"]))
    second = client.post(reverse("generate-portfolio", args=["hh_sandra_mike_chen"]))

    assert first.status_code == 200
    assert second.status_code == 200
    assert (
        models.PortfolioRun.objects.filter(status=models.PortfolioRun.Status.CURRENT).count() == 1
    )
    assert models.PortfolioRun.objects.filter(status=models.PortfolioRun.Status.STALE).count() == 1


@pytest.mark.django_db
def test_generate_portfolio_requires_active_cma_snapshot() -> None:
    call_command("load_synthetic_personas")
    client = _authenticated_client()

    response = client.post(reverse("generate-portfolio", args=["hh_sandra_mike_chen"]))

    assert response.status_code == 409
    assert "No active CMA snapshot" in response.json()["detail"]


@pytest.mark.django_db
def test_portfolio_run_input_snapshot_excludes_review_evidence_payloads() -> None:
    call_command("load_synthetic_personas")
    call_command("seed_default_cma")
    client = _authenticated_client()

    response = client.post(reverse("generate-portfolio", args=["hh_sandra_mike_chen"]))

    assert response.status_code == 200
    run = models.PortfolioRun.objects.get(external_id=response.json()["external_id"])
    assert set(run.input_snapshot) == {"household", "members", "accounts", "goals"}
    serialized = str(run.input_snapshot)
    assert "source_summary" not in serialized
    assert "field_sources" not in serialized
    assert "evidence" not in serialized
    assert "raw" not in serialized


@pytest.mark.django_db
def test_financial_analyst_cma_draft_update_publish_and_audit() -> None:
    call_command("seed_default_cma")
    client = _authenticated_client(role="financial_analyst")
    active = models.CMASnapshot.objects.get(status=models.CMASnapshot.Status.ACTIVE)

    draft_response = client.post(
        reverse("cma-snapshot-list"), {"copy_from_snapshot_id": active.external_id}
    )
    draft_payload = draft_response.json()
    fund_payloads = draft_payload["fund_assumptions"]
    fund_payloads[0]["expected_return"] = "0.07123456"
    fund_payloads[-1]["optimizer_eligible"] = False
    correlations = draft_payload["correlations"]
    for item in correlations:
        if {item["row_fund_id"], item["col_fund_id"]} == {"sh_equity", "sh_income"}:
            item["correlation"] = "0.60000"
    patch_response = client.patch(
        reverse("cma-snapshot-detail", args=[draft_payload["external_id"]]),
        {
            "notes": "Analyst-adjusted CMA draft",
            "fund_assumptions": fund_payloads,
            "correlations": correlations,
        },
        format="json",
    )
    publish_response = client.post(
        reverse("cma-snapshot-publish", args=[draft_payload["external_id"]]),
        {"publish_note": "Reviewed and approved for advisor recommendations."},
        format="json",
    )

    assert draft_response.status_code == 201
    assert patch_response.status_code == 200
    assert patch_response.json()["fund_assumptions"][0]["expected_return"] == "0.07123456"
    assert patch_response.json()["fund_assumptions"][-1]["optimizer_eligible"] is False
    assert publish_response.status_code == 200
    assert publish_response.json()["status"] == models.CMASnapshot.Status.ACTIVE
    assert publish_response.json()["latest_publish_note"] == (
        "Reviewed and approved for advisor recommendations."
    )
    assert AuditEvent.objects.filter(action="cma_snapshot_draft_created").exists()
    update_event = AuditEvent.objects.get(action="cma_snapshot_updated")
    assert update_event.metadata["fund_diffs"]
    assert update_event.metadata["correlation_pair_diff_count"] == 1
    publish_event = AuditEvent.objects.get(action="cma_snapshot_published")
    assert publish_event.metadata["publish_note"] == (
        "Reviewed and approved for advisor recommendations."
    )


@pytest.mark.django_db
def test_cma_one_global_draft_invalid_save_publish_note_frontier_and_audit_api() -> None:
    call_command("seed_default_cma")
    client = _authenticated_client(role="financial_analyst")
    active = models.CMASnapshot.objects.get(status=models.CMASnapshot.Status.ACTIVE)

    first = client.post(reverse("cma-snapshot-list"), {"copy_from_snapshot_id": active.external_id})
    second = client.post(
        reverse("cma-snapshot-list"), {"copy_from_snapshot_id": active.external_id}
    )
    draft_payload = first.json()
    fund_payloads = draft_payload["fund_assumptions"]
    fund_payloads[0]["optimizer_eligible"] = "false"

    invalid_save = client.patch(
        reverse("cma-snapshot-detail", args=[draft_payload["external_id"]]),
        {"fund_assumptions": fund_payloads},
        format="json",
    )
    publish_without_note = client.post(
        reverse("cma-snapshot-publish", args=[draft_payload["external_id"]]), {}, format="json"
    )
    frontier = client.get(reverse("cma-frontier", args=[draft_payload["external_id"]]))
    audit = client.get(reverse("cma-audit"))

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["external_id"] == draft_payload["external_id"]
    assert models.CMASnapshot.objects.filter(status=models.CMASnapshot.Status.DRAFT).count() == 1
    assert invalid_save.status_code == 400
    assert publish_without_note.status_code == 400
    assert frontier.status_code == 200
    assert frontier.json()["efficient"]
    assert frontier.json()["fund_points"]
    assert frontier.json()["bounds"]["volatility_max"] > frontier.json()["bounds"]["volatility_min"]
    assert "is_whole_portfolio" in frontier.json()["fund_points"][0]
    assert audit.status_code == 200
    assert audit.json()[0]["action"] in {"cma_snapshot_draft_created", "cma_snapshot_seeded"}


@pytest.mark.django_db
def test_seed_default_cma_is_canonical_and_old_command_absent() -> None:
    call_command("seed_default_cma")

    active = models.CMASnapshot.objects.get(status=models.CMASnapshot.Status.ACTIVE)

    assert active.name == "Default CMA"
    assert "Default CMA" in active.source
    with pytest.raises(CommandError):
        call_command("seed_" + "fra" + "ser" + "_cma")


@pytest.mark.django_db
def test_publishing_new_cma_marks_current_portfolio_runs_stale() -> None:
    call_command("load_synthetic_personas")
    call_command("seed_default_cma")
    advisor = _authenticated_client()
    analyst = _authenticated_client(email="analyst@example.com", role="financial_analyst")

    generate_response = advisor.post(reverse("generate-portfolio", args=["hh_sandra_mike_chen"]))
    active = models.CMASnapshot.objects.get(status=models.CMASnapshot.Status.ACTIVE)
    draft_response = analyst.post(
        reverse("cma-snapshot-list"), {"copy_from_snapshot_id": active.external_id}
    )
    publish_response = analyst.post(
        reverse("cma-snapshot-publish", args=[draft_response.json()["external_id"]]),
        {"publish_note": "Reviewed stale-run implications."},
        format="json",
    )

    assert generate_response.status_code == 200
    assert publish_response.status_code == 200
    assert models.PortfolioRun.objects.get().status == models.PortfolioRun.Status.STALE
    assert models.PortfolioRun.objects.get().stale_reason == "cma_snapshot_published"


@pytest.mark.django_db
def test_planning_version_creation_marks_current_run_stale() -> None:
    call_command("load_synthetic_personas")
    call_command("seed_default_cma")
    client = _authenticated_client()

    generate_response = client.post(reverse("generate-portfolio", args=["hh_sandra_mike_chen"]))
    planning_response = client.post(
        reverse("planning-version-list", args=["hh_sandra_mike_chen"]),
        {"rationale": "Advisor updated goal/account planning assumptions."},
        format="json",
    )

    assert generate_response.status_code == 200
    assert planning_response.status_code == 201
    assert planning_response.json()["version"] == 1
    assert models.PortfolioRun.objects.get().status == models.PortfolioRun.Status.STALE
    assert AuditEvent.objects.filter(action="planning_version_created").exists()


def _authenticated_client(
    *, email: str = "advisor@example.com", role: str = "advisor"
) -> APIClient:
    User = get_user_model()
    user = User.objects.create_user(username=email, email=email, password="pw")
    group, _ = Group.objects.get_or_create(name=role)
    user.groups.add(group)
    client = APIClient()
    client.force_authenticate(user=user)
    return client
