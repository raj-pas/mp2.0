from __future__ import annotations

from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from extraction.classification import classify_document
from extraction.llm import (
    DEFAULT_BEDROCK_MAX_TOKENS,
    _bedrock_max_tokens,
    facts_from_model_text,
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


def test_bedrock_fact_parser_accepts_aliases_and_skips_null_values() -> None:
    facts = facts_from_model_text(
        """
        [
          {"field_path": "household.display_name", "raw_value": "Demo", "confidence": "High"},
          {"path": "risk.household_score", "value": null, "confidence_level": "low"}
        ]
        """,
        "run-1",
    )

    assert len(facts) == 1
    assert facts[0].field == "household.display_name"
    assert facts[0].confidence == "high"


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
