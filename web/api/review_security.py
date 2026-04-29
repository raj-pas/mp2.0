from __future__ import annotations

import hashlib
import os
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import connection


def secure_data_root() -> Path:
    configured = getattr(settings, "MP20_SECURE_DATA_ROOT", "") or ""
    if not configured:
        raise ImproperlyConfigured(
            "MP20_SECURE_DATA_ROOT must be set to an outside-repo directory before "
            "real document upload is enabled."
        )

    root = Path(configured).expanduser().resolve()
    repo_root = Path(settings.REPO_ROOT).resolve()
    if root == repo_root or repo_root in root.parents:
        raise ImproperlyConfigured(
            "MP20_SECURE_DATA_ROOT must live outside the repository for real client files."
        )

    root.mkdir(parents=True, exist_ok=True)
    return root


def assert_real_upload_backend_ready() -> None:
    secure_data_root()
    if (
        getattr(settings, "MP20_REQUIRE_POSTGRES_FOR_REAL_UPLOADS", True)
        and connection.vendor != "postgresql"
    ):
        raise ImproperlyConfigured(
            "Real document upload requires PostgreSQL so queue claiming, retries, and audit "
            "immutability use the production-like path."
        )


def workspace_storage_dir(workspace_external_id: str) -> Path:
    workspace_dir = secure_data_root() / "review-workspaces" / str(workspace_external_id)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    return workspace_dir


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def write_uploaded_file(*, workspace_external_id: str, filename: str, content: bytes) -> Path:
    suffix = Path(filename).suffix.lower()
    digest = sha256_bytes(content)
    safe_name = f"{digest}{suffix}"
    target = workspace_storage_dir(workspace_external_id) / safe_name
    if not target.exists():
        target.write_bytes(content)
        os.chmod(target, 0o600)
    return target


def relative_secure_path(path: Path) -> str:
    return str(path.resolve().relative_to(secure_data_root()))
