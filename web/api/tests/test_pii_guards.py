"""Tests for Phase 2 PII scrub.

Closes audit findings PII-1, PII-2, PII-3, PII-4, PII-SER, REDACT-1
(per docs/agent/extraction-audit.md). Verifies that:
  - exception summaries persisted to DB columns are structured
  - HTTP responses use sanitized payloads
  - audit-event metadata never carries raw str(exc)
  - extended redaction patterns catch routing numbers, phone numbers,
    and addresses
"""

from __future__ import annotations

import pytest
from extraction.llm import BedrockNonJsonError, BedrockTokenLimitError
from web.api.error_codes import (
    failure_code_for_exc,
    friendly_message_for_code,
    safe_audit_metadata,
    safe_exception_summary,
    safe_response_payload,
)
from web.api.review_redaction import redact_evidence_quote


class TestFailureCodeMapping:
    def test_bedrock_token_limit_maps_to_typed_code(self) -> None:
        exc = BedrockTokenLimitError("real-PII content that should not leak: client X")
        assert failure_code_for_exc(exc) == "bedrock_token_limit"

    def test_bedrock_non_json_maps_to_typed_code(self) -> None:
        exc = BedrockNonJsonError("more PII-laden text from Bedrock response")
        assert failure_code_for_exc(exc) == "bedrock_non_json"

    def test_unknown_exception_falls_back_to_class_name(self) -> None:
        exc = ValueError("real-PII goes here")
        # Class name is structurally PII-safe even if the message body leaks.
        assert failure_code_for_exc(exc) == "ValueError"


class TestSafeExceptionSummary:
    def test_summary_is_structured_only_no_pii(self) -> None:
        # Construct an exception whose message simulates a PII-leak
        # body that real-PII Bedrock errors might carry.
        exc = BedrockNonJsonError(
            "Failed to parse Bedrock response for client Jane Smith, "
            "DOB 1980-04-15, account 1234567890..."
        )
        summary = safe_exception_summary(exc)
        # Summary contains only ExceptionClass:failure_code
        assert summary == "BedrockNonJsonError:bedrock_non_json"
        # Verify NO PII content is in the summary
        assert "Jane" not in summary
        assert "1980" not in summary
        assert "1234567890" not in summary


class TestSafeResponsePayload:
    def test_response_payload_carries_code_and_friendly_message(self) -> None:
        exc = BedrockTokenLimitError("doc too long: client X's 2024 statement")
        payload = safe_response_payload(exc)
        assert payload["code"] == "bedrock_token_limit"
        assert "manual entry" in payload["detail"].lower()
        # Verify NO PII content in detail
        assert "client X" not in payload["detail"]
        assert "2024 statement" not in payload["detail"]

    def test_response_payload_extra_kwargs_merge(self) -> None:
        exc = ValueError("internal validation error")
        payload = safe_response_payload(exc, missing_approvals=["goals"], readiness={})
        assert payload["code"] == "ValueError"
        assert payload["missing_approvals"] == ["goals"]
        assert "readiness" in payload


class TestSafeAuditMetadata:
    def test_audit_metadata_has_structured_failure_code_only(self) -> None:
        exc = BedrockNonJsonError("PII-laden message")
        meta = safe_audit_metadata(exc, workspace_id="abc-123", advisor_email="x@y.z")
        assert meta["failure_code"] == "bedrock_non_json"
        assert meta["workspace_id"] == "abc-123"
        # detail must not be in the metadata
        assert "detail" not in meta
        # PII content must not surface anywhere
        for key, value in meta.items():
            assert "PII-laden" not in str(value), f"PII leaked into key {key}: {value!r}"


class TestRedactionPatternsExtended:
    def test_redacts_routing_number_format(self) -> None:
        # SIN + routing share the same `\d{3}-\d{3}-\d{3}` format.
        # SIN/SSN pattern fires first; either marker is acceptable
        # because the goal is "value is gone", not "marker says routing".
        text = "Routing number: 099-001-123 belongs to Royal Bank"
        result = redact_evidence_quote(text)
        assert "099-001-123" not in result
        assert "[SIN/SSN REDACTED]" in result or "[ROUTING REDACTED]" in result

    def test_redacts_phone_number_canadian_format(self) -> None:
        text = "Reach client at (204) 555-1234 or 204-555-1234"
        result = redact_evidence_quote(text)
        assert "(204) 555-1234" not in result
        assert "204-555-1234" not in result
        assert "[PHONE REDACTED]" in result

    def test_redacts_street_address(self) -> None:
        text = "Mailing address: 123 Main Street, Winnipeg MB"
        result = redact_evidence_quote(text)
        assert "123 Main Street" not in result
        assert "[ADDRESS REDACTED]" in result

    def test_does_not_redact_normal_amounts(self) -> None:
        # Sanity: $5,000.00 shouldn't trigger any of the new patterns
        text = "Account balance: $5,000.00 invested in equity funds."
        result = redact_evidence_quote(text)
        assert "$5,000.00" in result


class TestFriendlyMessageMapping:
    def test_known_codes_have_specific_copy(self) -> None:
        msg = friendly_message_for_code("bedrock_token_limit")
        assert "manual entry" in msg.lower()

    def test_unknown_codes_fall_back_to_default(self) -> None:
        msg = friendly_message_for_code("never_seen_before_code")
        # Default is the catch-all "Something went wrong..."
        assert "retry" in msg.lower() or "ops" in msg.lower()


@pytest.mark.django_db
class TestFailOrRetryDoesNotPersistRawException:
    """Regression test for PII-2 + PII-3 — verifies _fail_or_retry
    persists the structured summary, not raw str(exc).

    This is the most critical leak vector because the data lands in DB
    columns that survive across sessions and get exposed via
    `ProcessingJobSerializer.last_error` + `ReviewDocumentSerializer.failure_reason`.
    """

    def test_processing_job_last_error_is_structured(self) -> None:
        from web.api import models
        from web.api.review_processing import _fail_or_retry

        # Synthesize a workspace + processing job
        workspace = models.ReviewWorkspace.objects.create(
            label="pii-guard-test",
            data_origin=models.ReviewWorkspace.DataOrigin.SYNTHETIC,
        )
        job = models.ProcessingJob.objects.create(
            workspace=workspace,
            job_type=models.ProcessingJob.JobType.PROCESS_DOCUMENT,
            status=models.ProcessingJob.Status.PROCESSING,
            attempts=3,
            max_attempts=3,  # force FAILED branch
        )

        exc = BedrockNonJsonError("Failed Bedrock response for Jane Smith, DOB 1980-04-15")
        _fail_or_retry(job, exc)
        job.refresh_from_db()

        # Structured summary, not raw exception message
        assert job.last_error == "BedrockNonJsonError:bedrock_non_json"
        assert "Jane" not in job.last_error
        assert "1980" not in job.last_error
        assert job.metadata["failure_code"] == "bedrock_non_json"
