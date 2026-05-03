"""JSON log formatter (Phase 6.9 — sub-session #5).

Emits structured JSON to stdout so Docker logs / journalctl /
CloudWatch can parse fields without regex. Inherits from
`pythonjsonlogger.jsonlogger.JsonFormatter` so all stdlib logging
calls (logger.info, logger.exception, …) flow through transparently.

Each record carries:
  - `time` — ISO-8601 timestamp.
  - `level` — log level name.
  - `logger` — Python logger name (e.g., "django.request").
  - `message` — the formatted log message.
  - `request_id` — the per-request UUID from RequestIDMiddleware
    (None for log lines outside an HTTP request, e.g., management
    commands or worker drains).
  - `module` / `funcName` / `lineno` — call-site context.

PII discipline (canon §11.8.3): NEVER include exception stack text
verbatim — use `safe_exception_summary` from `web/api/error_codes.py`
where exception summaries reach log lines, and structurally redact
any raw advisor input via `web/api/review_redaction.py` BEFORE
calling `logger.info(...)`. The formatter itself doesn't add any
sanitization layer.
"""

from __future__ import annotations

import logging
from typing import Any

# Graceful import: if python-json-logger isn't installed (e.g.,
# the container image was built before the dep was added), fall
# back to stdlib `logging.Formatter` so Django boots cleanly.
# Production deploys must install python-json-logger to get
# JSON-formatted stdout per Phase 6.9 §4.1.
try:
    from pythonjsonlogger.json import JsonFormatter as _BaseJsonFormatter

    _HAS_JSON_LOGGER = True
except ImportError:  # pragma: no cover — covered by deploy boot path
    _BaseJsonFormatter = logging.Formatter  # type: ignore[assignment,misc]
    _HAS_JSON_LOGGER = False


class Mp20JsonFormatter(_BaseJsonFormatter):  # type: ignore[misc,valid-type]
    """Wrap pythonjsonlogger to inject the per-request UUID.

    Falls back to stdlib Formatter when python-json-logger is not
    installed; the resulting log lines are plain-text instead of
    JSON but the Django process still boots.
    """

    def add_fields(  # type: ignore[override]
        self,
        log_record: dict[str, Any],
        record: Any,
        message_dict: dict[str, Any],
    ) -> None:
        if not _HAS_JSON_LOGGER:
            return  # plain-text fallback — nothing to inject
        super().add_fields(log_record, record, message_dict)
        # Lazy import to avoid circular: request_id.py is imported
        # by Django's MIDDLEWARE which itself imports this module
        # only when LOGGING fires.
        from web.mp20_web.request_id import get_request_id

        log_record["time"] = log_record.pop("asctime", None) or record.created
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        rid = get_request_id()
        if rid is not None:
            log_record["request_id"] = rid
