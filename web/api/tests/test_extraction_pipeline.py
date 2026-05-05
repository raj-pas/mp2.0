from __future__ import annotations

from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from extraction.classification import classify_document
from extraction.llm import (
    DEFAULT_BEDROCK_MAX_TOKENS,
    BedrockExtractionError,
    BedrockNonJsonError,
    BedrockSchemaMismatchError,
    BedrockTokenLimitError,
    _bedrock_max_tokens,
    visual_content_blocks,
)
from extraction.parsers import parse_document_path
from extraction.schemas import FactCandidate
from web.api import models
from web.api.review_processing import process_job
from web.api.review_state import reviewed_state_from_workspace


def test_adaptive_classifier_uses_content_signals() -> None:
    result = classify_document(
        "bundle-item.pdf",
        ".pdf",
        text="Account Statement\nRRSP holdings\nMarket Value 250000",
    )

    assert result.document_type == "statement"
    assert result.route == "adaptive"
    assert "accounts" in result.schema_hints


def test_low_confidence_classifier_uses_multi_schema_sweep() -> None:
    result = classify_document("misc.pdf", ".pdf", text="A short ambiguous financial memo.")

    assert result.document_type == "generic_financial"
    assert result.route == "fallback"
    assert "generic_financial_sweep" in result.schema_hints


def test_xlsx_parser_preserves_sheet_names_and_row_locations(tmp_path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    path = tmp_path / "planning.xlsx"
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Retirement Projection"
    sheet.append(["Goal", "Horizon", "Amount"])
    sheet.append(["Retirement", 5, 250000])
    workbook.save(path)

    parsed = parse_document_path(path)
    classification = classify_document(
        path.name,
        path.suffix,
        text=parsed.text,
        parse_metadata=parsed.metadata,
    )

    assert parsed.method == "xlsx"
    assert parsed.metadata["sheet_names"] == ["Retirement Projection"]
    assert "Retirement Projection!2" in parsed.text
    assert classification.document_type == "planning"


def test_pdf_visual_blocks_use_provider_safe_payloads(tmp_path) -> None:
    fitz = pytest.importorskip("fitz")
    path = tmp_path / "scan.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Scanned page placeholder")
    document.save(path)

    blocks, overflow = visual_content_blocks(path, max_pages=1)

    assert blocks
    assert blocks[0]["source"]["media_type"] in {"image/jpeg", "image/png"}
    assert len(blocks[0]["source"]["data"]) < 6_500_000
    assert overflow == {}


@pytest.mark.django_db
def test_field_specific_authority_prefers_kyc_identity_fact() -> None:
    """Phase P1.1 (2026-05-05): identity anchors (display_name +
    account_number) on both docs let the entity-alignment matcher
    map both `people[0]` references to a single canonical person,
    so the age conflict surfaces on the canonical field."""
    user = _user()
    workspace = models.ReviewWorkspace.objects.create(label="Authority review", owner=user)
    kyc_doc = models.ReviewDocument.objects.create(
        workspace=workspace,
        original_filename="profile.pdf",
        extension="pdf",
        file_size=1,
        sha256="kyc-authority",
        document_type="kyc",
    )
    note_doc = models.ReviewDocument.objects.create(
        workspace=workspace,
        original_filename="notes.docx",
        extension="docx",
        file_size=1,
        sha256="note-authority",
        document_type="meeting_note",
    )
    # Identity anchors on both docs so the matcher merges to one
    # canonical person (TIGHTENED 2-field threshold: name + last4).
    for doc in (kyc_doc, note_doc):
        models.ExtractedFact.objects.create(
            workspace=workspace,
            document=doc,
            field="people[0].display_name",
            value="Sarah Chen",
            confidence="high",
            extraction_run_id="anchor",
        )
        models.ExtractedFact.objects.create(
            workspace=workspace,
            document=doc,
            field="accounts[0].account_number",
            value="98765432",
            confidence="high",
            extraction_run_id="anchor",
        )
    models.ExtractedFact.objects.create(
        workspace=workspace,
        document=note_doc,
        field="people[0].age",
        value=70,
        confidence="high",
        extraction_run_id="note",
    )
    models.ExtractedFact.objects.create(
        workspace=workspace,
        document=kyc_doc,
        field="people[0].age",
        value=62,
        confidence="medium",
        extraction_run_id="kyc",
    )

    state = reviewed_state_from_workspace(workspace)

    assert state["people"][0]["age"] == 62
    age_conflicts = [c for c in state["conflicts"] if c.get("label") == "People age"]
    assert age_conflicts, f"expected People age conflict; got {state['conflicts']!r}"


@pytest.mark.django_db
def test_manual_entry_marks_document_and_audits(tmp_path, settings) -> None:
    """The manual-entry endpoint is the advisor escape hatch when extraction
    can't recover. It must:
      1. Flip document.status from FAILED → MANUAL_ENTRY (distinct so
         reconcile knows to skip cleanly).
      2. Preserve the previous failure_code in metadata for audit.
      3. Cancel any in-flight jobs so they don't re-process.
      4. Fire `review_document_manual_entry_marked` audit event.
      5. Trigger reconcile so workspace state reflects the exclusion.
    """
    from django.urls import reverse
    from rest_framework.test import APIClient

    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(
        label="Manual entry escape",
        owner=user,
        data_origin=models.ReviewWorkspace.DataOrigin.SYNTHETIC,
    )
    document = models.ReviewDocument.objects.create(
        workspace=workspace,
        original_filename="hopeless.pdf",
        extension="pdf",
        file_size=1,
        sha256="manual-entry",
        status=models.ReviewDocument.Status.FAILED,
        failure_reason="Bedrock truncated thrice.",
        processing_metadata={"failure_code": "bedrock_token_limit"},
    )
    in_flight_job = models.ProcessingJob.objects.create(
        workspace=workspace,
        document=document,
        status=models.ProcessingJob.Status.QUEUED,
    )

    response = client.post(
        reverse("review-document-manual-entry", args=[workspace.external_id, document.id])
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "manual_entry"
    assert body["previous_status"] == "failed"
    assert body["previous_failure_code"] == "bedrock_token_limit"

    document.refresh_from_db()
    assert document.status == models.ReviewDocument.Status.MANUAL_ENTRY
    assert document.processing_metadata["manual_entry_previous_failure_code"] == (
        "bedrock_token_limit"
    )
    assert "manual_entry_marked_at" in document.processing_metadata
    assert document.failure_reason == ""

    in_flight_job.refresh_from_db()
    assert in_flight_job.status == models.ProcessingJob.Status.FAILED

    # Audit event
    from web.audit.models import AuditEvent

    audit = AuditEvent.objects.filter(
        action="review_document_manual_entry_marked",
        entity_id=str(document.id),
    ).first()
    assert audit is not None
    assert audit.metadata["previous_failure_code"] == "bedrock_token_limit"

    # Reconcile re-queued
    assert workspace.processing_jobs.filter(
        job_type=models.ProcessingJob.JobType.RECONCILE_WORKSPACE,
        status__in=[
            models.ProcessingJob.Status.QUEUED,
            models.ProcessingJob.Status.PROCESSING,
        ],
    ).exists()


@pytest.mark.django_db
def test_manual_entry_rejects_non_terminal_doc_status(tmp_path, settings) -> None:
    """Manual-entry is the escape hatch for non-recoverable extraction
    failures — it must NOT silently drop a successfully-reconciled doc
    out of the extraction record. Reject with 409 if the advisor tries
    to mark a non-terminal doc as manual entry.
    """
    from django.urls import reverse
    from rest_framework.test import APIClient

    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(
        label="Reconciled doc protection",
        owner=user,
        data_origin=models.ReviewWorkspace.DataOrigin.SYNTHETIC,
    )
    document = models.ReviewDocument.objects.create(
        workspace=workspace,
        original_filename="reconciled.pdf",
        extension="pdf",
        file_size=1,
        sha256="reconciled-protection",
        status=models.ReviewDocument.Status.RECONCILED,
    )

    response = client.post(
        reverse("review-document-manual-entry", args=[workspace.external_id, document.id])
    )

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "manual_entry_not_eligible"
    assert body["current_status"] == "reconciled"

    # The doc's status didn't change.
    document.refresh_from_db()
    assert document.status == models.ReviewDocument.Status.RECONCILED


@pytest.mark.django_db
def test_manual_entry_accepts_unsupported_and_ocr_required(tmp_path, settings) -> None:
    """Beyond `failed`, the eligible-states list also includes
    `unsupported` (file type Bedrock can't parse) and `ocr_required`
    (advisor opts out of OCR). Both should be markable as manual-entry.
    """
    from django.urls import reverse
    from rest_framework.test import APIClient

    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(
        label="Eligible-state coverage",
        owner=user,
        data_origin=models.ReviewWorkspace.DataOrigin.SYNTHETIC,
    )
    for sha, status in (
        ("eligible-unsupported", models.ReviewDocument.Status.UNSUPPORTED),
        ("eligible-ocr", models.ReviewDocument.Status.OCR_REQUIRED),
    ):
        document = models.ReviewDocument.objects.create(
            workspace=workspace,
            original_filename=f"{sha}.pdf",
            extension="pdf",
            file_size=1,
            sha256=sha,
            status=status,
        )
        response = client.post(
            reverse(
                "review-document-manual-entry",
                args=[workspace.external_id, document.id],
            )
        )
        assert response.status_code == 200, (
            f"manual-entry failed for status={status}: {response.content!r}"
        )


@pytest.mark.django_db
def test_manual_entry_rejects_non_pii_role(tmp_path, settings) -> None:
    """Same RBAC as the rest of the review pipeline — the analyst role
    must NOT be able to mark documents as manual-entry on behalf of an
    advisor.
    """
    from django.contrib.auth.models import Group
    from django.urls import reverse
    from rest_framework.test import APIClient

    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    User = get_user_model()
    analyst = User.objects.create_user(
        username="analyst@example.com",
        email="analyst@example.com",
        password="pw",
    )
    analyst_group, _ = Group.objects.get_or_create(name="financial_analyst")
    analyst.groups.add(analyst_group)
    advisor = _user()
    workspace = models.ReviewWorkspace.objects.create(
        label="Cross-role test",
        owner=advisor,
        data_origin=models.ReviewWorkspace.DataOrigin.SYNTHETIC,
    )
    document = models.ReviewDocument.objects.create(
        workspace=workspace,
        original_filename="x.pdf",
        extension="pdf",
        file_size=1,
        sha256="rbac-test",
        status=models.ReviewDocument.Status.FAILED,
    )

    client = APIClient()
    client.force_authenticate(user=analyst)
    response = client.post(
        reverse("review-document-manual-entry", args=[workspace.external_id, document.id])
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_typed_bedrock_error_surfaces_structured_failure_code(
    tmp_path, settings, monkeypatch
) -> None:
    """End-to-end: when the extraction layer raises a typed
    BedrockExtractionError, the worker's _fail_or_retry must propagate
    `.failure_code` (not the class name) into both the document's
    processing_metadata and the audit event.

    Without this, the UI's failure-code copy and recovery affordances
    can't route correctly: the advisor sees `ValueError` instead of
    `bedrock_token_limit` and gets generic copy.
    """
    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    user = _user()
    workspace = models.ReviewWorkspace.objects.create(
        label="Failure-code wiring",
        owner=user,
        data_origin=models.ReviewWorkspace.DataOrigin.SYNTHETIC,
    )
    storage_dir = Path(settings.MP20_SECURE_DATA_ROOT) / "review-workspaces" / workspace.external_id
    storage_dir.mkdir(parents=True)
    source = storage_dir / "notes.txt"
    source.write_text("Synthetic note.")
    document = models.ReviewDocument.objects.create(
        workspace=workspace,
        original_filename="notes.txt",
        extension="txt",
        file_size=source.stat().st_size,
        sha256="failure-code",
        storage_path=f"review-workspaces/{workspace.external_id}/notes.txt",
    )
    job = models.ProcessingJob.objects.create(
        workspace=workspace,
        document=document,
        attempts=3,
        max_attempts=3,  # exhaust on this attempt → terminal FAILED
    )

    def raise_token_limit(*_args, **_kwargs):
        raise BedrockTokenLimitError("Bedrock truncated mid-output.")

    monkeypatch.setattr("web.api.review_processing.extract_facts", raise_token_limit)

    process_job(job)

    document.refresh_from_db()
    job.refresh_from_db()
    assert document.status == models.ReviewDocument.Status.FAILED
    assert document.processing_metadata["failure_code"] == "bedrock_token_limit"
    assert job.metadata["failure_code"] == "bedrock_token_limit"
    # Audit event also carries the structured code.
    from web.audit.models import AuditEvent

    audit = AuditEvent.objects.filter(
        action="review_processing_failed", entity_id=str(job.id)
    ).first()
    assert audit is not None
    assert audit.metadata["failure_code"] == "bedrock_token_limit"


@pytest.mark.django_db
def test_failed_reprocess_preserves_previous_good_facts(tmp_path, settings, monkeypatch) -> None:
    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    user = _user()
    workspace = models.ReviewWorkspace.objects.create(
        label="Atomic reprocess",
        owner=user,
        data_origin=models.ReviewWorkspace.DataOrigin.SYNTHETIC,
    )
    storage_dir = Path(settings.MP20_SECURE_DATA_ROOT) / "review-workspaces" / workspace.external_id
    storage_dir.mkdir(parents=True)
    source = storage_dir / "notes.txt"
    source.write_text("Account statement with holdings.")
    document = models.ReviewDocument.objects.create(
        workspace=workspace,
        original_filename="notes.txt",
        extension="txt",
        file_size=source.stat().st_size,
        sha256="atomic",
        storage_path=f"review-workspaces/{workspace.external_id}/notes.txt",
    )
    models.ExtractedFact.objects.create(
        workspace=workspace,
        document=document,
        field="household.display_name",
        value="Existing Good Fact",
        extraction_run_id="old",
    )
    job = models.ProcessingJob.objects.create(
        workspace=workspace,
        document=document,
        attempts=3,
        max_attempts=3,
    )

    def fail_extract(*_args, **_kwargs):
        raise ValueError("synthetic parser failure")

    monkeypatch.setattr("web.api.review_processing.extract_facts", fail_extract)

    process_job(job)

    document.refresh_from_db()
    assert document.status == models.ReviewDocument.Status.FAILED
    assert models.ExtractedFact.objects.filter(
        document=document,
        field="household.display_name",
        value="Existing Good Fact",
    ).exists()


@pytest.mark.django_db
def test_process_document_skips_null_fact_values(tmp_path, settings, monkeypatch) -> None:
    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    user = _user()
    workspace = models.ReviewWorkspace.objects.create(
        label="Null fact review",
        owner=user,
        data_origin=models.ReviewWorkspace.DataOrigin.SYNTHETIC,
    )
    storage_dir = Path(settings.MP20_SECURE_DATA_ROOT) / "review-workspaces" / workspace.external_id
    storage_dir.mkdir(parents=True)
    source = storage_dir / "notes.txt"
    source.write_text("Household name Demo.")
    document = models.ReviewDocument.objects.create(
        workspace=workspace,
        original_filename="notes.txt",
        extension="txt",
        file_size=source.stat().st_size,
        sha256="null-fact",
        storage_path=f"review-workspaces/{workspace.external_id}/notes.txt",
    )
    job = models.ProcessingJob.objects.create(workspace=workspace, document=document)

    monkeypatch.setattr(
        "web.api.review_processing.extract_facts",
        lambda *_args, **_kwargs: (
            [
                FactCandidate(
                    field="household.display_name",
                    value="Demo",
                    confidence="high",
                    derivation_method="extracted",
                    extraction_run_id="run",
                ),
                FactCandidate(
                    field="risk.household_score",
                    value=None,
                    confidence="medium",
                    derivation_method="extracted",
                    extraction_run_id="run",
                ),
            ],
            {},
        ),
    )

    process_job(job)

    document.refresh_from_db()
    assert document.status == models.ReviewDocument.Status.FACTS_EXTRACTED
    assert models.ExtractedFact.objects.filter(document=document).count() == 1
    assert document.processing_metadata["extraction"]["discarded_fact_count"] == 1


def test_bedrock_max_tokens_defaults_to_16384(monkeypatch) -> None:
    """Regression guard: the default output budget must be 16384.

    The previous default (4096) deterministically truncated mid-JSON for
    spreadsheet planning docs and large native PDFs in the 2026-05-01
    Niesner real-PII checkpoint. Lowering this default below 16384
    re-introduces the truncation bug.
    """
    monkeypatch.delenv("MP20_BEDROCK_MAX_TOKENS", raising=False)
    assert _bedrock_max_tokens() == 16384
    assert DEFAULT_BEDROCK_MAX_TOKENS == 16384


def test_bedrock_max_tokens_honors_env_override(monkeypatch) -> None:
    monkeypatch.setenv("MP20_BEDROCK_MAX_TOKENS", "32768")
    assert _bedrock_max_tokens() == 32768


def test_bedrock_max_tokens_falls_back_on_invalid_env(monkeypatch) -> None:
    """Garbage env values must NOT silently degrade extraction quality.

    A typo'd or non-int MP20_BEDROCK_MAX_TOKENS (`"large"`, `"-1"`,
    `"0"`, empty) should fall back to the safe default rather than
    propagating a low/zero limit into Bedrock and re-introducing the
    truncation bug.
    """
    for bad in ("not-a-number", "0", "-100", ""):
        monkeypatch.setenv("MP20_BEDROCK_MAX_TOKENS", bad)
        assert _bedrock_max_tokens() == 16384, f"failed for env value: {bad!r}"


def test_bedrock_extraction_error_inherits_value_error() -> None:
    """Existing `except ValueError:` callers (the repair-retry path,
    _fail_or_retry, etc.) must keep catching the typed errors without
    code change.
    """
    for cls in (BedrockNonJsonError, BedrockTokenLimitError, BedrockSchemaMismatchError):
        assert issubclass(cls, ValueError), f"{cls.__name__} must inherit from ValueError"
        assert issubclass(cls, BedrockExtractionError)


def test_bedrock_call_sites_use_configurable_max_tokens(monkeypatch) -> None:
    """All three Bedrock invocation sites must read max_tokens from the
    same configurable source. Hardcoding 4096 (or any other constant)
    in any one site re-introduces the truncation bug for that path.
    """
    from extraction import llm as llm_module

    src = (Path(llm_module.__file__)).read_text()
    # No remaining hardcoded `max_tokens=4096` in the module — every call
    # site routes through `_bedrock_max_tokens()`.
    assert "max_tokens=4096" not in src, (
        "Found a hardcoded max_tokens=4096 in extraction/llm.py. "
        "All Bedrock call sites must use _bedrock_max_tokens() so the "
        "16384-default truncation fix applies uniformly."
    )
    # All three call sites we know about should reference the helper.
    helper_call_count = src.count("_bedrock_max_tokens()")
    assert helper_call_count >= 3, (
        f"Expected at least 3 _bedrock_max_tokens() call sites (text + "
        f"visual + repair), found {helper_call_count}. A new Bedrock "
        f"call site without the helper would re-introduce the truncation "
        f"bug."
    )


def _user():
    User = get_user_model()
    return User.objects.create_user(
        username="extractor@example.com", email="extractor@example.com", password="pw"
    )
