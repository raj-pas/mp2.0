"""WSGI config for MP2.0."""

from __future__ import annotations

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.mp20_web.settings")

# OpenTelemetry instrumentation (locked decision #31b). No-op unless
# MP20_OTEL_ENABLED=1; called before get_wsgi_application so Django gets
# auto-instrumented at import time.
from web.mp20_web.otel import configure_opentelemetry  # noqa: E402

configure_opentelemetry()

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
