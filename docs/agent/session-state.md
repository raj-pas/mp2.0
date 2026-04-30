# MP2.0 Session State

**Last updated:** 2026-04-30
**Branch:** `feature/ux-rebuild` (cut from `main` for the v36 UI/UX rewrite per locked decision #9)
**Phase:** R5 — Wizard onboarding **COMPLETE** (5-step `/wizard/new` route with zod schema + per-tab draft recovery + live risk-profile recompute + atomic commit fires AuditEvent + 8/8 e2e)
**Status:** R0 lands the substrate for the v36 advisor console rewrite. Five new pure
engine modules with 216 parity tests; engine purity AST-enforced; new R0 modules pass
mypy strict. Backend ships drf-spectacular OpenAPI, django-csp 4.x security headers,
self-hosted-fonts scaffold (.woff2 download manual), OpenTelemetry hookup (env-toggled).
Frontend ships v36 design tokens (paper/ink/copper/gold/buckets/funds/fonts), TS strict
+ noUncheckedIndexedAccess + zero-`any`, ESLint flat config (jsx-a11y + i18next +
react-hooks), react-i18next scaffolding (en + fr placeholder), holding shell with
top-level + per-route ErrorBoundary, all old surfaces removed (App.tsx replaced;
ReviewShell + CmaWorkbench + api.ts + types.ts deleted; rebuilt across R2-R9).
Vocabulary CI guard scans frontend + backend serializers/migrations/management
commands/fixtures. Pre-existing portfolio v2 + secure-local review pipeline +
immutable audit + analyst CMA Workbench remain on `main`; ride forward via the
phase-by-phase rebuild.

## Current Goal

Phases R0 + R1 + R2 + R3 + R4 + R5 of the v36 UI/UX rewrite are complete on
`feature/ux-rebuild`. The approved migration plan at
`~/.claude/plans/i-want-you-to-rosy-mccarthy.md` (39 locked decisions
across 9 rounds) governs the rewrite. R0 laid the foundation (engine
modules + backend plumbing + frontend foundation); R1 added the backend
surface the new UI will call (4 new models + 18 endpoints + centralized
audit-event regression suite); R2 shipped the chrome (TopBar +
ContextPanel + BrowserRouter + auth gate + per-route ErrorBoundary);
R3 ships the three-view stage — HouseholdRoute (AUM split strip +
d3-hierarchy squarified treemap with click-to-drill into account or
goal), AccountRoute (4-tile KPI strip + Chart.js fund-composition
ring + top-funds AllocationBars + clickable goals-in-account list),
GoalRoute (4 KPI tiles + reusable RiskBandTrack 5-band marker +
linked-accounts list), populated per-kind ContextPanel
(HouseholdContext / AccountContext / GoalContext), and full
TanStack Query hooks (`useHousehold`, `useTreemap`, `useClients`).
Risk descriptors flow through `lib/risk.ts` canon-aligned helper.
Phase R4 (Goal allocation + projections fan chart + optimizer
output + rebalance moves + 5-band RiskSlider with override flow)
is next.

Pre-R0, the `main` branch already shipped the canon v2.7 portfolio v2 stack:

- DB-backed synthetic Sandra/Mike Chen persona
- authenticated client list/detail in the advisor shell
- authenticated generate-portfolio call through DRF into the link-first
  engine
- Postgres-only runtime/test foundation; missing or non-Postgres `DATABASE_URL`
  fails loudly
- secure browser multi-file upload into `MP20_SECURE_DATA_ROOT` outside the repo
- Postgres-backed worker queue and parser/extraction pass
- canonical `extraction/` package for adaptive classification, deterministic
  parsing, Bedrock prompt routing, structured fact validation, normalization,
  and field-specific source authority helpers
- reviewed client state, missing-field checklist, section approval, matching,
  and versioned commit to current household tables
- advisor-grade editable review sections with provenance snippets, conflict and
  unknown handling hooks, approval notes, sanitized timeline, and strict
  `engine_ready + construction_ready + approved sections` commit gate
- worker heartbeat/stale visibility, retry metadata, duplicate reconcile
  suppression, manual reconcile, OCR overflow metadata, and local artifact
  disposal/report command
- Default CMA v2 fixtures, analyst-only CMA Workbench draft/edit/publish/audit,
  Chart.js efficient frontier view, PortfolioRun hashes/traces/history,
  advisor explainability, goal-risk audit metadata, and a Household/Account/Goal
  portfolio console

Canon v2.3 still raises the next bar:

- Phase A: Som-demo-grade offsite foundation across ingestion, engine, reporting.
- Phase B: pilot hardening and IS validation before any advisor logs in.
- Phase C: 3-5 Steadyhand advisors using the system with bounded real-client
  pilot data.

## Active Handoff

Portfolio v2 construction, audit, and advisor console changes are in the
working tree. Current verification passed during implementation:

- `uv run ruff check .`
- `uv run ruff format --check .`
- `DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 uv run python -m pytest engine/tests/test_engine.py -q`
- `DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 uv run python -m pytest web/api/tests/test_api.py -q`
- `DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 uv run python web/manage.py makemigrations --check --dry-run`
- `scripts/test-python-postgres.sh`
- `npm run build`
- `npm run e2e:synthetic`

Still manual before real-derived use:

- Manual secure-root `npm run e2e:real` before real-derived use

Implemented pieces:

- Removed SQLite fallback from active settings. `DATABASE_URL` is required and
  must use `postgres://` or `postgresql://`.
- Added `scripts/test-python-postgres.sh`; it starts Compose Postgres, waits for
  health, exports a localhost Postgres URL when needed, and runs pytest without
  resetting the DB volume.
- Docker/local bootstrap now seeds Default CMA assumptions and creates advisor plus
  financial analyst local users from env vars.
- Added tracked Default CMA fixture data without committing the source HTML.
  Advisor console HTML remains reference-only.
- Ported covariance/frontier/percentile/projection math into pure `engine/`
  code and moved optimizer output to link-first recommendations.
- Added global CMA snapshot/fund/correlation models, seed command, analyst-only
  draft/update/publish/audit APIs, frontier API, and CMA Workbench UI.
- Upgraded portfolio output to `engine_output.link_first.v2`; removed legacy
  household output storage and mutable current/stale lifecycle fields.
- Added append-only `PortfolioRunEvent` lifecycle rows for generated, reused,
  decline, regeneration, CMA/household invalidation, hash mismatch, audit export,
  and generation failure.
- Added durable goal-account link ids, account cash state, account-first rollups,
  current-vs-ideal diagnostics, holding alias mapping diagnostics, whole-fund
  metadata warnings, v2 run manifests, and sanitized audit export.
- Portfolio generation now starts from committed household/person/account/goal/
  link state only and fails clearly when no active CMA snapshot exists.
- Financial analysts can access CMA assumptions/frontier/audit metadata but
  remain blocked from real-client/review PII surfaces; advisors cannot access
  raw CMA assumptions, edit, or publish CMA.
- PlanningVersion snapshots can be created for advisor planning edits and now
  append household-change invalidation events to current portfolio runs.
- Publishing a new CMA now appends CMA invalidation events instead of mutating
  stored run status.
- Advisor console now has Household, Account, and Goal tabs; recommendation
  cards show direct fund weights first, label building-block vs whole-portfolio
  funds, and expose structured diagnostics in an audit drawer.
- Review state versioning now locks workspace rows before merge/version
  creation so fast Postgres-backed edits do not collide or lose prior edits.
- Browser E2E now covers synthetic review commit, advisor generate/history, and
  analyst CMA Workbench workflow. Chart assertions are DOM-based; screenshots
  and Playwright reports are retained as artifacts on failure in CI.
- Household and goal risk now use the same 1-5 contract. Legacy 1-10 household
  values are remapped with `ceil(old / 2)` by Django data migration, new values
  above 5 fail validation, and visible `/10` risk labels have been removed.
- Review readiness now distinguishes `engine_ready` from `construction_ready`.
  Review commit requires both readiness gates plus required section approvals;
  portfolio generation still requires an explicit advisor click after commit.
- Real-bundle E2E artifacts/logs must stay under `MP20_SECURE_DATA_ROOT`. The
  local harness uses generic bundle numbers and filters empty directories; avoid
  HTML report output for real runs.

## Canon v2.3 Context To Carry Forward

- The optimization unit is `GoalAccountLink`, not goal-alone. Engine output is
  per-link first, then per-account and household rollups.
- Goal risk is a 5-point snap-to-grid scale mapped to percentiles 5/15/25/35/45.
- The three-tab household/account/goal view is now the central advisor UX.
  Every tab reconciles to the same PortfolioRun output, with fund-level direct
  weights first and asset/geography look-through metadata available for whole
  funds when present.
- Extraction/review is a hardened secure-local scaffold being moved into the
  canonical `extraction/` package. It still needs IS validation, richer temporal
  reconciliation, coverage-matrix hardening, and CI PII checks.
- Real client PII must only enter through the authenticated browser upload with
  `MP20_SECURE_DATA_ROOT` outside the repo. Do not copy real contents into agent
  memory, repo files, CI, or logs.
- Pilot launch is gated by Phase B exit criteria, including real auth/RBAC,
  pilot disclaimer, feedback channel, kill-switch, compliance mapping, deeper
  CMA governance, and an end-to-end real tier-2 persona review with Lori.

## Known Scaffold Drift From Canon

- Whole-portfolio funds are optimizer eligible and may mix with building-block
  funds. Fund-of-funds execution collapse suggestions remain out of scope.
- Real tax-drag math is still out of scope; v1 stores neutral/stub tax-drag
  metadata on CMA funds.
- Household and goal risk are both 1-5. The specific weighting for the future
  household x goal composite is still open and should remain parameterized.
- Extraction/LLM routing enforces Bedrock env for real-derived facts and keeps
  raw text transient. Boundary pseudonymization is retired by the canon's
  defense-in-depth decision; CI PII checks remain pending.
- Audit log is append-only and PortfolioRun stores input/output/CMA/run-signature
  hashes plus technical trace. Portfolio lifecycle events are append-only and
  advisor audit export is sanitized.
- Auth/RBAC is still early: endpoints require login, advisor team access is
  modeled, and financial analysts are denied PII, but Phase B still needs MFA,
  session timeout, lockout, password reset, and production role governance.
- Frontend has the full three-tab advisor pivot and analyst CMA Workbench
  surfaces, but still lacks richer fan charts and pilot-mode disclaimer wording.

## Next Recommended Work

1. Harden extraction/reconciliation into the canon five-layer flow with IS
   validation and better source-review UX.
2. Build the three-tab household/account/goal UI around current reviewed state
   and PortfolioRun outputs.
3. Add Phase B pilot gates: real auth roles, MFA/session policy, disclaimer,
   feedback channel, broader audit records, and CMA governance.
4. Add fund-of-funds execution collapse suggestions and real tax-drag math when
   Fraser/Purpose inputs are ready.

## Notes for Parallel Sessions

- Use light handoffs; no file-level locking.
- Start by checking `git status` and reading this file.
- Update this file and append to `handoff-log.md` after meaningful work.
