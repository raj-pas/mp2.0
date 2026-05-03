# MP2.0 Session State

**Last updated:** 2026-05-02 (Phase 5a done; 5b+ pending)
**Branch:** `feature/ux-rebuild` (cut from `main` for the v36 UI/UX rewrite per locked decision #9)
**HEAD:** Phase 5a commit (Conflict-resolution endpoint + ConflictPanel)
**Phase:** **Beta-pilot hardening 0-5a done; 5b-8 pending.** Phase 5a closes CONFLICT-CARD: backend `ReviewWorkspaceConflictResolveView` (POST /api/review-workspaces/<wsid>/conflicts/resolve/) atomic+select_for_update with structured validation; per-conflict candidate enrichment with redacted evidence quotes; frontend `ConflictPanel` + `ConflictCard` + `useResolveConflict` hook + i18n keys. 408 pytest passing (400 + 8 new); drift gate caught + regenerated `api-types.ts` correctly. R7 done + post-R7 hardening (3.A/B/E) + R10 sweep 55/55 + R8 methodology + demo prep was DONE per prior sessions. The 2026-05-02 session re-audited at HEAD `f5f2519`, found 8 prior findings closed + 8 still open + 2 new (ENUM-CASE demo-blocker, BUG-1 atomicity), planned 9 phases via 12 user-interview rounds (~50 locked decisions), and executed Phases 0-3:
- **Phase 0** (commit `1e10ea7`): persisted `docs/agent/extraction-audit.md` (living doc), `docs/agent/baselines/f5f2519.md`, handoff-log entry; cancelled scheduled trigger trig_018jTLBFnRJ8oTAiZbyQXwBv (subsumed); installed bandit + pytest-cov + pytest-benchmark + factory-boy + python-json-logger dev-deps + bandit config. Found + fixed 2 unused imports + 1 format drift in test_db_state_integrity.py from prior session.
- **Phase 1** (commit `a861c35`; +6 tests): closed ENUM-CASE — `_normalize_regulatory_enum` helper applied to regulatory_objective + regulatory_time_horizon + regulatory_risk_rating in `_account_to_engine`; existing `_normalize_lowercase_enum` applied to marital_status. Per canon §9.4.5 raises on unknown values; empty passes through.
- **Phase 2** (commit `f2486f1`; +14 tests + grep guard): closed PII-1/2/3/4/SER + REDACT-1. New `web/api/error_codes.py` with `failure_code_for_exc`, `safe_exception_summary`, `safe_response_payload`, `safe_audit_metadata`, `friendly_message_for_code`. 11+ str(exc) sites scrubbed in views.py + preview_views.py + review_processing.py. Extended `_REDACTION_PATTERNS` for routing/phone/address. New CI guard `scripts/check-pii-leaks.sh`. 5 existing tests updated to assert structured `code` field.
- **Phase 3** (commit `0277675`; +4 tests): closed BUG-1 + REC-1. `ReviewDocumentManualEntryView.post` decorated `@transaction.atomic` + `select_for_update` on document. `process_document` wraps fact bulk_create + FACTS_EXTRACTED save + enqueue_reconcile in one atomic block.

**Demo to CEO+CPO 2026-05-04; release 2026-05-08.** Phase 3.A (Bedrock max_tokens 4096→16384, env-configurable) closes the truncation bug. Phase 3.B (typed BedrockExtractionError + structured failure_code) routes diagnostic detail to advisor-facing UI copy. Phase 3.E (manual-entry escape hatch) gives advisors a deliberate path forward when extraction can't recover. **R10 sweep across all 7 client folders: 55/55 docs reconciled (100%), 2,304 facts extracted, 0 new failures** — Phases 3.C+D defense-in-depth polish confirmed unnecessary; the simpler max_tokens fix subsumed both originally-flagged failure modes (xlsx + large-PDF). Gates at HEAD: 330 pytest, 10/10 e2e, ruff/format/typecheck/lint/build/vocab/migrations all green. **Read [`docs/agent/post-r7-handoff-2026-05-01.md`](post-r7-handoff-2026-05-01.md) FIRST** for full context. Foundation reset (`scripts/reset-v2-dev.sh --yes`) cleared 54 stale ProcessingJobs from prior sessions. **User-reported "button greys, nothing happens" upload bug ROOT-CAUSED + fixed**: a live `FileList` reference race in `DocDropOverlay.handleFilesPicked` — `event.target.value = ""` cleared the live FileList before React's deferred `setFiles` callback could read it; fix snapshots `Array.from(picked)` synchronously. Synthetic full pipeline validated end-to-end (upload → worker → reconcile → state PATCH → approve → commit → portfolio gen). Niesner real-PII checkpoint: 12 docs uploaded, 285 facts extracted across 10 reconciled docs (PDFs + DOCX), 2 known-bad-bounded failures (6.2MB Plan PDF + 1 xlsx — both `Bedrock did not return valid JSON`); UI surfaces all correctly. Gates: 319 pytest + 10/10 e2e + ruff + typecheck + lint + build + vocab.
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

Phases R0 + R1 + R2 + R3 + R4 + R5 + R6 + R7 of the v36 UI/UX rewrite are complete on
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
