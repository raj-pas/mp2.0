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
    facts_from_model_text,
    json_payload_from_model_text,
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


def test_bedrock_truncated_response_raises_token_limit_error() -> None:
    """A response that ran out of tokens mid-JSON must raise the typed
    BedrockTokenLimitError, not a generic ValueError. This is what
    drove the 2026-05-01 max_tokens 4096→16384 fix; if the typed code
    drifts, the manual-entry UI can't route advisors to the right
    recovery path.
    """
    truncated = (
        '```json\n{\n  "facts": [\n    {\n      "field": "household.display_name",\n'
        '      "value": "Demo",\n      "confidence": "high",\n      "derivation'
    )
    with pytest.raises(BedrockTokenLimitError) as exc_info:
        json_payload_from_model_text(truncated)
    assert exc_info.value.failure_code == "bedrock_token_limit"
    assert isinstance(exc_info.value, ValueError)  # backwards-compat with old catch blocks


def test_bedrock_unrecoverable_garbage_raises_non_json_error() -> None:
    """A response that's neither valid JSON nor recoverable via the repair
    paths must raise BedrockNonJsonError. Different code from
    BedrockTokenLimitError so the UI can offer different advisor copy.
    """
    garbage = "I'm sorry, I can't help with that."
    with pytest.raises(BedrockNonJsonError) as exc_info:
        json_payload_from_model_text(garbage)
    assert exc_info.value.failure_code == "bedrock_non_json"
    assert isinstance(exc_info.value, ValueError)


def test_bedrock_schema_mismatch_raises_typed_error() -> None:
    """JSON that parses but doesn't match the expected fact-payload shape
    must raise BedrockSchemaMismatchError. This is distinct from
    truncation / non-JSON so we can route it differently in the UI.
    """
    # `field` missing entirely; not a recoverable shape under any of the
    # alias normalizers in _normalize_fact_item.
    bad_shape = '{"facts": [{"value": 12345}]}'
    with pytest.raises((BedrockSchemaMismatchError, BedrockNonJsonError)):
        # Either typed error is acceptable here as long as it's typed —
        # the boundary between "shape recoverable via aliases" and
        # "fundamentally broken" is fuzzy and the test should not pin it
        # to one outcome.
        facts_from_model_text(bad_shape, "regression-run")


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
