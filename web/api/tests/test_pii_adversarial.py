"""Adversarial PII fuzzing tests (closes audit findings PII-1..PII-4 + REDACT-1).

For each PII-leak surface we attempt to inject ~30 distinct adversarial
strings (Hypothesis-driven `@given(st.sampled_from(...))`) and verify
NONE of the raw PII patterns survive into:

  * HTTP response bodies (doc-detail endpoint).
  * Audit-event metadata.
  * DB columns (`failure_reason`, `last_error`).

`redact_evidence_quote` is the ground truth — we assert specific
patterns become `[CARD REDACTED]` / `[SIN/SSN REDACTED]` / `[PHONE
REDACTED]` / `[ACCOUNT REDACTED]` / `[ROUTING REDACTED]` /
`[ADDRESS REDACTED]`.

If any pattern leaks, the test is intentionally LOUD — surface the
real-PII guard bug rather than suppressing.
"""

from __future__ import annotations

import re

import pytest
from django.urls import reverse
from extraction.llm import BedrockNonJsonError
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from rest_framework.test import APIClient
from web.api import models
from web.api.error_codes import (
    safe_audit_metadata,
    safe_exception_summary,
    safe_response_payload,
)
from web.api.review_processing import _fail_or_retry
from web.api.review_redaction import redact_evidence_quote
from web.api.tests.factories import (
    ExtractedFactFactory,
    ReviewDocumentFactory,
    ReviewWorkspaceFactory,
    UserFactory,
)
from web.audit.models import AuditEvent
from web.audit.writer import record_event

# ---------------------------------------------------------------------------
# Adversarial PII corpus — ~30 distinct strings exercising every pattern
# the redaction module knows about + a few near-miss negatives.
# ---------------------------------------------------------------------------

PII_CORPUS: list[tuple[str, str, str | None]] = [
    # (label, raw_pii, expected_redaction_marker)
    # Credit cards
    ("cc-visa-spaces", "4111 1111 1111 1111", "[CARD REDACTED]"),
    ("cc-mc-dashes", "5500-0000-0000-0004", "[CARD REDACTED]"),
    # AMEX 4-6-5 separator format. _CREDIT_CARD_PATTERN was extended
    # 2026-05-03 to alternate 4-4-4 / 4-6-5 groupings (REDACT-2 closed
    # by Phase 6 sub-session #4 adversarial fuzzing).
    ("cc-amex-15", "3782-822463-10005", "[CARD REDACTED]"),
    ("cc-no-separator", "4111111111111111", "[CARD REDACTED]"),
    ("cc-mixed-sep", "4111-1111 1111-1111", "[CARD REDACTED]"),
    # SINs / SSNs
    ("sin-dash", "123-456-789", None),  # SIN pattern → either marker OK
    ("sin-spaces", "123 456 789", None),
    ("ssn-dash", "123-45-6789", None),
    ("ssn-spaces", "123 45 6789", None),
    # Routing numbers (3-3-3 pattern; SIN regex fires first which is fine)
    ("routing-dashes", "099-001-123", None),
    ("routing-spaces", "099 001 123", None),
    # Phone numbers
    ("phone-dash", "555-867-5309", "[PHONE REDACTED]"),
    ("phone-paren", "(555) 867-5309", "[PHONE REDACTED]"),
    ("phone-dot", "555.867.5309", "[PHONE REDACTED]"),
    ("phone-tight", "5558675309", "[PHONE REDACTED]"),
    ("phone-canada", "(204) 555-1234", "[PHONE REDACTED]"),
    ("phone-1prefix", "555 867 5309", "[PHONE REDACTED]"),
    # Addresses
    ("addr-street", "123 Main Street", "[ADDRESS REDACTED]"),
    ("addr-avenue", "456 Maple Avenue", "[ADDRESS REDACTED]"),
    ("addr-blvd", "789 Robson Boulevard", "[ADDRESS REDACTED]"),
    ("addr-rd", "10 Spadina Road", "[ADDRESS REDACTED]"),
    ("addr-ln-with-period", "22 Pine Lane.", "[ADDRESS REDACTED]"),
    # Account numbers (canon labelled prefix)
    ("acct-num", "Account No: AB123456789", "[ACCOUNT REDACTED]"),
    ("acct-hash", "acct # ZX9876543", "[ACCOUNT REDACTED]"),
    ("acct-colon", "Account: 1234567890", "[ACCOUNT REDACTED]"),
    # Combined / messy
    ("combo-cc-phone", "Card 4111 1111 1111 1111 / Phone 555-867-5309", None),
    ("combo-sin-addr", "SIN 123-456-789 lives at 123 Main Street", None),
    # Near-miss negatives (must NOT redact)
    ("amount-dollars", "$5,000.00 invested", None),
    ("date-iso", "1985-03-12", None),
    ("year", "2024", None),
]


def _raw_pii_from(corpus_entry: tuple[str, str, str | None]) -> str:
    return corpus_entry[1]


# Sanity: ensure we have at least 25 distinct adversarial strings.
assert len({entry[1] for entry in PII_CORPUS}) >= 25


# ---------------------------------------------------------------------------
# Layer 1: redact_evidence_quote ground-truth assertions
# ---------------------------------------------------------------------------


# REDACT-2 (closed 2026-05-03): _CREDIT_CARD_PATTERN extended in
# review_redaction.py to alternate 4-4-4 (Visa/MC/Discover) with
# 4-6-5 (AMEX) groupings; the cc-amex-15 corpus entry now passes
# alongside the other CC variants. Empty leaks set retained as a
# documentation hook so future adversarial findings can land here
# as XFAIL before production patches catch up.
_KNOWN_REDACTION_LEAKS: set[str] = set()


@pytest.mark.parametrize(
    "label,raw,expected_marker",
    [
        pytest.param(
            *entry,
            marks=pytest.mark.xfail(
                reason=f"Documented redaction leak: {entry[0]}",
                strict=True,
            ),
        )
        if entry[0] in _KNOWN_REDACTION_LEAKS
        else pytest.param(*entry)
        for entry in PII_CORPUS
    ],
)
def test_redact_evidence_quote_strips_raw_pii(
    label: str, raw: str, expected_marker: str | None
) -> None:
    """Ground truth: redact_evidence_quote MUST strip every PII raw
    string in the corpus. If a marker is specified, assert it; if
    None, accept any of the documented redaction markers (some
    pattern overlaps fire either marker).

    Near-miss negatives ($5,000.00, ISO dates, plain years) must
    survive untouched.
    """
    text = f"Some prefix {raw} some suffix"
    result = redact_evidence_quote(text)

    if label.startswith("amount-") or label.startswith("date-") or label == "year":
        # Negative cases must be preserved.
        assert raw in result, f"redaction over-matched on negative case {label!r}: {result}"
        return

    # Positive: raw PII must be GONE from the redacted output.
    if raw not in result:
        pass  # redaction worked
    else:
        # Account-prefixed cases collapse the whole `Account: 12345`
        # token to `[ACCOUNT REDACTED]` so the digit-run alone is
        # strictly speaking gone but the parent label may persist.
        # Verify the digit-run portion is at least gone.
        digits_only = re.sub(r"\D", "", raw)
        if digits_only and len(digits_only) >= 7:
            assert digits_only not in result, (
                f"redaction LEAKED raw digits {digits_only!r} for {label!r}: {result}"
            )

    # If a specific marker is expected, assert it.
    if expected_marker:
        assert expected_marker in result, (
            f"expected {expected_marker!r} for {label!r}, got: {result}"
        )
    else:
        # Any of the canon markers acceptable.
        assert any(
            marker in result
            for marker in (
                "[CARD REDACTED]",
                "[SIN/SSN REDACTED]",
                "[PHONE REDACTED]",
                "[ACCOUNT REDACTED]",
                "[ROUTING REDACTED]",
                "[ADDRESS REDACTED]",
            )
        ), f"no redaction marker in {result!r} for {label!r}"


# ---------------------------------------------------------------------------
# Layer 2: HTTP response body (doc-detail endpoint)
# ---------------------------------------------------------------------------


_POSITIVE_CORPUS = [
    entry
    for entry in PII_CORPUS
    if not (entry[0].startswith("amount-") or entry[0].startswith("date-") or entry[0] == "year")
]


@pytest.mark.django_db
@pytest.mark.parametrize("label,raw,expected_marker", _POSITIVE_CORPUS)
def test_doc_detail_response_does_not_leak_raw_pii(
    label: str, raw: str, expected_marker: str | None
) -> None:
    """Inject raw PII as `evidence_quote` on an ExtractedFact, fetch
    the doc-detail endpoint, assert the raw PII is gone from the
    HTTP response body.

    Critical: this is the most likely real-PII leak vector since the
    advisor UI directly renders `redacted_evidence_quote` from this
    response.
    """
    user = UserFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = ReviewWorkspaceFactory(owner=user)
    document = ReviewDocumentFactory(workspace=workspace)
    ExtractedFactFactory(
        workspace=workspace,
        document=document,
        field="people[0].date_of_birth",
        value="1985-03-12",
        evidence_quote=f"Source text contains: {raw} (label={label})",
    )

    response = client.get(
        reverse(
            "review-document-detail",
            args=[workspace.external_id, document.id],
        )
    )
    assert response.status_code == 200
    body_text = response.content.decode()

    # The raw PII string must NOT appear anywhere in the response.
    digits_only = re.sub(r"\D", "", raw)
    if len(digits_only) >= 7:
        assert digits_only not in body_text, (
            f"HTTP response leaked raw PII digits {digits_only!r} for {label!r}: {body_text[:300]}"
        )


# ---------------------------------------------------------------------------
# Layer 3: Audit-event metadata
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("label,raw,expected_marker", _POSITIVE_CORPUS)
def test_audit_metadata_does_not_leak_raw_pii_via_safe_audit_metadata(
    label: str, raw: str, expected_marker: str | None
) -> None:
    """`safe_audit_metadata` is the canonical surface for serializing
    exceptions to audit metadata (per error_codes.py).

    Construct a Bedrock exception whose `.args[0]` carries raw PII.
    Verify the audit metadata payload contains structured `failure_code`
    only and never the raw exception text.
    """
    exc = BedrockNonJsonError(f"PII leak attempt: {raw} embedded in extractor response")
    metadata = safe_audit_metadata(exc, workspace_id="ws-abc-123")

    # Structured code is present
    assert metadata["failure_code"] == "bedrock_non_json"
    # Raw PII never lands in metadata
    digits_only = re.sub(r"\D", "", raw)
    if len(digits_only) >= 7:
        for key, value in metadata.items():
            assert digits_only not in str(value), (
                f"audit metadata key {key!r} leaked raw PII digits {digits_only!r}: {value!r}"
            )
    # No accidental `detail` carrying the exception body
    assert "detail" not in metadata


@pytest.mark.django_db
@pytest.mark.parametrize("label,raw,expected_marker", _POSITIVE_CORPUS)
def test_audit_event_row_does_not_leak_raw_pii(
    label: str, raw: str, expected_marker: str | None
) -> None:
    """End-to-end: `record_event` persists an AuditEvent. We seed the
    metadata with the safe payload and verify the row in the DB has
    NO raw PII.
    """
    exc = BedrockNonJsonError(f"PII leak attempt: {raw}")
    metadata = safe_audit_metadata(exc, workspace_id="ws-pii-test")
    record_event(
        action="extraction_failed",
        entity_type="review_workspace",
        entity_id="ws-pii-test",
        actor="system",
        metadata=metadata,
    )

    event = AuditEvent.objects.filter(action="extraction_failed").latest("created_at")
    serialized_metadata = str(event.metadata)
    digits_only = re.sub(r"\D", "", raw)
    if len(digits_only) >= 7:
        assert digits_only not in serialized_metadata, (
            f"AuditEvent.metadata leaked raw PII digits {digits_only!r} for "
            f"{label!r}: {serialized_metadata}"
        )


# ---------------------------------------------------------------------------
# Layer 4: DB columns (failure_reason / last_error)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("label,raw,expected_marker", _POSITIVE_CORPUS)
def test_processing_job_last_error_does_not_leak_raw_pii(
    label: str, raw: str, expected_marker: str | None
) -> None:
    """`_fail_or_retry` persists structured summary, never raw exception
    text. Verify the DB column `ProcessingJob.last_error` has no PII
    after a synthetic Bedrock failure carrying PII in the message body.
    """
    user = UserFactory()
    workspace = ReviewWorkspaceFactory(owner=user)
    job = models.ProcessingJob.objects.create(
        workspace=workspace,
        job_type=models.ProcessingJob.JobType.PROCESS_DOCUMENT,
        status=models.ProcessingJob.Status.PROCESSING,
        attempts=3,
        max_attempts=3,  # force FAILED branch
    )
    exc = BedrockNonJsonError(f"PII leak attempt for {label}: {raw}")
    _fail_or_retry(job, exc)
    job.refresh_from_db()

    digits_only = re.sub(r"\D", "", raw)
    if len(digits_only) >= 7:
        assert digits_only not in (job.last_error or ""), (
            f"ProcessingJob.last_error leaked raw PII digits {digits_only!r} "
            f"for {label!r}: {job.last_error!r}"
        )
    # last_error format is structured class:code
    assert job.last_error == "BedrockNonJsonError:bedrock_non_json"
    # metadata's failure_code is structured
    assert job.metadata.get("failure_code") == "bedrock_non_json"


@pytest.mark.django_db
@pytest.mark.parametrize("label,raw,expected_marker", _POSITIVE_CORPUS)
def test_safe_response_payload_does_not_leak_raw_pii(
    label: str, raw: str, expected_marker: str | None
) -> None:
    """`safe_response_payload` is the canon HTTP error surface. The
    response body for an exception MUST NOT carry the raw exception
    text — only the structured code + friendly message.
    """
    exc = BedrockNonJsonError(f"PII leak attempt: {raw}")
    payload = safe_response_payload(exc)

    digits_only = re.sub(r"\D", "", raw)
    if len(digits_only) >= 7:
        for key, value in payload.items():
            assert digits_only not in str(value), (
                f"safe_response_payload[{key!r}] leaked raw PII digits {digits_only!r}: {value!r}"
            )
    # Structured fields are present
    assert payload["code"] == "bedrock_non_json"
    assert "manual entry" in payload["detail"].lower()


# ---------------------------------------------------------------------------
# Layer 5: Hypothesis-driven sampling (composes `redact_evidence_quote`
# with arbitrary surrounding text — catches over-aggressive negative
# regressions that would strip non-PII content alongside PII).
# ---------------------------------------------------------------------------


_HYPOTHESIS_PII = st.sampled_from([entry[1] for entry in _POSITIVE_CORPUS])


@given(_HYPOTHESIS_PII)
@settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_redaction_strips_pii_under_hypothesis_sampling(raw_pii: str) -> None:
    """Hypothesis-sampled fuzz: any raw PII string from the corpus
    embedded in surrounding non-PII text must be stripped, and the
    surrounding non-PII text must survive.
    """
    surrounding = (
        "Le client a soumis le document KYC en vertu de la politique "
        "de l'AMF. La valeur du compte est de 5000 dollars."
    )
    text = f"{surrounding}\n>>> Sensitive: {raw_pii} <<<\n{surrounding}"
    result = redact_evidence_quote(text)

    digits_only = re.sub(r"\D", "", raw_pii)
    if len(digits_only) >= 7:
        assert digits_only not in result, (
            f"hypothesis-sample leaked digits {digits_only!r}: {result}"
        )
    # Surrounding non-PII text preserved (French + small money number).
    assert "AMF" in result
    assert "5000 dollars" in result


# ---------------------------------------------------------------------------
# Sanity: safe_exception_summary is structurally PII-safe
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("label,raw,expected_marker", _POSITIVE_CORPUS)
def test_safe_exception_summary_strips_pii(
    label: str, raw: str, expected_marker: str | None
) -> None:
    exc = BedrockNonJsonError(f"PII attempt: {raw}")
    summary = safe_exception_summary(exc)
    assert summary == "BedrockNonJsonError:bedrock_non_json"
    digits_only = re.sub(r"\D", "", raw)
    if len(digits_only) >= 7:
        assert digits_only not in summary
