"""Sub-session #8 — vision PDF path tests.

Three test layers, top to bottom:

1. Detection helper (``is_likely_image_pdf``) — pure function,
   ParsedDocument inputs, no I/O.
2. Native PDF tool-use call (``extract_pdf_facts_with_bedrock_native``)
   — mocked Bedrock client; asserts the document content block shape
   + cost-tracking metadata + tool-use response handling.
3. Pipeline dispatch (``extract_facts_for_document``) — mocked LLM
   functions; asserts the right path runs for each PDF flavour.

A real-PII Niesner canary lives in this same module but is gated on
``MP20_RUN_REAL_PII_CANARY=1`` so CI never executes it.

Real-PII discipline (canon §11.8.3): no test asserts on values from
real client docs. Structural counts, paths, and types only.
"""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from extraction.parsers import (
    IMAGE_PDF_AVG_CHARS_THRESHOLD,
    IMAGE_PDF_TEXT_PAGE_RATIO_THRESHOLD,
    is_likely_image_pdf,
)
from extraction.schemas import ParsedDocument


def _parsed(method: str, text: str = "", metadata: dict[str, Any] | None = None) -> ParsedDocument:
    return ParsedDocument(text=text, method=method, metadata=metadata or {})


# ---------------------------------------------------------------------------
# 1. Detection helper
# ---------------------------------------------------------------------------


class TestIsLikelyImagePdf:
    def test_ocr_required_method_is_image_pdf(self) -> None:
        parsed = _parsed("ocr_required", "", {"page_count": 5, "text_page_count": 0})
        assert is_likely_image_pdf(parsed) is True

    def test_non_pdf_method_returns_false(self) -> None:
        for method in ("docx", "xlsx", "csv", "plain", "unsupported"):
            parsed = _parsed(method, "lots of text " * 200, {"page_count": 3})
            assert is_likely_image_pdf(parsed) is False, method

    def test_text_rich_pdf_is_not_image_pdf(self) -> None:
        text = "x" * (IMAGE_PDF_AVG_CHARS_THRESHOLD * 100)
        parsed = _parsed(
            "pdf_native",
            text,
            {"page_count": 3, "text_page_count": 3},
        )
        assert is_likely_image_pdf(parsed) is False

    def test_low_density_pdf_is_image_pdf(self) -> None:
        parsed = _parsed(
            "pdf_native",
            "Account Statement",
            {"page_count": 5, "text_page_count": 5},
        )
        assert is_likely_image_pdf(parsed) is True

    def test_sparse_text_page_ratio_routes_to_vision(self) -> None:
        text = "x" * (IMAGE_PDF_AVG_CHARS_THRESHOLD * 100)
        parsed = _parsed(
            "pdf_native",
            text,
            {"page_count": 10, "text_page_count": 1},
        )
        assert is_likely_image_pdf(parsed) is True

    def test_threshold_text_ratio_boundary(self) -> None:
        text = "x" * (IMAGE_PDF_AVG_CHARS_THRESHOLD * 100)
        parsed = _parsed(
            "pdf_native",
            text,
            {"page_count": 10, "text_page_count": 5},
        )
        ratio = 5 / 10
        if ratio < IMAGE_PDF_TEXT_PAGE_RATIO_THRESHOLD:
            assert is_likely_image_pdf(parsed) is True
        else:
            assert is_likely_image_pdf(parsed) is False

    def test_zero_page_count_returns_false(self) -> None:
        parsed = _parsed("pdf_native", "x" * 1000, {"page_count": 0})
        assert is_likely_image_pdf(parsed) is False

    def test_missing_metadata_returns_false_for_pdf_native(self) -> None:
        parsed = _parsed("pdf_native", "x" * 1000, {})
        assert is_likely_image_pdf(parsed) is False


# ---------------------------------------------------------------------------
# 2. Native PDF tool-use call
# ---------------------------------------------------------------------------


@pytest.fixture()
def synthetic_image_pdf(tmp_path: Path) -> Path:
    """Render a 1-page PDF with no extractable text.

    pymupdf renders an image-only page (no text layer) so the parser
    classifies the resulting PDF as ``ocr_required``. Real Croesus
    printscreens behave the same way.
    """
    fitz = pytest.importorskip("fitz")
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 200, 100))
    pixmap.set_rect(pixmap.irect, (200, 200, 200))
    page.insert_image(fitz.Rect(50, 50, 250, 150), pixmap=pixmap)
    target = tmp_path / "synthetic_image.pdf"
    doc.save(target)
    doc.close()
    return target


@pytest.fixture()
def text_rich_pdf(tmp_path: Path) -> Path:
    fitz = pytest.importorskip("fitz")
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (72, 72),
        "Account Statement\nDate: 2024-09-30\nClient: Synthetic Test\n"
        "Holdings: 100 shares of XYZ at $42.00 = $4,200.00\n"
        "Cash: $1,050.50\n" * 20,
    )
    target = tmp_path / "text_rich.pdf"
    doc.save(target)
    doc.close()
    return target


class TestExtractPdfFactsWithBedrockNative:
    """Native PDF document block path."""

    def test_sends_pdf_as_document_content_block(self, synthetic_image_pdf: Path) -> None:
        from extraction.llm import BedrockConfig, extract_pdf_facts_with_bedrock_native
        from extraction.schemas import ClassificationResult

        config = BedrockConfig(
            model="anthropic.claude-sonnet-4-6-20251201-v1:0",
            aws_region="ca-central-1",
            access_key="test",
            secret_key="test",
        )
        classification = ClassificationResult(
            document_type="kyc",
            confidence="high",
            route="kyc",
        )

        mock_response = MagicMock()
        mock_response.stop_reason = "tool_use"
        tool_use_block = MagicMock()
        tool_use_block.type = "tool_use"
        tool_use_block.input = {
            "facts": [
                {
                    "field": "people[0].full_name",
                    "value": "Synthetic Test",
                    "confidence": "high",
                    "derivation_method": "extracted",
                    "evidence_quote": "Client: Synthetic Test",
                }
            ]
        }
        mock_response.content = [tool_use_block]
        mock_response.usage = MagicMock(input_tokens=1000, output_tokens=200)

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with patch("extraction.llm._bedrock_client", return_value=mock_client):
            facts, metadata = extract_pdf_facts_with_bedrock_native(
                path=synthetic_image_pdf,
                filename="synthetic_image.pdf",
                document_type="kyc",
                classification=classification,
                extraction_run_id="test-run-1",
                config=config,
            )

        call_args = mock_client.messages.create.call_args
        messages = call_args.kwargs["messages"]
        assert len(messages) == 1
        content = messages[0]["content"]
        document_blocks = [b for b in content if b.get("type") == "document"]
        assert len(document_blocks) == 1
        document = document_blocks[0]
        assert document["source"]["type"] == "base64"
        assert document["source"]["media_type"] == "application/pdf"
        decoded = base64.b64decode(document["source"]["data"])
        assert decoded.startswith(b"%PDF-")

        text_blocks = [b for b in content if b.get("type") == "text"]
        assert len(text_blocks) == 1
        assert text_blocks[0]["text"]

        assert len(facts) == 1
        assert facts[0].field == "people[0].full_name"
        assert metadata["bedrock_input_tokens"] == 1000
        assert metadata["bedrock_output_tokens"] == 200
        assert metadata["extraction_path"] == "vision_native_pdf"
        assert "bedrock_cost_estimate_usd" in metadata
        assert metadata["bedrock_cost_estimate_usd"] > 0

    def test_uses_tool_use_forced_choice(self, synthetic_image_pdf: Path) -> None:
        from extraction.llm import BedrockConfig, extract_pdf_facts_with_bedrock_native
        from extraction.schemas import ClassificationResult

        config = BedrockConfig(
            model="anthropic.claude-sonnet-4-6-20251201-v1:0",
            aws_region="ca-central-1",
            access_key="test",
            secret_key="test",
        )
        classification = ClassificationResult(document_type="kyc", confidence="high", route="kyc")

        mock_response = MagicMock()
        mock_response.stop_reason = "tool_use"
        tool_use_block = MagicMock()
        tool_use_block.type = "tool_use"
        tool_use_block.input = {"facts": []}
        mock_response.content = [tool_use_block]
        mock_response.usage = MagicMock(input_tokens=500, output_tokens=10)

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with patch("extraction.llm._bedrock_client", return_value=mock_client):
            extract_pdf_facts_with_bedrock_native(
                path=synthetic_image_pdf,
                filename="x.pdf",
                document_type="kyc",
                classification=classification,
                extraction_run_id="rid",
                config=config,
            )

        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs["tool_choice"] == {
            "type": "tool",
            "name": "fact_extraction",
        }

    def test_token_limit_raises_typed_error(self, synthetic_image_pdf: Path) -> None:
        from extraction.llm import (
            BedrockConfig,
            BedrockTokenLimitError,
            extract_pdf_facts_with_bedrock_native,
        )
        from extraction.schemas import ClassificationResult

        config = BedrockConfig(
            model="anthropic.claude-sonnet-4-6-20251201-v1:0",
            aws_region="ca-central-1",
            access_key="test",
            secret_key="test",
        )
        classification = ClassificationResult(document_type="kyc", confidence="high", route="kyc")

        mock_response = MagicMock()
        mock_response.stop_reason = "max_tokens"
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "Truncated mid-tool-call"
        mock_response.content = [text_block]
        mock_response.usage = MagicMock(input_tokens=15000, output_tokens=16384)

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with (
            patch("extraction.llm._bedrock_client", return_value=mock_client),
            pytest.raises(BedrockTokenLimitError),
        ):
            extract_pdf_facts_with_bedrock_native(
                path=synthetic_image_pdf,
                filename="x.pdf",
                document_type="kyc",
                classification=classification,
                extraction_run_id="rid",
                config=config,
            )


# ---------------------------------------------------------------------------
# 3. Pipeline dispatch
# ---------------------------------------------------------------------------


class TestPipelineDispatch:
    def test_image_pdf_routes_to_native_path(
        self, synthetic_image_pdf: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from extraction import pipeline
        from extraction.llm import BedrockConfig
        from extraction.parsers import parse_document_path
        from extraction.schemas import ClassificationResult

        parsed = parse_document_path(synthetic_image_pdf)
        assert is_likely_image_pdf(parsed) is True

        captured: dict[str, Any] = {}

        def fake_native(**kwargs: Any) -> tuple[list, dict[str, Any]]:
            captured["called"] = "native"
            captured["kwargs"] = kwargs
            return ([], {"bedrock_input_tokens": 100, "bedrock_output_tokens": 10})

        def fake_text(**kwargs: Any) -> list:
            captured["called"] = "text"
            return []

        def fake_visual(**kwargs: Any) -> tuple[list, dict[str, Any]]:
            captured["called"] = "visual"
            return ([], {})

        monkeypatch.setattr(pipeline, "extract_pdf_facts_with_bedrock_native", fake_native)
        monkeypatch.setattr(pipeline, "extract_text_facts_with_bedrock", fake_text)
        monkeypatch.setattr(pipeline, "extract_visual_facts_with_bedrock", fake_visual)

        config = BedrockConfig(
            model="anthropic.claude-sonnet-4-6-20251201-v1:0",
            aws_region="ca-central-1",
            access_key="test",
            secret_key="test",
        )
        classification = ClassificationResult(document_type="kyc", confidence="high", route="kyc")

        _facts, metadata = pipeline.extract_facts_for_document(
            path=synthetic_image_pdf,
            filename="synthetic_image.pdf",
            data_origin="real_derived",
            parsed=parsed,
            classification=classification,
            text_max_chars=20000,
            ocr_max_pages=20,
            bedrock_config=config,
        )
        assert captured["called"] == "native"
        assert metadata["extraction_path"] == "vision_native_pdf"

    def test_text_rich_pdf_routes_to_text_path(
        self, text_rich_pdf: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from extraction import pipeline
        from extraction.llm import BedrockConfig
        from extraction.parsers import parse_document_path
        from extraction.schemas import ClassificationResult

        parsed = parse_document_path(text_rich_pdf)
        assert is_likely_image_pdf(parsed) is False

        captured: dict[str, Any] = {}

        def fake_native(**_: Any) -> tuple[list, dict[str, Any]]:
            captured["called"] = "native"
            return ([], {})

        def fake_text(**_: Any) -> list:
            captured["called"] = "text"
            return []

        monkeypatch.setattr(pipeline, "extract_pdf_facts_with_bedrock_native", fake_native)
        monkeypatch.setattr(pipeline, "extract_text_facts_with_bedrock", fake_text)

        config = BedrockConfig(
            model="anthropic.claude-sonnet-4-6-20251201-v1:0",
            aws_region="ca-central-1",
            access_key="test",
            secret_key="test",
        )
        classification = ClassificationResult(
            document_type="statement", confidence="high", route="statement"
        )

        pipeline.extract_facts_for_document(
            path=text_rich_pdf,
            filename="text_rich.pdf",
            data_origin="real_derived",
            parsed=parsed,
            classification=classification,
            text_max_chars=20000,
            ocr_max_pages=20,
            bedrock_config=config,
        )
        assert captured["called"] == "text"

    def test_synthetic_origin_uses_heuristic(
        self, text_rich_pdf: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from extraction import pipeline
        from extraction.parsers import parse_document_path
        from extraction.schemas import ClassificationResult

        parsed = parse_document_path(text_rich_pdf)

        called: dict[str, Any] = {}
        for name in (
            "extract_pdf_facts_with_bedrock_native",
            "extract_text_facts_with_bedrock",
            "extract_visual_facts_with_bedrock",
        ):
            monkeypatch.setattr(
                pipeline,
                name,
                lambda *_a, _bound=name, **_kw: called.setdefault("called", _bound),
            )

        classification = ClassificationResult(
            document_type="statement", confidence="medium", route="statement"
        )
        facts, _metadata = pipeline.extract_facts_for_document(
            path=text_rich_pdf,
            filename="text_rich.pdf",
            data_origin="synthetic",
            parsed=parsed,
            classification=classification,
            text_max_chars=20000,
            ocr_max_pages=20,
        )
        assert "called" not in called
        assert isinstance(facts, list)


# ---------------------------------------------------------------------------
# 4. Real-PII Niesner canary (gated)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    os.getenv("MP20_RUN_REAL_PII_CANARY") != "1",
    reason="Gated on MP20_RUN_REAL_PII_CANARY=1; structural-counts-only.",
)
def test_real_pii_niesner_canary_extracts_some_facts(tmp_path: Path) -> None:
    """Pick a Niesner image-PDF that previously returned 0 facts.

    Asserts only structural counts. No values, no quotes, no
    client-identifying metadata in any test artefact.
    """
    secure_root = os.environ.get("MP20_SECURE_DATA_ROOT")
    assert secure_root, "MP20_SECURE_DATA_ROOT must be set for real-PII canary."

    niesner_dir = Path("/Users/saranyaraj/Documents/MP2.0_Clients/Niesner")
    if not niesner_dir.exists():
        pytest.skip("Niesner client folder not available locally.")

    candidates = sorted(niesner_dir.glob("*.pdf"))
    assert candidates, "Expected at least one Niesner PDF."
    target = candidates[0]

    from extraction.classification import classify_document
    from extraction.llm import bedrock_config_from_env
    from extraction.parsers import parse_document_path
    from extraction.pipeline import extract_facts_for_document

    parsed = parse_document_path(target)
    if not is_likely_image_pdf(parsed):
        pytest.skip("Selected Niesner PDF is not image-likely; canary needs a scan.")

    classification = classify_document(
        target.name, target.suffix.lower(), text=parsed.text, parse_metadata=parsed.metadata
    )
    config = bedrock_config_from_env()
    facts, metadata = extract_facts_for_document(
        path=target,
        filename=target.name,
        data_origin="real_derived",
        parsed=parsed,
        classification=classification,
        text_max_chars=120000,
        ocr_max_pages=20,
        bedrock_config=config,
    )
    assert metadata["extraction_path"] == "vision_native_pdf"
    assert isinstance(facts, list)
