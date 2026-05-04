# MP2.0 Session State

**Last updated:** 2026-05-04 PM (sub-session #5 ADDENDUM — real-PII validation done after user pushback + authorization; A6.11 partial / A6.15 latency probe done; visual-verification 32/32; only locked #100 real-Chrome smoke remains as user manual step)
**Branch:** `feature/ux-rebuild` (24 commits past origin; user pushes Mon morning)
**HEAD:** `b48fa1b` (post-tag close-out + 2 baselines regenerated for stability). Tag `v0.1.2-engine-display` at `e5cd859` (testing-frozen point; subsequent commits are docs + baseline-stability fix). Tags: `v0.1.0-pilot` + `v0.1.1-improved-intake` + **`v0.1.2-engine-display`**
**Phase:** **Engine→UI Display Integration MISSION COMPLETE + REAL-PII VALIDATED.** 5 sub-sessions across 4 days; 24 commits past baseline `081cfc8`; tag `v0.1.2-engine-display` cut. **Real-PII validated post-tag** (user authorization received): Seltzer 5/5 + Weryha 5/5 + Niesner 12/13 reconciled + workspace labels matched to visual-verification expectations. **All 32/32 visual-verification PASS** (was 24/32 pre-restore). 24/24 cross-browser. 9/9 demo dress rehearsal API latency steps within budget (trigger steps 516-541ms vs 10s budget). A6.11 PARTIAL: real-PII upload+drain pipeline validated; auto-trigger fire on Niesner COMMIT NOT exercised (42 conflicts + 3 missing sections require advisor manual resolution before construction-readiness; commit-bypass would violate locked engine-ready discipline). The auto-trigger code path is data-shape-agnostic + comprehensively tested on synthetic Sandra/Mike. **ONLY remaining gap: locked #100 real-Chrome smoke** — user manual step (5-10 min in actual Chrome before push; procedure documented in handoff entry). 5 sub-sessions span: 111 locked decisions migrated to `docs/agent/decisions.md` "Engine→UI Display Integration (2026-05-03/04)" section per locked #91; plan file `~/.claude/plans/i-want-you-to-jolly-beacon.md` + `docs/agent/engine-ui-display-starter-prompt.md` DELETED per locked #11+#42 lifecycle. Auto-memory file at `project_engine_ui_display.md`; MEMORY.md updated with new "START HERE" pointer. Sub-session #5 specifically: A6.14 code-reviewer dispatched on cumulative diff `081cfc8...HEAD` — surfaced + fixed 1 BLOCKING (PII-leak via `str(exc)` in ReviewedStateNotConstructionReady handler, would have persisted account-id-bearing text in immutable audit rows forever) + 2 CRITICAL (`latest_portfolio_failure.reason_code` was reading `metadata.source` instead of `metadata.failure_code` + AdvisorSummaryPanel i18n key namespace mismatch — same bug class as `6d7a4ca` Banner fix). A6.13c rollback smoke 11/11 PASS (helper-level via `override_settings(MP20_ENGINE_ENABLED=False)` + HTTP-level via APIClient with HTTP_HOST=localhost). A6 Round 3 Agent E: 8 NEW visual regression tests + 6 baseline PNGs (banner / advisor-summary single-link / advisor-summary multi-link / household-portfolio-panel / goal-route-full / household-route-full); both `--update-snapshots` AND clean re-run verified. A6.12 cross-browser: 3 NEW tests × 3 browsers = 24/24 (chromium + webkit + firefox). A6.9/A6.13/A6.13b documentation: design-system.md + CHANGELOG.md + ops-runbook.md (NEW) + pilot-rollback.md updated. **903 backend pytest passing** (was 854 baseline; +49 net new). 177 Vitest in 19 files (was 82 in 13; +95). 32 visual-verification chromium (was 24; +8 engine→UI). 24 cross-browser (chromium+webkit+firefox; +14 engine→UI). 13 foundation e2e (unchanged). All static gates green. Bundle 267.22 kB gzipped (under 290 kB per #85). Perf benchmarks: typed-skip 311us, REUSED 266ms, cold first-run 530ms — locked #56 strict P99<1000ms preserved. **DEFERRED**: A6.11 Niesner real-PII auto-trigger smoke (locked #79+#86) + A6.15 demo dress rehearsal (locked #95) — both require per-target Bedrock authorization beyond locked #34's `reset-v2-dev.sh --yes` pre-authorization; permission system correctly denied real-PII uploads. Synthetic auto-trigger comprehensively validated (903 backend + 11/11 rollback smoke); deferral does not block tag or pilot launch on the technical side. **NEXT**: user reviews + pushes Mon morning. Optional pre-push validation: A6.11 + A6.15 with explicit real-PII upload authorization. Pilot launch Mon 2026-05-08. **PRE-Engine→UI HISTORICAL STATE:** 5 commits past sub-session #3 close-out (`46f37e3`); 17 commits past sub-session #1 entry baseline (`081cfc8`). Round 1 Agent A: 3 Hypothesis property suites (~520 LoC; +13 tests pinning auto-trigger idempotency + audit metadata invariants per locked #99 + workspace trigger gate per locked #27). Round 1 Agent B: 7 Vitest test files (~1693 LoC; +95 tests; mockHousehold byte-for-byte match per locked #55 to live `/api/clients/hh_sandra_mike_chen/` payload). REAL PRODUCTION BUG caught + fixed by Agent B (`6d7a4ca`: RecommendationBanner i18n keys at `goal.X` should have been `routes.goal.X`; production users would have seen literal i18n keys without this fix per locked #X.10 verification protocol). Round 2 Agent C: concurrency stress (4 workspace triggers + skip path) + RBAC matrix (12 cells for 4 new endpoints) + connection pool capacity test per locked #80+#102 (~883 LoC; +19 tests). Round 2 Agent D: perf benchmarks (3 new with realistic per-scenario budgets per locked #56) + full advisor lifecycle integration test per locked #96 + pre-A2 compat per locked #97 + HouseholdDetail JSON shape snapshot per locked #101 (~828 LoC; +7 tests). Both agent stalls (Round 1 Agent A + Round 2 Agent C) at 10min watchdog were verification-phase only; files complete + correct on disk; main thread #X.10 verification passed. 882 backend pytest in isolation post-Round-1 (was 869 baseline; +13 from Hypothesis); +26 from Round 2 (~913 backend pytest passing in isolation across all sub-session #4 files). 177 Vitest in 19 files (was 82 in 13; +95 from Agent B). Foundation e2e 13/13 (unchanged). All static gates green at HEAD: ruff/format/typecheck/lint/build/vocab/PII/OpenAPI/migrations. Bundle 267.21 kB gzipped (under 290 kB threshold per #85). Perf benchmarks: typed-skip 311us, REUSED 266ms, cold first-run 530ms — all within budget; locked #56 strict P99<1000ms preserved. Pre-existing test-isolation flake (concurrency_stress + migration_rollbacks interaction) documented in handoff entry; per-file isolation runs are reliable. **NEXT: sub-session #5** (A6 Round 3 visual regression baselines via Agent E per locked #82 + A6.9 design-system + A6.10 tag bump v0.1.2-engine-display + A6.11 Niesner real-PII smoke per locked #79+#86 + A6.12 cross-browser + A6.13 CHANGELOG/ops-runbook + A6.13c rollback smoke per locked #103 + A6.14 code-reviewer subagent dispatch on full sub-session #1-#4 diff + A6.15 demo dress rehearsal per locked #95+#88 + A6.16 close-out: decisions migration per locked #91 + delete starter prompt + cumulative ping). Plan: `~/.claude/plans/i-want-you-to-jolly-beacon.md` (111 locked decisions). Sub-session #5 boots from `docs/agent/engine-ui-display-starter-prompt.md` (1584 lines; full mission reference). Demo Mon 2026-05-04 TODAY; pilot launch Mon 2026-05-08. Final tag: `v0.1.2-engine-display` at A6.10. **PRESERVED HISTORICAL STATE:** A0 pre-flight green (983 tests at baseline `081cfc8`); A0.2 latency probe locked SYNC-INLINE (Sandra/Mike P99=258ms · medium-stress P99=239ms · large-stress P99=235ms; all under 1000ms threshold per locked #56). A1 Sandra/Mike refreshed (RiskProfile anchor=22.5/score=3/Balanced + 7 canonical sh_* funds + advisor pre-ack disclaimer v1 + tour). A2a 5 typed exceptions + `_trigger_portfolio_generation` + `_trigger_and_audit` + `_trigger_and_audit_for_workspace` + 4 trigger points wired (review_commit / wizard_commit / override / realignment) + latest_portfolio_failure SerializerMethodField. Tests: 866 backend passed (was 854 baseline; +4 A1 smoke + +8 A2a auto-trigger). All static gates clean. Engine probe live: 200/314ms wall (REUSED path). **NEXT: sub-session #2** (A2b 4 workspace-level triggers + A2c ~50 test updates + A3a backend moves preview; estimated 5-7 hr per #92). Halt-and-flush gate per locked #46 met. Plan: `~/.claude/plans/i-want-you-to-jolly-beacon.md` (111 locked decisions). Demo Mon 2026-05-04; pilot launch Mon 2026-05-08. Final tag: `v0.1.2-engine-display` at A6.10.

**Pre-mission status (preserved as historical context — superseded by Engine→UI work):** 8 commits past `448b281` this session. Phase 7 R10 sweep across 12 real-PII docs (Seltzer 5 + Weryha 5 + Wurya 2) post-Phase-4-fixes: total 365 → 215 facts (−41% recall) but eliminates ~40 hallucinated section paths + 2 defaulted facts (canon §9.4.5 wins) + cuts inferred-fact count from ~52 to ~16. Quality up, quantity down — user accepted the trade-off + asked for Phase 9 iteration. `docs/agent/r10-sweep-results-2026-05-02.md` captures per-doc diff. `docs/agent/phase9-fact-quality-iteration.md` plans the post-pilot recovery (10 alternatives canvassed; recommended layered approach combining permissive base + strict per-type + inferred-with-evidence-validation + empirical advisor-productivity measurement). This session shipped 5 commits past `448b281`: Phase 4 Bedrock tool-use (HEAD 7a2e252), Phase 4.5 OpenAPI codegen + drift gate (413fd02), Phase 5a Conflict-resolution endpoint + ConflictPanel (2b28220), Phase 5b.1+5b.6 PilotBanner + Feedback model + WelcomeTour with server-side ack (288c3e7), Phase 5b.2/5b.7/5b.9/5b.14 WorkerHealthBanner + polling backoff + ConfidenceChip + axe-core + pilot-features-smoke spec (e952c61). Tests: 362 baseline → 420 (+58 net new). Remaining 5b sub-phases not yet built: 5b.3 inline failed-doc CTAs, 5b.4 DocDropOverlay improvements, 5b.5 DocDetailPanel slide-out, 5b.7 ClientPicker pagination, 5b.8 session-interruption recovery, 5b.10/11 FactOverride end-to-end, 5b.12/13 bulk + defer conflict UI, 5b.demo-check. Plus 5c, 6, 6.9, 7, 8. R7 done + post-R7 hardening (3.A/B/E) + R10 sweep 55/55 + R8 methodology + demo prep was DONE per prior sessions. The 2026-05-02 session re-audited at HEAD `f5f2519`, found 8 prior findings closed + 8 still open + 2 new (ENUM-CASE demo-blocker, BUG-1 atomicity), planned 9 phases via 12 user-interview rounds (~50 locked decisions), and executed Phases 0-3:
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
