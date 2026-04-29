from __future__ import annotations

import os
import subprocess
import sys


def test_settings_fail_loudly_without_database_url() -> None:
    env = os.environ.copy()
    env.pop("DATABASE_URL", None)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import web.mp20_web.settings",
        ],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "DATABASE_URL is required" in result.stderr


def test_settings_reject_non_postgres_database_url() -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = "sqlite:///db.sqlite3"

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import web.mp20_web.settings",
        ],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "DATABASE_URL must use postgres:// or postgresql://" in result.stderr
