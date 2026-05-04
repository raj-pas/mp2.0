# Changelog

All notable changes to MP2.0 are documented here. The format
adheres to [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow `vMAJOR.MINOR.PATCH-pre`. The current pilot is
tagged `v0.1.0-pilot`.

## v0.1.2-engine-display — 2026-05-04

Engine→UI display integration. Closes the gap between the engine's
`PortfolioRun` output and the advisor's eyes. Sub-sessions #1-#5
across 4 days; 111 locked decisions captured in
`~/.claude/plans/i-want-you-to-jolly-beacon.md`.

### Added

- **Engine recommendations on the Goal route** — every committed
  household with an active CMA snapshot now displays a
  `RecommendationBanner` with run signature + freshness, an
  `AdvisorSummaryPanel` with engine `link_recommendation.advisor_summary`
  per goal-account link, and `useGeneratePortfolio` mutation hook
  for the Regenerate / Retry / Generate CTAs. ARIA `aria-live="polite"`
  per locked #109; Sonner toast on failure with `lastSurfacedRef`
  dedup per locked #9.
- **Household-level rollup panel** — `HouseholdPortfolioPanel` between
  AUM strip and treemap (per locked #10) with expected return,
  volatility, top 4 funds. Mirrors Banner failure pattern per locked #19.
- **Auto-trigger on every committed-state mutation** — synchronous
  invocation of `_trigger_portfolio_generation` inside
  `transaction.atomic` (per locked #74; helper-managed atomic per #81)
  on 8 trigger points: review_commit, wizard_commit, override,
  realignment, conflict_resolve, defer_conflict, fact_override,
  section_approve. The 4 workspace-level triggers gate on
  `linked_household_id is None` per locked #27 — silent-skip with
  `portfolio_generation_skipped_post_<source>` audit when the
  workspace is not yet linked.
- **5 typed exceptions** for known engine states:
  `EngineKillSwitchBlocked`, `NoActiveCMASnapshot`,
  `InvalidCMAUniverse`, `ReviewedStateNotConstructionReady`,
  `MissingProvenance`. Caller emits skip audit + returns None per
  locked #9 typed-skip path.
- **Failure surfacing for unexpected exceptions** —
  `HouseholdDetailSerializer.latest_portfolio_failure`
  SerializerMethodField returns `{action, reason_code,
  exception_summary, occurred_at}` (sanitized via
  `safe_audit_metadata`). RecommendationBanner reads + shows inline
  error + Retry CTA + Sonner toast on mount; HouseholdPortfolioPanel
  mirrors the same pattern.
- **`/api/preview/moves/` reads from `goal_rollups`** when a
  PortfolioRun exists for the household; `SLEEVE_REF_POINTS`
  calibration as fallback. Response includes `source: "portfolio_run"
  | "calibration"` so the frontend can label the source per locked #6.
- **Sandra/Mike Chen synthetic auto-seeded with PortfolioRun** —
  `load_synthetic_personas` invokes `_trigger_portfolio_generation(
  source="synthetic_load")` after persona load. Demo-ready state via
  `bash scripts/reset-v2-dev.sh --yes` (which now bootstraps the
  advisor user BEFORE loading the persona; previously the order was
  reversed and AdvisorProfile pre-ack was silently skipped).
- **RiskProfile + canonical sh_* fund holdings on Sandra/Mike** —
  RiskProfile inputs (Q1=5, Q2=B, Q3=["career"], Q4=B) yield
  household score 3 / Balanced / anchor=22.5 per Hayes worked example.
  7 canonical funds (sh_income, sh_equity, sh_global_equity,
  sh_builders, sh_founders, sh_savings, sh_small_cap_equity) totaling
  $1,308,000 across 4 accounts.
- **Advisor disclaimer + tour pre-acked on synthetic load** —
  `advisor_pre_ack: {disclaimer: true, tour: true}` in
  `personas/sandra_mike_chen/client_state.json` populates
  `AdvisorProfile.disclaimer_acknowledged_at` (v1) +
  `tour_completed_at` so PilotBanner + WelcomeTour don't interrupt
  demo flow.
- **`mockHousehold` test factory** at
  `frontend/src/__tests__/__fixtures__/household.ts` per locked #84 —
  defaults match the live `/api/clients/hh_sandra_mike_chen/` payload
  byte-for-byte (including allocation weights with full precision /
  scientific notation for tiny weights). Per locked #55: locks the
  cost-key bug class at `2bd77d3` (fixture / payload shape drift).
- **Comprehensive test coverage** — 3 Hypothesis property suites
  (auto-trigger idempotency / audit metadata invariants /
  workspace trigger gate per locked #99); 7 Vitest test files
  including StrictMode double-invoke tests per locked #64 and
  expectTypeOf compile-time contract tests per locked #104; pool
  capacity regression at 120 concurrent connections per locked #80
  + #102; full advisor lifecycle integration test per locked #96;
  pre-A2 backwards compat + HouseholdDetail JSON-shape snapshot
  per locked #97 + #101; visual regression baselines via Playwright
  per locked #82 (extending `frontend/e2e/visual-verification.spec.ts`).
- **Perf benchmarks for the auto-trigger path** (per locked #56) —
  P50 / P99 budgets enforced. Measured: typed-skip 311us; REUSED
  path 266ms; cold first-run 530ms. All within budget; locked #56
  strict P99<1000ms preserved.

### Changed

- **HouseholdDetailSerializer** — added `latest_portfolio_failure`
  field. Pre-existing PortfolioRun consumers continue to work (null
  is the default; no breaking change).
- **Frontend `LinkRecommendation` type** in `frontend/src/lib/household.ts`
  now matches `engine.schemas.LinkRecommendation` exactly (was
  drifted: previously had `{fund_id, weight}[]`; engine sends
  `Allocation[]` with sleeve_id / sleeve_name / asset_class_weights /
  geography_weights / fund_type). 4 helpers added: `findGoalRollup`,
  `findHouseholdRollup`, `findGoalLinkRecommendations`,
  `findLinkRecommendationRow`.
- **`scripts/reset-v2-dev.sh`** — `bootstrap_local_advisor` now runs
  BEFORE `load_synthetic_personas` so AdvisorProfile pre-ack from the
  fixture lands successfully.

### Tests

- Backend pytest: ~913 tests in isolation (was 854 baseline at
  `081cfc8`; +59 net new across A1 fixture smoke + auto-trigger
  regression + Hypothesis property suites + concurrency stress +
  RBAC matrix + connection pool capacity + perf benchmarks +
  full lifecycle integration + pre-A2 compat + HouseholdDetail
  JSON-shape snapshot).
- Frontend Vitest: 177 tests in 19 files (was 82 in 13; +95
  comprehensive engine→UI display coverage).
- Foundation e2e: 13/13 chromium passing (unchanged).
- Visual-verification e2e: extended with engine→UI surfaces
  per A6 Round 3.
- Cross-browser: webkit + firefox spot-check on engine→UI
  surfaces per A6.12.
- Bundle size: 267.21 kB gzipped (under 290 kB threshold per
  locked #85).

### Architecture

- Helper trio at `web/api/views.py:621-968`:
  `_trigger_portfolio_generation`,
  `_trigger_and_audit`,
  `_trigger_and_audit_for_workspace`.
- Sync-inline auto-trigger per locked #74 (response IS truth;
  no `transaction.on_commit`; no polling). PostgreSQL pool to 150
  + max_connections to 200 supports 100-parallel concurrent commits
  per locked #80.
- Helper-managed `transaction.atomic` per locked #81 — uses
  savepoints under nested-atomic semantics so request-context
  callers (via Django's per-request atomic) and management-command
  callers (load_synthetic_personas, upload_and_drain.py) both work
  without per-callsite atomic boilerplate.

### Audit

- 111 user-locked decisions documented in this work; migrated to
  `docs/agent/decisions.md` "Engine→UI Display Integration
  (2026-05-03/04)" section per locked #91. Distilled to 1-line
  entries grouped by dimension (architecture / UX / operational /
  testing / documentation / continuity / meta).
- 5 sub-sessions over 4 days. Sub-session boundaries documented in
  `docs/agent/handoff-log.md` with per-phase verbose ~400-word
  entries per `production-quality-bar.md` §9.

### Deferred to a later release

- Dual-line fan chart (engine canonical + calibration what-if)
  per locked #24 + #90 — AdvisorSummaryPanel covers the engine
  recommendation explanation; fan chart enhancement is post-pilot
  scope.
- OTEL exporter backend wire-up — spans wrap `_trigger_portfolio_generation`
  per locked #89 but no-op locally; pilot-week observability adds
  the backend (post-pilot scope per `docs/agent/next-session-starter-prompt.md`
  §11).

## v0.1.0-pilot — 2026-05-08

Limited-beta pilot release for 3-5 advisors at Steadyhand on
real-PII workflows.

### Added

- **Bedrock tool-use extraction** (Phase 4) — replaces the
  free-form-JSON path with Anthropic's tool-use API.
  Eliminates the JSON-repair surface (REPAIR-1 + REPAIR-2)
  entirely; structurally impossible failure shapes
  (markdown tables, prose preambles, alternate-key drift) are
  removed at the API layer. SDK probe verifies forward-compat
  on Sonnet 4.6 + Opus 4.7. Per-doc-type prompt modules in
  `extraction/prompts/{base,kyc,statement,meeting_note,planning,generic}.py`
  with shared no-fabrication guidance + canonical-vocabulary
  + canonical-field-inventory. Confidence floor caps fact
  confidence to one tier above classification confidence
  (PROMPT-5 semantics); `multi_schema_sweep` classification
  routes to the generic builder.
- **OpenAPI-typescript codegen + drift CI gate** (Phase 4.5)
  — `frontend/src/lib/api-types.ts` generated from
  drf-spectacular's `/api/schema/`; `scripts/check-openapi-codegen.sh`
  fails CI on drift. Closes the FE/BE enum-drift bug class.
- **Conflict-resolution card UI + endpoint** (Phase 5a) —
  `POST /api/review-workspaces/<wsid>/conflicts/resolve/` with
  atomic + select_for_update, structured failure codes,
  rationale capture, evidence-ack checkbox. Per-conflict
  candidate enrichment with redacted evidence quotes. New
  frontend `ConflictPanel` + `ConflictCard` components wired
  into the Review screen.
- **Pilot disclaimer banner with server-side audit-tracked
  acknowledgement** (Phase 5b.1) — `AdvisorProfile` model
  (1:1 with `auth.User`) holds `disclaimer_acknowledged_at`
  + `disclaimer_acknowledged_version`. Endpoint
  `POST /api/disclaimer/acknowledge/` emits
  `disclaimer_acknowledged` audit event with metadata
  `{version, advisor_id, ip, user_agent, acknowledged_at}`.
  Bumping `DISCLAIMER_VERSION` triggers re-ack.
- **In-app feedback infrastructure** (Phase 5b.1) — `Feedback`
  model with Linear-mirroring schema; `POST /api/feedback/`
  for advisor submit, `GET /api/feedback/report/`
  (analyst-only with status/severity/since/advisor filters
  + CSV export), `PATCH /api/feedback/<id>/` for ops triage.
  Django admin registered.
- **First-login welcome tour** (Phase 5b.6) — 3-step
  coachmark with server-side ack via `tour_completed_at`
  User-profile field; `POST /api/tour/complete/` is
  idempotent + audit-event-emitting.
- **Worker health banner** (Phase 5b.2) — renders only when
  `worker_health.status` is stale/offline AND active jobs > 0.
- **Polling backoff** (Phase 5b.7) — `useReviewWorkspace`
  exponential backoff with jitter once stillProcessing
  (3s base → 30s max).
- **Confidence chip component** (Phase 5b.9) — color + text +
  ARIA label single-source rendering; not color-only per
  WCAG 2.1 AA. Wired into `ConflictPanel.CandidateRow`.
- **axe-core a11y testing in Playwright** (Phase 5b.14) +
  `pilot-features-smoke.spec.ts` covering banner + feedback +
  axe scans on `/` + `/review`.
- **Append-only `FactOverride` model** (Phase 5b.10/11
  foundation) — append-only via the `HouseholdSnapshot`
  pattern; latest-row-wins per `(workspace, field)`.
- **Pilot rollback procedure** (`docs/agent/pilot-rollback.md`)
  — severity classification, kill-switch, code revert,
  DB recovery, on-call list, post-incident audit.
- **Pilot success metrics + end-criteria**
  (`docs/agent/pilot-success-metrics.md`) — quantitative bars,
  weekly cadence, GA criteria, off-ramp conditions.
- **Pilot advisor provisioning command** (Phase 8.5) —
  `python web/manage.py provision_pilot_advisors --config-file=...`
  reads YAML from `MP20_SECURE_DATA_ROOT`, idempotent, audit-
  event-emitting per advisor. Refuses plain-text passwords.

### Fixed

- **ENUM-CASE engine-adapter normalization** (Phase 1) —
  `regulatory_objective`, `regulatory_time_horizon`,
  `regulatory_risk_rating`, `marital_status` now case-normalize
  before engine consumption. Real-PII Bedrock outputs
  capitalized values; the engine `Literal` validators were
  rejecting silently before this fix.
- **PII leak class** (Phase 2) — 11+ sites scrubbed across
  `views.py`, `preview_views.py`, `review_processing.py`.
  New `web/api/error_codes.py` is the single source of truth
  for exception → structured `failure_code` mapping. Audit
  metadata records structured codes only; raw exception text
  never reaches DB columns / API response bodies / audit rows.
  CI gate `scripts/check-pii-leaks.sh` prevents regression.
  `_REDACTION_PATTERNS` extended with routing numbers, phone
  numbers, addresses.
- **Manual-entry concurrency** (Phase 3 / BUG-1) —
  `ReviewDocumentManualEntryView.post` decorated
  `@transaction.atomic` + document fetched via
  `select_for_update()`. Concurrent advisor calls now
  serialize cleanly.
- **Reconcile-enqueue ordering** (Phase 3 / REC-1) —
  `process_document` wraps fact bulk_create + FACTS_EXTRACTED
  state save + enqueue_reconcile in one atomic block.
  Eliminates the "advisor sees stuck state forever if enqueue
  fails after job COMPLETED" friction class.
- **Confidence floor over-aggressive cap** (Phase 4
  hardening) — refined `_cap_fact_confidence` to
  `min(rank+1, 3)` semantics. Low classification floors HIGH
  to MEDIUM but doesn't collapse medium to low.
- **Per-doc-type prompt narrowed extraction under
  multi_schema_sweep** (Phase 4 hardening) — dispatcher now
  routes to `generic.build_prompt` when classification route
  is `multi_schema_sweep`, regardless of `document_type`.

### Audit

- 50+ user-locked decisions documented in
  `docs/agent/decisions.md`.
- 8+ commits past `f5f2519` baseline this pilot wave.
- Tests: 362 baseline → **422** (+60 net new) with full gate
  green per phase. Phase 9 will add Hypothesis property suites
  + concurrency stress + edge cases + migration rollback +
  100% coverage gate.
- Phase 7 R10 partial sweep against 12 real-PII docs: total
  365 → 215 facts (−41% recall) with canon §9.4.5
  quality wins (eliminated ~40 hallucinated section paths +
  2 defaulted facts; cut inferred-fact count from ~52 to ~16).
  Trade-off accepted by user; Phase 9 plans the post-pilot
  recovery iteration.

### Deferred to Phase 9 (post-pilot)

- Fact-quality iteration to recover legitimate recall in the
  −41% without re-introducing hallucinations.
  See `docs/agent/phase9-fact-quality-iteration.md`.

### Deferred to a later release

- Phase 5b polish (5b.3 inline failed-doc CTAs,
  5b.4 DocDropOverlay improvements, 5b.5 DocDetailPanel
  slide-out, 5b.7 ClientPicker pagination, 5b.8
  session-interruption recovery, 5b.10/11 FactOverride
  end-to-end UI, 5b.12/13 bulk + defer conflict UI).
- Phase 5c UX spec docs.
- Phase 6 Hypothesis + concurrency stress + factory_boy +
  Vitest unit tests + edge-case scenarios + per-migration
  rollback tests + 100% coverage gate.
- Phase 6.9 perf budget gate (P50 < 250ms / P99 < 1000ms).

These ship in subsequent sub-sessions before the 2026-05-08
release.
