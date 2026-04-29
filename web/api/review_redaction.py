from __future__ import annotations

import hashlib
import hmac
import re
from typing import Any

from django.conf import settings

_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_CREDIT_CARD_PATTERN = re.compile(
    r"(?<!\$)(?<!\d)\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{1,7}(?!\d)"
)
_SIN_PATTERN = re.compile(r"(?<!\$)(?<!#)(?<!\d)\b\d{3}[-\s]\d{3}[-\s]\d{3}\b(?!\s*%)(?!\d)")
_SSN_PATTERN = re.compile(r"(?<!\$)(?<!#)(?<!\d)\b\d{3}[-\s]\d{2}[-\s]\d{4}\b(?!\s*%)(?!\d)")
_ACCOUNT_PATTERN = re.compile(
    r"(?i)(?:account|acct)[\s.]*(?:no|number|num|#)?[\s.:]*(?!T\d{4}\b)(?!TP-\d)[A-Z]*[-]?\d{5,}"
)

_REDACTION_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (_CREDIT_CARD_PATTERN, "[CARD REDACTED]"),
    (_SIN_PATTERN, "[SIN/SSN REDACTED]"),
    (_SSN_PATTERN, "[SIN/SSN REDACTED]"),
    (_ACCOUNT_PATTERN, "[ACCOUNT REDACTED]"),
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
