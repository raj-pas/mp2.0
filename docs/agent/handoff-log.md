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

## 2026-04-28 — Canon v2.3 Review and Memory Sync

- Reviewed `MP2.0_Working_Canon.md` v2.3, `CLAUDE.md`, `docs/agent/*`, README,
  engine, web, frontend, extraction, integration, Docker, CI, and persona files.
- Synced agent memory to the Day-2 lock-ins: Phase A/B/C delivery, goal-account
  optimization unit, 5-point risk mapping, three-tab advisor view, tax-drag
  schema, CMA admin boundary, real-PII blockers, pilot gates, and override
  patterns.
- Recorded key scaffold drift for future sessions: engine still returns
  goal-level Phase 1 output, extraction is stubbed, auth/RBAC is Phase 0, PII
  controls are incomplete, audit is light, and the UI lacks the three-tab /
  click-through recommendation workflow.

## 2026-04-28 — Secure-Local Review Tranche Implemented

- Added secure-root validation for `MP20_SECURE_DATA_ROOT`; upload/review hard
  fails if the root is missing or inside the repository.
- Added local advisor bootstrap, review workspace/document/job/fact/state/
  approval models, migration, serializers, APIs, and tests.
- Added Postgres-backed worker command `process_review_queue` with transactional
  claim, retry policy, local parsers, Bedrock fail-closed routing, structured
  fact storage, and reviewed-state reconciliation.
- Added sensitive identifier hash/redacted-display handling and minimally
  redacted evidence quotes.
- Added React review workflow: login, workspace creation, upload/status, active
  jobs, facts, quick-fill edits, section approvals, readiness, retry, matches,
  and link-or-create commit.
- Updated Docker Compose with a `worker` service sharing Postgres and the secure
  data-root mount.
- Updated README, `.env.example`, `CLAUDE.md`, and agent memory for the new
  secure-local workflow and safety rules.
- Verification passed: `uv run ruff check .`, `uv run pytest`, `npm run build`.
