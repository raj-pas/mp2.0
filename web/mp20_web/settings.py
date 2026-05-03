"""Settings for the Phase 1 MP2.0 scaffold."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BASE_DIR

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "mp20-local-dev-only")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [
    host for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "csp",  # CSP middleware (locked decision #22c).
    "rest_framework",
    "drf_spectacular",  # OpenAPI schema (locked decision #24b).
    "web.audit",
    "web.api",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    # Request ID first so every later middleware + view can correlate
    # log lines via thread-local state (Phase 6.9 — sub-session #5).
    "web.mp20_web.request_id.RequestIDMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # CSP middleware applies after security (locked decision #22c).
    "csp.middleware.CSPMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "web.mp20_web.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "web.mp20_web.wsgi.application"


def _database_from_url(database_url: str) -> dict:
    parsed = urlparse(database_url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ImproperlyConfigured("DATABASE_URL must use postgres:// or postgresql://")
    if not parsed.path.lstrip("/"):
        raise ImproperlyConfigured("DATABASE_URL must include a database name.")

    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": parsed.username or "",
        "PASSWORD": parsed.password or "",
        "HOST": parsed.hostname or "",
        "PORT": parsed.port or "",
    }


if not (database_url := os.getenv("DATABASE_URL")):
    raise ImproperlyConfigured("DATABASE_URL is required and must point to PostgreSQL.")
DATABASES = {"default": _database_from_url(database_url)}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Winnipeg"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MP20_SECURE_DATA_ROOT = os.getenv("MP20_SECURE_DATA_ROOT", "")
MP20_ENGINE_ENABLED = os.getenv("MP20_ENGINE_ENABLED", "1") == "1"
MP20_REVIEW_TEAM_SLUG = os.getenv("MP20_REVIEW_TEAM_SLUG", "steadyhand")
MP20_WORKER_NAME = os.getenv("MP20_WORKER_NAME", "local-worker")
MP20_WORKER_STALE_SECONDS = int(os.getenv("MP20_WORKER_STALE_SECONDS", "60"))
MP20_OCR_MAX_PAGES = int(os.getenv("MP20_OCR_MAX_PAGES", "12"))
MP20_TEXT_EXTRACTION_MAX_CHARS = int(os.getenv("MP20_TEXT_EXTRACTION_MAX_CHARS", "24000"))
AWS_REGION = os.getenv("AWS_REGION", "ca-central-1")
BEDROCK_MODEL = os.getenv("BEDROCK_MODEL", "global.anthropic.claude-sonnet-4-6")

CORS_ALLOWED_ORIGINS = [
    origin
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if origin
]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["web.permissions.permissions.AllowPhaseOneAccess"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# OpenAPI schema (locked decision #24b).
SPECTACULAR_SETTINGS = {
    "TITLE": "MP2.0 API",
    "DESCRIPTION": (
        "MP2.0 — planning-first model portfolio platform. Per canon §9.4.2 "
        "engine purity, financial numbers come from `engine/` only; AI "
        "extracts and styles, never invents."
    ),
    "VERSION": "0.2.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    # Tag groupings used by the new R1 preview endpoints.
    "TAGS": [
        {"name": "auth", "description": "Session + login + logout."},
        {"name": "clients", "description": "Household list + detail."},
        {"name": "portfolio", "description": "PortfolioRun + lifecycle events."},
        {"name": "preview", "description": "Read-only engine previews (no commits)."},
        {"name": "cma", "description": "Capital Market Assumptions (analyst-only)."},
        {"name": "review", "description": "Doc-drop + conflict resolution."},
        {"name": "snapshots", "description": "Append-only HouseholdSnapshot lifecycle."},
    ],
}

# Security headers (locked decision #22c). Self-hosted fonts (locked
# decision #22d) drop third-party font-src; CSP can stay tight.
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_BROWSER_XSS_FILTER = True

# CSP via django-csp 4.x dict format. ``strict-dynamic`` for scripts via
# nonce; self-only for everything else. Vite dev (port 5173) needs
# websocket for HMR — allowed only in dev (not in production deploys).
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ["'self'"],
        "script-src": ["'self'", "'strict-dynamic'"],
        # Tailwind + shadcn inject style elements at runtime; allow inline.
        "style-src": ["'self'", "'unsafe-inline'"],
        "font-src": ["'self'", "data:"],
        "img-src": ["'self'", "data:", "blob:"],
        "connect-src": [
            "'self'",
            *CORS_ALLOWED_ORIGINS,
            "ws://localhost:5173",  # Vite HMR.
        ],
        "frame-ancestors": ["'none'"],
        "object-src": ["'none'"],
        "base-uri": ["'self'"],
        "form-action": ["'self'"],
    },
    "INCLUDE_NONCE_IN": ["script-src"],
}

# OpenTelemetry instrumentation (locked decision #31b, canon §9.1).
# Disabled by default in dev to avoid OTLP-not-running noise; production
# AWS turns OTEL_SDK_DISABLED=false and points OTEL_EXPORTER_OTLP_ENDPOINT
# at Elastic APM. Instrumentation is wired in web/mp20_web/otel.py.
MP20_OTEL_ENABLED = os.getenv("MP20_OTEL_ENABLED", "0") == "1"

# Phase 6.9 (sub-session #5): JSON logging to stdout. Docker logs +
# journalctl + (post-pilot) CloudWatch / Elastic can parse fields
# without regex. Uses python-json-logger; Mp20JsonFormatter injects
# the per-request UUID from RequestIDMiddleware.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "web.mp20_web.json_logging.Mp20JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "stdout_json": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["stdout_json"],
            "level": os.getenv("MP20_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "django.request": {
            "handlers": ["stdout_json"],
            "level": "WARNING",
            "propagate": False,
        },
        "web": {
            "handlers": ["stdout_json"],
            "level": os.getenv("MP20_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "extraction": {
            "handlers": ["stdout_json"],
            "level": os.getenv("MP20_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "engine": {
            "handlers": ["stdout_json"],
            "level": os.getenv("MP20_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
    },
}
