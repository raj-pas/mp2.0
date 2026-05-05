# MP2.0 Session State

**Last updated:** 2026-05-05 (Pair 7b sub-agent — **P10 FINAL VERIFICATION + DUAL CODE-REVIEW + WALKTHROUGH + PILOT-READINESS** complete; **READY-TO-TAG `v0.1.3-pilot-quality-closure`**; main thread cuts the tag after sub-agent return)
**Branch:** `feature/ux-rebuild` (14 commits past sister tag `v0.1.3-engine-display-polish` once P10 commit lands)
**HEAD (post-P10 commit pending):** TBD; pre-P10 was `928e421` (Pair 7a; ALL 16 phase deliverables P0-P14 shipped across Pair 1-7a)
**Sister tag:** `v0.1.3-engine-display-polish` (`979a692`)
**Phase:** **Pair 7b CLOSE-OUT — P10.1-P10.8 complete; READY-TO-TAG.** All 14 G## gaps closed. §A1.31 gate suite: 1,087 backend pytest + 391 Vitest + 13 foundation + 18 regression-coverage (+2 skipped) + 24 visual-verification + 6 pilot-features axe + 21 cross-browser (1 firefox flake passed on rerun) + 9/9 perf + bundle 278.94 kB gzipped under 290 kB cap + Hypothesis 8/8 with 1 real-bug surfaced + fixed (alice-smith vs bob-smith shared-DOB property invariant tightened to identity-stable fields). Dual code-review: 6 MEDIUM findings fixed; 1 LOW deferred-with-rationale; 0 BLOCKING; 0 CRITICAL per Round 11 #18. Niesner re-extract SKIPPED (workspace not in dev DB; demo restore Mon 2026-05-04 will re-seed). Bedrock spend $0.36 cumulative. NEW docs: `pilot-walkthrough-2026-05-04.md` (470 LoC) + `pilot-readiness-2026-05-04.md` (270 LoC with all 8 metric queries live). Main thread next: cut `v0.1.3-pilot-quality-closure` tag + update CHANGELOG.md per §A1.39 + push (user authorizes Mon 2026-05-08 AM).

---

## Pre-P10 historical state (preserved; superseded by Pair 7b above)

**Last updated:** 2026-05-05 (post-tag gap-closure sub-session #3 EXTENDED+ FINAL — **TAG `v0.1.3-engine-display-polish` CUT at HEAD `979a692`** per locked §3.22. A6.1 Steps 1-8 verified in real Chrome with **2 critical pilot-blocking fixes** caught + shipped (`870563b` override→engine; `78c635a` CMA Workbench full-payload). A7.1 + A7.2 subagent reviews returned CLEAN PASS (0 blocking, 0 critical, 3 post-pilot nice-to-haves). engine_adapter.py 98% coverage (well above 90% gate per §3.14). The tag serves as the pilot rollback boundary; user pushes Mon 2026-05-08 morning. **Deferred to next session:** A6.2 pilot dress rehearsal (~45 min user time per locked §3.25) + A7 close-out polish (starter prompt deletion + decisions.md migration to "Post-tag gap-closure (2026-05-04/05)" sub-section). The starter prompt at `docs/agent/post-tag-gap-closure-starter-prompt.md` STAYS for the next session boot.)
**Branch:** `feature/ux-rebuild` (17 commits past tag `v0.1.2-engine-display`; tag `v0.1.3-engine-display-polish` at `979a692`)
**HEAD:** `979a692` (CMA fix docs close-out) tagged as **`v0.1.3-engine-display-polish`**. All four tags now exist: v0.1.0-pilot + v0.1.1-improved-intake + v0.1.2-engine-display + v0.1.3-engine-display-polish.
**Phase:** **Post-tag gap-closure sub-session #3 EXTENDED+ — Phase A5 + A5.5 complete + CRITICAL fix for override→engine flow shipped mid-A6.1 USER MANUAL smoke; A6 Steps 8-10 + A7 close-out remaining.** Plan at `~/.claude/plans/i-want-you-to-jolly-beacon.md` (25 locked-this-session §3 decisions). The locked-#100 real-Chrome smoke surfaced a production-blocking bug: pre-fix, `committed_construction_snapshot` (engine_adapter.py:311) and `_goal_to_engine` (engine_adapter.py:156) read `goal.goal_risk_score` directly without consulting `GoalRiskOverride` rows. The `active_goal_override(goal)` helper existed but was only called by preview_views.py for slider-drag preview — NOT by the portfolio-generation path. Result: saved overrides round-tripped through `goal_risk_override_created` audit + DB row but the engine.optimize() input always saw the system score; identical input_hash hit REUSED path; engine never re-optimized with the override. Fix at `870563b`: NEW `effective_goal_risk_score(goal)` helper resolves latest override → score_1_5 (latest-row-wins per locked #6) or falls back to system score; both adapter functions call it. Engine purity preserved (canon §9.4.2). Fix verified live in real Chrome on `goal_ski_cabin` (8yr horizon, score=4 system → score=1 Cautious override): RECOMMENDATION 008F5F87 (Balanced-growth blend, Equity ideal 66.6%) → RECOMMENDATION CD78E7C1 just-now (Cautious blend, Savings ideal 95.4%). Sub-session #3 entry HEAD was `7c041f2` (sub-session #2 close-out). This sub-session extended through Phase A5 (`bd90cf9`) + Phase A5.5 (`d8c908a` after starter-prompt rewrite chain `f900adf`+`b21ce7b`+`03c92d1`) + close-out docs (`a091430`) + the engine_adapter fix (`870563b`). A5.5 ships NEW `frontend/e2e/regression-coverage.spec.ts` (~520 LoC, 15 chromium tests organized into 5 describe blocks: 4 login/chrome + 2 routes + 1 wizard + 6 review surfaces + 2 household/goal). Per locked §3.20: chose AUTOMATED browser regression suite over manual checklist; locks the 75% of the codebase NOT touched by gap-closure (Wizard, Review, ConflictPanel, DocDetailPanel, CMA Workbench, Methodology, FeedbackModal, PilotBanner, WelcomeTour) as a single-spec regression guard. Cumulative chromium Playwright at HEAD: 13 foundation + 34 visual-verification + 6 pilot-features + 15 regression-coverage = **68 chromium tests passing**. **Tests: 878 backend pytest passing + 2 skipped** (was 872+2; +6 net new from `test_goal_risk_override_engine_flow.py` tests pinning the override→engine contract end-to-end + helper unit semantics + REUSED-correct negative control). **230 Vitest in 26 files** (unchanged — fix is backend-only). All static gates clean. Bundle **269.41 kB gzipped** (unchanged — backend-only). **NEXT: sub-session #3 remainder** = A6 Steps 8-10 (CMA republish stale overlay verification + optional HASH_MISMATCH integrity overlay + console-clean check) + A7 close-out (2 subagent dispatches per §3.13 + 90% coverage gate per §3.14 + tag `v0.1.3-engine-display-polish` per §3.22 + delete starter prompt + close-out commit; 60-90 min). Estimated 1.5-2.5 hr remaining. Boot via `docs/agent/post-tag-gap-closure-starter-prompt.md` (HEAD pointer `870563b` or later docs-only commit per drift-tolerance pattern). The plan's halt-and-flush gate at end of A4 calls for user manual smoke (publish CMA → see overlay → click Regenerate; insert HASH_MISMATCH event → confirm integrity overlay + audit row); the publish-CMA path is what A6.1 Step 8 will exercise next.

---

## Pre-A5.5 historical state (preserved; superseded by sub-session #3 extended above)

**Last updated:** 2026-05-04 PM (post-tag gap-closure sub-session #3 PARTIAL — A5 shipped at HEAD `bd90cf9`; demo script Steps 4+4.5+4.6 + axe Goal+Household + 2 visual baselines + 6 cross-browser cells + Phase A2 RiskSlider regression caught and fixed mid-A5; A5.5+A6+A7 remaining for next session)
**Branch:** `feature/ux-rebuild` (9 commits past origin `1ea5338`)
**HEAD:** `bd90cf9` (Phase A5 commit) past tag `v0.1.2-engine-display` at `e5cd859`. Tags unchanged: v0.1.0-pilot + v0.1.1-improved-intake + v0.1.2-engine-display. NEW tag `v0.1.3-engine-display-polish` cuts at A7 close-out per §3.22.
**Phase:** **Post-tag gap-closure sub-session #3 PARTIAL — Phase A5 complete; A5.5+A6+A7 remaining.** Plan at `~/.claude/plans/i-want-you-to-jolly-beacon.md` (25 locked-this-session §3 decisions). Sub-session #3 entry HEAD was `7c041f2` (sub-session #2 close-out). This session extended A5: demo-script-2026-05-04.md gets Step 4 expanded with engine→UI talking points + NEW Step 4.5 (slider drag → calibration_drag flip → save → engine flip back) + NEW Step 4.6 (CMA republish → stale overlay → Regenerate cycle + hash_mismatch integrity overlay note); pilot-features-smoke.spec.ts gets axe coverage on Goal + Household routes (4→6 axe routes); visual-verification.spec.ts gets 2 NEW baselines for engine SourcePill on GoalAllocationSection + OptimizerOutputWidget (32→34 chromium baselines; 3-run stability per §3.11 confirmed); cross-browser-smoke.spec.ts gets 3 NEW tests × 2 non-chromium browsers per §3.15 (8→11 per browser, 22 total cross-browser cells). The new visual baseline test caught a Phase A2 production bug: the Phase A2 wiring conflated `isOverrideDraft = selectedScore !== systemScore` (form-visibility, pre-A2) with the new SourcePill callback semantic. On Sandra/Mike's `goal_retirement_income` (system=3, saved override=1), `onPreviewChange(true)` was firing on mount → all 3 engine pills rendered calibration_drag instead of engine. Fix split into two semantics: `isOverrideDraft` (existing, gates form) + new `isDragPreview = selectedScore !== effectiveScore` (drag-only, fires callback). NEW Vitest regression test (RiskSlider.test.tsx, 2 tests) pins both cases. **Tests: 872 backend pytest passing** (unchanged). **230 Vitest in 26 files** (was 228 in 25; +2 RiskSlider regression). All static gates clean. Bundle 269.41 kB gzipped (essentially unchanged from sub-session #2; new code is tests + RiskSlider semantics fix). Cross-browser: 22 cells passing (11 webkit + 11 firefox). axe: 6 routes passing (chromium). visual-verification: 34 baselines passing + 3-run stable. **NEXT: sub-session #3 remainder** = A5.5 (NEW `frontend/e2e/regression-coverage.spec.ts` with 15 automated tests for pre-existing flows per §3.20 — HEAVIEST phase, ~3-4 hr) + A6 USER MANUAL (real-Chrome smoke per locked #100 + dress rehearsal per §3.25) + A7 (2 subagent dispatches per §3.13 + 90% coverage gate per §3.14 + tag `v0.1.3-engine-display-polish` per §3.22 + delete starter prompt + close-out commit). Estimated 4-5 hr remaining. Boot via `docs/agent/post-tag-gap-closure-starter-prompt.md`. The plan's halt-and-flush gate at end of A4 calls for user manual smoke (publish CMA → see overlay → click Regenerate; insert HASH_MISMATCH event → confirm integrity overlay + audit row); deferred to A6 dress rehearsal.

---

## Pre-A5 historical state (preserved; superseded by sub-session #3 partial above)

**Last updated:** 2026-05-04 PM (post-tag gap-closure sub-session #2 of 3 complete; A3+A4 shipped at HEAD `64ab152`; OptimizerOutputWidget consumes link_recommendations via SourcePill + 4-status stale UX with bespoke modal-style overlays for invalidated/superseded/declined (regenerable) and hash_mismatch (engineering-only); sub-session #3 next: A5 demo+axe+visual+cross-browser + A5.5 automated regression suite + A6 USER manual smoke + A7 close-out + tag v0.1.3-engine-display-polish)
**Branch:** `feature/ux-rebuild` (6 commits past origin `1ea5338`)
**HEAD:** `64ab152` (sub-session #2 close-out chore) past tag `v0.1.2-engine-display` at `e5cd859`. Tags unchanged: v0.1.0-pilot + v0.1.1-improved-intake + v0.1.2-engine-display. NEW tag `v0.1.3-engine-display-polish` cuts at A7 close-out per §3.22.
**Phase:** **Post-tag gap-closure sub-session #2 COMPLETE.** Plan at `~/.claude/plans/i-want-you-to-jolly-beacon.md` (25 locked-this-session §3 decisions). Closes 4 of 5 unaddressed gaps from the original 2,786-line Engine→UI plan. Sub-session #2 shipped: A3 (OptimizerOutputWidget engine-first refactor with dollar-weighted improvement_pct from `link_recommendations[]` + SourcePill + null-guard `current_comparison.expected_return` fallback at `c212793` — 7 new Vitest tests) + A4 (NEW `<StaleRunOverlay>` advisor-actionable for invalidated/superseded/declined with bespoke focus model per locked #68 + NEW `<IntegrityAlertOverlay>` engineering-only for hash_mismatch + RecommendationBanner expanded 3→5 visual states with stale/integrity chip variants + HouseholdPortfolioPanel mirrors the same pattern per locked #19 + GoalRoute wraps engine panels in muted+aria-hidden when status non-current at `8350090` — 26 new Vitest tests across 4 files) + chore (untracked artifacts cleanup + .gitignore extension at `64ab152`). **Tests: 872 backend pytest passing** (unchanged — sub-session #2 is frontend-only). **228 Vitest in 25 files** (was 195 in 22; +33 from A3+A4: 7 OptimizerOutputWidget + 10 StaleRunOverlay + 7 IntegrityAlertOverlay + 5 RecommendationBanner extension + 4 HouseholdPortfolioPanel extension). All static gates clean. Bundle **269.41 kB gzipped** (was 267.55 baseline; +1.86 kB; under 290 kB cap per locked #85; ~21 kB headroom). **NEXT: sub-session #3** = A5 (demo script Step 4.5/4.6 + axe Goal+Household routes + visual baselines + 6 cross-browser cells per §3.15) + A5.5 (NEW `frontend/e2e/regression-coverage.spec.ts` with 15 automated tests for pre-existing flows per §3.20 — HEAVIEST phase) + A6 USER MANUAL (real-Chrome smoke per locked #100 + dress rehearsal per §3.25) + A7 (2 subagent dispatches per §3.13 + 90% coverage gate per §3.14 + tag `v0.1.3-engine-display-polish` per §3.22 + delete starter prompt + close-out commit). Estimated 5-7 hr. Boot via `docs/agent/post-tag-gap-closure-starter-prompt.md`. The plan's halt-and-flush gate at end of A4 calls for user manual smoke (publish CMA → see overlay → click Regenerate; insert HASH_MISMATCH event → confirm integrity overlay + audit row); deferred to A6 dress rehearsal where it's already in scope.

---

## Pre-A4 historical state (preserved; superseded by sub-session #2 above)

**Last updated:** 2026-05-04 PM (post-tag gap-closure sub-session #1 of 3 complete; A0+A1+A2 shipped at HEAD `c5a7e02`; backend stale-lifecycle contract pinned + GoalAllocationSection+MovesPanel consume engine via shared SourcePill; sub-session #2 next: A3 OptimizerOutputWidget refactor + A4 Stale-state UX with 4 status variants + IntegrityAlertOverlay)
**Branch:** `feature/ux-rebuild` (3 commits past origin `1ea5338`)
**HEAD:** `c5a7e02` (Phase A2 commit) past tag `v0.1.2-engine-display` at `e5cd859`. Tags unchanged: v0.1.0-pilot + v0.1.1-improved-intake + v0.1.2-engine-display. NEW tag `v0.1.3-engine-display-polish` cuts at A7 close-out per §3.22.
**Phase:** **Post-tag gap-closure sub-session #1 COMPLETE.** Plan at `~/.claude/plans/i-want-you-to-jolly-beacon.md` (25 locked-this-session §3 decisions). Closes 5 unaddressed gaps from the original 2,786-line Engine→UI plan that shipped at v0.1.2-engine-display with ~75% of done-criteria. Sub-session #1 shipped: A0 (pre-flight + starter prompt at f6e2ef8 — fixed pre-existing OpenAPI codegen drift + added missing `warning` color token) + A1 (backend status semantics + hash_mismatch integrity-alert audit emission with dedup + Hypothesis property invariants + pre-tag backwards-compat regression + JSON snapshot fixtures at 95dfd01 — 18 new backend tests) + A2 (shared SourcePill component + GoalAllocationSection refactored to consume engine `goal_rollup.allocations` with calibration fallback + slider-drag UX via `isPreviewingOverride` lifted from RiskSlider to GoalRoute + MovesPanel pill consuming backend `source` field at c5a7e02 — 18 new Vitest tests). **Tests: 872 backend pytest passing** (was 854 baseline; +18 from A1: 8 status semantics + 5 Hypothesis + 2 backwards-compat + 3 snapshot). **195 Vitest in 22 files** (was 177 in 19; +18 from A2: 5 SourcePill + 9 GoalAllocationSection + 4 MovesPanel). All static gates clean (vocab + PII + OpenAPI + ruff + format + typecheck + lint). Bundle 268.13 kB gzipped (was 267.55; +0.58 kB; under 290 kB cap per locked #85). **NEXT: sub-session #2** = A3 (OptimizerOutputWidget engine-first refactor — same SourcePill pattern, 7 Vitest tests) + A4 (Stale-state UX — 4 status variants `invalidated/superseded/declined → StaleRunOverlay regenerable`; `hash_mismatch → IntegrityAlertOverlay engineering-only` per locked §3.2 + §3.5; ~10 new Vitest tests + 2 visual baselines). Estimated 3-4 hr. Boot via `docs/agent/post-tag-gap-closure-starter-prompt.md`.

---

## Pre-gap-closure historical state (preserved; superseded by sub-session #1 above)

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
