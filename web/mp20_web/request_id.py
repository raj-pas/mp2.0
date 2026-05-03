"""Per-request UUID middleware (Phase 6.9 — sub-session #5).

Adds an `X-Request-ID` header on every response + binds the same
UUID to a thread-local `request_id` field that the JSON logging
formatter picks up. Lets ops correlate log lines that all came
from the same advisor request without hitting the audit-log
heavyweight path.

Honors a client-supplied `X-Request-ID` header if one is present
(e.g., the React frontend can attach a UUID before submitting a
mutation so the request-trace spans the network boundary).
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

# Thread-local stash. The JSON formatter (web/mp20_web/json_logging.py)
# reads this on every emit so log records carry the request_id even
# when the logger is invoked from deep inside view code that doesn't
# have the request object handy.
_local = threading.local()


def get_request_id() -> str | None:
    return getattr(_local, "request_id", None)


def _set_request_id(value: str | None) -> None:
    if value is None:
        if hasattr(_local, "request_id"):
            delattr(_local, "request_id")
    else:
        _local.request_id = value


class RequestIDMiddleware:
    """Bind a UUID to every request + echo it on the response."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Trust client-supplied UUID-shaped header; otherwise mint one.
        client_id = request.headers.get("X-Request-ID", "").strip()
        if _looks_like_uuid(client_id):
            request_id = client_id
        else:
            request_id = uuid.uuid4().hex
        _set_request_id(request_id)
        try:
            response = self.get_response(request)
        finally:
            _set_request_id(None)
        response["X-Request-ID"] = request_id
        return response


def _looks_like_uuid(value: str) -> bool:
    if len(value) not in {32, 36}:
        return False
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True
