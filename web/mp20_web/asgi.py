"""ASGI config for MP2.0."""

from __future__ import annotations

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.mp20_web.settings")

# OpenTelemetry instrumentation (locked decision #31b). No-op unless
# MP20_OTEL_ENABLED=1.
from web.mp20_web.otel import configure_opentelemetry  # noqa: E402

configure_opentelemetry()

from django.core.asgi import get_asgi_application  # noqa: E402

application = get_asgi_application()
