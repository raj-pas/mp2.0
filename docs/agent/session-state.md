# MP2.0 Session State

**Last updated:** 2026-04-29
**Branch:** `main`
**Phase:** Secure ingest hardening plus advisor-grade review tranche
**Status:** Local thin slice supports authenticated team-scoped advisor review,
secure-local upload/review to `engine_ready`, approval-gated commit, and
defensive committed client display

## Current Goal

Use the existing scaffold as the base for the canon v2.3 build sequence while
moving real-data intake through a secure local review gate:

- DB-backed synthetic Sandra/Mike Chen persona
- authenticated client list/detail in the advisor shell
- authenticated generate-portfolio call through DRF into the pure Python engine
  stub
- light audit events for core actions
- smoke tests and CI
- authenticated local advisor review workspace
- browser multi-file upload into `MP20_SECURE_DATA_ROOT` outside the repo
- Postgres-backed worker queue and parser/extraction pass
- reviewed client state, missing-field checklist, section approval, matching,
  and versioned commit to current household tables
- advisor-grade editable review sections with provenance snippets, conflict and
  unknown handling hooks, approval notes, sanitized timeline, and strict
  `engine_ready + approved sections` commit gate
- worker heartbeat/stale visibility, retry metadata, duplicate reconcile
  suppression, manual reconcile, OCR overflow metadata, and local artifact
  disposal/report command

Canon v2.3 raises the next bar substantially:

- Phase A: Som-demo-grade offsite foundation across ingestion, engine, reporting.
- Phase B: pilot hardening and IS validation before any advisor logs in.
- Phase C: 3-5 Steadyhand advisors using the system with bounded real-client pilot
  data.

## Active Handoff

Secure ingest hardening and advisor-grade review tranche has landed in the
working tree. Current verification passed:

- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run pytest`
- `npm run build`
- `npx playwright test e2e/synthetic-review.spec.ts --list`
- Full local synthetic Playwright execution was attempted against Docker Compose
  but stopped before browser launch because Chromium was not installed locally;
  `npx playwright install chromium` hung and was terminated. CI installs Chromium
  before running the synthetic browser E2E.
- Existing browser E2E history remains useful, but this tranche only committed
  Playwright specs/config and verified test discovery locally; full browser
  execution is wired for Docker Compose CI.

Implemented pieces:

- real-upload APIs now fail closed without Postgres; synthetic tests can still
  use SQLite
- advisor access is a single shared team scope; financial analysts receive 403
  for real-client PII surfaces
- audit rows are immutable through model guards plus DB triggers, and workspace
  timeline serialization redacts sensitive before/after fields
- engine kill-switch blocks portfolio generation without blocking intake/review
- worker heartbeat, stale job flags, retry eligibility, failure code/stage, OCR
  overflow metadata, duplicate reconcile suppression, and manual reconcile
  endpoint are implemented
- Bedrock fact payloads are validated against typed schemas with controlled JSON
  repair before failure
- reviewed state now includes field-source metadata; section approval blocks
  plain `approved` when required fields, unresolved conflicts, or required
  unknowns remain; commit requires all required sections approved
- Quick Fill was replaced by editable household, people, accounts, goals,
  mapping, and risk review sections with collapsed provenance and override notes
- committed client display uses defensive currency/percent formatting and avoids
  `$NaN`/blank financial states
- Playwright synthetic E2E and local real-bundle regression scaffolds were added;
  real-bundle artifacts must be directed under the secure data root
- local artifact disposal/report command added:
  `uv run python web/manage.py dispose_review_artifacts`

This tranche has local commits only; do not push unless explicitly asked.

## Canon v2.3 Context To Carry Forward

- The optimization unit is `GoalAccountLink`, not goal-alone. Engine output must
  become per-link first, then per-account and household rollups.
- Risk is a 5-point snap-to-grid scale mapped to percentiles 5/15/25/35/45.
  Advisor-visible risk should expose household component, goal component, and
  combined score.
- The three-tab household/account/goal view is the central advisor UX. Every tab
  reconciles to the same total AUM and toggles fund vs asset-class look-through.
- Extraction/review is now a hardened secure-local scaffold. It is not yet the
  full five-layer canon system and still needs IS validation, richer temporal
  reconciliation, pseudonymization, and CI PII checks.
- Real client PII must only enter through the authenticated browser upload with
  `MP20_SECURE_DATA_ROOT` outside the repo. Do not copy real contents into agent
  memory, repo files, CI, or logs.
- Pilot launch is gated by Phase B exit criteria, including real auth/RBAC,
  pilot disclaimer, feedback channel, kill-switch, compliance mapping, CMA admin
  view, and an end-to-end real tier-2 persona review with Lori.

## Known Scaffold Drift From Canon

- Engine schemas/output are still Phase 1 goal-level placeholders.
- Household risk remains 1-10 in code; canon uses 1-5 client/advisor language.
- `Goal.target_amount` is required in code; canon says future-dollar targets are
  optional secondary inputs.
- Extraction/LLM routing now enforces Bedrock env for real-derived facts and
  keeps raw text transient, but pseudonymization and CI PII checks are pending.
- Audit log is append-only but does not yet provide an audit browser UI or full
  input/output trace.
- Auth/RBAC is still early: endpoints require login, advisor team access is
  modeled, and financial analysts are denied PII, but Phase B still needs MFA,
  session timeout, lockout, password reset, and admin boundaries.
- Frontend lacks the three-tab pivot, click-through assignment, current-vs-ideal
  allocation, fan chart, and pilot-mode disclaimer.

## Next Recommended Work

1. Run the Docker Compose synthetic Playwright E2E end to end in CI/local once
   browsers are installed and the stack is available.
2. Convert engine schemas and output to the canon v2.3 per-link contract.
3. Harden extraction/reconciliation into the canon five-layer flow with IS
   validation and better source-review UX.
4. Build the three-tab household/account/goal UI around current reviewed state.
5. Add Phase B pilot gates: real auth roles, MFA/session policy, disclaimer,
   kill-switch, feedback channel, richer audit records, and CMA admin boundary.

## Notes for Parallel Sessions

- Use light handoffs; no file-level locking.
- Start by checking `git status` and reading this file.
- Update this file and append to `handoff-log.md` after meaningful work.
