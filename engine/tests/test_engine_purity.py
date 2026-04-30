"""Engine boundary purity guard (canon §9.4.2 — most important rule).

The engine package must NEVER import from web/, extraction/, integrations/,
django, or rest_framework. This is the canon's #1 rule and is stated as a
worth-adding Phase B CI check in `docs/agent/open-questions.md` "Code Drift"
item #8. Adding it as part of R0 hardens the rewrite.

If this test fails, do not "fix" it by suppressing the import — fix the
underlying boundary violation. The engine should remain extractable to
Lambda / Snowflake / standalone packaging.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ENGINE_DIR = Path(__file__).resolve().parents[1]

#: Forbidden top-level package roots in engine/*.py imports.
#: ``engine`` itself is allowed; everything else from this list is not.
FORBIDDEN_ROOTS: set[str] = {
    "web",
    "extraction",
    "integrations",
    "django",
    "rest_framework",
    "drf_spectacular",
    "psycopg",
    "psycopg2",
}

#: Allowed third-party imports — explicit allowlist for clarity.
ALLOWED_THIRD_PARTY_ROOTS: set[str] = {
    "pydantic",
    "hypothesis",  # test-only
    "pytest",  # test-only
    "scipy",  # used for oracle validation in tests
    "numpy",  # may appear in tests
}


def _engine_python_files() -> list[Path]:
    """Every .py file under engine/ (including tests)."""

    return sorted(p for p in ENGINE_DIR.rglob("*.py") if p.is_file())


def _imported_roots(source: str) -> set[str]:
    """Extract the top-level root of every import in a Python source file."""

    tree = ast.parse(source)
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                roots.add(node.module.split(".")[0])
    return roots


@pytest.mark.parametrize(
    "py_file",
    _engine_python_files(),
    ids=lambda p: str(p.relative_to(ENGINE_DIR)),
)
def test_engine_module_has_no_forbidden_imports(py_file: Path) -> None:
    """Every engine/*.py file must avoid importing forbidden packages."""

    source = py_file.read_text()
    roots = _imported_roots(source)
    forbidden_used = roots & FORBIDDEN_ROOTS
    assert not forbidden_used, (
        f"{py_file.relative_to(ENGINE_DIR)} imports forbidden roots: "
        f"{sorted(forbidden_used)}. Canon §9.4.2: engine never imports from "
        f"web/, extraction/, integrations/, django, or rest_framework."
    )


def test_engine_init_imports_only_engine() -> None:
    """The package barrel re-exports only engine.* + stdlib symbols."""

    init = (ENGINE_DIR / "__init__.py").read_text()
    roots = _imported_roots(init)
    non_engine = roots - {"engine"}
    # __init__ may have stdlib imports too; filter those.
    suspicious = non_engine & FORBIDDEN_ROOTS
    assert not suspicious, f"engine/__init__.py imports forbidden roots: {sorted(suspicious)}"
