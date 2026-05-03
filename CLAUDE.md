# CLAUDE.md — MP2.0

This file is the primary Claude Code entrypoint for MP2.0 implementation
sessions. The working canon remains authoritative for product, strategy,
regulatory, and architecture intent: `MP2.0_Working_Canon.md`.

## Start Every Session

1. Run `git status --short --branch`.
2. Read `docs/agent/session-state.md`.
3. Check `docs/agent/open-questions.md` for blockers that affect your task.
4. Preserve user or parallel-session changes; do not reset or overwrite them.

## Current Status

The Phase 1 runnable scaffold and first secure-local review workflow are
implemented on `main`:

- Django/DRF + Postgres backend
- Postgres-backed ingestion worker queue
- React/Vite advisor shell
- link-first portfolio engine
- synthetic Sandra/Mike Chen persona
- local advisor and financial analyst login, authenticated client access, and
  review workspace UI
- secure outside-repo browser upload path
- advisor-grade reviewed sections with provenance snippets, conflict/unknown
  handling hooks, edit notes, readiness checklist, matching, and strict
  `engine_ready + construction_ready + required approvals` link-or-create
  commit gating
- worker heartbeat/stale visibility, retry metadata, duplicate reconcile
  suppression, manual reconcile, and provider-safe OCR overflow metadata
- immutable audit logging with sanitized workspace timeline events
- Postgres-only settings contract; missing/non-Postgres `DATABASE_URL` fails
  loudly
- Default CMA seed fixture, analyst-only CMA Workbench draft/edit/publish/audit
  workflow, Chart.js efficient-frontier view, immutable `PortfolioRun` storage, run hashes,
  technical trace, advisor "why this recommendation" summary, and run history
- household and goal risk are both on the canon 1-5 scale; legacy 1-10 values
  are migrated and new values above 5 are rejected
- `MP20_ENGINE_ENABLED` kill-switch for recommendation generation
- repo-persistent agent memory

The working canon is now v2.7. It reframes the next work as Phase A/B/C:

- Phase A: offsite scaffold and Som-demo-grade foundation.
- Phase B: pilot hardening and IS validation before any advisor pilot use.
- Phase C: controlled pilot with 3-5 Steadyhand advisors using real clients.

Important: the current scaffold is useful foundation code, not pilot-grade
software. Treat the gap between the scaffold and canon v2.3 as the next
implementation backlog.

## Non-Negotiable Architecture Rules

- Engine is a library, not a service.
- `engine/` must not import Django, DRF, `web/`, `extraction/`, or `integrations/`.
- Web code translates DB models into `engine.schemas` Pydantic models at the boundary.
- The engine contract is moving from goal-level output to goal-account-link output.
  The optimization unit is `GoalAccountLink`, then account and household rollups.
- `PortfolioRun` is now the source of truth for generated recommendations;
  `Household.last_engine_output` is legacy/deprecated.
- `engine_ready` means reviewed facts are sufficient; `construction_ready`
  means committed household data can pass portfolio generation rules. Commit
  requires both gates plus required section approvals.
- External systems stay behind adapters in `integrations/`.
- AI can extract and style; it must not invent financial numbers.
- Keep real client raw files out of git.
- Real uploads must enter only through the authenticated local browser workflow
  with `MP20_SECURE_DATA_ROOT` set outside this repository.
- `DATABASE_URL` is required and must point to Postgres. SQLite is not an active
  runtime/test fallback.
- Real-derived extraction routes through Bedrock in ca-central-1. Anthropic
  direct is synthetic-only.
- Do not copy real client contents into repo files, memory docs, CI logs, or
  commit messages. Store only structured facts, run metadata, and minimally
  redacted evidence quotes in the DB.
- Audit logs are separate from observability logs. Audit rows are append-only via
  model guards plus backend-specific DB triggers.
- Client-visible risk vocabulary uses cautious / conservative-balanced /
  balanced / balanced-growth / growth-oriented, not low / medium / high.
- CMA editing and efficient-frontier visualization are financial-analyst-only
  surfaces. Advisors may generate and view runs but cannot edit CMA inputs.

## Current Scaffold Gaps vs Canon v2.3

- Engine now returns link-first recommendations with goal/account/
  household rollups and risk-to-percentile mapping 1-5 -> 5/15/25/35/45.
  Remaining canon gaps include fund-of-funds collapse suggestions, real tax-drag
  math, and compliance ratings.
- Extraction has a first secure-local scaffold: upload, raw storage, queue,
  local parsers, Bedrock routing, structured facts, reviewed state, readiness,
  and commit. The full five-layer canon workflow still needs richer
  reconciliation, IS validation, and source-review UX.
- Auth is still early but no longer open by default: client/review APIs require
  login, and real committed households are advisor-owned. Phase B still requires
  production-grade roles, password reset, MFA, session timeout, and lockout.
- UI now includes advisor recommendation output/history and financial analyst
  CMA Workbench/frontier workflow. Canon still requires the full household/account/goal
  three-tab pivot, fund vs asset-class toggle, pilot disclaimer surfaces, and
  richer current-vs-ideal visuals.
- PII guardrails use the canon defense-in-depth regime: secure-root validation,
  Bedrock ca-central-1 fail-closed routing, transient raw text, redacted evidence
  quotes, sensitive-ID hash/display, authenticated/RBAC-scoped app access, and
  retention/disposal tooling for local raw artifacts. Boundary pseudonymization
  is explicitly retired for this tranche; CI PII checks and encryption posture
  validation remain Phase B hardening.

## Build Commands

```bash
cp .env.example .env
# edit MP20_SECURE_DATA_ROOT to an outside-repo directory before upload/review
docker compose up --build

uv sync --all-groups
uv run ruff check .
uv run ruff format --check .
scripts/test-python-postgres.sh

cd frontend
npm install
npm run build
npm run codegen   # regenerate src/lib/api-types.ts when backend schema changes
PLAYWRIGHT_BASE_URL=http://localhost:5173 npm run e2e:synthetic
```

OpenAPI-typescript codegen (Phase 4.5): `frontend/src/lib/api-types.ts`
is generated from drf-spectacular's schema. Run `npm run codegen` after
any backend serializer change; CI gate `scripts/check-openapi-codegen.sh`
fails on drift.

## Git Protocol

- Work directly on `main` unless instructed otherwise.
- Make logical local commits after checks pass.
- Do not push unless explicitly asked.
- Update `docs/agent/session-state.md` and append to
  `docs/agent/handoff-log.md` after meaningful implementation or research.

## Useful Project Memory

- `docs/agent/session-state.md` — current implementation state and next work
- `docs/agent/handoff-log.md` — append-only dated handoffs
- `docs/agent/decisions.md` — implementation decisions distilled from the canon
- `docs/agent/open-questions.md` — tracked unresolved decisions
- `docs/agent/r10-sweep-results-2026-05-02.md` — Phase 4 tool-use migration R10 sweep (per-doc structural diff; canon §9.4.5 quality wins + −41% recall regression)
- `docs/agent/phase9-fact-quality-iteration.md` — post-pilot fact-quality iteration plan; recovers legitimate recall in the new tool-use path without re-introducing hallucinations
- `docs/agent/pilot-rollback.md` — Sev-1 rollback procedure for the limited-beta pilot (kill-switch, code revert, DB recovery, on-call list)
- `docs/agent/pilot-success-metrics.md` — quantitative pilot success metrics + weekly cadence + GA criteria + off-ramp conditions
- `docs/agent/next-session-starter-prompt.md` — copy/paste-ready bring-up prompt for the next sub-session (pre-flight checks + locked decisions + sub-session plan)
- `docs/agent/production-quality-bar.md` — production-grade UX-polish + comprehensive test-coverage map + production-infra requirements; load-bearing for sub-sessions #2-#7 (every per-phase ping gates on items from this doc)
