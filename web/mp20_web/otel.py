"""OpenTelemetry instrumentation hookup (locked decision #31b, canon §9.1).

Disabled by default in dev. Production sets ``MP20_OTEL_ENABLED=1`` and
``OTEL_EXPORTER_OTLP_ENDPOINT=https://...`` to point at Elastic APM (canon
§9.1). When enabled, Django + psycopg2 traces are emitted via OTLP/HTTP;
trace IDs propagate via the W3C ``traceparent`` header so frontend spans
(see frontend/src/lib/otel.ts when added in R2) reconstruct end-to-end.

Instrumentation respects canon §9.3 logging discipline: span attributes
carry no PII (request bodies, query params with PII not auto-recorded).
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def configure_opentelemetry() -> None:
    """Initialize OTel SDK if MP20_OTEL_ENABLED=1; no-op otherwise."""

    if os.getenv("MP20_OTEL_ENABLED", "0") != "1":
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.django import DjangoInstrumentor
        from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:  # pragma: no cover - dependency present in pyproject.
        logger.warning("opentelemetry packages missing; skipping instrumentation.")
        return

    resource = Resource.create({SERVICE_NAME: os.getenv("OTEL_SERVICE_NAME", "mp20-web")})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter()
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    DjangoInstrumentor().instrument()
    Psycopg2Instrumentor().instrument()
    logger.info("OpenTelemetry tracing enabled.")
