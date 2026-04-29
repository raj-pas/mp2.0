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
- pure Python engine stub
- synthetic Sandra/Mike Chen persona
- local advisor login, authenticated client access, and review workspace UI
- secure outside-repo browser upload path
- advisor-grade reviewed sections with provenance snippets, conflict/unknown
  handling hooks, edit notes, readiness checklist, matching, and strict
  link-or-create commit gating
- worker heartbeat/stale visibility, retry metadata, duplicate reconcile
  suppression, manual reconcile, and provider-safe OCR overflow metadata
- immutable audit logging with sanitized workspace timeline events
- `MP20_ENGINE_ENABLED` kill-switch for recommendation generation
- repo-persistent agent memory

The working canon is now v2.3. It reframes the next work as Phase A/B/C:

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
- External systems stay behind adapters in `integrations/`.
- AI can extract and style; it must not invent financial numbers.
- Keep real client raw files out of git.
- Real uploads must enter only through the authenticated local browser workflow
  with `MP20_SECURE_DATA_ROOT` set outside this repository.
- Real-upload APIs require Postgres by default; SQLite is only for synthetic
  tests and non-real local work.
- Real-derived extraction routes through Bedrock in ca-central-1. Anthropic
  direct is synthetic-only.
- Do not copy real client contents into repo files, memory docs, CI logs, or
  commit messages. Store only structured facts, run metadata, and minimally
  redacted evidence quotes in the DB.
- Audit logs are separate from observability logs. Audit rows are append-only via
  model guards plus backend-specific DB triggers.
- Client-visible risk vocabulary uses cautious / conservative-balanced /
  balanced / balanced-growth / growth-oriented, not low / medium / high.
- CMA editing and efficient-frontier visualization are admin-only surfaces.

## Current Scaffold Gaps vs Canon v2.3

- Engine still returns Phase 1 goal-level blends; canon requires per-link blends,
  per-account rollups, resolved risk per link, fund-of-funds collapse suggestions,
  fan chart data per link, tax-drag/CMA audit trace, and compliance ratings.
- Risk is currently a 1-10 placeholder; canon locks a 5-point snap-to-grid scale
  mapped to optimizer percentiles 5/15/25/35/45.
- Extraction has a first secure-local scaffold: upload, raw storage, queue,
  local parsers, Bedrock routing, structured facts, reviewed state, readiness,
  and commit. The full five-layer canon workflow still needs richer
  reconciliation, IS validation, and source-review UX.
- Auth is still early but no longer open by default: client/review APIs require
  login, and real committed households are advisor-owned. Phase B still requires
  production-grade roles, password reset, MFA, session timeout, and lockout.
- UI is a Phase 1 advisor shell. Canon requires the household/account/goal
  three-tab view, fund vs asset-class toggle, click-through goal-account
  assignment, current-vs-ideal allocation, and pilot disclaimer surfaces.
- PII guardrails are partial: secure-root validation, Bedrock fail-closed routing,
  transient raw text, redacted evidence quotes, and sensitive-ID hash/display
  exist. Retention/disposal tooling exists for local raw artifacts. Scrub-pass
  hooks, pseudonymization storage, CI PII checks, and encryption posture
  validation are still pending.

## Build Commands

```bash
cp .env.example .env
# edit MP20_SECURE_DATA_ROOT to an outside-repo directory before upload/review
docker compose up --build

uv sync --all-groups
uv run ruff check .
uv run ruff format --check .
uv run pytest

cd frontend
npm install
npm run build
npx playwright test e2e/synthetic-review.spec.ts --list
```

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
