# MP2.0 Handoff Log

## 2026-04-28 — Phase 1 Scaffold Started

- User approved implementation of the Phase 1 runnable MVP scaffold.
- Chosen defaults: main-direct work, local commits only, repo-file memory,
  Claude-first instructions, Docker Compose first, Python 3.12, Node 22,
  `uv + npm`, Ruff/pytest/frontend build smoke checks.
- Non-blockers remain tracked in `open-questions.md`.

## 2026-04-28 — Phase 1 Scaffold Implemented

- Added root tooling: `pyproject.toml`, `uv.lock`, `.python-version`,
  Dockerfile, Docker Compose, README, `.env.example`, `.gitignore`, and smoke CI.
- Added `CLAUDE.md` plus agent memory docs under `docs/agent/`.
- Added pure `engine/` package with Pydantic schemas, illustrative Steadyhand
  sleeves, optimizer stub, compliance stub, and tests.
- Added Django/DRF backend with DB models, migrations, synthetic persona loader,
  web-to-engine adapter, light audit table/writer, and API tests.
- Added React/Vite/Tailwind advisor shell wired to client list/detail and
  generate-portfolio API calls.
- Added extraction/integration adapter placeholders for future phases.
- Verification passed: Ruff check, Ruff format check, pytest, frontend build,
  Docker Compose config validation, Django check, migrations, and synthetic
  persona load.
- Docker Compose is running after a restart; backend logs show successful 200
  responses for client list, client detail, and generate-portfolio calls.
- `npm install` reported 2 moderate dependency audit findings; no automatic fix
  was applied during scaffold implementation.

## 2026-04-28 — Detail Financial Summary Fix

- Fixed `$NaN` in the advisor shell by adding `goal_count` and `total_assets`
  to the household detail API response, matching the list API shape.
- Added a backend regression test that asserts the Sandra/Mike detail payload
  includes `goal_count = 3` and `total_assets = 1280000`.
- Also moved the Docker backend virtualenv to `/opt/mp20-venv` so local `uv run`
  commands do not break the bind-mounted container runtime.
