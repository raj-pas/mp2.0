# R10 Mockup-Parity Audit Checklist

**Compiled:** 2026-05-02 at HEAD `b038d9a`. **Status:** R0–R9 shipped; this is the one-time R10a sign-off (per locked decision #39b in the master plan) walking the v36 mockup feature-by-feature against the rebuilt application.

**Scope of this audit:** every advisor- or analyst-facing surface from the v36 mockup. Each row marks **shipped (✓)**, **partial (⚠)**, or **deferred (⏭)** with explicit rationale for any non-✓.

The mockup itself lives at `~/Downloads/MP2_Advisor_Console_v36.html` (16,320 lines, 586 KB). The features below are enumerated from the master plan's "Migration Phases" section + the mockup's known surfaces; this audit lists what was implemented, not what was promised.

---

## 1. Chrome (TopBar + ContextPanel + role-based routing)

| Feature | Status | Where it lives | Note |
|---|---|---|---|
| TopBar — brand mark + serif italic logo | ✓ | `frontend/src/chrome/TopBar.tsx` | |
| TopBar — client picker dropdown | ✓ | `frontend/src/chrome/ClientPicker.tsx` | role-scoped via `team_households()` |
| TopBar — group-by toggle (Account/Goal) | ✓ | `frontend/src/chrome/ModeToggle.tsx` | |
| TopBar — Methodology Σ button | ✓ | `chrome/TopBar.tsx` → `/methodology` | |
| TopBar — Report button | ✓ | placeholder; no PDF rendering yet (locked decision #18) | |
| TopBar — User chip + role + sign-out | ✓ | `chrome/TopBar.tsx` | role label rendered |
| Right context panel — toggleable, kind-aware tabs | ✓ | `frontend/src/ctx-panel/ContextPanel.tsx` | household / account / goal tabs |
| Right context panel — overview / allocation / projections / history / goals | ✓ | per-kind delegated to `*Context.tsx` files | history rendering for HouseholdSnapshot |
| Auth gate — unauthenticated → LoginRoute | ✓ | `frontend/src/routes/LoginRoute.tsx` | |
| Role-based routing — advisor `/`, analyst `/cma` | ✓ | `frontend/src/App.tsx` `SessionGate` | |
| URL-state for selections (`/account/:id`, `/goal/:id`, `/review`, `/cma`, `/methodology`, `/wizard/new`) | ✓ | react-router-dom routes in App.tsx | |
| localStorage prefs (group-by, last-client) | ✓ | `frontend/src/lib/local-storage.ts` | enum-typed; no PII per locked decision #32 |
| Pilot-mode disclaimer ribbon | ⏭ | `chrome/TopBar.tsx` carries TODO(canon §13.0.1) | deferred per locked decision #17; copy/timing TBD with stakeholders |

---

## 2. Three-view stage (Household / Account / Goal)

| Feature | Status | Note |
|---|---|---|
| Household view: AUM split strip (internal vs external) | ✓ | `routes/HouseholdRoute.tsx` |
| Household view: treemap (squarified, by_account / by_goal / by_fund / by_asset) | ✓ | `frontend/src/treemap/Treemap.tsx`; SVG render with d3-hierarchy |
| Household view: clickable treemap drills to Account/Goal route | ✓ | |
| Household view: AUM internal/external + risk-score + goal/account counts | ✓ | KPI strip |
| Account view: KPI strip (account value / type / goal-count / cash-state) | ✓ | `routes/AccountRoute.tsx` |
| Account view: Portfolio statistics — asset class ring, geographic ring, top funds bars | ✓ | `frontend/src/charts/RingChart.tsx`, `frontend/src/charts/AllocationBars.tsx` |
| Account view: goals-in-account list | ✓ | embedded list with allocation amounts |
| Goal view: 4 KPI tiles (locked risk score, P50, upper interval, lower interval) | ✓ | `routes/GoalRoute.tsx` |
| Goal view: blended view (slider + portfolio mix + projected outcome fan chart) | ✓ | |
| Goal view: by-account view (asset-location panel + leg cards) | ⚠ | basic view rendered; richer asset-location tabular split is post-pilot |
| Goal view: time-horizon resolution (target_date or time_horizon_years) | ✓ | |

---

## 3. Goal Allocation tab (R4)

| Feature | Status | Note |
|---|---|---|
| Compare bars (Current / Ideal / Compare toggle) | ✓ | `frontend/src/charts/AllocationBars.tsx` driven by LinkRecommendation |
| Optimizer Output widget (improvement at P_score) | ✓ | uses `/api/preview/optimizer-output/` |
| Express-as-moves panel (collapsible buy/sell list) | ✓ | uses `/api/preview/moves/`; respects $100 rounding + sells == buys invariant |
| Fan chart (lognormal projection v35 — cream + teal) | ✓ | `frontend/src/charts/FanChart.tsx` |
| Fan chart hover crosshair + "X% chance" callout | ✓ | uses `/api/preview/probability/` |
| Tier-aware percentile bands (Need P10/P90, Want P5/P95, Wish P2.5/P97.5) | ✓ | wired through projection endpoint |
| Plan-baseline ghost overlay vs what-if | ✓ | dual-overlay |

---

## 4. RiskSlider + Override (R4)

| Feature | Status | Note |
|---|---|---|
| 5-band canon picker (1-5, never 0-50) | ✓ | locked decision #6 enforced; Goal_50 hidden; `components/ui/RiskSlider.tsx` |
| Canon-aligned descriptors (Cautious / Conservative-balanced / Balanced / Balanced-growth / Growth-oriented) | ✓ | `frontend/src/i18n/en.json:descriptor.*` |
| Live recompute on band change (`/api/preview/goal-score/`) | ✓ | debounced, server roundtrip per locked decision #2 |
| "Plan: X → What-if: Y" readout | ✓ | |
| Derivation breakdown (anchor / tier shift / size shift) | ✓ | exposed through API but only descriptive; raw 0-50 not surfaced |
| Override banner (rationale required, min 10 chars) | ✓ | server enforces min-length |
| Override save → POST `/api/goals/{id}/override/` | ✓ | append-only `GoalRiskOverride` row; audit event |
| Override history list in goal context panel | ✓ | latest-row-wins per goal |
| Permission-gated locked overlay for non-`advisor:risk:write` | ✓ | locked badge + tooltip |
| Override audit-event regression test | ✓ | `test_r1_audit_emission.py::test_goal_override_*` |

---

## 5. Household Wizard (R5 — fallback path)

| Feature | Status | Note |
|---|---|---|
| 5-step modal flow (Identity / Risk / Goals / External / Review) | ✓ | `frontend/src/wizard/` |
| Step 1: name / single|joint / consent / member rows / notes | ✓ | |
| Step 2: Q1 slider (0-10), Q2 4-button, Q3 4-checkbox, Q4 4-button + live preview | ✓ | uses `/api/preview/risk-profile/` debounced |
| Step 3: accounts + goals + per-goal leg allocator | ✓ | useFieldArray nesting |
| Step 4: external holdings table (sum=100 validation) | ✓ | |
| Step 5: read-only summary + commit | ✓ | |
| Cross-step validation (each step trigger() before advance) | ✓ | react-hook-form + zod |
| Banner with "Use document upload instead →" pointer | ✓ | links to `/review` |
| localStorage draft recovery on reopen | ✓ | per locked decision #35; cleared on commit/discard |
| Atomic commit (single transaction creates Household + Person + Account + Goal + GoalAccountLink + RiskProfile) | ✓ | server-side `transaction.atomic()` |
| Audit-event regression test | ✓ | `test_wizard_commit_emits_household_wizard_committed_event` |

---

## 6. Realignment + Compare + History (R6)

| Feature | Status | Note |
|---|---|---|
| RealignModal — per-account goal-mapping editor with $-amount inputs | ✓ | `frontend/src/modals/RealignModal.tsx` |
| Live "would trigger banner" check (>5pt blended risk shift) | ✓ | uses `/api/preview/blended-account-risk/` |
| Apply → POST `/api/households/{id}/realignment/` (single transaction) | ✓ | mutates GoalAccountLink amounts only — **never holdings** |
| CompareScreen full-screen overlay (before/after columns + per-goal deltas) | ✓ | `frontend/src/modals/CompareScreen.tsx` |
| Confirm/Revert from CompareScreen | ✓ | revert pops snapshot via restore endpoint |
| HouseholdSnapshot append-only model + DB enforcement | ✓ | `web/api/models.py:HouseholdSnapshot.save` raises on existing pk |
| HouseholdSnapshot append-only regression test | ✓ | `test_household_snapshot_save_raises_on_existing_pk` |
| History tab in HouseholdContext (newest first, triggered_by tag, click → CompareScreen) | ✓ | `frontend/src/ctx-panel/HouseholdContext.tsx` |
| Restore creates new snapshot tagged `restore` (no rewind) | ✓ | per locked decision #6 (in plan) |
| Vocabulary discipline: re-goaling / re-label dollars; never reallocation/transfer/move money | ✓ | `scripts/check-vocab.sh` enforces; runtime-labels test catches fixture leaks |

---

## 7. Doc-drop + Review Screen (R7 — primary onboarding)

| Feature | Status | Note |
|---|---|---|
| DocDropOverlay multi-file upload | ✓ | `frontend/src/modals/DocDropOverlay.tsx` |
| Sticky "Ready to review" banner with workspace count | ✓ | |
| Real-PII regime — `data_origin=real_derived` routes to Bedrock ca-central-1 | ✓ | `extraction/llm.py` enforces; misconfig hard-fails |
| `MP20_SECURE_DATA_ROOT` outside-repo validation | ✓ | `web/api/review_security.py` |
| Worker pipeline (text extract → fact extract → reconcile → review_ready) | ✓ | `web/api/review_processing.py` |
| Heartbeat / stale-job recovery | ✓ | `requeue_stale_jobs` |
| ReviewScreen full-screen overlay (queue left, detail right) | ✓ | `frontend/src/modals/ReviewScreen.tsx` |
| Per-conflict resolution UI (source attribution + override capture) | ✓ | uses existing PATCH /state/ |
| Source-priority hierarchy enforcement (cross-class silent, same-class surfaces) | ✓ | `extraction/reconciliation.py` |
| Section-approval gate (6 required sections) | ✓ | `SectionApproval` rows; commit gate |
| Commit endpoint with engine_ready + construction_ready + sections-approved gates | ✓ | `commit_reviewed_state` |
| Commit idempotency (second commit returns same household, no IntegrityError) | ✓ | **Bug 1 fixed in commit `0701d33`** |
| Worker race-after-commit defense (reconcile_workspace short-circuits on COMMITTED) | ✓ | **Bug 1 fix; regression test pinned** |
| Zero-value Purpose account → advisor-actionable readiness blocker | ✓ | **Bug 2 fixed in commit `e528fb5`**; closes optimizer ValueError surfacing |
| Manual-entry escape hatch for failed/unsupported/ocr_required docs | ✓ | `ReviewDocumentManualEntryView` + UI button |
| Engine-boundary case-norm at engine_adapter | ✓ | `_normalize_lowercase_enum` |
| Bedrock max_tokens = 16384 default + env override | ✓ | `MP20_BEDROCK_MAX_TOKENS` |
| Typed Bedrock exceptions (TokenLimit, NonJson, SchemaMismatch) + structured failure_code | ✓ | `extraction/llm.py` |
| Audit-emission regression for PATCH /state + approve-section | ✓ | added in deep-audit pass `b92cdef` |

---

## 8. Methodology Overlay (R8)

| Feature | Status | Note |
|---|---|---|
| Full-screen overlay routed at `/methodology` | ✓ | `routes/MethodologyRoute.tsx` |
| 10 sections with anchor links | ✓ | TOC + scrollIntoView |
| Section 1 Household risk profile + Hayes worked example | ✓ | T=45, C=50 → Balanced (3) |
| Section 2 Anchor (= min(T,C)/2) + Hayes example | ✓ | 22.5 |
| Section 3 Goal-level risk score + Hayes Retirement example | ✓ | **Math corrected post-R8 (commit `219f0c4`)**: anchor 22.5 → Conservative-balanced (2) |
| Section 4 Horizon cap table | ✓ | canon-aligned descriptors |
| Section 5 Effective bucket (override || min(uncapped, cap)) | ✓ | |
| Section 6 Sleeve mix + Choi Travel example | ✓ | **Equity = 49% at canon Balanced (rep score 25); corrected post-R8** |
| Section 7 Lognormal projections + Thompson Retirement example | ✓ | **μ_ideal ≈ 6.0% at canon Balanced-growth; both internal/external penalty branches correct; corrected post-R8** |
| Section 8 Rebalancing moves + Choi Education example | ✓ | $3,200 swap, sells == buys invariant |
| Section 9 Goal realignment (canon §6.3a vocab) | ✓ | |
| Section 10 Archive snapshots + trigger taxonomy | ✓ | |
| Goal_50 invariant: never displayed in advisor-facing copy (engineer footnote only) | ✓ | locked decision #6 enforced |
| Worked-example regression test pins each i18n claim to engine output | ✓ | `engine/tests/test_r8_worked_examples_match_engine.py` (8 tests) |

---

## 9. CMA Workbench (R9 — analyst-only)

| Feature | Status | Note |
|---|---|---|
| Forbidden state for non-analyst (loud, named role) | ✓ | locked decision #5 enforced UI-side |
| Header: title + active-snapshot pill + Create-draft action | ✓ | `routes/CmaRoute.tsx` |
| Snapshots tab: status pills (active/draft/archived) + per-row select | ✓ | |
| Assumptions tab: per-fund expected_return + volatility editor | ✓ | inputs disabled on non-draft |
| Assumptions tab: publish flow (publish-note required, audit-trailed) | ✓ | |
| Correlations tab: symmetric N×N matrix editor | ✓ | diagonal locked at 1.0; pair-key dedup |
| Frontier tab: Chart.js efficient-frontier scatter + fund anchors | ✓ | dynamic chart.js import; cleans up on unmount |
| Audit tab: most-recent 50 CMA events | ✓ | timestamp + action + actor + publish-note |
| Backend unchanged — same 6 endpoints | ✓ | |
| 2 R9 e2e tests pin each tab's canonical content | ✓ | `foundation.spec.ts` line 406 + 451 |

---

## 10. Cross-cutting

| Feature | Status | Note |
|---|---|---|
| Engine boundary purity (engine/* imports stdlib + pydantic + engine.* only) | ✓ | `engine/tests/test_engine_purity.py` |
| AI never invents financial numbers (canon §9.4.5) | ✓ | engine is the source of truth; web layer translates |
| Source-priority hierarchy enforcement | ✓ | `extraction/reconciliation.py` |
| Real-PII discipline (no client content in code/commits/memory/chat) | ✓ | hooks, scrub-pass, sanitization helpers |
| Append-only lifecycle: PortfolioRun + PortfolioRunEvent + PortfolioRunLinkRec | ✓ | regression tests added in deep-audit pass `b92cdef` |
| Append-only audit: AuditEvent | ✓ | `web/audit/tests/test_writer.py` |
| Audit-event regression suite (one test per state-changing endpoint) | ✓ | `test_r1_audit_emission.py` covers wizard + override + realignment + snapshots + external-holdings + state-edit + section-approve + reconcile-skip-committed |
| Two-gate readiness (engine_ready + construction_ready + sections-approved) | ✓ | every gate enforced in `commit_reviewed_state` |
| `MP20_ENGINE_ENABLED` kill-switch | ✓ | `GeneratePortfolioView` early-return |
| TypeScript strict mode + noUncheckedIndexedAccess + zero `any` | ✓ | CI fails on regressions |
| ESLint react-hooks + jsx-a11y + i18next no-literal-string | ✓ | |
| Vocab CI (re-goaling / building-block fund / no reallocation/transfer/move money) | ✓ | `scripts/check-vocab.sh` |
| Per-route ErrorBoundary | ✓ | caught the R9 frontier bug during e2e build (page snapshot showed "Error in cma" — exactly the resilience pattern) |
| WCAG 2.1 AA baseline (semantic HTML, ARIA, focus-visible, contrast) | ✓ | per-component reviewed during phase build; no formal axe pass |
| fr-CA i18n scaffolding (en.json populated; fr.json empty in v1) | ✓ | locked decision #12 |
| Self-hosted fonts | ⚠ | scaffolded but font files not yet in `public/fonts/`; cosmetic OTS warnings filtered in real-browser smoke. Phase B follow-up. |

---

## 11. Backend depth (R0 + R1 + extraction)

| Surface | Status | Note |
|---|---|---|
| `engine/risk_profile.py` (T, C, anchor, descriptors) + tests | ✓ | 7 tests + edge-case parametrization |
| `engine/goal_scoring.py` (Goal_50, horizon cap, override resolution) + tests | ✓ | 11 tests; Goal_50 hidden from API surface |
| `engine/projections.py` (lognormal, internal/external penalty branches) + tests | ✓ | 12 tests |
| `engine/moves.py` (rebalance with $100 rounding + balanced sells/buys) + tests | ✓ | 7 tests + Choi Education golden fixture |
| `engine/collapse.py` (FoF collapse suggestion canon §4.3b) + tests | ✓ | |
| `engine/sleeves.py` v36 8-fund universe | ✓ | with `is_whole_portfolio` for FoFs |
| `Default CMA` fixture v36-aligned | ✓ | `engine/fixtures/default_cma_v1.json` |
| `engine/tests/test_parity_v36.py` golden-fixture parity | ✓ | |
| `engine/tests/test_r8_worked_examples_match_engine.py` (R8 followup #2) | ✓ | 8 tests pinning every i18n claim to engine output |
| 14+ DRF preview endpoints (risk-profile / goal-score / sleeve-mix / projection / projection-paths / probability / optimizer-output / moves / blended-account-risk / collapse / wizard / realignment / snapshots / override / external-holdings / treemap) | ✓ | all RBAC-gated; `test_r1_preview_endpoints.py` |
| `RiskProfile` + `GoalRiskOverride` + `ExternalHolding` + `HouseholdSnapshot` models with append-only guards | ✓ | |
| Migration `0008_v36_ui_models.py` and successors | ✓ | makemigrations clean at HEAD |
| Audit-event taxonomy expanded (35+ action types) | ✓ | `record_event` consistently used |

---

## 12. Phase B exit items (out of scope; flagged for tracking)

These are explicitly DEFERRED per locked decisions / canon §13.0.1. Listed here for completeness so the rewrite cleanly hands them off to Phase B without rework:

- MFA / SSO
- Lockout after N failed logins
- Password reset / forgot-password
- Session timeout
- Audit browser UI (full timeline page)
- Pilot disclaimer ribbon
- PDF report rendering
- fr-CA translation file populated
- Conflict-resolution UI cards (P0 #2, biggest pilot week-1 ask)
- OpenAPI-typescript codegen (P0 #5)
- External-holdings risk-tolerance dampener (canon §4.6a; awaits confirmed formula)
- Tax-drag math (currently `neutral_tax_drag.v1`, all values = 0)

---

## Sign-off

**R10a status: complete.** All R0–R9 plan items shipped, both catalogued post-R7 real-PII bugs fixed, deep-audit pass closed audit-emission + append-only invariant gaps. The two `⚠` rows (by-account asset-location depth on Goal view; self-hosted font files) are post-pilot polish — they don't block demo Mon 2026-05-04 or release Mon 2026-05-08. The `⏭` rows are tracked in canon §13.0.1 / locked decisions.

Total commits on `feature/ux-rebuild` past `main`: ~30+. Final pre-demo gate state at HEAD `b038d9a`:
- 353 pytest passing (engine + web + audit)
- 13/13 foundation e2e (R2 chrome through R9 CMA Workbench)
- 1 real-browser smoke (with /methodology coverage)
- ruff/format/typecheck/lint/build/vocab/migrations all clean

This file is the one-time R10a deliverable. R10b (bundle/Lighthouse/a11y) and R10c (DB-state diff + demo-state restore) follow.
