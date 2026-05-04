"""Unit tests for the R10 sweep automation helpers.

Targets the pure-function helpers that don't require a live backend
or filesystem-resident client folders. The full sweep is exercised
end-to-end by running the script against the demo stack; these
tests catch regressions in the stop-condition + idempotency logic
that the live sweep alone wouldn't surface cleanly.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# Module loaded by file path because scripts/ isn't a package.
_HERE = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location("r10_sweep", _HERE / "r10_sweep.py")
assert _SPEC is not None and _SPEC.loader is not None
r10_sweep = importlib.util.module_from_spec(_SPEC)
sys.modules["r10_sweep"] = r10_sweep
_SPEC.loader.exec_module(r10_sweep)


class TestSumWorkspaceCost:
    def test_returns_zero_for_empty_documents(self) -> None:
        assert r10_sweep._sum_workspace_cost({}) == 0.0
        assert r10_sweep._sum_workspace_cost({"documents": []}) == 0.0

    def test_sums_per_doc_cost_flat_shape(self) -> None:
        # Backwards-compat path: when processing_metadata has cost
        # at the top level (older payloads or test mocks), the
        # helper falls back to reading from there.
        payload = {
            "documents": [
                {"processing_metadata": {"bedrock_cost_estimate_usd": 0.05}},
                {"processing_metadata": {"bedrock_cost_estimate_usd": 0.03}},
                {"processing_metadata": {}},
            ]
        }
        assert abs(r10_sweep._sum_workspace_cost(payload) - 0.08) < 1e-9

    def test_sums_per_doc_cost_nested_shape(self) -> None:
        # Production shape (caught by the live R10 run, 2026-05-03):
        # the pipeline stores token + cost fields nested under the
        # ``extraction`` key. The helper must read from there or it
        # will report $0 for every doc — the bug the cost-key
        # follow-up commit fixed.
        payload = {
            "documents": [
                {"processing_metadata": {"extraction": {"bedrock_cost_estimate_usd": 0.05}}},
                {"processing_metadata": {"extraction": {"bedrock_cost_estimate_usd": 0.03}}},
                {"processing_metadata": {"extraction": {}}},
            ]
        }
        assert abs(r10_sweep._sum_workspace_cost(payload) - 0.08) < 1e-9

    def test_nested_shape_takes_precedence_over_flat(self) -> None:
        # If both shapes appear in the same payload (transitional
        # case during a deploy), the nested key wins because
        # ``_doc_extraction_meta`` returns the inner dict whenever
        # one exists.
        payload = {
            "documents": [
                {
                    "processing_metadata": {
                        "bedrock_cost_estimate_usd": 99.0,  # ignored
                        "extraction": {"bedrock_cost_estimate_usd": 0.05},
                    }
                },
            ]
        }
        assert abs(r10_sweep._sum_workspace_cost(payload) - 0.05) < 1e-9

    def test_handles_malformed_costs_gracefully(self) -> None:
        payload = {
            "documents": [
                {"processing_metadata": {"bedrock_cost_estimate_usd": "not-a-number"}},
                {"processing_metadata": {"bedrock_cost_estimate_usd": None}},
                {"processing_metadata": {"bedrock_cost_estimate_usd": 0.10}},
            ]
        }
        assert abs(r10_sweep._sum_workspace_cost(payload) - 0.10) < 1e-9


class TestDocExtractionMeta:
    def test_returns_inner_extraction_dict_when_present(self) -> None:
        doc = {
            "processing_metadata": {
                "extraction": {"bedrock_input_tokens": 1234, "extraction_path": "text"},
                "parse_method": "ocr_required",
            }
        }
        meta = r10_sweep._doc_extraction_meta(doc)
        assert meta.get("bedrock_input_tokens") == 1234
        assert meta.get("extraction_path") == "text"

    def test_returns_top_level_when_no_extraction_key(self) -> None:
        doc = {"processing_metadata": {"bedrock_input_tokens": 999}}
        meta = r10_sweep._doc_extraction_meta(doc)
        assert meta.get("bedrock_input_tokens") == 999

    def test_returns_empty_when_no_metadata(self) -> None:
        doc: dict = {}
        meta = r10_sweep._doc_extraction_meta(doc)
        assert meta == {}

    def test_handles_non_dict_extraction_value(self) -> None:
        # Defensive: if ``extraction`` is a non-dict (e.g., a string
        # from a malformed payload), fall back to top-level so the
        # caller doesn't crash on a .get() call.
        doc = {
            "processing_metadata": {
                "extraction": "malformed",
                "bedrock_input_tokens": 42,
            }
        }
        meta = r10_sweep._doc_extraction_meta(doc)
        assert meta.get("bedrock_input_tokens") == 42


class TestEmptySummary:
    def test_skipped_reason_threaded_through(self) -> None:
        s = r10_sweep._empty_summary("MissingFolder", skipped_reason="folder_not_found")
        assert s["folder"] == "MissingFolder"
        assert s["skipped_reason"] == "folder_not_found"
        assert s["docs_uploaded"] == 0
        assert s["cost_usd"] == 0.0

    def test_default_skipped_reason_is_none(self) -> None:
        s = r10_sweep._empty_summary("ActiveFolder")
        assert s["skipped_reason"] is None
        assert s["halted_on"] is None


class TestTodaySectionAlreadyPresent:
    def test_returns_false_for_missing_file(self, tmp_path: Path) -> None:
        assert (
            r10_sweep._today_section_already_present(tmp_path / "does-not-exist.md", "## Header")
            is False
        )

    def test_detects_today_dated_header(self, tmp_path: Path) -> None:
        from datetime import UTC, datetime

        today = datetime.now(UTC).strftime("%Y-%m-%d")
        target = tmp_path / "ledger.md"
        target.write_text(
            f"## Header — {today} 14:23 UTC\n\nContent\n",
            encoding="utf-8",
        )
        assert r10_sweep._today_section_already_present(target, "## Header") is True

    def test_does_not_match_different_date(self, tmp_path: Path) -> None:
        target = tmp_path / "ledger.md"
        target.write_text(
            "## Header — 1999-01-01 14:23 UTC\n\nContent\n",
            encoding="utf-8",
        )
        assert r10_sweep._today_section_already_present(target, "## Header") is False

    def test_does_not_match_different_prefix(self, tmp_path: Path) -> None:
        from datetime import UTC, datetime

        today = datetime.now(UTC).strftime("%Y-%m-%d")
        target = tmp_path / "ledger.md"
        target.write_text(
            f"## Other Section — {today}\n\nContent\n",
            encoding="utf-8",
        )
        assert r10_sweep._today_section_already_present(target, "## Header") is False


class TestMaybeAnonymize:
    def test_disabled_returns_identity_map(self) -> None:
        folders = ["Niesner", "Seltzer"]
        out, mapping = r10_sweep._maybe_anonymize(folders, enabled=False)
        assert out == folders
        assert mapping == {f: f for f in folders}

    def test_enabled_substitutes_sha256_prefix(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("MP20_SECURE_DATA_ROOT", str(tmp_path))
        folders = ["Niesner", "Seltzer"]
        out, mapping = r10_sweep._maybe_anonymize(folders, enabled=True)
        assert all(o.startswith("client_") for o in out)
        assert all(len(o) == len("client_") + 8 for o in out)
        # Mapping is keyed anon -> orig
        for anon, orig in mapping.items():
            assert orig in folders
            assert anon.startswith("client_")
        # Map file written to MP20_SECURE_DATA_ROOT/_debug/
        debug_dir = tmp_path / "_debug"
        assert debug_dir.is_dir()
        files = list(debug_dir.glob("r10_sweep_anon_map_*.txt"))
        assert len(files) == 1
        body = files[0].read_text(encoding="utf-8")
        assert "Niesner" in body
        assert "Seltzer" in body

    def test_enabled_without_secure_root_skips_map_write(self, monkeypatch) -> None:
        monkeypatch.delenv("MP20_SECURE_DATA_ROOT", raising=False)
        out, mapping = r10_sweep._maybe_anonymize(["A", "B"], enabled=True)
        # Anonymization still happens; map just isn't persisted.
        assert all(o.startswith("client_") for o in out)
        assert len(mapping) == 2


@pytest.mark.parametrize(
    "folders",
    [
        ["Gumprich"],
        ["Niesner", "Seltzer"],
        ["A", "B", "C", "D", "E", "F", "G"],
    ],
)
def test_maybe_anonymize_preserves_count(folders, monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("MP20_SECURE_DATA_ROOT", str(tmp_path))
    out, mapping = r10_sweep._maybe_anonymize(folders, enabled=True)
    assert len(out) == len(folders)
    assert len(mapping) == len(folders)
