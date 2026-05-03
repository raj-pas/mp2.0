from __future__ import annotations

import hashlib
import hmac
import re
from typing import Any

from django.conf import settings

_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
# REDACT-2 (Phase 6 sub-session #4 — flagged by adversarial fuzzing
# in test_pii_adversarial.py): the prior 4-4-4-1+ pattern only caught
# Visa/MC/Discover (16-digit 4-4-4-4 grouping). AMEX uses a 15-digit
# 4-6-5 grouping (e.g., 3782-822463-10005) which slipped through
# unredacted. Alternation covers both grouping shapes. Order matters
# (longer pattern first) so the 4-4-4-1+ branch doesn't claim part
# of a 4-6-5 number.
_CREDIT_CARD_PATTERN = re.compile(
    r"(?<!\$)(?<!\d)"
    r"(?:"
    r"\d{4}[\s\-]?\d{6}[\s\-]?\d{5}"  # AMEX 4-6-5
    r"|"
    r"\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{1,7}"  # Visa/MC/Discover 4-4-4-1+
    r")"
    r"(?!\d)"
)
_SIN_PATTERN = re.compile(r"(?<!\$)(?<!#)(?<!\d)\b\d{3}[-\s]\d{3}[-\s]\d{3}\b(?!\s*%)(?!\d)")
_SSN_PATTERN = re.compile(r"(?<!\$)(?<!#)(?<!\d)\b\d{3}[-\s]\d{2}[-\s]\d{4}\b(?!\s*%)(?!\d)")
_ACCOUNT_PATTERN = re.compile(
    r"(?i)(?:account|acct)(?:\s*(?:no|number|num))?[\s.:#]+"
    r"(?!T\d{4}\b)(?!TP-\d)(?=[A-Z0-9_-]*\d)[A-Z0-9_-]{5,}"
)
# Phase 2 (2026-05-02) — REDACT-1: extend redaction patterns to cover
# routing numbers (Canadian: 9-digit transit/institution; US: 9-digit
# routing) + phone numbers (NA format) + simple street addresses. These
# previously slipped through evidence-quote redaction.
_ROUTING_PATTERN = re.compile(r"(?<!\$)(?<!\d)\b\d{3}[-\s]?\d{3}[-\s]?\d{3}\b(?!\s*%)(?!\d)")
_PHONE_PATTERN = re.compile(r"(?<!\d)\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b(?!\d)")
# Best-effort street-address: digit run + word + common street suffix.
# Acknowledged limitation: misses PO boxes, rural routes, addresses
# without a numeric prefix. Documented as a known partial in
# docs/agent/extraction-audit.md.
_ADDRESS_PATTERN = re.compile(
    r"\b\d+\s+[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\s+"
    r"(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Way|Place|Pl)\b\.?",
    re.IGNORECASE,
)

_REDACTION_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (_CREDIT_CARD_PATTERN, "[CARD REDACTED]"),
    (_SIN_PATTERN, "[SIN/SSN REDACTED]"),
    (_SSN_PATTERN, "[SIN/SSN REDACTED]"),
    (_ACCOUNT_PATTERN, "[ACCOUNT REDACTED]"),
    # Order matters: routing must run AFTER credit-card / SIN to avoid
    # over-matching their digit runs.
    (_ROUTING_PATTERN, "[ROUTING REDACTED]"),
    (_PHONE_PATTERN, "[PHONE REDACTED]"),
    (_ADDRESS_PATTERN, "[ADDRESS REDACTED]"),
)


def redact_evidence_quote(text: str) -> str:
    redacted = text
    for pattern, replacement in _REDACTION_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def pii_detection_summary(text: str) -> list[dict[str, int | str]]:
    summary: list[dict[str, int | str]] = []
    checks = (
        ("email", _EMAIL_PATTERN),
        ("card", _CREDIT_CARD_PATTERN),
        ("sin_ssn", _SIN_PATTERN),
        ("ssn", _SSN_PATTERN),
        ("account", _ACCOUNT_PATTERN),
    )
    for name, pattern in checks:
        count = len(pattern.findall(text))
        if count:
            summary.append({"type": name, "count": count})
    return summary


def sensitive_identifier_hash(value: str) -> str:
    secret = settings.SECRET_KEY.encode()
    return hmac.new(secret, value.strip().encode(), hashlib.sha256).hexdigest()


def redacted_identifier_display(value: str) -> str:
    cleaned = re.sub(r"\s+", "", value.strip())
    if len(cleaned) <= 4:
        return "****"
    return f"****{cleaned[-4:]}"


def sanitize_sensitive_identifier_values(value: Any) -> Any:
    """Replace sensitive identifier values with hash plus redacted display."""
    if isinstance(value, list):
        return [sanitize_sensitive_identifier_values(item) for item in value]
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            if _is_sensitive_identifier_key(key) and item is not None and item != "":
                raw = str(item)
                sanitized[key] = {
                    "hash": sensitive_identifier_hash(raw),
                    "display": redacted_identifier_display(raw),
                }
            else:
                sanitized[key] = sanitize_sensitive_identifier_values(item)
        return sanitized
    return value


def sanitize_fact_value(field: str, value: Any) -> Any:
    if _is_sensitive_identifier_key(_leaf_field_name(field)) and value is not None and value != "":
        if isinstance(value, (str, int, float)):
            raw = str(value)
            return {
                "hash": sensitive_identifier_hash(raw),
                "display": redacted_identifier_display(raw),
            }
    return sanitize_sensitive_identifier_values(value)


def _is_sensitive_identifier_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_").replace(" ", "_")
    return normalized in {
        "account_number",
        "account_no",
        "acct_number",
        "acct_no",
        "sin",
        "ssn",
        "tax_id",
        "tax_identifier",
        "client_identifier",
        "government_id",
    }


def _leaf_field_name(field: str) -> str:
    return field.rsplit(".", 1)[-1]
