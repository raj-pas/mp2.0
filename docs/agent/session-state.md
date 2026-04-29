# MP2.0 Session State

**Last updated:** 2026-04-29
**Branch:** `main`
**Phase:** Postgres foundation plus Fraser PortfolioRun tranche
**Status:** Local thin slice supports authenticated team-scoped advisor review,
secure-local upload/review to `engine_ready`, approval-gated commit, Fraser
link-first portfolio generation, immutable PortfolioRun history, and analyst
CMA/frontier workflow.

## Current Goal

Use the existing scaffold as the base for the canon v2.3 build sequence while
moving real-data intake through a secure local review gate and generated
portfolio recommendations through durable PortfolioRun records:

- DB-backed synthetic Sandra/Mike Chen persona
- authenticated client list/detail in the advisor shell
- authenticated generate-portfolio call through DRF into the Fraser link-first
  engine
- Postgres-only runtime/test foundation; missing or non-Postgres `DATABASE_URL`
  fails loudly
- secure browser multi-file upload into `MP20_SECURE_DATA_ROOT` outside the repo
- Postgres-backed worker queue and parser/extraction pass
- reviewed client state, missing-field checklist, section approval, matching,
  and versioned commit to current household tables
- advisor-grade editable review sections with provenance snippets, conflict and
  unknown handling hooks, approval notes, sanitized timeline, and strict
  `engine_ready + approved sections` commit gate
- worker heartbeat/stale visibility, retry metadata, duplicate reconcile
  suppression, manual reconcile, OCR overflow metadata, and local artifact
  disposal/report command
- Fraser extracted fixtures, CMA seed/defaults, analyst-only CMA draft/edit/
  publish, efficient frontier view, PortfolioRun hashes/traces/history, and
  advisor explainability

Canon v2.3 still raises the next bar:

- Phase A: Som-demo-grade offsite foundation across ingestion, engine, reporting.
- Phase B: pilot hardening and IS validation before any advisor logs in.
- Phase C: 3-5 Steadyhand advisors using the system with bounded real-client
  pilot data.

## Active Handoff

Postgres foundation plus Fraser PortfolioRun tranche has landed in the working
tree. Current verification passed:

- `uv run ruff check .`
- `uv run ruff format --check .`
- `scripts/test-python-postgres.sh`
- `npm run build`
- Docker Compose browser E2E:
  `PLAYWRIGHT_BASE_URL=http://localhost:5173 npm run e2e:synthetic`

Implemented pieces:

- Removed SQLite fallback from active settings. `DATABASE_URL` is required and
  must use `postgres://` or `postgresql://`.
- Added `scripts/test-python-postgres.sh`; it starts Compose Postgres, waits for
  health, exports a localhost Postgres URL when needed, and runs pytest without
  resetting the DB volume.
- Docker/local bootstrap now seeds Fraser CMA defaults and creates advisor plus
  financial analyst local users from env vars.
- Extracted durable Fraser v1 fixtures from
  `/Users/saranyaraj/Downloads/mp20_scenario_evaluator_v23-2.html` without
  committing the full HTML. Advisor console HTML remains reference-only.
- Ported Fraser covariance/frontier/percentile/projection math into pure
  `engine/` code and moved optimizer output to link-first recommendations.
- Added global CMA snapshot/fund/correlation models, seed command, analyst-only
  draft/update/publish APIs, frontier API, and CMA UI modal.
- Added immutable PortfolioRun storage, link recommendation rows, run hashes,
  full committed construction snapshot, engine output JSON, advisor summary,
  technical trace, current/stale status, and run-history UI.
- Portfolio generation now starts from committed household/person/account/goal/
  link state only and fails clearly when no active CMA snapshot exists.
- Financial analysts can access CMA/frontier metadata but remain blocked from
  real-client/review PII surfaces; advisors cannot edit or publish CMA.
- PlanningVersion snapshots can be created for advisor planning edits and mark
  current portfolio runs stale.
- Review state versioning now locks workspace rows before merge/version
  creation so fast Postgres-backed edits do not collide or lose prior edits.
- Browser E2E now covers synthetic review commit, advisor generate/history, and
  analyst CMA/frontier workflow. Chart assertions are DOM-based; screenshots are
  retained as Playwright artifacts on failure.

## Canon v2.3 Context To Carry Forward

- The optimization unit is `GoalAccountLink`, not goal-alone. Engine output is
  per-link first, then per-account and household rollups.
- Goal risk is a 5-point snap-to-grid scale mapped to percentiles 5/15/25/35/45.
- The three-tab household/account/goal view remains the central advisor UX.
  Every tab should reconcile to the same total AUM and eventually toggle fund vs
  asset-class look-through.
- Extraction/review is a hardened secure-local scaffold. It is not yet the full
  five-layer canon system and still needs IS validation, richer temporal
  reconciliation, pseudonymization, and CI PII checks.
- Real client PII must only enter through the authenticated browser upload with
  `MP20_SECURE_DATA_ROOT` outside the repo. Do not copy real contents into agent
  memory, repo files, CI, or logs.
- Pilot launch is gated by Phase B exit criteria, including real auth/RBAC,
  pilot disclaimer, feedback channel, kill-switch, compliance mapping, deeper
  CMA governance, and an end-to-end real tier-2 persona review with Lori.

## Known Scaffold Drift From Canon

- Fund-of-funds collapse suggestions are still out of scope.
- Real tax-drag math is still out of scope; v1 stores neutral/stub tax-drag
  metadata on CMA funds.
- Household risk remains 1-10 in some intake/display surfaces; goal risk is now
  1-5 for portfolio optimization.
- Extraction/LLM routing enforces Bedrock env for real-derived facts and keeps
  raw text transient, but pseudonymization and CI PII checks are pending.
- Audit log is append-only and PortfolioRun stores input/output hashes plus
  technical trace, but there is no audit browser UI.
- Auth/RBAC is still early: endpoints require login, advisor team access is
  modeled, and financial analysts are denied PII, but Phase B still needs MFA,
  session timeout, lockout, password reset, and production role governance.
- Frontend has advisor recommendation/history and analyst CMA/frontier surfaces,
  but still lacks the full three-tab pivot, asset-class look-through, richer fan
  chart, and pilot-mode disclaimer.

## Next Recommended Work

1. Harden extraction/reconciliation into the canon five-layer flow with IS
   validation and better source-review UX.
2. Build the three-tab household/account/goal UI around current reviewed state
   and PortfolioRun outputs.
3. Add Phase B pilot gates: real auth roles, MFA/session policy, disclaimer,
   feedback channel, richer audit records, and CMA governance.
4. Add fund-of-funds execution collapse suggestions and real tax-drag math when
   Fraser/Purpose inputs are ready.

## Notes for Parallel Sessions

- Use light handoffs; no file-level locking.
- Start by checking `git status` and reading this file.
- Update this file and append to `handoff-log.md` after meaningful work.
