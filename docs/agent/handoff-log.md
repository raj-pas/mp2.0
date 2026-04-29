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

## 2026-04-28 — Browser E2E Review Flow Verified

- Ran a complete Chrome-headless browser E2E using synthetic upload content and
  AWS/Bedrock credentials loaded from `ike-agent/.env` without printing secrets.
- Flow covered: local login, review workspace creation, browser upload, worker
  processing, Bedrock extraction, visible extracted facts, `engine_ready`,
  section approval, match step, create-household commit, and client detail.
- Final E2E evidence showed committed workspace
  `review_58042dfd-b4a7-456f-a384-85f35c147c6e` with one account and one goal;
  screenshot saved at `/tmp/mp20-e2e-final.png`.
- E2E uncovered and fixed: session endpoint not reporting authenticated sessions,
  strict Bedrock JSON parsing, inability to reconcile indexed fact paths like
  `accounts[0].current_value`, and scalar sensitive identifier values not being
  hashed/redacted.
- Verification after fixes passed: `uv run ruff check .`, `uv run ruff format
  --check .`, `uv run pytest`, and `npm run build`.

## 2026-04-28 — Client/Auth Boundary Hardened

- Tightened the default DRF permission hook from allow-all to authenticated-by-
  default. Login/session remain explicit public endpoints.
- Added explicit login requirements for client list, client detail, and
  generate-portfolio APIs.
- Added nullable `Household.owner`; shared synthetic households can remain
  ownerless, while reviewed-state commits create advisor-owned households.
- Scoped client list/detail/generate access to shared synthetic plus the
  authenticated advisor's households; commit link targets must be owned by the
  current advisor.
- Updated the frontend so client queries and visible client data are gated by
  session auth.
- Added regression tests for unauthenticated denial, household visibility
  scoping, owner-scoped commits, and cross-advisor link rejection.
- Verification passed: `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run pytest`, `npm run build`, and a Chrome-headless UI check confirming
  no client data before login and visible client/review UI after login.

## 2026-04-29 — Review Self-Link Candidate Fixed

- Fixed a committed-workspace UX/API regression where the already-linked
  household could appear as a link candidate through backend matching or the
  frontend fallback matcher.
- Backend matching now returns no candidates for linked/committed workspaces,
  commit clears stale match candidates, repeated commit is idempotent for the
  linked household, and relinking a committed workspace to another household is
  rejected.
- Frontend link/create controls are hidden once the workspace is linked, and
  fallback matches exclude the linked household.
- Added regression tests for match scoring, self-link suppression, idempotent
  commit, and relink rejection.
- Verification passed: `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run pytest`, and `npm run build`.

## 2026-04-29 — Docker Compose Worker Real-Bundle Run

- Stopped the old local Django/Vite processes and created a gitignored `.env`
  for Docker Compose using ike-agent AWS credentials without printing secrets.
- Set the secure data root to `/private/tmp/mp20-secure-data`, matching the
  previously uploaded files, and started the full Compose stack.
- Transferred the queued review workspace metadata from the prior local SQLite
  run into Compose Postgres via the secure data root so the worker could process
  the already-uploaded bundle.
- Read the Compose log stream through worker processing. The worker stored
  structured facts for the successfully extracted documents; some documents
  failed after retries because Bedrock output did not parse as valid JSON.
- Fixed reconciliation for qualitative risk facts such as `Low`, which had been
  crashing state reconciliation when coerced directly to `int`.
- Final Compose state for that bundle: workspace is `review_ready`; successful
  documents reconciled and failed documents remain visible for retry/manual
  handling; `engine_ready` remains blocked by missing account values/holdings
  marker, goal horizon, and advisor-confirmed goal-account mapping.
- Verification passed: `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run pytest`, and `npm run build`.

## 2026-04-29 — Secure Ingest Hardening + Advisor Review Implemented

- Hardened real-upload safety: real-derived upload now requires an outside-repo
  `MP20_SECURE_DATA_ROOT` and Postgres by default; synthetic upload remains
  testable on SQLite.
- Added advisor team access semantics plus financial-analyst PII denial.
- Added immutable audit protections with model guards and DB triggers, sanitized
  workspace timeline serialization, edit audit hashes, and kill-switch audit
  events.
- Added worker heartbeat/stale-job visibility, retry/failure metadata, duplicate
  reconcile suppression, manual reconcile endpoint, typed Bedrock fact schema
  validation, JSON repair, OCR overflow metadata, and artifact disposal/report
  command.
- Replaced Quick Fill with advisor-grade editable review sections for household,
  people, accounts, goals, goal-account mapping, and risk, including provenance
  snippets, override reasons, conflict/unknown hooks, approval statuses/notes,
  and strict `engine_ready + required approvals` commit gating.
- Improved committed client display with defensive financial formatting and
  clearer account/goal/mapping/holdings empty states.
- Added Playwright synthetic E2E config/spec, local real-bundle regression
  scaffold, CI Docker Compose E2E job, and ignored Playwright artifact folders.
- Verification passed: `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run pytest`, `npm run build`, and Playwright test discovery for synthetic
  and real-regression specs.
- Full local synthetic Playwright execution was attempted against Docker Compose
  but could not launch because local Chromium was missing; the browser install
  command hung and was terminated. CI is configured to install Chromium before
  running the synthetic browser E2E.
