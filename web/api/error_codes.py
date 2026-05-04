"""Structured exception → advisor-facing failure code mapping (Phase 2 PII scrub).

Single source of truth for converting Python exceptions into structured
codes that:
  1. Persist safely to DB columns (`ProcessingJob.last_error`,
     `ReviewDocument.failure_reason`) without leaking real-PII text.
  2. Surface in HTTP 4xx/5xx response bodies as `{detail, code}`.
  3. Land in audit-event metadata as `failure_code`, never raw exception
     text.

Per canon §11.8.3 (real-PII discipline) + dossier §10: never `str(exc)`
to a serializer surface, DB column, audit metadata `detail` field, or
HTTP response body. Raw exception text may carry extracted client
content; structured codes are PII-safe.

Closes audit findings PII-1, PII-2, PII-3, PII-4, PII-SER (per
docs/agent/extraction-audit.md).
"""

from __future__ import annotations

# Re-exported lazily to avoid an import-cycle through extraction.llm during
# Django startup. The mapping resolves typed exceptions at call time.


def failure_code_for_exc(exc: Exception) -> str:
    """Map any exception to a stable, advisor-safe failure code.

    BedrockExtractionError subclasses (extraction/llm.py) carry their
    own typed `.failure_code`. Other exception types fall back to the
    class name so we don't lose diagnostic signal — but the goal over
    time is to grow the typed taxonomy so every failure routes through
    a code the UI can render specific copy + recovery affordance for.

    The class-name fallback is structurally PII-safe (just the type)
    even when the message body would leak.
    """
    # Local import to avoid the extraction → web → extraction import cycle.
    from extraction.llm import BedrockExtractionError

    if isinstance(exc, BedrockExtractionError):
        return exc.failure_code
    return exc.__class__.__name__


def safe_exception_summary(exc: Exception) -> str:
    """Return a PII-safe summary of an exception suitable for DB storage.

    Format: ``"<ExceptionClass>:<failure_code>"``.

    Used by `ProcessingJob.last_error` + `ReviewDocument.failure_reason`
    + audit-event `failure_code` slots. NEVER includes the exception
    message body which may contain real-PII extracted from client docs.
    """
    return f"{exc.__class__.__name__}:{failure_code_for_exc(exc)}"


# Friendly advisor copy per failure code. The frontend renders a
# `review.failure_code.<code>` i18n key; this dict is the backend-side
# fallback used when the frontend doesn't have the i18n key wired (e.g.
# fresh deploy + new code) OR when the response goes to a non-i18n
# consumer (curl tests, Linear tickets, audit reports).
_FRIENDLY_MESSAGES: dict[str, str] = {
    # Bedrock extraction failure codes (defined in extraction/llm.py)
    "bedrock_token_limit": (
        "This document is too long for automated extraction. "
        "Mark as manual entry and fill in fields by hand."
    ),
    "bedrock_non_json": (
        "Couldn't extract structured data from this document. Retry once, or mark as manual entry."
    ),
    "bedrock_schema_mismatch": (
        "Extraction returned unexpected data shape. Retry, or escalate to engineering."
    ),
    "bedrock_unknown": (
        "Extraction failed for an unexpected reason. Retry, or escalate to engineering."
    ),
    # Worker-recovery codes
    "WorkerStalled": (
        "Worker stalled mid-job. Auto-recovery will retry; check back in 60 seconds."
    ),
    # Engine→UI display typed exceptions (v0.1.2-engine-display).
    # Frontend renders Banner inline error + Sonner toast on these; the
    # message must be advisor-actionable WITHOUT leaking PII (the original
    # blocker text often interpolates account_id/goal_id).
    "EngineKillSwitchBlocked": (
        "Recommendation generation is temporarily disabled. "
        "Engineering has been notified; check back shortly."
    ),
    "NoActiveCMASnapshot": (
        "An analyst needs to publish the latest CMA before recommendations can be generated."
    ),
    "InvalidCMAUniverse": (
        "The active CMA snapshot has a configuration issue. "
        "Notify a financial analyst to publish a corrected snapshot."
    ),
    "ReviewedStateNotConstructionReady": (
        "This household isn't ready for portfolio generation yet. "
        "Open the household and resolve the outstanding readiness items "
        "(holdings, goal-account allocations, missing sections) before "
        "retrying."
    ),
    "MissingProvenance": (
        "Some facts on this household are missing source provenance. "
        "Re-run extraction on the affected documents, or contact ops."
    ),
    # Generic catch-all for un-mapped exception class names
    "_default": "Something went wrong. Please retry, or contact ops if it persists.",
}


def friendly_message_for_code(code: str) -> str:
    """Return PII-safe, advisor-friendly copy for a failure code.

    Backend-side fallback. Frontend should prefer the
    `review.failure_code.<code>` i18n key for proper localization (if
    fr-CA support lands per locked decision #12).
    """
    return _FRIENDLY_MESSAGES.get(code, _FRIENDLY_MESSAGES["_default"])


def safe_response_payload(exc: Exception, **extra: object) -> dict[str, object]:
    """Return a PII-safe HTTP response body for an exception.

    Replaces the legacy ``Response({"detail": str(exc)}, ...)`` pattern.
    Returns ``{"detail": friendly_message, "code": failure_code, ...extra}``.

    Per Phase 2 PII scrub (2026-05-02): the response body never carries
    raw exception text; structured codes are PII-safe even when the
    exception message body would leak real-PII content extracted from
    client docs.

    Closes audit finding PII-1.
    """
    code = failure_code_for_exc(exc)
    payload: dict[str, object] = {
        "detail": friendly_message_for_code(code),
        "code": code,
    }
    payload.update(extra)
    return payload


def safe_audit_metadata(exc: Exception, **extra: object) -> dict[str, object]:
    """Return a PII-safe audit-event metadata dict for an exception.

    Replaces the legacy ``metadata={"detail": str(exc), ...}`` pattern.
    Returns ``{"failure_code": <code>, ...extra}``.

    Closes audit finding PII-4. Audit events are append-only (locked
    #37 + Postgres triggers); ensuring no raw exception text lands
    here is critical because the audit row is immutable forever.
    """
    payload: dict[str, object] = {
        "failure_code": failure_code_for_exc(exc),
    }
    payload.update(extra)
    return payload
