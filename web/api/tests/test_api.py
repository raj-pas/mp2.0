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
    assert payload["output"]["schema_version"] == "engine_output.link_first.v2"
    assert payload["output"]["run_manifest"]["engine_output_schema"] == (
        "engine_output.link_first.v2"
    )
    assert payload["output"]["link_recommendations"]
    risk_audit = payload["output"]["link_recommendations"][0]["explanation"]["goal_risk_audit"]
    assert risk_audit["scale"] == "1-5"
    assert risk_audit["cma"]["hash"] == payload["cma_hash"]
    assert risk_audit["account_link"]["link_id"]
    assert payload["input_hash"]
    assert payload["output_hash"]
    assert payload["cma_hash"]
    assert payload["run_signature"]
    assert payload["link_recommendation_rows"]
    assert AuditEvent.objects.filter(action="portfolio_run_generated").exists()
    assert models.PortfolioRunEvent.objects.filter(
        portfolio_run__household__external_id="hh_sandra_mike_chen",
        event_type=models.PortfolioRunEvent.EventType.GENERATED,
    ).exists()
    assert "unmapped_current_holdings" not in payload["output"]["warnings"]


@pytest.mark.django_db
def test_generate_portfolio_reuses_same_input_run() -> None:
    call_command("load_synthetic_personas")
    call_command("seed_default_cma")
    client = _authenticated_client()

    first = client.post(reverse("generate-portfolio", args=["hh_sandra_mike_chen"]))
    second = client.post(reverse("generate-portfolio", args=["hh_sandra_mike_chen"]))

    assert first.status_code == 200
    assert second.status_code == 200
    assert models.PortfolioRun.objects.count() == 1
    assert second.json()["external_id"] == first.json()["external_id"]
    assert models.PortfolioRunEvent.objects.filter(
        event_type=models.PortfolioRunEvent.EventType.REUSED
    ).exists()


@pytest.mark.django_db
def test_generate_portfolio_blocks_duplicate_current_lifecycle_state() -> None:
    call_command("load_synthetic_personas")
    call_command("seed_default_cma")
    client = _authenticated_client()

    first = client.post(reverse("generate-portfolio", args=["hh_sandra_mike_chen"]))
    run = models.PortfolioRun.objects.get(external_id=first.json()["external_id"])
    models.PortfolioRun.objects.create(
        household=run.household,
        cma_snapshot=run.cma_snapshot,
        generated_by=run.generated_by,
        as_of_date=run.as_of_date,
        run_signature=run.run_signature,
        input_snapshot=run.input_snapshot,
        output=run.output,
        input_hash=run.input_hash,
        output_hash=run.output_hash,
        cma_hash=run.cma_hash,
        reviewed_state_hash=run.reviewed_state_hash,
        approval_snapshot_hash=run.approval_snapshot_hash,
        engine_version=run.engine_version,
        advisor_summary=run.advisor_summary,
        technical_trace=run.technical_trace,
    )

    response = client.post(reverse("generate-portfolio", args=["hh_sandra_mike_chen"]))

    assert response.status_code == 409
    assert "Duplicate or ambiguous" in response.json()["detail"]
    assert models.PortfolioRunEvent.objects.filter(
        event_type=models.PortfolioRunEvent.EventType.GENERATION_FAILED,
        reason_code="ambiguous_current_lifecycle",
    ).exists()


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
def test_hash_mismatch_records_event_and_regenerates() -> None:
    call_command("load_synthetic_personas")
    call_command("seed_default_cma")
    client = _authenticated_client()

    first = client.post(reverse("generate-portfolio", args=["hh_sandra_mike_chen"]))
    run = models.PortfolioRun.objects.get(external_id=first.json()["external_id"])
    models.PortfolioRun.objects.filter(pk=run.pk).update(
        output={"schema_version": "engine_output.link_first.v2", "tampered": True}
    )
    second = client.post(reverse("generate-portfolio", args=["hh_sandra_mike_chen"]))

    assert second.status_code == 200
    assert models.PortfolioRun.objects.count() == 2
    assert models.PortfolioRunEvent.objects.filter(
        portfolio_run=run,
        event_type=models.PortfolioRunEvent.EventType.HASH_MISMATCH,
    ).exists()


@pytest.mark.django_db
def test_declined_run_regenerates_new_run() -> None:
    call_command("load_synthetic_personas")
    call_command("seed_default_cma")
    client = _authenticated_client()

    first = client.post(reverse("generate-portfolio", args=["hh_sandra_mike_chen"]))
    decline = client.post(
        reverse(
            "portfolio-run-decline",
            args=["hh_sandra_mike_chen", first.json()["external_id"]],
        ),
        {"reason": "Advisor wants a different portfolio blend."},
        format="json",
    )
    second = client.post(reverse("generate-portfolio", args=["hh_sandra_mike_chen"]))

    assert decline.status_code == 200
    assert decline.json()["status"] == "declined"
    assert second.status_code == 200
    assert second.json()["external_id"] != first.json()["external_id"]
    assert models.PortfolioRunEvent.objects.filter(
        event_type=models.PortfolioRunEvent.EventType.REGENERATED_AFTER_DECLINE
    ).exists()


@pytest.mark.django_db
def test_portfolio_audit_export_is_sanitized() -> None:
    call_command("load_synthetic_personas")
    call_command("seed_default_cma")
    client = _authenticated_client()

    response = client.post(reverse("generate-portfolio", args=["hh_sandra_mike_chen"]))
    export_response = client.get(
        reverse(
            "portfolio-run-audit-export",
            args=["hh_sandra_mike_chen", response.json()["external_id"]],
        )
    )

    assert export_response.status_code == 200
    payload = export_response.json()
    assert payload["schema_version"] == "portfolio_run_audit_export.v2"
    assert payload["verification"]["ok"] is True
    serialized = str(payload)
    assert "source_summary" not in serialized
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
def test_invalid_positive_definite_cma_save_returns_diagnostics_and_rolls_back() -> None:
    call_command("seed_default_cma")
    client = _authenticated_client(role="financial_analyst")
    active = models.CMASnapshot.objects.get(status=models.CMASnapshot.Status.ACTIVE)
    draft_response = client.post(
        reverse("cma-snapshot-list"), {"copy_from_snapshot_id": active.external_id}
    )
    draft_payload = draft_response.json()
    correlations = draft_payload["correlations"]
    for item in correlations:
        if {item["row_fund_id"], item["col_fund_id"]} == {"sh_builders", "sh_equity"}:
            item["correlation"] = "0.79200"

    response = client.patch(
        reverse("cma-snapshot-detail", args=[draft_payload["external_id"]]),
        {"correlations": correlations},
        format="json",
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["code"] == "correlation_matrix_not_positive_definite"
    assert payload["diagnostics"]["suggested_pairs"][0]["row_fund_id"] == "sh_builders"
    assert payload["diagnostics"]["suggested_pairs"][0]["col_fund_id"] == "sh_equity"
    assert payload["diagnostics"]["suggested_pairs"][0]["current"] == "0.79200"
    assert payload["diagnostics"]["suggested_pairs"][0]["suggested"] == "0.82200"

    draft = models.CMASnapshot.objects.get(external_id=draft_payload["external_id"])
    saved_value = models.CMACorrelation.objects.get(
        snapshot=draft,
        row_fund_id="sh_builders",
        col_fund_id="sh_equity",
    ).correlation
    assert str(saved_value) == "0.82200"
    assert not AuditEvent.objects.filter(action="cma_snapshot_updated").exists()


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
    assert models.PortfolioRunEvent.objects.filter(
        event_type=models.PortfolioRunEvent.EventType.INVALIDATED_BY_CMA,
        reason_code="cma_snapshot_published",
    ).exists()


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
    assert models.PortfolioRunEvent.objects.filter(
        event_type=models.PortfolioRunEvent.EventType.INVALIDATED_BY_HOUSEHOLD_CHANGE,
        reason_code="planning_version_created",
    ).exists()
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
