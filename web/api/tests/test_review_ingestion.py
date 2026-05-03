from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from web.api import models
from web.api.review_processing import (
    claim_next_job,
    enqueue_reconcile,
    ensure_bedrock_configured,
    process_job,
    record_worker_heartbeat,
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


@pytest.mark.django_db
def test_evidence_endpoint_audits_redacted_fact_access() -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(label="Evidence review", owner=user)
    document = models.ReviewDocument.objects.create(
        workspace=workspace,
        original_filename="notes.txt",
        extension="txt",
        file_size=1,
        sha256="evidence",
        document_type="meeting_note",
    )
    fact = models.ExtractedFact.objects.create(
        workspace=workspace,
        document=document,
        field="goals[0].name",
        value="Retirement",
        evidence_quote="Retirement goal discussed.",
        extraction_run_id="evidence",
    )

    response = client.get(reverse("review-fact-evidence", args=[workspace.external_id, fact.id]))

    assert response.status_code == 200
    assert response.json()["redacted"] is True
    assert AuditEvent.objects.filter(action="review_evidence_viewed").exists()


def test_bedrock_config_fails_closed(monkeypatch) -> None:
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.delenv("BEDROCK_MODEL", raising=False)

    with pytest.raises(ImproperlyConfigured):
        ensure_bedrock_configured()


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
    workspace = models.ReviewWorkspace.objects.create(
        label="Synthetic review",
        owner=user,
        data_origin=models.ReviewWorkspace.DataOrigin.SYNTHETIC,
    )

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
def test_upload_ignores_system_files_before_job_creation(tmp_path, settings) -> None:
    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(
        label="System file review",
        owner=user,
        data_origin=models.ReviewWorkspace.DataOrigin.SYNTHETIC,
    )

    response = client.post(
        reverse("review-workspace-upload", args=[workspace.external_id]),
        {"files": [SimpleUploadedFile(".DS_Store", b"noise")]},
        format="multipart",
    )

    assert response.status_code == 200
    assert response.json()["ignored"] == [{"filename": ".DS_Store", "reason": "system_file"}]
    assert workspace.documents.count() == 0
    assert workspace.processing_jobs.count() == 0
    workspace.refresh_from_db()
    assert workspace.status == models.ReviewWorkspace.Status.DRAFT


@pytest.mark.django_db
def test_upload_to_stale_workspace_id_returns_404(tmp_path, settings) -> None:
    """Pins the 404 contract that DocDropOverlay's session-recovery
    path depends on (Phase 5b.8 Option D fallback).

    When a session expires mid-upload, the frontend stashes the
    workspace_id in sessionStorage. On re-login the resume flow
    posts directly to that workspace; if the workspace was deleted
    server-side or never owned by this user (defensive against
    server-side state divergence), the upload must return 404 so
    the frontend falls through to a fresh create + upload. A 403
    or 500 here would silently break recovery.
    """
    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        reverse(
            "review-workspace-upload",
            args=["00000000-0000-0000-0000-000000000000"],
        ),
        {"files": [SimpleUploadedFile("a.txt", b"x")]},
        format="multipart",
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_real_upload_uses_secure_storage_and_queues_without_backend_flag(
    tmp_path, settings
) -> None:
    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(label="Real review", owner=user)

    response = client.post(
        reverse("review-workspace-upload", args=[workspace.external_id]),
        {"files": [SimpleUploadedFile("notes.txt", b"Real client note.")]},
        format="multipart",
    )

    assert response.status_code == 200
    assert len(response.json()["uploaded"]) == 1
    assert workspace.documents.count() == 1
    assert workspace.processing_jobs.filter(status=models.ProcessingJob.Status.QUEUED).exists()
    assert AuditEvent.objects.filter(action="review_documents_uploaded").exists()


@pytest.mark.django_db
def test_engine_kill_switch_blocks_generation(settings) -> None:
    settings.MP20_ENGINE_ENABLED = False
    user = _user()
    household = models.Household.objects.create(
        external_id="kill_switch_household",
        owner=user,
        display_name="Kill Switch Household",
        household_type="single",
        household_risk_score=3,
    )
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(reverse("generate-portfolio", args=[household.external_id]), {})

    assert response.status_code == 403
    assert AuditEvent.objects.filter(action="engine_kill_switch_blocked").exists()


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


@pytest.mark.django_db
def test_reconcile_queue_suppresses_duplicate_pending_jobs() -> None:
    user = _user()
    workspace = models.ReviewWorkspace.objects.create(label="Reconcile review", owner=user)

    first = enqueue_reconcile(workspace)
    second = enqueue_reconcile(workspace)

    assert first.id == second.id
    assert (
        workspace.processing_jobs.filter(
            job_type=models.ProcessingJob.JobType.RECONCILE_WORKSPACE
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_worker_heartbeat_records_current_job() -> None:
    user = _user()
    workspace = models.ReviewWorkspace.objects.create(label="Heartbeat review", owner=user)
    job = models.ProcessingJob.objects.create(workspace=workspace)

    heartbeat = record_worker_heartbeat(name="pytest-worker", current_job=job)

    assert heartbeat.name == "pytest-worker"
    assert heartbeat.current_job == job


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
    assert not readiness.construction_ready
    assert any(item["section"] == "goal_account_mapping" for item in readiness.missing)


def test_construction_readiness_blocks_unsupported_account_type() -> None:
    state = _engine_ready_state()
    state["accounts"][0]["type"] = "SIF"

    readiness = readiness_for_state(state)

    assert readiness.engine_ready
    assert not readiness.construction_ready
    assert any(
        "Unsupported engine account type" in item["label"]
        for item in readiness.construction_missing
    )


@pytest.mark.django_db
def test_plain_section_approval_is_blocked_with_missing_data() -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(
        label="Incomplete review",
        owner=user,
        reviewed_state={
            "household": {"display_name": "", "household_type": "couple"},
            "people": [],
            "accounts": [],
            "goals": [],
            "goal_account_links": [],
            "risk": {},
        },
    )

    response = client.post(
        reverse("review-workspace-approve-section", args=[workspace.external_id]),
        {"section": "household", "status": "approved"},
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["blockers"][0]["kind"] == "missing"


@pytest.mark.django_db
def test_commit_requires_required_section_approvals() -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(label="Ready review", owner=user)
    workspace.reviewed_state = _engine_ready_state()
    workspace.readiness = readiness_for_state(workspace.reviewed_state).__dict__
    workspace.save()

    response = client.post(reverse("review-workspace-commit", args=[workspace.external_id]), {})

    assert response.status_code == 400
    # Phase 2 PII scrub: detail is now a generic friendly message; the
    # durable contract is the structured `code` field that the
    # frontend reads to look up `review.failure_code.<code>` i18n.
    assert response.json()["code"] == "sections_not_approved"


@pytest.mark.django_db
def test_review_state_patch_rejects_legacy_household_risk_score() -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(
        label="Risk review",
        owner=user,
        reviewed_state=_engine_ready_state(),
    )

    response = client.patch(
        reverse("review-workspace-state", args=[workspace.external_id]),
        {"state": {"risk": {"household_score": 6}}},
        format="json",
    )

    assert response.status_code == 400
    # Phase 2 PII scrub: detail is now generic friendly text; assert
    # structured code (ValidationError / ValueError class name).
    assert response.json()["code"] in {"ValueError", "ValidationError"}


@pytest.mark.django_db
def test_commit_requires_construction_ready() -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(label="Construction review", owner=user)
    state = _engine_ready_state()
    state["accounts"][0]["type"] = "SIF"
    workspace.reviewed_state = state
    workspace.readiness = readiness_for_state(state).__dict__
    workspace.save()
    _approve_required_sections(workspace, user)

    response = client.post(reverse("review-workspace-commit", args=[workspace.external_id]), {})

    assert response.status_code == 400
    # Phase 2 PII scrub: assert structured code, not detail string.
    assert response.json()["code"] == "construction_not_ready"


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
def test_qualitative_risk_fact_reconciles_without_crashing() -> None:
    user = _user()
    workspace = models.ReviewWorkspace.objects.create(label="Qualitative risk", owner=user)
    document = models.ReviewDocument.objects.create(
        workspace=workspace,
        original_filename="profile.txt",
        extension="txt",
        file_size=1,
        sha256="qual-risk",
        document_type="kyc",
    )
    models.ExtractedFact.objects.create(
        workspace=workspace,
        document=document,
        field="risk.household_score",
        value="Low",
        extraction_run_id="test",
    )

    state = reviewed_state_from_workspace(workspace)

    assert state["household"]["household_risk_score"] == 2
    assert state["risk"]["household_score"] == 2


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
    call_command("seed_default_cma")
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(label="Ready review", owner=user)
    workspace.reviewed_state = _engine_ready_state()
    workspace.readiness = readiness_for_state(workspace.reviewed_state).__dict__
    workspace.save()
    _approve_required_sections(workspace, user)

    response = client.post(reverse("review-workspace-commit", args=[workspace.external_id]), {})

    assert response.status_code == 200
    household_id = response.json()["household_id"]
    assert models.Household.objects.filter(external_id=household_id).exists()
    assert AuditEvent.objects.filter(action="review_state_committed").exists()

    generate_response = client.post(reverse("generate-portfolio", args=[household_id]), {})

    assert generate_response.status_code == 200
    assert models.PortfolioRun.objects.filter(household__external_id=household_id).exists()
    assert models.PortfolioRunEvent.objects.filter(
        portfolio_run__household__external_id=household_id,
        event_type=models.PortfolioRunEvent.EventType.GENERATED,
    ).exists()

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
    _approve_required_sections(workspace, user)
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
    # Phase 2 PII scrub: detail is now generic; assert code field.
    assert second_response.json()["code"] == "unknown"


@pytest.mark.django_db
def test_disposal_command_reports_and_deletes_outdated_artifacts(tmp_path, settings) -> None:
    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    user = _user()
    workspace = models.ReviewWorkspace.objects.create(label="Disposal review", owner=user)
    storage_dir = Path(settings.MP20_SECURE_DATA_ROOT) / "review-workspaces" / workspace.external_id
    storage_dir.mkdir(parents=True)
    source = storage_dir / "old.txt"
    source.write_text("old artifact")
    document = models.ReviewDocument.objects.create(
        workspace=workspace,
        original_filename="old.txt",
        extension="txt",
        file_size=source.stat().st_size,
        sha256="old",
        storage_path=f"review-workspaces/{workspace.external_id}/old.txt",
        processing_metadata={"artifact_version": "old"},
    )

    call_command("dispose_review_artifacts", "--delete")

    assert not source.exists()
    assert models.ReviewDocument.objects.get(pk=document.pk).storage_path
    assert AuditEvent.objects.filter(action="review_artifact_disposal_delete").exists()


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


def _approve_required_sections(workspace: models.ReviewWorkspace, user) -> None:
    for section in ("household", "people", "accounts", "goals", "goal_account_mapping", "risk"):
        models.SectionApproval.objects.create(
            workspace=workspace,
            section=section,
            status=models.SectionApproval.Status.APPROVED,
            approved_by=user,
        )


# ---------------------------------------------------------------------------
# Full doc-drop pipeline regression — covers the post-R7 fixes that surfaced
# during the upload/parse/commit deep-dig:
#   1. ReviewWorkspaceSerializer exposes `required_sections` (drives the
#      frontend approval gate, prevents enum drift).
#   2. State PATCH invalidates approvals when the new state has fresh
#      blockers (closes the silent-gate-evasion path).
#   3. Commit error response carries a structured `code` +
#      `missing_approvals` body so the toast can be actionable.
#   4. Worker auto-recovers jobs left in PROCESSING by a crashed worker
#      (else the workspace polls forever).
#   5. Per-file try/except in upload — a single bad file shouldn't 500
#      the whole batch.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_workspace_serializer_exposes_required_sections() -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(
        label="Required-sections probe",
        owner=user,
        data_origin=models.ReviewWorkspace.DataOrigin.SYNTHETIC,
    )

    response = client.get(reverse("review-workspace-detail", args=[workspace.external_id]))

    assert response.status_code == 200
    body = response.json()
    assert body["required_sections"] == [
        "household",
        "people",
        "accounts",
        "goals",
        "goal_account_mapping",
        "risk",
    ]


@pytest.mark.django_db
def test_state_patch_invalidates_stale_section_approval(tmp_path, settings) -> None:
    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(label="Patch invalidation", owner=user)
    workspace.reviewed_state = _engine_ready_state()
    workspace.readiness = readiness_for_state(workspace.reviewed_state).__dict__
    workspace.save()
    _approve_required_sections(workspace, user)

    # Drop a required goal field — `goals` should flip back to needs_attention.
    patch_state = dict(workspace.reviewed_state)
    patch_state["goals"] = [{"id": "goal_ready", "name": "Retirement"}]  # no horizon
    response = client.patch(
        reverse("review-workspace-state", args=[workspace.external_id]),
        {"state": patch_state},
        format="json",
    )

    assert response.status_code == 200
    assert "goals" in response.json()["invalidated_approvals"]
    workspace.refresh_from_db()
    goals_approval = workspace.section_approvals.get(section="goals")
    assert goals_approval.status == models.SectionApproval.Status.NEEDS_ATTENTION
    # Untouched approvals stay approved.
    people_approval = workspace.section_approvals.get(section="people")
    assert people_approval.status == models.SectionApproval.Status.APPROVED


@pytest.mark.django_db
def test_commit_returns_structured_error_with_missing_approvals(tmp_path, settings) -> None:
    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(label="Structured error", owner=user)
    workspace.reviewed_state = _engine_ready_state()
    workspace.readiness = readiness_for_state(workspace.reviewed_state).__dict__
    workspace.save()
    # Approve only some of the required sections so commit fails the
    # section-approval gate — that's the case where the user gets a
    # generic 400 today and doesn't know which section to fix.
    for section in ("household", "people", "accounts"):
        models.SectionApproval.objects.create(
            workspace=workspace,
            section=section,
            status=models.SectionApproval.Status.APPROVED,
            approved_by=user,
        )

    response = client.post(reverse("review-workspace-commit", args=[workspace.external_id]))

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "sections_not_approved"
    assert set(body["missing_approvals"]) == {"goals", "goal_account_mapping", "risk"}
    assert body["required_sections"] == [
        "household",
        "people",
        "accounts",
        "goals",
        "goal_account_mapping",
        "risk",
    ]


@pytest.mark.django_db
def test_worker_auto_recovers_stale_processing_job(tmp_path, settings) -> None:
    """A worker that crashed mid-job leaves the row in PROCESSING with an
    old `locked_at`. The next claim cycle should requeue (or fail) it
    so the workspace doesn't poll on it forever.
    """
    from web.api.review_processing import requeue_stale_jobs

    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    settings.MP20_WORKER_STALE_SECONDS = 60
    user = _user()
    workspace = models.ReviewWorkspace.objects.create(label="Stale job", owner=user)
    document = models.ReviewDocument.objects.create(
        workspace=workspace,
        original_filename="notes.txt",
        extension="txt",
        file_size=10,
        sha256="stale",
        storage_path="missing/notes.txt",
    )
    # Job 1: stale + retries left → should requeue.
    fresh = models.ProcessingJob.objects.create(
        workspace=workspace,
        document=document,
        status=models.ProcessingJob.Status.PROCESSING,
        attempts=1,
        max_attempts=3,
    )
    models.ProcessingJob.objects.filter(pk=fresh.pk).update(
        locked_at=fresh.created_at - timedelta(seconds=120)
    )
    # Job 2: stale + retries exhausted → should be marked FAILED.
    document_2 = models.ReviewDocument.objects.create(
        workspace=workspace,
        original_filename="notes2.txt",
        extension="txt",
        file_size=10,
        sha256="exhausted",
        storage_path="missing/notes2.txt",
    )
    exhausted = models.ProcessingJob.objects.create(
        workspace=workspace,
        document=document_2,
        status=models.ProcessingJob.Status.PROCESSING,
        attempts=3,
        max_attempts=3,
    )
    models.ProcessingJob.objects.filter(pk=exhausted.pk).update(
        locked_at=exhausted.created_at - timedelta(seconds=120)
    )

    requeued = requeue_stale_jobs()

    assert requeued == 2
    fresh.refresh_from_db()
    exhausted.refresh_from_db()
    document_2.refresh_from_db()
    assert fresh.status == models.ProcessingJob.Status.QUEUED
    assert fresh.locked_at is None
    assert exhausted.status == models.ProcessingJob.Status.FAILED
    assert document_2.status == models.ReviewDocument.Status.FAILED
    assert AuditEvent.objects.filter(action="review_job_auto_recovered").count() == 2


@pytest.mark.django_db
def test_upload_partial_failure_does_not_500_whole_batch(tmp_path, settings, monkeypatch) -> None:
    """A bad file in a multi-file upload should land in `ignored`, not
    abort the request. The good files still upload and an audit event
    fires for the failure.
    """
    from web.api import views as views_module

    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(
        label="Partial failure",
        owner=user,
        data_origin=models.ReviewWorkspace.DataOrigin.SYNTHETIC,
    )

    real_write = views_module.write_uploaded_file

    def flaky_write(**kwargs):
        if kwargs["filename"] == "broken.txt":
            raise OSError("simulated disk failure")
        return real_write(**kwargs)

    monkeypatch.setattr(views_module, "write_uploaded_file", flaky_write)

    good = SimpleUploadedFile("good.txt", b"healthy contents")
    bad = SimpleUploadedFile("broken.txt", b"this one fails")
    response = client.post(
        reverse("review-workspace-upload", args=[workspace.external_id]),
        {"files": [good, bad]},
        format="multipart",
    )

    assert response.status_code == 200
    body = response.json()
    assert [row["filename"] for row in body["uploaded"]] == ["good.txt"]
    assert any(
        row["filename"] == "broken.txt"
        and row["reason"] == "upload_failed"
        and row.get("failure_code") == "OSError"
        for row in body["ignored"]
    )
    # The good file's processing job is still queued.
    assert workspace.processing_jobs.filter(status="queued").count() == 1
    # Per-file failure is auditable.
    assert AuditEvent.objects.filter(action="review_document_upload_failed").exists()


@pytest.mark.django_db
def test_full_pipeline_upload_to_commit(tmp_path, settings) -> None:
    """End-to-end happy path: POST upload → worker process → reconcile →
    state to engine-ready → approve all required sections → commit →
    household exists + audit event recorded. This is the regression
    safety net for the doc-drop deep-dig.
    """
    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    call_command("seed_default_cma")
    user = _user()
    api_client = APIClient()
    api_client.force_authenticate(user=user)

    # 1. Create workspace via the same endpoint the UI hits.
    create_response = api_client.post(
        reverse("review-workspace-list"),
        {"label": "E2E pipeline", "data_origin": "synthetic"},
        format="json",
    )
    assert create_response.status_code == 200
    workspace_id = create_response.json()["external_id"]

    # 2. Upload a document via multipart.
    upload = SimpleUploadedFile("notes.txt", b"Synthetic E2E note.")
    upload_response = api_client.post(
        reverse("review-workspace-upload", args=[workspace_id]),
        {"files": [upload]},
        format="multipart",
    )
    assert upload_response.status_code == 200
    assert len(upload_response.json()["uploaded"]) == 1

    # 3. Worker processes the doc + reconciles.
    process_doc_job = claim_next_job()
    assert process_doc_job is not None
    process_job(process_doc_job)
    reconcile = claim_next_job()
    assert reconcile is not None
    process_job(reconcile)

    # 4. The detail endpoint reflects required_sections + readiness.
    detail = api_client.get(reverse("review-workspace-detail", args=[workspace_id]))
    assert detail.status_code == 200
    body = detail.json()
    assert "household" in body["required_sections"]
    # Reconcile may not produce engine-ready state from a tiny note —
    # the next step seeds an engine-ready state directly.

    # 5. Promote workspace to engine-ready state (mirrors what advisor
    #    edits during real review). Use the PATCH endpoint to exercise
    #    the new approval-invalidation path with a stale `goals`
    #    approval that should NOT be invalidated (since the patch
    #    leaves goals fully populated).
    workspace = models.ReviewWorkspace.objects.get(external_id=workspace_id)
    models.SectionApproval.objects.create(
        workspace=workspace,
        section="goals",
        status=models.SectionApproval.Status.APPROVED,
        approved_by=user,
    )
    patch_response = api_client.patch(
        reverse("review-workspace-state", args=[workspace_id]),
        {"state": _engine_ready_state()},
        format="json",
    )
    assert patch_response.status_code == 200
    # `goals` approval still valid because the patched state still has
    # all goal fields → not invalidated.
    assert "goals" not in patch_response.json()["invalidated_approvals"]

    # 6. Approve all remaining required sections.
    for section in ("household", "people", "accounts", "goal_account_mapping", "risk"):
        approve_response = api_client.post(
            reverse("review-workspace-approve-section", args=[workspace_id]),
            {"section": section, "status": "approved"},
            format="json",
        )
        assert approve_response.status_code == 200, (
            f"approve {section} failed: {approve_response.content!r}"
        )

    # 7. Commit produces a household + audit event.
    commit_response = api_client.post(
        reverse("review-workspace-commit", args=[workspace_id]),
        format="json",
    )
    assert commit_response.status_code == 200, commit_response.content
    household_id = commit_response.json()["household_id"]
    assert models.Household.objects.filter(external_id=household_id).exists()
    assert AuditEvent.objects.filter(
        action="review_state_committed", entity_id=workspace_id
    ).exists()


@pytest.mark.django_db
def test_commit_after_patch_state_flips_status_and_is_idempotent(tmp_path, settings) -> None:
    """Regression for the catalogued post-R7 real-PII bug:

    After a state-PATCH (which calls create_state_version) seeds a
    state version + sets workspace.status = engine_ready, then a
    successful POST /commit must:
      1. Persist workspace.status = COMMITTED (not engine_ready)
      2. Be idempotent — a second POST /commit returns the SAME
         household, never an IntegrityError on Household.external_id

    This exercises the nested @transaction.atomic interaction between
    create_state_version (called by both the PATCH endpoint and
    commit_reviewed_state internally) and commit_reviewed_state's
    final save. The existing test_commit_requires_engine_ready_and_
    creates_household covers a path where workspace.reviewed_state is
    seeded directly without going through the PATCH endpoint — so it
    misses any state-versioning interaction.
    """

    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    call_command("seed_default_cma")
    user = _user()
    api_client = APIClient()
    api_client.force_authenticate(user=user)

    create_response = api_client.post(
        reverse("review-workspace-list"),
        {"label": "Re-commit regression", "data_origin": "synthetic"},
        format="json",
    )
    assert create_response.status_code == 200
    workspace_id = create_response.json()["external_id"]

    # PATCH /state — exact production path that creates a versioned state
    # row with status=engine_ready BEFORE the commit endpoint runs.
    patch_response = api_client.patch(
        reverse("review-workspace-state", args=[workspace_id]),
        {"state": _engine_ready_state()},
        format="json",
    )
    assert patch_response.status_code == 200

    workspace = models.ReviewWorkspace.objects.get(external_id=workspace_id)
    assert workspace.status == models.ReviewWorkspace.Status.ENGINE_READY, (
        "PATCH /state did not flip workspace to engine_ready — bug in "
        "create_state_version or readiness math, not the bug we're after"
    )

    for section in ("household", "people", "accounts", "goals", "goal_account_mapping", "risk"):
        approve_response = api_client.post(
            reverse("review-workspace-approve-section", args=[workspace_id]),
            {"section": section, "status": "approved"},
            format="json",
        )
        assert approve_response.status_code == 200, (
            f"approve {section} failed: {approve_response.content!r}"
        )

    first_commit = api_client.post(
        reverse("review-workspace-commit", args=[workspace_id]),
        format="json",
    )
    assert first_commit.status_code == 200, first_commit.content
    household_id = first_commit.json()["household_id"]

    # ── core invariant: workspace must end at COMMITTED in DB ────────────
    workspace.refresh_from_db()
    assert workspace.status == models.ReviewWorkspace.Status.COMMITTED, (
        f"Workspace status is {workspace.status}, expected COMMITTED. "
        "The catalogued post-R7 bug: create_state_version inside "
        "commit_reviewed_state writes status=engine_ready, and the "
        "outer save's update_fields list must override it back to "
        "COMMITTED before the transaction commits."
    )
    assert workspace.linked_household is not None
    assert workspace.linked_household.external_id == household_id

    # ── idempotency: second POST returns same household, no IntegrityError ─
    second_commit = api_client.post(
        reverse("review-workspace-commit", args=[workspace_id]),
        format="json",
    )
    assert second_commit.status_code == 200, (
        f"Second commit returned {second_commit.status_code}; "
        f"body={second_commit.content!r}. The catalogued bug is: "
        "second commit hits Household.external_id unique-constraint "
        "with a 500 IntegrityError because the workspace.status check "
        "in commit_reviewed_state's early-return failed."
    )
    assert second_commit.json()["household_id"] == household_id
    assert models.Household.objects.filter(external_id=household_id).count() == 1

    # ── audit invariant: only ONE review_state_committed event emitted,
    # not one per commit attempt — second was a no-op return.
    committed_events = AuditEvent.objects.filter(
        action="review_state_committed", entity_id=workspace_id
    )
    assert committed_events.count() == 1, (
        f"Expected 1 review_state_committed event after 2 commit calls "
        f"(second is a no-op idempotent return); got {committed_events.count()}."
    )


@pytest.mark.django_db
def test_zero_value_purpose_account_surfaces_construction_blocker_not_500() -> None:
    """Catalogued post-R7 real-PII bug 2: a Purpose account with
    current_value=0 (or None) and a goal-account-link must surface a
    clear construction-ready blocker BEFORE the optimizer is invoked.

    Pre-fix behavior: state passes both engine_ready and
    construction_ready, commit succeeds, household is created, and
    THEN GeneratePortfolio crashes inside engine.optimizer with
    `ValueError: Every goal-account link must include allocated
    dollars or percentage` — surfaces as a 500 that gives the advisor
    no actionable signal.

    Post-fix: construction_blockers_for_state flags the zero-value
    Purpose account as needing an advisor decision (provide value,
    archive, or delete). The commit endpoint returns 400 with a
    blocker message that names the affected account.
    """

    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(label="Zero-value review", owner=user)
    # Two-account state: one good (gives engine_ready a positive
    # current_value to satisfy the existing line-226 check), one
    # zero-value Purpose account that the existing logic was silently
    # skipping in _full_assignment_blockers.
    state = _engine_ready_state()
    state["accounts"] = [
        {
            "id": "acct_good",
            "type": "RRSP",
            "current_value": 100000,
            "is_held_at_purpose": True,
            "missing_holdings_confirmed": True,
        },
        {
            "id": "acct_zero",
            "type": "TFSA",
            "current_value": 0,  # ← the bug seed
            "is_held_at_purpose": True,
            "missing_holdings_confirmed": True,
        },
    ]
    state["goal_account_links"] = [
        {"goal_id": "goal_ready", "account_id": "acct_good", "allocated_amount": 100000},
        # Pct-based link on a zero-value account — this is the exact
        # combination that crashes engine.optimizer._link_amount.
        {"goal_id": "goal_ready", "account_id": "acct_zero", "allocated_pct": 1.0},
    ]
    workspace.reviewed_state = state
    workspace.readiness = readiness_for_state(state).__dict__
    workspace.save()
    _approve_required_sections(workspace, user)

    response = client.post(reverse("review-workspace-commit", args=[workspace.external_id]), {})

    assert response.status_code == 400, (
        f"Commit should be rejected with a 400 + advisor-actionable "
        f"blocker, not a 500 from the optimizer. Got "
        f"{response.status_code}: body={response.content!r}"
    )
    body = response.json()
    # The specific blocker lives in readiness.missing (engine_ready
    # missing list, since zero-value Purpose accounts are a "advisor
    # action required" gate per canon §6.3). The detail text gives the
    # category ("Reviewed state is not engine-ready"); the readiness
    # payload gives the per-blocker actionable message.
    missing = body.get("readiness", {}).get("missing", [])
    blocker_text = " ".join(item.get("label", "") for item in missing).lower()
    assert "value" in blocker_text, (
        f"Expected a readiness.missing entry naming the account's "
        f"missing/zero value. Got missing={missing!r}, detail={body.get('detail')!r}"
    )
    assert any("acct_zero" in item.get("label", "") for item in missing), (
        f"Blocker should name the affected account so the advisor "
        f"knows which one to fix. Got: {missing!r}"
    )


@pytest.mark.django_db
def test_zero_value_purpose_account_surfaces_household_level_blocker() -> None:
    """Defense-in-depth for the catalogued bug: even if a zero-value
    Purpose account survives state-level checks, the household-level
    portfolio_generation_blockers_for_household must surface a clear
    advisor-actionable blocker BEFORE the optimizer is reached.

    `current_value` is a NOT-NULL column with default=0, so the bug's
    "current_value=None" really means "current_value=0 from extraction
    that didn't return a number." Both surface the same failure mode
    in engine.optimizer._link_amount.
    """

    from web.api.review_state import portfolio_generation_blockers_for_household

    user = _user()
    household = models.Household.objects.create(
        external_id="zero_value_household",
        owner=user,
        display_name="Zero Value Household",
        household_type="single",
        household_risk_score=3,
    )
    person = models.Person.objects.create(
        household=household,
        external_id="person_zero",
        name="Zero Value Client",
        dob=date(1962, 1, 1),
    )
    # Good account so household-level checks have a positive baseline.
    good_account = models.Account.objects.create(
        household=household,
        external_id="acct_good",
        owner_person=person,
        account_type="RRSP",
        current_value=100000,
        is_held_at_purpose=True,
    )
    # Zero-value account is the bug seed.
    zero_account = models.Account.objects.create(
        household=household,
        external_id="acct_zero",
        owner_person=person,
        account_type="TFSA",
        current_value=0,
        is_held_at_purpose=True,
    )
    goal = models.Goal.objects.create(
        household=household,
        external_id="goal_zero",
        name="Retirement",
        target_date=date.today() + timedelta(days=365 * 5),
        goal_risk_score=3,
    )
    models.GoalAccountLink.objects.create(
        goal=goal,
        account=good_account,
        external_id="link_good",
        allocated_amount=100000,
    )
    models.GoalAccountLink.objects.create(
        goal=goal,
        account=zero_account,
        external_id="link_zero",
        allocated_pct=Decimal("1"),
    )

    # MUST NOT raise; must return a blocker list mentioning the
    # zero-value account so the advisor can act.
    blockers = portfolio_generation_blockers_for_household(household)
    assert isinstance(blockers, list), "blocker function must return a list, not raise"
    assert any("value" in b.lower() for b in blockers), (
        f"Expected a blocker mentioning the missing/zero account value. Got: {blockers}"
    )


@pytest.mark.django_db
def test_post_commit_worker_reconcile_does_not_downgrade_status(tmp_path, settings) -> None:
    """ROOT CAUSE for the catalogued post-R7 real-PII bug:

    The Niesner failure mode was: after a successful commit, a stale
    background worker pass on a still-draining doc called
    `reconcile_workspace`, which unconditionally wrote
    workspace.status = ENGINE_READY, silently downgrading the just-
    committed workspace. Subsequent commit attempts then failed the
    early-return at commit_reviewed_state:463 and tried to recreate
    the linked household → IntegrityError on Household.external_id.

    Race condition (sequential, single-threaded since both run in
    same Postgres):
      1. POST /commit → workspace.status = COMMITTED, household linked
      2. Worker processes the next doc job for this workspace
      3. Worker's reconcile_workspace overwrites status → ENGINE_READY
      4. Workspace is now in an inconsistent state: status=engine_ready
         but linked_household != None
      5. Next POST /commit fails at line 463 check, recreates household
         → IntegrityError on Household.external_id unique constraint.

    Fix: reconcile_workspace + create_state_version must be defensive
    — never downgrade a COMMITTED workspace.
    """

    from web.api.review_processing import reconcile_workspace

    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    call_command("seed_default_cma")
    user = _user()
    api_client = APIClient()
    api_client.force_authenticate(user=user)

    create_response = api_client.post(
        reverse("review-workspace-list"),
        {"label": "Worker race regression", "data_origin": "synthetic"},
        format="json",
    )
    assert create_response.status_code == 200
    workspace_id = create_response.json()["external_id"]

    api_client.patch(
        reverse("review-workspace-state", args=[workspace_id]),
        {"state": _engine_ready_state()},
        format="json",
    )
    for section in ("household", "people", "accounts", "goals", "goal_account_mapping", "risk"):
        api_client.post(
            reverse("review-workspace-approve-section", args=[workspace_id]),
            {"section": section, "status": "approved"},
            format="json",
        )

    first_commit = api_client.post(
        reverse("review-workspace-commit", args=[workspace_id]),
        format="json",
    )
    assert first_commit.status_code == 200
    household_id = first_commit.json()["household_id"]

    workspace = models.ReviewWorkspace.objects.get(external_id=workspace_id)
    assert workspace.status == models.ReviewWorkspace.Status.COMMITTED

    # ── simulate the catalogued race: a stale worker pass calls
    # reconcile_workspace AFTER the commit landed. This used to silently
    # downgrade status. Post-fix it must be a no-op (or at least preserve
    # COMMITTED).
    reconcile_workspace(workspace)

    workspace.refresh_from_db()
    assert workspace.status == models.ReviewWorkspace.Status.COMMITTED, (
        f"reconcile_workspace silently downgraded the committed workspace "
        f"to {workspace.status}. This is the catalogued post-R7 real-PII "
        "bug — reconcile must not write status when the workspace is "
        "already COMMITTED (and ideally should refuse to run at all)."
    )
    assert workspace.linked_household is not None
    assert workspace.linked_household.external_id == household_id

    # ── second commit must still be idempotent after the worker pass.
    second_commit = api_client.post(
        reverse("review-workspace-commit", args=[workspace_id]),
        format="json",
    )
    assert second_commit.status_code == 200, (
        f"Second commit after stale worker reconcile returned "
        f"{second_commit.status_code}; body={second_commit.content!r}"
    )
    assert second_commit.json()["household_id"] == household_id
    assert models.Household.objects.filter(external_id=household_id).count() == 1
