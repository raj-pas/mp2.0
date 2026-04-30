from __future__ import annotations

from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from extraction.classification import classify_document
from extraction.parsers import parse_document_path
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


@pytest.mark.django_db
def test_field_specific_authority_prefers_kyc_identity_fact() -> None:
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
    assert state["conflicts"][0]["label"] == "People age"


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


def _user():
    User = get_user_model()
    return User.objects.create_user(
        username="extractor@example.com", email="extractor@example.com", password="pw"
    )
