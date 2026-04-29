from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from web.api import models
from web.api.review_processing import (
    _json_payload_from_model_text,
    claim_next_job,
    ensure_bedrock_configured,
    process_job,
)
from web.api.review_redaction import (
    redact_evidence_quote,
    redacted_identifier_display,
    sanitize_fact_value,
    sanitize_sensitive_identifier_values,
    sensitive_identifier_hash,
)
from web.api.review_security import secure_data_root
from web.api.review_state import (
    match_candidates,
    readiness_for_state,
    reviewed_state_from_workspace,
)
from web.audit.models import AuditEvent


@pytest.mark.django_db
def test_secure_root_rejects_repo_local_path(settings) -> None:
    settings.MP20_SECURE_DATA_ROOT = str(settings.REPO_ROOT / "ignored-real-data")

    with pytest.raises(ImproperlyConfigured):
        secure_data_root()


@pytest.mark.django_db
def test_secure_root_accepts_outside_repo(tmp_path, settings) -> None:
    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")

    assert secure_data_root() == (tmp_path / "secure").resolve()


def test_minimal_evidence_redaction_preserves_context() -> None:
    quote = "Jane is 67 with Account #1234567 and target $500,000."

    redacted = redact_evidence_quote(quote)

    assert "Jane" in redacted
    assert "$500,000" in redacted
    assert "1234567" not in redacted


def test_sensitive_identifier_hash_and_display() -> None:
    assert sensitive_identifier_hash("Account #1234567") == sensitive_identifier_hash(
        "Account #1234567"
    )
    assert redacted_identifier_display("1234567") == "****4567"


def test_sensitive_identifier_values_are_hash_and_display_only() -> None:
    sanitized = sanitize_sensitive_identifier_values(
        {"account_number": "1234567", "nested": [{"sin": "123 456 789"}]}
    )

    assert sanitized["account_number"]["display"] == "****4567"
    assert sanitized["account_number"]["hash"] != "1234567"
    assert sanitized["nested"][0]["sin"]["display"] == "****6789"


def test_sensitive_scalar_fact_value_is_hash_and_display_only() -> None:
    sanitized = sanitize_fact_value("accounts[0].account_number", "12345ABC")

    assert sanitized["display"] == "****5ABC"
    assert sanitized["hash"] != "12345ABC"


def test_bedrock_config_fails_closed(monkeypatch) -> None:
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.delenv("BEDROCK_MODEL", raising=False)

    with pytest.raises(ImproperlyConfigured):
        ensure_bedrock_configured()


def test_bedrock_json_payload_accepts_fenced_response() -> None:
    payload = _json_payload_from_model_text(
        "Here is the JSON:\n"
        '```json\n{"facts": [{"field": "household.display_name", "value": "Demo"}]}\n```'
    )

    assert payload["facts"][0]["field"] == "household.display_name"


@pytest.mark.django_db
def test_session_reports_authenticated_user_after_login() -> None:
    _user()
    client = APIClient()

    login_response = client.post(
        reverse("local-login"),
        {"email": "advisor@example.com", "password": "pw"},
        format="json",
    )
    session_response = client.get(reverse("session"))

    assert login_response.status_code == 200
    assert login_response.json()["authenticated"] is True
    assert session_response.status_code == 200
    assert session_response.json()["authenticated"] is True


@pytest.mark.django_db
@override_settings(MP20_SECURE_DATA_ROOT="/tmp/mp20-test-secure")
def test_authenticated_upload_deduplicates_and_enqueues(tmp_path, settings) -> None:
    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(label="Real review", owner=user)

    upload = SimpleUploadedFile("notes.txt", b"Retirement goal in five years.")
    response = client.post(
        reverse("review-workspace-upload", args=[workspace.external_id]),
        {"files": [upload]},
        format="multipart",
    )

    assert response.status_code == 200
    assert len(response.json()["uploaded"]) == 1
    assert workspace.documents.count() == 1
    assert workspace.processing_jobs.filter(status="queued").count() == 1

    duplicate = SimpleUploadedFile("notes-copy.txt", b"Retirement goal in five years.")
    response = client.post(
        reverse("review-workspace-upload", args=[workspace.external_id]),
        {"files": [duplicate]},
        format="multipart",
    )

    assert response.status_code == 200
    assert len(response.json()["duplicates"]) == 1
    assert workspace.documents.count() == 1


@pytest.mark.django_db
def test_failed_document_retry_queues_new_job(tmp_path, settings) -> None:
    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(label="Retry review", owner=user)
    document = models.ReviewDocument.objects.create(
        workspace=workspace,
        original_filename="broken.txt",
        extension="txt",
        file_size=0,
        sha256="retry",
        status=models.ReviewDocument.Status.FAILED,
        failure_reason="temporary parser error",
    )

    response = client.post(
        reverse("review-document-retry", args=[workspace.external_id, document.id]), {}
    )

    assert response.status_code == 200
    assert document.processing_jobs.filter(status=models.ProcessingJob.Status.QUEUED).exists()
    document.refresh_from_db()
    assert document.status == models.ReviewDocument.Status.UPLOADED


@pytest.mark.django_db
def test_worker_processes_synthetic_text_document(tmp_path, settings) -> None:
    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    user = _user()
    workspace = models.ReviewWorkspace.objects.create(
        label="Synthetic review",
        owner=user,
        data_origin=models.ReviewWorkspace.DataOrigin.SYNTHETIC,
    )
    storage_dir = Path(settings.MP20_SECURE_DATA_ROOT) / "review-workspaces" / workspace.external_id
    storage_dir.mkdir(parents=True)
    source = storage_dir / "notes.txt"
    source.write_text("Synthetic client note.")
    document = models.ReviewDocument.objects.create(
        workspace=workspace,
        original_filename="notes.txt",
        extension="txt",
        file_size=source.stat().st_size,
        sha256="abc",
        storage_path=f"review-workspaces/{workspace.external_id}/notes.txt",
    )
    models.ProcessingJob.objects.create(workspace=workspace, document=document)

    job = claim_next_job()
    assert job is not None
    process_job(job)
    reconcile_job = claim_next_job()
    assert reconcile_job is not None
    process_job(reconcile_job)

    document.refresh_from_db()
    workspace.refresh_from_db()
    assert document.status == models.ReviewDocument.Status.RECONCILED
    assert workspace.reviewed_state["schema_version"] == "reviewed_client_state.v1"
    assert workspace.extracted_facts.exists()


def test_readiness_requires_goal_account_mapping() -> None:
    state = {
        "household": {
            "display_name": "Household",
            "household_type": "couple",
            "household_risk_score": 3,
        },
        "people": [{"name": "Advisor Client", "age": 62}],
        "accounts": [
            {
                "id": "acct_1",
                "type": "RRSP",
                "current_value": 100000,
                "missing_holdings_confirmed": True,
            }
        ],
        "goals": [{"id": "goal_1", "name": "Retirement", "time_horizon_years": 5}],
        "goal_account_links": [],
        "risk": {"household_score": 3},
    }

    readiness = readiness_for_state(state)

    assert not readiness.engine_ready
    assert any(item["section"] == "goal_account_mapping" for item in readiness.missing)


@pytest.mark.django_db
def test_indexed_extracted_facts_reconcile_to_reviewed_state() -> None:
    user = _user()
    workspace = models.ReviewWorkspace.objects.create(label="Indexed facts", owner=user)
    document = models.ReviewDocument.objects.create(
        workspace=workspace,
        original_filename="statement.txt",
        extension="txt",
        file_size=1,
        sha256="indexed",
        document_type="statement",
    )
    facts = {
        "people[0].display_name": "Indexed Client",
        "people[0].age": 62,
        "accounts[0].account_type": "RRSP",
        "accounts[0].current_value": 250000,
        "accounts[0].missing_holdings_confirmed": True,
        "goals[0].name": "Retirement",
        "goals[0].time_horizon_years": 5,
        "goal_account_links[0].goal_name": "Retirement",
        "goal_account_links[0].allocated_value": 250000,
    }
    for field, value in facts.items():
        models.ExtractedFact.objects.create(
            workspace=workspace,
            document=document,
            field=field,
            value=value,
            extraction_run_id="test",
        )

    state = reviewed_state_from_workspace(workspace)

    assert state["people"][0]["name"] == "Indexed Client"
    assert state["accounts"][0]["type"] == "RRSP"
    assert state["goals"][0]["name"] == "Retirement"
    assert state["goal_account_links"][0]["account_id"] == state["accounts"][0]["id"]
    assert state["readiness"]["engine_ready"] is True


@pytest.mark.django_db
def test_match_candidates_use_name_and_member_signals() -> None:
    user = _user()
    household = models.Household.objects.create(
        external_id="ready_household",
        owner=user,
        display_name="Ready Household",
        household_type="couple",
        household_risk_score=3,
    )
    models.Person.objects.create(
        external_id="ready_person",
        household=household,
        name="Ready Client",
        dob=date(1964, 1, 1),
    )
    workspace = models.ReviewWorkspace.objects.create(
        label="Ready review",
        owner=user,
        reviewed_state=_engine_ready_state(),
    )

    candidates = match_candidates(workspace)

    assert candidates == [
        {
            "household_id": "ready_household",
            "display_name": "Ready Household",
            "confidence": 80,
            "reasons": ["household name", "member name: Ready Client"],
        }
    ]


@pytest.mark.django_db
def test_committed_workspace_does_not_match_its_linked_household() -> None:
    user = _user()
    household = models.Household.objects.create(
        external_id="linked_household",
        owner=user,
        display_name="Ready Household",
        household_type="couple",
        household_risk_score=3,
    )
    workspace = models.ReviewWorkspace.objects.create(
        label="Ready review",
        owner=user,
        linked_household=household,
        status=models.ReviewWorkspace.Status.COMMITTED,
        reviewed_state=_engine_ready_state(),
        match_candidates=[
            {
                "household_id": household.external_id,
                "display_name": household.display_name,
                "confidence": 60,
                "reasons": ["household name"],
            }
        ],
    )
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get(reverse("review-workspace-matches", args=[workspace.external_id]))

    assert response.status_code == 200
    assert response.json()["candidates"] == []
    workspace.refresh_from_db()
    assert workspace.match_candidates == []


@pytest.mark.django_db
def test_commit_requires_engine_ready_and_creates_household(tmp_path, settings) -> None:
    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(label="Ready review", owner=user)
    workspace.reviewed_state = _engine_ready_state()
    workspace.readiness = readiness_for_state(workspace.reviewed_state).__dict__
    workspace.save()

    response = client.post(reverse("review-workspace-commit", args=[workspace.external_id]), {})

    assert response.status_code == 200
    household_id = response.json()["household_id"]
    assert models.Household.objects.filter(external_id=household_id).exists()
    assert AuditEvent.objects.filter(action="review_state_committed").exists()

    second_response = client.post(
        reverse("review-workspace-commit", args=[workspace.external_id]), {}
    )

    assert second_response.status_code == 200
    assert second_response.json()["household_id"] == household_id
    assert models.Household.objects.filter(external_id=household_id).count() == 1


@pytest.mark.django_db
def test_committed_workspace_cannot_relink_to_different_household(tmp_path, settings) -> None:
    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(label="Ready review", owner=user)
    workspace.reviewed_state = _engine_ready_state()
    workspace.readiness = readiness_for_state(workspace.reviewed_state).__dict__
    workspace.save()
    first_response = client.post(
        reverse("review-workspace-commit", args=[workspace.external_id]), {}
    )
    other_household = models.Household.objects.create(
        external_id="other_ready_household",
        owner=user,
        display_name="Other Ready Household",
        household_type="single",
        household_risk_score=3,
    )

    second_response = client.post(
        reverse("review-workspace-commit", args=[workspace.external_id]),
        {"household_id": other_household.external_id},
        format="json",
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 400
    assert (
        second_response.json()["detail"]
        == "Review workspace is already committed to another household."
    )


def _user():
    User = get_user_model()
    return User.objects.create_user(
        username="advisor@example.com", email="advisor@example.com", password="pw"
    )


def _engine_ready_state() -> dict:
    return {
        "schema_version": "reviewed_client_state.v1",
        "household": {
            "display_name": "Ready Household",
            "household_type": "couple",
            "household_risk_score": 3,
        },
        "people": [{"id": "person_ready", "name": "Ready Client", "age": 62}],
        "accounts": [
            {
                "id": "acct_ready",
                "type": "RRSP",
                "current_value": 100000,
                "missing_holdings_confirmed": True,
            }
        ],
        "goals": [{"id": "goal_ready", "name": "Retirement", "time_horizon_years": 5}],
        "goal_account_links": [
            {"goal_id": "goal_ready", "account_id": "acct_ready", "allocated_amount": 100000}
        ],
        "risk": {"household_score": 3},
    }
