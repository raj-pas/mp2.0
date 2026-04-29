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
    "rest_framework",
    "web.audit",
    "web.api",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
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
}
