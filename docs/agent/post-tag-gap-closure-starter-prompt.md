# Post-tag Gap-Closure — High-Fidelity Starter Prompt

**Compiled:** 2026-05-04 PM (post sub-session #3 PARTIAL close-out — A0+A1+A2+A3+A4+A5 done; A5.5+A6+A7 remaining)
**Authoritative for:** sub-session #3 remainder post-`/compact` boot (Phase A5.5 + A6 + A7)
**Lifecycle:** deleted at A7 close-out per locked decision §3.8
**Owns:** mission + vision + reading list + pre-flight gates + active per-phase specs + anti-patterns + first concrete action + cumulative state at HEAD `f900adf` (this rewrite) on top of code state at `0ccdd29`
**Does NOT own:** implementation line-by-line (in `~/.claude/plans/i-want-you-to-jolly-beacon.md`); historical narrative per phase (in `docs/agent/handoff-log.md`)

> **READ IN ORDER. DO NOT SKIM. DO NOT SKIP AHEAD.** This document is load-bearing because the user has been burned by every shortcut: "I'll just glance at the dossier" → re-introduces fixed bugs; "git add -A is fine, I won't have stray files" → committed runtime artifacts in 8350090; "the slider semantic looks right" → permanently flipped pills to calibration_drag (caught only by visual baseline). The cost of reading this prompt end-to-end is 15 minutes; the cost of skipping it is half a sub-session.

**ENTRY POINT FOR FRESH `/compact` BOOT:**
1. Read [`MEMORY.md`](../../../.claude/projects/-Users-saranyaraj-Projects-github-repo-mp2-0/memory/MEMORY.md) (auto-loaded; first entry = "START HERE")
2. Read **THIS file** end-to-end (≈800 lines; ≈12 min)
3. Read [`docs/agent/handoff-log.md`](handoff-log.md) — last 1-3 entries (sub-session #1, #2, #3-partial close-outs)
4. Read [`docs/agent/session-state.md`](session-state.md) — top headline only
5. Read `~/.claude/plans/i-want-you-to-jolly-beacon.md` — §3 table (25 locked decisions) + §A5.5 + §A6 + §A7 sections
6. Run §3 pre-flight in this prompt — expect HEAD at `b21ce7b` or later (the rewrite landed at `f900adf`; the self-reference fix at `b21ce7b`; code state unchanged from `0ccdd29`), 872 backend pytest, 230 Vitest in 26 files, bundle 269.41 kB gzipped, all static gates clean
7. Output the [§15 first-message template](#15-first-message-to-the-user-post-boot-template) — under 100 words
8. Begin **Phase A5.5** (NEW `frontend/e2e/regression-coverage.spec.ts`) — see [§2 active scope](#2-active-scope-a55--a6--a7-only) + plan file §A5.5

---

## §0. Mission — what this work is, why it matters, what's at stake

### The narrow mission
Close 5 unaddressed functional/UX gaps from the original 2,786-line Engine→UI Display Integration plan (`/Users/saranyaraj/Documents/tmp_Engine to UI Display Integration Plan_Demo and Pilot.md`) that shipped at tag `v0.1.2-engine-display` with **~75%** of its done-criteria. The work lands as **additive commits past the tag**, then cuts a NEW tag `v0.1.3-engine-display-polish` at Phase A7 close-out per locked §3.22. **At HEAD `f900adf` the work is 11 commits past the tag (10 functional + this rewrite); 4 of 5 gaps are closed; only A5.5+A6+A7 remain.**

### The 5 gaps (audited against the original plan; status at HEAD `f900adf`)

| # | Gap | Status | Where closed |
|---|---|---|---|
| 1 | `GoalAllocationSection` ideal bars use calibration not engine | ✅ CLOSED | A2 commit `c5a7e02` (sub-session #1) |
| 2 | `OptimizerOutputWidget` improvement uses calibration not engine | ✅ CLOSED | A3 commit `c212793` (sub-session #2) |
| 3 | Stale-state UX entirely absent (no overlay; no Regenerate; no integrity routing) | ✅ CLOSED | A4 commit `8350090` (sub-session #2) — 4 status variants + StaleRunOverlay + IntegrityAlertOverlay |
| 4 | Demo script not updated for engine→UI | ✅ CLOSED | A5 commit `bd90cf9` (sub-session #3) — Step 4 expanded + Step 4.5 + Step 4.6 |
| 5 | axe coverage missing on Goal + Household routes | ✅ CLOSED | A5 commit `bd90cf9` — 4→6 axe routes |

**All 5 gaps closed. The remaining work (A5.5+A6+A7) is regression coverage + USER manual smoke + close-out + tag, not new gap-closure.** This matters for the next agent's mental model: don't search for new gaps; the work is *consolidating* what shipped.

### Vision — why this work pays forward to pilot

**Pilot launches Mon 2026-05-08** with 3-5 advisors using REAL client data. The advisor's mental model — established in v0.1.2-engine-display + cemented by the gap-closure — is:
- Open household → see engine `HouseholdPortfolioPanel` rollup + treemap (✓)
- Drill into goal → see `RecommendationBanner` + engine ideal bars + engine improvement + `AdvisorSummaryPanel` (✓ all engine-canonical post-A3)
- Drag risk slider → live what-if; pills flip to `calibration_drag`; on save, engine auto-regenerates and pills flip back to engine (✓ A2 + A3 + RiskSlider semantic-split fix in A5)
- Analyst republishes CMA → previous run goes stale; advisor sees overlay + Regenerate CTA; integrity violations route to engineering (✓ A4 + A1 audit emission)

The pilot would have surfaced the engine vs calibration confusion in week 1 (gap #1 was the highest-leverage); the gap-closure prevents that. The remaining A5.5+A6+A7 work prevents the *opposite* failure: a regression in the 75% of the codebase the gap-closure didn't touch (cross-cutting i18n key collisions, type-system narrowing, route-level ErrorBoundary changes), which would surface as advisor-blocking bugs the engine→UI tests don't catch.

### Long-term intent — what this work cements

This isn't just gap-closure for v0.1.3-engine-display-polish. The work establishes:
- **Shared `<SourcePill>` abstraction** (A2) — single visual contract for "engine vs calibration" consumed by 3 surfaces (allocation + moves + optimizer); future advisor surfaces inherit
- **Stale-lifecycle backend contract** (A1) — 5 status semantics + `portfolio_run_integrity_alert` audit emission with per-(run, advisor) dedup + Hypothesis property invariants + JSON snapshot regression + ops-runbook §2 engineering response procedure; engineers grep the audit log when integrity violations surface in production
- **Production-quality test bars** — 90% line coverage gate (locked §3.14, stricter than locked #61's 85%); cross-browser tests for new Goal-route surfaces (locked §3.15, 22 cells across webkit + firefox); automated browser regression suite for 15 pre-existing flows (locked §3.20, scope of A5.5); 3x baseline-stability run for visual regression (locked §3.11). These bars become the standard for every future advisor surface.
- **Continuity discipline** — multi-sub-session execution with deletable starter-prompt artifact (this file), per-phase ~400-word handoff entries, tag-cut at close-out for clean rollback granularity

The work is **production-grade software for a limited user set; no excuses, no cutting corners** (pre-existing locked rule). Demo pressure is exactly when the discipline matters most — the May 8 launch is the hard gate, not "ready Friday."

---

## §1. Cumulative inventory — what already shipped at HEAD `f900adf`

**10 commits past tag `v0.1.2-engine-display` at `e5cd859`** (full chain in `git log --oneline e5cd859..HEAD`):

| Commit | Phase | Summary | Tests added |
|---|---|---|---|
| `f6e2ef8` | A0 | Pre-flight + starter prompt + 2 baseline fixes (OpenAPI codegen drift + missing `warning` token) | 0 (pre-flight only) |
| `95dfd01` | A1 | Backend status semantics + `portfolio_run_integrity_alert` audit emission + Hypothesis invariants + pre-tag backwards-compat + JSON snapshot fixtures | +18 backend (8 status semantics + 5 Hypothesis + 2 backwards-compat + 3 snapshot) |
| `c5a7e02` | A2 | NEW `<SourcePill>` + GoalAllocationSection engine-first + MovesPanel pill + RiskSlider `onPreviewChange` callback + GoalRoute `isPreviewingOverride` state lift | +18 Vitest (5 SourcePill + 9 GoalAllocationSection + 4 MovesPanel) |
| `987f8f8` | (close-out #1) | Sub-session #1 handoff entry + session-state refresh | 0 (docs only) |
| `808650e` | (docs) | Starter prompt rewrite (sub-session #1 close-out) | 0 (docs only) |
| `c212793` | A3 | OptimizerOutputWidget engine-first refactor (dollar-weighted improvement_pct from `link_recommendations[]`; null-guard `current_comparison.expected_return` → `link.expected_return` fallback; `* 100` to match backend pct-scale) | +7 Vitest |
| `8350090` | A4 | NEW `<StaleRunOverlay>` (advisor-actionable; 3 status variants) + NEW `<IntegrityAlertOverlay>` (engineering-only; no Regenerate) + RecommendationBanner expanded 3→5 visual states + HouseholdPortfolioPanel mirrors stale chip pattern (locked #19) + GoalRoute wraps engine panels in muted+aria-hidden when status non-current; 9 new i18n keys | +26 Vitest (10 StaleRunOverlay + 7 IntegrityAlertOverlay + 5 RecommendationBanner ext + 4 HouseholdPortfolioPanel ext) |
| `64ab152` | (chore) | Untrack `.claude/scheduled_tasks.lock` + `test-results/.last-run.json` (caught from `git add -A` in 8350090); .gitignore extension | 0 |
| `7c041f2` | (close-out #2) | Sub-session #2 handoff entry + session-state refresh | 0 (docs only) |
| `bd90cf9` | A5 | Demo script Step 4 expanded + NEW Step 4.5 (slider drag → calibration_drag pill flip → save → engine flip back) + NEW Step 4.6 (CMA republish → stale overlay → Regenerate cycle) + axe coverage on Goal + Household routes (4→6 axe routes) + 2 visual baselines for engine SourcePill (32→34 chromium baselines; 3-run stable per §3.11) + 6 cross-browser cells per §3.15 (3 tests × 2 non-chromium = 8→11 per browser, 22 total) + **RiskSlider semantic-split regression fix** (caught Phase A2 production bug via the new visual baseline test; split `isOverrideDraft` form-visibility flag from new `isDragPreview` callback flag) + NEW RiskSlider.test.tsx with 2 regression tests | +2 Vitest (RiskSlider regression) |
| `0ccdd29` | (close-out #3 partial) | Sub-session #3 PARTIAL handoff entry + session-state refresh + starter-prompt entry-point pointer | 0 (docs only) |
| `f900adf` | (docs) | Starter prompt deep rewrite for sub-session #3 remainder boot — incorporates 5 new gotcha classes from this session, narrows §2 to active scope (A5.5+A6+A7), refreshes pre-flight HEAD/counts | 0 (docs only) |

**Cumulative test bar at HEAD `f900adf`** (code unchanged from `0ccdd29`; only docs at `f900adf`; each must verify in §3 pre-flight):
- Backend pytest: **872 passed + 2 skipped** (was 854 baseline at v0.1.2-engine-display; +18 net new from A1)
- Backend perf budget (in isolation): **9 passed**
- Frontend Vitest: **230 passed in 26 files** (was 177 in 19 baseline; +53 net new across A1-A5)
- Bundle: **269.41 kB gzipped** (was 267.55 baseline; +1.86 kB; under 290 kB cap per locked #85; ~21 kB headroom)
- chromium foundation e2e: **13 passed** (unchanged)
- chromium visual-verification: **34 passed** (was 32 baseline; +2 from A5 SourcePill baselines; 3-run stability confirmed per §3.11)
- chromium pilot-features-smoke (axe): **6 passed** (was 4; +2 axe routes from A5)
- webkit cross-browser: **11 passed** (was 8; +3 from A5)
- firefox cross-browser: **11 passed** (was 8; +3 from A5)
- All static guards (vocab CI / PII grep / OpenAPI codegen / ruff / format / typecheck / lint / makemigrations): **OK**

**Code-level contracts the next agent depends on (DO NOT REGRESS):**
- [`frontend/src/goal/SourcePill.tsx`](../../frontend/src/goal/SourcePill.tsx) — shared component with 3 variants; `role="status"` + `aria-label`; 8-char run-signature prefix is `aria-hidden`
- [`frontend/src/goal/GoalAllocationSection.tsx`](../../frontend/src/goal/GoalAllocationSection.tsx) — engine-first decision tree per locked §3.1
- [`frontend/src/goal/OptimizerOutputWidget.tsx`](../../frontend/src/goal/OptimizerOutputWidget.tsx) — dollar-weighted engine improvement_pct with null-guard fallback
- [`frontend/src/goal/MovesPanel.tsx`](../../frontend/src/goal/MovesPanel.tsx) — reads backend `query.data.source` field
- [`frontend/src/goal/StaleRunOverlay.tsx`](../../frontend/src/goal/StaleRunOverlay.tsx) — 3-status overlay with bespoke focus model (mirror DocDetailPanel)
- [`frontend/src/goal/IntegrityAlertOverlay.tsx`](../../frontend/src/goal/IntegrityAlertOverlay.tsx) — engineering-only; NO Regenerate; NO focus management
- [`frontend/src/goal/RecommendationBanner.tsx`](../../frontend/src/goal/RecommendationBanner.tsx) — 5 visual states (current + 3 stale + integrity)
- [`frontend/src/routes/HouseholdPortfolioPanel.tsx`](../../frontend/src/routes/HouseholdPortfolioPanel.tsx) — stale + integrity chip variants per locked #19
- [`frontend/src/routes/GoalRoute.tsx`](../../frontend/src/routes/GoalRoute.tsx) — owns `isPreviewingOverride` state; wraps engine panels in mute+overlay
- [`frontend/src/components/ui/RiskSlider.tsx`](../../frontend/src/components/ui/RiskSlider.tsx) — `isOverrideDraft` (form visibility) split from `isDragPreview` (parent callback) per A5 regression fix
- [`web/api/serializers.py`](../../web/api/serializers.py) — `PortfolioRunSummarySerializer.get_status` emits `portfolio_run_integrity_alert` AuditEvent on `hash_mismatch` (rate-limited via `events.filter(...).exists()`)
- [`web/api/views.py`](../../web/api/views.py) `:551` — `ClientDetailView.get` passes `context={"request": request}`
- [`frontend/tailwind.config.ts`](../../frontend/tailwind.config.ts) — includes `warning: "#B87333"` color token
- [`docs/agent/ops-runbook.md`](ops-runbook.md) §2 "Portfolio Run Integrity Alert" — engineering response procedure
- New i18n keys in [`frontend/src/i18n/en.json`](../../frontend/src/i18n/en.json):
  - `goal_allocation.from_run` / `from_calibration` / `from_calibration_drag` / `run_source` (A2)
  - `routes.goal.stale_overlay_title/_body/_regenerate`, `declined_overlay_title/_body`, `integrity_overlay_title/_body/_run_ref`, `stale_chip_label`, `integrity_chip_label` (A4)
  - `routes.household.stale_chip_label`, `routes.household.integrity_chip_label` (A4)

---

## §2. Active scope — A5.5 + A6 + A7 only

**Done so far** (skip these — they're committed, tested, and verified):
- ~~Phase A0~~ — pre-flight + baselines fixed at `f6e2ef8`
- ~~Phase A1~~ — backend stale-lifecycle contract pinned at `95dfd01`
- ~~Phase A2~~ — SourcePill + GoalAllocationSection + MovesPanel + slider state lift at `c5a7e02`
- ~~Phase A3~~ — OptimizerOutputWidget engine-first at `c212793`
- ~~Phase A4~~ — Stale-state UX (4 status variants + 2 overlays) at `8350090`
- ~~Phase A5~~ — Demo + axe + visual baselines + cross-browser + RiskSlider regression fix at `bd90cf9`

**Remaining** (the active scope — your work for this session):

### Phase A5.5 — Automated browser regression coverage (per §3.20) (~3-4 hr) ⚠️ HEAVIEST PHASE

**Why:** §3.20 explicitly chose automated browser regression testing over manual checklist. The 75% of the codebase NOT touched by gap-closure could regress via cross-cutting changes (i18n key collisions, type-system narrowing, route-level ErrorBoundary changes, useEffect dependency drift). Phase A5.5 pins those flows as automated tests so a single `npm run e2e` catches them rather than relying on the user to remember to manually verify 15 distinct pre-existing flows.

**File:** NEW `frontend/e2e/regression-coverage.spec.ts` (~700-900 LoC, 15 tests)

**Test inventory** (specific flows that must NOT break):
1. Login → home → client picker pagination
2. Wizard Step 1-5 full flow
3. ReviewWorkspace doc upload + drain + reconcile
4. ConflictPanel single resolve
5. **DocDetailPanel slide-out + Esc close** (regression guard for `b14a199` — Esc handler bug)
6. Bulk conflict resolve
7. Defer + auto-resurface
8. Section approve
9. Household commit + auto-trigger PortfolioRun
10. Override → regenerate cycle
11. CMA Workbench draft → publish
12. Methodology page renders 10 sections
13. **FeedbackModal Esc close** (regression guard for `b14a199`)
14. PilotBanner ack flow (Phase 5b.1)
15. WelcomeTour ack flow

**Pattern** (mirror existing pilot-features-smoke + cross-browser specs):
```ts
import { expect, test, type Page } from "@playwright/test";

const ADVISOR_EMAIL = process.env.MP20_LOCAL_ADMIN_EMAIL ?? "advisor@example.com";
const ADVISOR_PASSWORD = process.env.MP20_LOCAL_ADMIN_PASSWORD ?? "change-this-local-password";

async function loginAdvisor(page: Page) {
  await page.goto("/");
  await page.getByLabel(/email/i).fill(ADVISOR_EMAIL);
  await page.getByLabel(/password/i).fill(ADVISOR_PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.locator('[data-testid="topbar"], header')).toBeVisible({ timeout: 15_000 });
}

test.describe("Regression coverage — pre-existing flows (per §3.20)", () => {
  test.skip(!process.env.MP20_LOCAL_ADMIN_EMAIL, "MP20_LOCAL_ADMIN_EMAIL not set; skipping");

  test.beforeEach(async ({ page }) => {
    await loginAdvisor(page);
  });

  test("DocDetailPanel Esc close regression guard (b14a199)", async ({ page }) => {
    await page.goto("/review");
    // ... navigate to a workspace, click a doc row, press Esc, assert panel closes + focus restored
  });

  // ... 14 more
});
```

**Setup:** Use `bash scripts/reset-v2-dev.sh --yes` in a session-scoped beforeAll hook for known synthetic state. Sandra/Mike auto-seeds with PortfolioRun + advisor pre-ack per locked #34 (only `--yes` is pre-authorized). Don't reset between tests — too slow.

**Gates:**
- Playwright `regression-coverage.spec.ts` — 15 passing on chromium
- Run twice consecutively to confirm zero flakes per locked §3.20
- Total chromium Playwright cumulative: 13 foundation + 34 visual-verification + 6 pilot-features + 15 regression = **68 chromium passing** at end of A5.5
- typecheck/lint/build clean (e2e specs don't go through `npm run lint` but Playwright type-checks them at runtime)

**Commit message template:**
```
test(e2e): automated regression coverage for 15 pre-existing high-traffic flows (per §3.20)

Phase A5.5 of post-tag gap-closure plan. NEW frontend/e2e/regression-coverage.spec.ts
with 15 automated browser tests covering pre-existing flows that aren't directly
touched by the gap-closure but might break via cross-cutting changes. Per locked
§3.20: chose automated over manual regression checklist.

Test inventory:
  1. Login + client picker pagination
  2. Wizard Step 1-5 full flow
  ...
  15. WelcomeTour ack flow

Regression guards explicitly named for prior bug classes:
  - DocDetailPanel Esc close (b14a199)
  - FeedbackModal Esc close (b14a199)
  - Override → regenerate cycle (engine→UI A2/A3 wiring)
  - Household commit + auto-trigger (engine→UI A2 wiring)

Gates:
  - 15 chromium passing on 2 consecutive runs (zero flakes per §3.20)
  - Cumulative chromium Playwright: 13 + 34 + 6 + 15 = 68
  - typecheck/lint/build clean
  - Bundle unchanged (test-only)

Locked decisions honored: §3.20 (automated), §3.14 (per-phase coverage),
§3.10 (theme-token grep no new tokens introduced).
```

**Halt-and-flush gate:** all 15 tests pass on 2 consecutive runs; CI runtime < 4 min; no flakes.

**Context budget warning:** A5.5 alone is the heaviest single phase in the plan. If you sense context approaching 70% mid-spec, halt at the next test-completion boundary, commit `wip(e2e): regression-coverage 9/15 tests landed; remaining 6 + flake-check pending`, write handoff entry, and suggest `/compact`. Do NOT push past 80% — past commits become unrecoverable past compaction.

### Phase A6 — Real-Chrome smoke + pilot dress rehearsal (USER MANUAL — ~45-60 min, NO commit)

#### A6.1 — Real-Chrome smoke (locked #100, ~20-30 min)

**You CANNOT automate this.** The FileList ref race + Esc handler bug class only surface in real Chrome (NOT headless Playwright). Locked #100 is mandatory pre-pilot.

**Procedure:** present user with checklist via `AskUserQuestion`; user runs in real Chrome (NOT headless, NOT DevTools-open). User reports back per step. If any step fails, halt + ping for diagnostic.

**Checklist (10 steps):**
1. `bash scripts/reset-v2-dev.sh --yes` (Sandra/Mike auto-seeds with PortfolioRun + advisor pre-ack)
2. Open real Chrome → `http://localhost:5173` → login
3. Confirm PilotBanner + WelcomeTour do NOT appear (pre-acked)
4. Sandra/Mike auto-loads → confirm:
   - HouseholdPortfolioPanel renders rollup + Top funds; status chip absent
   - Treemap visible
5. Drill into Retirement Income goal → confirm:
   - RecommendationBanner shows "Recommendation [8 hex] • Xm ago"
   - **GoalAllocationSection shows "Engine recommendation" pill with run sig** (Phase A2 wiring)
   - **MovesPanel shows "Engine recommendation" pill** (Phase A2 wiring)
   - **OptimizerOutputWidget shows engine-derived improvement + "Engine recommendation" pill** (Phase A3 wiring)
   - AdvisorSummaryPanel renders advisor_summary text
6. Drag risk slider → pills flip to "Calibration preview (drag mode)" → release → flip back (verify A2 + A5 RiskSlider regression fix is live)
7. Save override with rationale → confirm:
   - Banner timestamp updates within ~500ms
   - All 3 pills flip back to "Engine recommendation" with NEW run sig
8. Open analyst CMA Workbench → publish a new CMA → return to Sandra/Mike goal route → confirm:
   - **Stale overlay covers engine panels with Regenerate CTA** (Phase A4 wiring)
   - Banner shows "Stale: regenerate to refresh"
   - Regenerate button has focus
   - Press Tab → focus stays on Regenerate (focus-trap)
   - Press Esc → focus blurs but overlay stays (informational)
   - Click Regenerate → overlay dismisses + new run renders fresh
9. (Optional, if engineering wants integrity-overlay validation) Insert HASH_MISMATCH event via Django shell. Reload page → confirm:
   - Integrity overlay renders WITHOUT Regenerate button
   - DB has new `portfolio_run_integrity_alert` AuditEvent row
   - Reload again → no DUPLICATE audit row (dedup works)
10. Confirm DevTools Console clean (no warnings, no React errors, no a11y warnings)

#### A6.2 — Pilot dress rehearsal (locked #95 reactivated per §3.25, ~45 min)

**Procedure:** present 8-step demo flow via `AskUserQuestion`; user runs in actual Chrome with stopwatch; flag any step >threshold (8s non-trigger / 10s trigger per locked #88) as engineering follow-up before May 8 launch.

**Steps** (per `docs/agent/demo-script-2026-05-04.md` updated in A5):
1. Login → home (~30s; threshold 8s)
2. Pick Sandra/Mike → AUM strip + HouseholdPortfolioPanel + treemap (~45s; threshold 8s)
3. Drill into account → goal → KPI tiles + RecommendationBanner + AdvisorSummaryPanel (~60s; threshold 8s)
4. Goal allocation panel → engine ideal bars + "Engine recommendation" pill + Why panel (~45s; threshold 8s)
5. **NEW Step 4.5: drag slider → calibration_drag pill flip → save → engine pill flip back + banner timestamp updates** (~30s; threshold 10s)
6. **NEW Step 4.6: CMA Workbench publish → return to goal route → stale overlay → Regenerate → new run** (~60s; threshold 10s)
7. Switch to /review → DocDropOverlay + ReviewQueue render (~30s; threshold 8s)
8. Open Seltzer workspace → 5/5 reconciled chips + readiness panel (~60s; threshold 8s)
9. Review/approve sections → ConflictPanel resolution (~90s; threshold 10s)
10. Methodology page → 10 sections render (~30s; threshold 8s)

User reports timings + observations; document in handoff-log.

### Phase A7 — Close-out + 2 subagent reviews + 90% coverage gate + tag (~60-90 min)

**Files modified:**
- `docs/agent/session-state.md` — headline reflects gap-closure complete + new tag
- `docs/agent/handoff-log.md` — append per-phase verbose entry
- `docs/agent/decisions.md` — add sub-section "Post-tag gap-closure (2026-05-04 PM)" under existing "Engine→UI Display Integration"; distill 25 §3 locked-this-session decisions to 1-line entries
- `~/.claude/projects/-Users-saranyaraj-Projects-github-repo-mp2-0/memory/project_engine_ui_display.md` — note all 5 gaps closed past tag
- **DELETE:** `docs/agent/post-tag-gap-closure-starter-prompt.md` — THIS FILE (per §3.8 lifecycle)

**A7.1 — Code-reviewer subagent dispatch:**
```
Agent({
  description: "Cumulative gap-closure code review",
  subagent_type: "pr-review-toolkit:code-reviewer",
  prompt: "Review cumulative diff `e5cd859..HEAD` covering all 10 commits past tag v0.1.2-engine-display. Focus: PII discipline (no `str(exc)` in audit metadata), atomicity (transaction.atomic guards), audit-event regression (one event per kind per advisor), accessibility (ARIA, keyboard nav, focus management on StaleRunOverlay + IntegrityAlertOverlay), vocabulary discipline. Specifically verify: web/api/serializers.py:298-340 audit emission honors per-(run, advisor) dedup; frontend/src/goal/StaleRunOverlay.tsx focus model mirrors DocDetailPanel.tsx:56-67; frontend/src/components/ui/RiskSlider.tsx semantic split (isOverrideDraft for form-visibility vs isDragPreview for parent callback) is correctly documented and tested."
})
```
Fix all surfaced findings in a follow-up commit before A7.2.

**A7.2 — PII-focused subagent review (per §3.13):**
```
Agent({
  description: "PII-focused review of new audit metadata + i18n + payload reads",
  subagent_type: "general-purpose",
  prompt: "PII-focused review of cumulative diff e5cd859..HEAD. Specifically: (a) confirm new audit metadata fields in `portfolio_run_integrity_alert` (web/api/serializers.py:298-340) contain only structural fields {run_external_id, household_id, status, engine_version} — never raw text; (b) verify all new i18n strings in frontend/src/i18n/en.json contain no client identifiers, account numbers, SINs; (c) confirm frontend payload reads (latest_portfolio_run.status + new Allocation/Rollup reads) don't expose any field that wasn't already in pre-tag responses; (d) run `bash scripts/check-pii-leaks.sh` one final time at HEAD."
})
```
Fix any surfaced leak vectors before A7.3.

**A7.3 — Pre-push CI smoke (per §3.12):**
- Backend non-perf: 872 + 2 skipped (preserved across A2-A5; only A1 changed backend)
- Backend perf in isolation: 9/9
- Frontend Vitest: target ≥230 in ≥26 files
- Frontend typecheck/lint/build: clean; bundle ≤ 285 kB
- Playwright: 13 foundation + 34 visual + 6 pilot-features + 15 regression-coverage + 22 cross-browser = **90 passing**
- Static: ruff + format + vocab + PII + OpenAPI + migrations all clean
- Re-run 3x baseline stability check on A4 + A5 baselines (4 baselines total, all stable across 3 runs)

**A7.4 — Coverage gate (per §3.14, ≥ 90%):**
- Backend: `pytest --cov=web/api/serializers --cov=web/api/audit --cov=web/api/views --cov-fail-under=90 web/api/tests/test_portfolio_run_status_semantics.py web/api/tests/test_pre_a2_portfolio_run_compat.py web/api/tests/test_status_audit_invariants.py web/api/tests/test_household_detail_serializer_snapshot.py`
- Frontend: `vitest --run --coverage --coverage.thresholds.lines=90 --coverage.include='src/goal/SourcePill.tsx' --coverage.include='src/goal/StaleRunOverlay.tsx' --coverage.include='src/goal/IntegrityAlertOverlay.tsx' --coverage.include='src/goal/GoalAllocationSection.tsx' --coverage.include='src/goal/OptimizerOutputWidget.tsx' --coverage.include='src/goal/MovesPanel.tsx' --coverage.include='src/goal/RecommendationBanner.tsx' --coverage.include='src/routes/HouseholdPortfolioPanel.tsx' --coverage.include='src/components/ui/RiskSlider.tsx'`
- Halt + add tests if either gate fails

**A7.5 — Tag cut (per §3.22):**
```bash
git tag -a v0.1.3-engine-display-polish -m "Engine→UI display polish — closes 5 done-criteria gaps from v0.1.2-engine-display:
- GoalAllocationSection consumes engine goal_rollup (locked #5)
- OptimizerOutputWidget consumes link_recommendations (A3.3)
- Stale-state UX with 4 status variants + IntegrityAlertOverlay for hash_mismatch (locked #18, §3.2)
- MovesPanel pill via shared SourcePill (§3.3)
- Demo script + axe + cross-browser + automated regression coverage"
git tag -l "v0.1*"   # confirm: v0.1.0-pilot + v0.1.1-improved-intake + v0.1.2-engine-display + v0.1.3-engine-display-polish
```

**Push gate:** wait for explicit user authorization. Do NOT push (or push tags) unless user says "push to origin." Per pre-existing locked rule.

**Final commit:** `docs(engine-ui): close-out — gap-closure handoff + decisions update + session-state refresh + starter-prompt deleted`

**Halt-and-flush gate:** all 5 sub-phases (A7.1-A7.5) complete with no surfaced unfixed findings. User reviews cumulative diff + tag before authorizing push.

---

## §3. Pre-flight verification (mandatory; ~5 min)

**Run BEFORE any code change. Halt + AskUserQuestion if any gate red.**

### Sub-session #3 remainder entry baseline (HEAD: `b21ce7b` or later)
```bash
cd /Users/saranyaraj/Projects/github-repo/mp2.0

# 1. HEAD + working tree state
git status --short --branch          # expect: clean tree (test-results/ if present is gitignored)
git log --oneline -5                 # expect chain (newest → oldest):
                                     #   b21ce7b (self-ref fix) → f900adf (rewrite) → 0ccdd29 → bd90cf9 → 7c041f2
                                     # OR a more recent docs commit on top — that's fine if it's docs-only
git tag -l "v0.1*"                   # expect: v0.1.0-pilot + v0.1.1-improved-intake + v0.1.2-engine-display
                                     # NEW v0.1.3-engine-display-polish cuts at A7.5

# 2. Backend gate suite (~3 min)
docker compose exec -T backend bash -c "cd /app && uv run pytest --tb=no --ignore=web/api/tests/test_perf_budgets.py -q"
# expect: 872 passed, 2 skipped (final summary line; NOTE: backend output is verbose,
# capture summary via "| tail -3" — but the actual test count is on the LAST line, not
# always in the last 3; if the last 3 lines are warning-summary boilerplate, run again
# with "| grep -E 'passed|failed' | tail -3" or just look at the full tail with "| tail -8")

docker compose exec -T backend bash -c "cd /app && uv run pytest web/api/tests/test_perf_budgets.py --tb=no -q"
# expect: 9 passed (isolated; full-suite run may flake on busy box)

# 3. Frontend gates (~30s)
cd frontend && npm run typecheck && npm run lint && npm run test:unit -- --run && npm run build && cd ..
# expect: 230 Vitest in 26 files; bundle 269.41 kB gzipped

# 4. Static guards
bash scripts/check-vocab.sh           # expect: vocab CI: OK
bash scripts/check-pii-leaks.sh       # expect: PII grep guard: OK
bash scripts/check-openapi-codegen.sh # expect: OpenAPI codegen gate: OK

# 5. Live stack
docker compose ps                    # expect: backend + db running
curl -s -o /dev/null -w "backend: %{http_code}\n" http://localhost:8000/api/session/
curl -s -o /dev/null -w "frontend: %{http_code}\n" http://localhost:5173/
# expect: 200 / 200

# 6. Engine probe (must succeed before any code change)
curl -s -c /tmp/cookies.txt http://localhost:8000/api/session/ > /dev/null && \
  CSRF=$(grep csrftoken /tmp/cookies.txt | awk '{print $7}') && \
  curl -s -b /tmp/cookies.txt -c /tmp/cookies.txt -X POST http://localhost:8000/api/auth/login/ \
    -H "Content-Type: application/json" -H "X-CSRFToken: $CSRF" -H "Referer: http://localhost:8000" \
    -d '{"email":"advisor@example.com","password":"change-this-local-password"}' > /dev/null && \
  curl -s -b /tmp/cookies.txt http://localhost:8000/api/clients/hh_sandra_mike_chen/ | \
    jq '.latest_portfolio_run | {external_id, status, run_signature, has_links: (.output.link_recommendations | length > 0), has_rollup: (.output.goal_rollups | length > 0)}'
# expect: status="current"; non-null external_id + run_signature; has_links=true; has_rollup=true

# 7. (A5.5-specific) Browser availability
ls ~/Library/Caches/ms-playwright/ | grep -E "chromium|webkit|firefox"
# expect: at least one of each
```

If gate (1) shows HEAD before `b21ce7b` (i.e., `0ccdd29` or earlier), this prompt is from a future state and the actual HEAD is rolled back — halt + ask user. If HEAD is past `b21ce7b` and the recent commits are docs-only (`docs(...)` prefix), proceed; if there are unexpected `feat(...)` or `test(...)` commits, halt + read recent git log to understand what changed.

If gate (6) shows `status` ≠ `"current"` OR `has_links=false` OR `has_rollup=false`, the engine path is broken — investigate before any code change. Sandra/Mike's engine output is needed for A5.5 regression tests (override→regenerate flow + commit + auto-trigger).

---

## §4. Locked decisions reference

### 25 §3 locked-this-session decisions (full table in plan file `~/.claude/plans/i-want-you-to-jolly-beacon.md` §3)

Status legend: ✅ DONE in committed phase | ⏳ PENDING in active scope (A5.5/A6/A7)

| § | Decision summary | Status | Phase |
|---|---|---|---|
| §3.1 | Slider drag UX: engine pill on saved view; calibration_drag pill ONLY during slider drag; flips back on save | ✅ DONE (+ A5 RiskSlider regression fix split semantic) | A2, fixed in A5 |
| §3.2 | Stale-overlay 4 statuses: invalidated/superseded/declined → StaleRunOverlay (regenerable); hash_mismatch → IntegrityAlertOverlay (engineering-only) | ✅ DONE | A4 |
| §3.3 | MovesPanel source pill in scope at A2 | ✅ DONE | A2 |
| §3.4 | Stale chip + overlay copy: "Stale: regenerate to refresh" (technical-precise) | ✅ DONE | A4 |
| §3.5 | hash_mismatch backend audit emit on serializer access, rate-limited via `events.filter(...).exists()` | ✅ DONE | A1 |
| §3.6 | NO per-stale-view audit emit (status field in JSON is enough) | ✅ DONE | by omission |
| §3.7 | Slider state lift: `isPreviewingOverride` lifted from `RiskSlider` to `GoalRoute` via `onPreviewChange` | ✅ DONE (+ A5 semantic split) | A2, fixed in A5 |
| §3.8 | Multi-session execution; THIS prompt is the boot artifact; deleted at A7 | ✅ DONE (created A0) | A0, deleted A7 |
| §3.9 | English-only codebase confirmed; new keys land in `en.json` only | ✅ DONE | every commit |
| §3.10 | Theme-token grep gate at every commit gate using new tokens | ✅ DONE every gate | every commit |
| §3.11 | 3x baseline-stability run for visual regression | ✅ DONE (A5 baselines stable) | A5 |
| §3.12 | Pre-push CI smoke at A7 close-out | ⏳ PENDING | A7.3 |
| §3.13 | PII-focused review pass at A7 | ⏳ PENDING | A7.2 |
| §3.14 | ≥ 90% line coverage gate (stricter than locked #61's 85%) | ⏳ PENDING | A7.4 |
| §3.15 | Cross-browser extension (webkit + firefox) for new Goal-route surfaces | ✅ DONE (22 cells) | A5 |
| §3.16 | Backwards-compat regression for pre-tag households | ✅ DONE | A1 |
| §3.17 | Full ops-runbook entry for integrity-alert engineering response | ✅ DONE | A1 |
| §3.18 | Hypothesis property suite for status + audit-dedup invariants | ✅ DONE | A1 |
| §3.19 | NO new perf benchmarks; trust existing 9-test perf budget suite | ✅ DONE by omission | — |
| §3.20 | Automated browser regression coverage for 15 pre-existing flows | ⏳ PENDING — **THIS IS A5.5** | A5.5 |
| §3.21 | API contract snapshot extension (4 state fixtures) | ✅ DONE | A1 |
| §3.22 | New tag `v0.1.3-engine-display-polish` at A7 | ⏳ PENDING | A7.5 |
| §3.23 | NO frontend telemetry / Sentry breadcrumbs for stale overlay views | ✅ DONE by omission | — |
| §3.24 | NO backend rate limit on `/generate-portfolio/` | ✅ DONE by omission | — |
| §3.25 | Pilot dress rehearsal at A6 (locked #95 reactivated) | ⏳ PENDING | A6.2 |

**Active for A5.5+A6+A7:** §3.12, §3.13, §3.14, §3.20, §3.22, §3.25 — six decisions you must honor.

### 111 prior locked decisions (in [`docs/agent/decisions.md`](decisions.md) "Engine→UI Display Integration (2026-05-03/04)" section)

Most relevant for A5.5+A6+A7:
- **#9** Failure surfacing: typed-skip silent + audit; unexpected → catch-all + audit + `latest_portfolio_failure` SerializerMethodField + Banner inline + Sonner toast
- **#19** HouseholdPortfolioPanel mirrors RecommendationBanner failure pattern (✓ implemented A4)
- **#34** Pre-authorized: only `bash scripts/reset-v2-dev.sh --yes`; everything else needs explicit user authorization
- **#44** Per-phase verbose handoff entry (~400 words; locked #45 = template)
- **#56** Strict P99 ≤ 1000ms threshold; sync `engine.optimize()` inline (Sandra/Mike P99=258ms)
- **#64** StrictMode double-invoke tests for every new component
- **#68** Bespoke modal/overlay a11y: `aria-modal=true` is NOT enough — explicit Esc + focus restore + click-outside; mirror DocDetailPanel pattern (used A4)
- **#74** Auto-trigger SYNCHRONOUS inside `transaction.atomic`; response IS truth (not `transaction.on_commit`)
- **#85** Bundle size cap < 290 kB gzipped (current 269.41 = 21 kB headroom)
- **#88** Demo step time budgets: 8s non-trigger / 10s trigger
- **#100** Real-Chrome smoke is USER manual (cannot be automated) — A6.1
- **#X.10** Sub-agent verification protocol — Read every file the agent edited; re-run tests; spot-check citations; verify locked-decision compliance

---

## §5. Critical gotchas — code-level facts paid for in real time

These bug classes have surfaced in this session OR earlier sessions. The user has paid for each lesson with debugging time. Read them BEFORE writing tests or code.

### Backend test infrastructure
- **`web.audit.AuditEvent` table is APPEND-ONLY via PL/pgSQL trigger** (`web/audit/migrations/0002_audit_immutability.py`). Cannot DELETE rows. Pattern: capture before/after counts, assert delta. Don't `AuditEvent.objects.filter(...).delete()` in tests — it raises.
- **`PortfolioRunEvent` IS deletable** (no immutability trigger). Safe to `run.events.all().delete()` between Hypothesis examples.
- **Hypothesis with Django:** use `transactional_db` fixture (NOT `db`) when running multiple `@given` examples within one test; `db` (`transaction=False`) wraps the whole test in one transaction → cross-example state leaks. Pattern: `@pytest.mark.django_db(transaction=True)` + UUID-unique advisor emails per example to avoid append-only audit dedup carryover.
- **Hypothesis text noise:** `st.text()` generates `\x00` null bytes which Postgres rejects. Filter: `st.text(alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00"), ...)`.

### Vitest test infrastructure
- **react-i18next is mocked in `frontend/src/test/setup.ts`** to return the i18n KEY itself (not the resolved English text). Tests assert on key strings: `screen.getByText("goal_allocation.from_run")` not `screen.getByText("Engine recommendation")`.
- **Vitest globals are NOT auto-imported** despite `globals: true` in `vitest.config.ts`. Must explicitly `import { beforeEach, describe, expect, it, vi } from "vitest"` — otherwise typecheck + lint fail.
- **`mockHousehold` factory at `frontend/src/__tests__/__fixtures__/household.ts`** is byte-for-byte against live Sandra/Mike payload (locked #55). Already includes `latest_portfolio_run.status` field. Pattern: `mockHousehold({ latest_portfolio_run: mockPortfolioRun({ status: "invalidated", ... }) })`. Refresh fixture if drift suspected.
- **`@typescript-eslint/no-non-null-assertion` is enforced.** `movesState.data!.source` fails lint. Use `if (movesState.data) movesState.data.source = ...` or alternative narrowing.
- **Rules of Hooks lint catches what typecheck doesn't.** When wrapping engine panels in GoalRoute (Phase A4), `useGeneratePortfolio(household.id)` was called AFTER an early-return — typecheck passed, lint flagged. Pattern: lift all `useXxx` hooks above any early `return`; pass nullable args (most hooks accept `string | null`). [GoalRoute.tsx:46-48](../../frontend/src/routes/GoalRoute.tsx#L46) is the canonical example.

### Backend serializer context propagation (load-bearing for audit emission)
- **`HouseholdDetailSerializer.get_latest_portfolio_run` MUST pass `context=self.context`** to nested `PortfolioRunSerializer(run, context=self.context).data`. Without it, the nested serializer can't extract the requesting advisor's email for audit emission. Same for `get_portfolio_runs`. Fixed in A1 commit `95dfd01`.
- **`ClientDetailView.get` MUST pass `context={"request": request}`** to `HouseholdDetailSerializer(household, context={"request": request}).data`. Without it, no request flows to nested serializers. Fixed in A1.

### Frontend tooling + math
- **Tailwind tokens at `frontend/tailwind.config.ts`** (not in a separate `tokens.css`). Theme-token grep: `grep -E "(accent.*2|warning|danger|muted)" frontend/tailwind.config.ts`. `warning` was missing pre-A0 and silently no-op'd; A0 added `warning: "#B87333"`.
- **No `@radix-ui/react-focus-scope` in package.json.** Bespoke modal focus management uses manual `useEffect` + `window.addEventListener("keydown")` + `ref.focus()` per `DocDetailPanel.tsx:56-67` and `FeedbackButton.tsx:65-74`. StaleRunOverlay (A4) follows this pattern.
- **i18n FR file (`frontend/src/i18n/fr.json`) is a placeholder** with single `_comment` field. Per locked §3.9, English-only path; new keys land in `en.json` only.
- **`formatPct` consumes pct-scaled values** (5.0 → "5.0%", NOT 0.05 → "0.1%"). Engine math gives 0..1 returns (e.g., `link.expected_return = 0.08`); must `* 100` to match the backend `improvement_pct` contract at `web/api/preview_views.py:476`. Bug surfaced in A3 — first test run had `formatPct(0.05, 1) = "0.1%"` failing assertions for "5.0%". Fix: pre-multiply engine math by 100. See [`OptimizerOutputWidget.tsx`](../../frontend/src/goal/OptimizerOutputWidget.tsx) `engineImprovementPct` helper.

### Conflated-semantic flag bug class (A5 caught + fixed; preserve as pattern reference)
- **`isOverrideDraft` in RiskSlider.tsx had two distinct semantics conflated** before the A5 fix:
  1. Pre-A2 use: gates SaveOverrideForm visibility — true when `selectedScore !== systemScore` (advisor can confirm/adjust an existing saved override OR draft a new one)
  2. NEW Phase A2 use: fires `onPreviewChange` to flip SourcePill — should be true ONLY when actively dragging away from the committed effective score
- **Bug**: page-load with a saved override (system=3, override=1) had `selectedScore=1` (initialized from `effectiveScore=1`) ≠ `systemScore=3` → `isOverrideDraft=true` permanently → `onPreviewChange(true)` fired on mount → all 3 engine pills rendered `calibration_drag` instead of `engine`.
- **Why it escaped sub-session #1 Vitest**: GoalAllocationSection mocks didn't render RiskSlider directly. Caught only by Phase A5's new visual baseline test against the live goal route on Sandra/Mike's `goal_retirement_income` (which has a saved override).
- **Fix**: split into two flags. `isOverrideDraft = selectedScore !== systemScore` (kept for form visibility); NEW `isDragPreview = selectedScore !== effectiveScore` fires `onPreviewChange`. See [`RiskSlider.tsx:91-99`](../../frontend/src/components/ui/RiskSlider.tsx#L91-L99) + regression test [`RiskSlider.test.tsx`](../../frontend/src/components/ui/__tests__/RiskSlider.test.tsx).
- **General lesson:** when adding a new use case to an existing flag, audit whether the existing semantic still applies; introduce a new flag if the semantic forks. Mock-based unit tests don't catch flag conflation if the conflated parent isn't rendered in the mock — visual baselines on the live data path are the safety net.

### Git hygiene (caught in A4; preserve as discipline)
- **`git add -A` silently captures untracked artifacts.** A4 commit `8350090` shipped `.claude/scheduled_tasks.lock` (Claude Code runtime state) + `test-results/.last-run.json` (Playwright last-run output) inadvertently. Recovery cost a follow-up `chore` commit + `.gitignore` extension at `64ab152`.
- **Always stage explicit file lists.** Pattern: `git add path/to/file1 path/to/file2 ...`. If you genuinely need everything, use `git status --short` first to verify nothing untracked is creeping in.
- **`.gitignore` covers `.claude/` + `test-results/` at root** as of `64ab152`; if either reappears as tracked, something extended past root or the gitignore drifted.

### File:line reference for key contracts

#### Backend
| File:line | Purpose |
|---|---|
| `web/api/serializers.py:317-340` | `_portfolio_run_status` (5-state computation) |
| `web/api/serializers.py:298-340` | Integrity-alert audit emission (A1) |
| `web/api/serializers.py:148-150` | `get_latest_portfolio_run` with context propagation |
| `web/api/views.py:551` | `ClientDetailView.get` passing context |
| `web/api/views.py:3068+` | `_record_current_run_invalidations` (dedup pattern) |
| `web/api/views.py:1226-1278` | `CMASnapshotPublishView.post` (CMA publish → INVALIDATED_BY_CMA) |
| `web/api/preview_views.py:476` | Backend `improvement_pct = ... * 100` (pct-scale contract) |
| `web/api/models.py:338-350` | `PortfolioRunEvent.EventType` (9 event types) |
| `web/audit/writer.py:8-22` | `record_event` signature |
| `web/audit/migrations/0002_audit_immutability.py` | PL/pgSQL append-only trigger |

#### Frontend
| File:line | Purpose |
|---|---|
| `frontend/src/lib/household.ts:291-309` | `findGoalRollup` / `findHouseholdRollup` / `findGoalLinkRecommendations` |
| `frontend/src/lib/household.ts:65-85` | `Allocation` / `Rollup` / `LinkRecommendation` types |
| `frontend/src/lib/household.ts:222-228` | `latest_portfolio_failure` field |
| `frontend/src/lib/preview.ts:280-291` | `MovesResponse` type (with `source` field) |
| `frontend/src/lib/preview.ts:362-394` | `useGeneratePortfolio` mutation |
| `frontend/src/goal/SourcePill.tsx` | Shared engine/calibration/calibration_drag pill (A2) |
| `frontend/src/goal/GoalAllocationSection.tsx` | Engine-first ideal bars (A2) |
| `frontend/src/goal/MovesPanel.tsx` | Source pill + engine signature (A2) |
| `frontend/src/goal/OptimizerOutputWidget.tsx` | Engine improvement_pct + 4 stat tiles (A3); `engineImprovementPct` helper at line ~115 |
| `frontend/src/goal/StaleRunOverlay.tsx` | Bespoke modal-style overlay (A4); focus model lines 47-78 |
| `frontend/src/goal/IntegrityAlertOverlay.tsx` | Engineering-only overlay (A4); no Regenerate button |
| `frontend/src/goal/RecommendationBanner.tsx` | 5 visual states (A4 expanded 3→5) |
| `frontend/src/goal/AdvisorSummaryPanel.tsx` | Per-link advisor summaries |
| `frontend/src/routes/HouseholdPortfolioPanel.tsx` | Engine rollup + stale/integrity chip variants (A4) |
| `frontend/src/routes/GoalRoute.tsx:46-50` | `useGeneratePortfolio` lifted above early returns (Rules of Hooks) |
| `frontend/src/routes/GoalRoute.tsx:113-122` | Stale/integrity panel-mute wrapper (A4) |
| `frontend/src/components/ui/RiskSlider.tsx:91-99` | `isOverrideDraft` (form) vs `isDragPreview` (callback) split (A5 regression fix) |
| `frontend/src/modals/DocDetailPanel.tsx:56-67` | Esc handler + focus restore pattern (A4 reference) |
| `frontend/src/chrome/FeedbackButton.tsx:65-74` | Esc handler pattern (A4 alt reference) |
| `frontend/src/__tests__/__fixtures__/household.ts` | mockHousehold byte-for-byte fixture (locked #55) |
| `frontend/src/test/setup.ts` | Vitest setup (i18n mock returns key-as-text) |
| `frontend/tailwind.config.ts` | Theme tokens (accent, accent-2, warning, danger, muted) |
| `frontend/src/i18n/en.json` | All gap-closure i18n keys (goal_allocation.* + routes.goal.* + routes.household.*) |

#### Tests (regression guards from this session)
| File | Purpose |
|---|---|
| `web/api/tests/test_portfolio_run_status_semantics.py` | 8 status-semantics tests (A1) |
| `web/api/tests/test_status_audit_invariants.py` | 5 Hypothesis property tests (A1) |
| `web/api/tests/test_pre_a2_portfolio_run_compat.py` | Pre-tag backwards-compat (A1) |
| `web/api/tests/test_household_detail_serializer_snapshot.py` | API contract JSON snapshots (A1) |
| `frontend/src/goal/__tests__/SourcePill.test.tsx` | 5 SourcePill tests (A2) |
| `frontend/src/goal/__tests__/GoalAllocationSection.test.tsx` | 9 GoalAllocationSection tests (A2) |
| `frontend/src/goal/__tests__/MovesPanel.test.tsx` | 4 MovesPanel tests (A2) |
| `frontend/src/goal/__tests__/OptimizerOutputWidget.test.tsx` | 7 OptimizerOutputWidget tests (A3) |
| `frontend/src/goal/__tests__/StaleRunOverlay.test.tsx` | 10 StaleRunOverlay tests (A4) |
| `frontend/src/goal/__tests__/IntegrityAlertOverlay.test.tsx` | 7 IntegrityAlertOverlay tests (A4) |
| `frontend/src/components/ui/__tests__/RiskSlider.test.tsx` | 2 regression tests (A5 fix) |
| `frontend/e2e/visual-verification.spec.ts` | 34 baselines including 2 new A5 engine pills |
| `frontend/e2e/pilot-features-smoke.spec.ts` | 6 axe routes including Goal + Household (A5) |
| `frontend/e2e/cross-browser-smoke.spec.ts` | 11 cells per browser including 3 new A5 |

---

## §6. Reading list (priority order; ~12-15 min total)

1. **`MEMORY.md`** at `~/.claude/projects/-Users-saranyaraj-Projects-github-repo-mp2-0/memory/MEMORY.md` — auto-loaded; first entry "START HERE" points at `project_engine_ui_display.md`
2. **THIS FILE** — `docs/agent/post-tag-gap-closure-starter-prompt.md` — full context boot (~12 min)
3. **`docs/agent/handoff-log.md`** last 1-3 entries — sub-session #3 PARTIAL (Phase A5 + RiskSlider regression fix), #2 (A3+A4), #1 (A0+A1+A2) close-outs
4. **`docs/agent/session-state.md`** — current HEAD + phase line; refresh at sub-session boundary
5. **`~/.claude/plans/i-want-you-to-jolly-beacon.md`** — gap-closure plan; read §3 table (25 locked decisions) + §A5.5 + §A6 + §A7 sections specifically
6. **`docs/agent/decisions.md`** "Engine→UI Display Integration (2026-05-03/04)" section — 111 prior locked decisions (skim for #19/#34/#44/#64/#85/#88/#100/#X.10)
7. **`docs/agent/ops-runbook.md`** §2 "Portfolio Run Integrity Alert" — engineering response procedure (consumed by A6.1 step 9)
8. **`MP2.0_Working_Canon.md`** — only deep-read §9.4 architecture invariants + §11.8.3 real-PII + §6.3a vocabulary if touching governed surfaces (A5.5 doesn't; A7 close-out shouldn't)
9. **`frontend/e2e/foundation.spec.ts`** + **`frontend/e2e/pilot-features-smoke.spec.ts`** + **`frontend/e2e/cross-browser-smoke.spec.ts`** — read these BEFORE Phase A5.5 (mirror the test pattern: loginAdvisor helper, MP20_LOCAL_ADMIN_EMAIL skip, beforeEach login)
10. **`frontend/e2e/visual-verification.spec.ts`** lines 722-1050 — engine→UI display test patterns (A5 baselines for SourcePill; reference for any A5.5 test that needs to wait for an engine-rendered surface)

---

## §7. Anti-patterns — DO NOT REPEAT

These bug classes have been paid for. Each cost a round of "Is everything REALLY done?" pushback in prior sessions OR was caught in this session.

| Anti-pattern | Reality |
|---|---|
| **"Tests pass = ship-ready"** | sub-session #11 verification pass found StrictMode bug class that subagent gates missed; A5 visual baseline test caught the RiskSlider semantic-conflation bug that 195 Vitest tests didn't see. Foundation e2e + visual baselines + real-Chrome smoke are the catch-all. |
| **"Subagent says it's done"** | Verify by Reading every file the subagent touched (per locked #X.10); subagent gates pass against subagent-written fixtures, not against `foundation.spec.ts`. mockHousehold cost-key bug at `2bd77d3` was exactly this. |
| **Mock fixtures that don't mirror production payload shape** | mockHousehold byte-for-byte verified locked #55. Refresh fixture if drift suspected. The RiskSlider bug was related: the GoalAllocationSection mocks bypassed RiskSlider entirely, so the conflated flag never surfaced in unit tests. |
| **`setState((prev) => mutate-closure-array)` StrictMode-double-update class** | Caused DocDropOverlay regression at `bca0112`; the setState updater MUST be pure; compute new list OUTSIDE the updater (per locked #64). |
| **`aria-label` text vs visible text divergence** | Playwright `getByRole({ name: /.../i })` resolves to aria-label NOT visible text; use less-anchored regex (`/save.*draft/i`) or `getByText` for visible-text matches (locked #71). |
| **Bespoke modal/overlay needs explicit Esc handler + focus restore + click-outside** | `aria-modal=true` is NOT enough; FeedbackModal Esc bug at `b14a199` was exactly this. StaleRunOverlay (A4) mirrors DocDetailPanel pattern; A5.5 must include Esc-close regression guards for both DocDetailPanel and FeedbackModal. |
| **`str(exc)` anywhere in DB columns / API response bodies / audit metadata** | Use `safe_audit_metadata` from `web/api/error_codes.py`. Bedrock errors carry extracted client text → PII leak risk. A1 audit emission used structural-only metadata; A7.2 PII review explicitly verifies this. |
| **Hardcoded fund_ids on frontend** | Use canonical `sh_*` from CMA fixture; never hardcode `equity_fund` etc. |
| **Auto-regenerate on `INVALIDATED_BY_CMA` event** | Manual regenerate per canon §4.7.3 (locked #37). A4 Regenerate is advisor-clicked, not automatic. |
| **`AuditEvent.objects.filter(...).delete()` in tests** | Audit table has PL/pgSQL append-only trigger. Cannot delete. Use before/after count delta pattern. |
| **`@pytest.mark.django_db(transaction=False)` + Hypothesis** | Cross-example state leaks. Use `transaction=True` + UUID-unique data per example. |
| **`movesState.data!.source = "X"` in Vitest tests** | `@typescript-eslint/no-non-null-assertion` is enforced. Use `if (movesState.data) movesState.data.source = "X"`. |
| **Honest audit when user pushes back** | Three rounds of "Is everything done?" each surfaced a real bug; user's pushback is signal, not noise. Don't restate confidence — re-run higher-level tests + surface gaps explicitly. |
| **Skip the per-phase verbose ping discipline** | Production-quality-bar.md §9 + locked decision #44 require ~400-word verbose pings. Don't shortcut. |
| **Skip Phase A6 because "tests pass"** | The FileList ref race + Esc handler bug class only surface in real Chrome (NOT headless Playwright). Locked #100 is mandatory. |
| **NEW (A5): `git add -A` silently captures stray runtime artifacts** | A4 commit `8350090` shipped `.claude/scheduled_tasks.lock` + `test-results/.last-run.json` inadvertently. **Always stage explicit file lists** (`git add file1 file2 ...`). Run `git status --short` before commit to verify nothing creeping in. |
| **NEW (A5): Conflated-semantic flag class** | When extending a flag's use case (e.g. lifting `isOverrideDraft` to a parent callback), audit whether the existing semantic still applies; introduce a NEW flag if the semantic forks. Mock-based unit tests miss flag conflation if the conflated parent isn't rendered in the mock — visual baselines on live data are the safety net. |
| **NEW (A5): `formatPct(0..1, 1)` returns wrong string** | `formatPct` consumes already-percent-scaled values. Engine math (0..1 returns) must `* 100` to match backend pct-scale contract at `preview_views.py:476`. First A3 test run failed because `formatPct(0.05, 1)` returned `"0.1%"` not `"5.0%"`. |
| **NEW (A5): Rules of Hooks enforced by lint, NOT typecheck** | When refactoring routes (A4 GoalRoute), `useXxx(...)` calls after early-return blocks pass typecheck but fail `npm run lint`. Pattern: lift all hooks to top of component above any conditional return; pass nullable args (most hooks accept `string \| null`). |

---

## §8. Per-phase ping format (verbose ~400 words; locked #44 + production-quality-bar.md §9)

Every phase commit pings the user with:

1. **What changed** — HEAD + diff highlights with `file:line` citations
2. **What was tested** — new tests by name + count + invariants pinned + manual smoke + full gate-suite tail
3. **What didn't ship** — open items + reason + path forward + which sub-session it lands
4. **What's next** — phase continuation + estimated scope
5. **What's the risk** — regression possibilities + how the gates would catch them
6. **Locked decisions honored** — citation by §3.N (this session) and #N (prior)
7. **Continuity check** — session-state.md updated yes/no; handoff-log appended yes/no; this prompt deleted yes/no (only at A7)

**Evidence citation discipline:** cite specific commit hash, regression test ids, gate-output tail. Never opinions like "looks good" or "should work." Specific test counts only AFTER the suite runs.

---

## §9. Halt protocol

If context approaches 75% mid-phase OR you hit a stop condition:

1. **Halt at next natural breakpoint** — typically completion of current logical sub-task (one Vitest file done, one component refactored, one test list completed). For A5.5 specifically, halt between tests, not mid-test.
2. **Commit progress** with explicit `wip:` prefix if phase is incomplete: `wip(e2e): regression-coverage 9/15 tests landed; remaining 6 + flake-check pending`
3. **Write handoff-log entry** covering what's done + what remains within this phase + specific `file:line` resumption point
4. **Update session-state.md** headline
5. **Suggest `/compact`** with continuation cue: "Phase A<N> partial; <X-Y> remaining. Read post-tag-gap-closure-starter-prompt.md to continue."

NEVER strand uncommitted work across a halt. Plan file + handoff-log are the durable contract; mid-phase context loss is recoverable only via these.

A5.5 specifically: 15 tests is large for one commit but a single file. If you halt mid-spec, the file ends up partially populated; the wip commit captures it; next session resumes by reading the spec + plan §A5.5 + the handoff entry to know which tests are left.

---

## §10. Continuity discipline

### At every sub-session boundary (END of A5.5, A7):
1. Commit any uncommitted work (explicit file list, NOT `git add -A`)
2. Update `docs/agent/session-state.md` headline paragraph (preserve historical sections; add NEW section above)
3. Append per-phase verbose handoff-log entry (~400 words; § structure: HEAD + summary paragraph + per-phase commit detail + gates + what's next)
4. Update MEMORY.md ONLY at A7 close-out (sub-session boundaries when state changes materially)
5. Commit docs as a single commit: `docs(engine-ui): handoff-log + session-state for sub-session #N`
6. Suggest `/compact` to user

### At every sub-session START (post-`/compact`):
1. Read `MEMORY.md` (auto-loaded)
2. Read THIS FILE
3. Read `docs/agent/handoff-log.md` last 1-3 entries
4. Read `docs/agent/session-state.md`
5. Read plan §3 + relevant phase section
6. Run §3 pre-flight verification
7. Output [§15 first-message template](#15-first-message-to-the-user-post-boot-template) under 100 words

If steps 1-7 fail, halt + ask user. Never proceed against a broken or unexpected baseline.

### Sub-session bookkeeping
- Sub-session #1 = A0 + A1 + A2 (DONE; close-out at `987f8f8`)
- Sub-session #2 = A3 + A4 (DONE; close-out at `7c041f2`)
- Sub-session #3 = A5 + A5.5 + A6 + A7 (PARTIAL; A5 done at `bd90cf9`; partial close-out at `0ccdd29`; A5.5+A6+A7 remaining)

---

## §11. Communication style (user-stated preferences)

- **Cite specific evidence** (commit hash, regression test ids, gate-output tail) — never opinions like "looks good" / "should work" / "ready to ship"
- **Verbose per-phase pings with `file_path:line_number`** specifics
- **Specific test counts only AFTER the suite runs** (use "let me check" until then)
- **Latency claims only after measurement**
- **Don't overclaim.** "Tests pass" needs the actual count + tail. "Engine works" needs the probe output.
- **The user redirects when you drift.** Treat redirects as normal input; reset cleanly without restating prior confidence.
- **When halting:** clean handoff entry + commit any wip + ping via AskUserQuestion. Don't strand uncommitted work across a halt.
- **Per-phase ping discipline:** every phase exit pings with §8 format. No shortcuts.
- **Auto mode preference:** the user explicitly chose AUTO mode in this session. Prefer action over planning; minimize check-ins for routine decisions; expect course corrections as normal input. When facing destructive operations or scope expansions outside the plan, ASK first via AskUserQuestion (the artifact-cleanup AskUserQuestion in this session was the right call).
- **Multi-option AskUserQuestion at decision points:** when surfacing a non-trivial choice (e.g., "what to do about stray artifacts in commit 8350090?"), present 2-4 explicit options with tradeoff descriptions. Don't ask binary "should I X?" — instead "X / Y / Z; X recommended because..."

---

## §12. First concrete action (Mode B — sub-session #3 remainder)

**This is the only mode for this session — A5.5 is the active scope.** No mode A (planning); no other modes; the decisions are locked.

1. Run §3 pre-flight (~5 min)
2. Output the [§15 first-message template](#15-first-message-to-the-user-post-boot-template) — under 100 words confirming dossier read + gates green + understanding of next phase
3. Begin **Phase A5.5** per plan file §A5.5: NEW `frontend/e2e/regression-coverage.spec.ts` with 15 automated browser tests for pre-existing flows
   - Read `frontend/e2e/foundation.spec.ts` first (≈10 min) for the loginAdvisor helper pattern + the existing flow exercises that already exist (some may overlap; don't duplicate)
   - Read `frontend/e2e/pilot-features-smoke.spec.ts` for the test.skip + beforeEach pattern
   - Implement all 15 tests in one file; use existing helpers; copy minor utility from foundation if needed
   - Run on chromium twice consecutively; expect 15 passing on both runs (zero flakes per §3.20)
   - Commit per template in [§2 Phase A5.5](#phase-a55--automated-browser-regression-coverage-per-320-3-4-hr-%EF%B8%8F-heaviest-phase)
4. After A5.5 commit + halt-and-flush gate green, decide based on context budget:
   - If <70% used: proceed to A6 (USER MANUAL — present checklist via AskUserQuestion)
   - If ≥70%: halt, write sub-session #3 second-partial close-out, suggest `/compact`
5. Phase A6 — present A6.1 real-Chrome smoke checklist + A6.2 dress rehearsal; collect user smoke results; document in handoff-log
6. Phase A7 — close-out (5 sub-phases A7.1-A7.5):
   - A7.1: dispatch `pr-review-toolkit:code-reviewer` on `e5cd859..HEAD`
   - A7.2: dispatch PII-focused `general-purpose` subagent
   - A7.3: pre-push CI smoke (full gate suite)
   - A7.4: 90% coverage gate
   - A7.5: cut tag `v0.1.3-engine-display-polish`
   - Final commit: handoff-log + decisions migration + session-state + memory update + DELETE this prompt
7. Wait for explicit user authorization to push (do NOT push without "push to origin")

---

## §13. Stop conditions (halt + AskUserQuestion when these fire)

1. §3 pre-flight gate red BEFORE any code change
2. Engine probe at sub-session entry returns ≠ 200 with valid output
3. HEAD has drifted unexpectedly past `b21ce7b` with NON-docs commits (someone shipped code beyond this prompt's compile point)
4. Bundle size grows past 290 kB gzipped (locked #85)
5. Vocab CI flags any new copy
6. PII grep guard fails on a new commit
7. A5.5 spec exceeds 5 hr wall-clock (per locked #46 phase ceiling)
8. A5.5 flake check (run-twice) shows any test that's flaky → halt; investigate determinism before proceeding
9. Code-reviewer subagent (A7.1) surfaces BLOCKING findings → fix before tag
10. PII-focused review (A7.2) surfaces leak vectors → fix before tag
11. 90% coverage gate (A7.4) fails → add tests before tag
12. Visual baselines drift across 3 consecutive runs (§3.11) at A7.3 → halt; investigate determinism cause
13. Phase A6 user smoke flags console warnings, visual regressions, or focus-trap escapes
14. Phase A6 dress rehearsal flags any step > threshold (8s non-trigger / 10s trigger per locked #88)
15. User says "push" before A7.5 tag cut → halt; one final commit + tag before push
16. Sub-agent claims work done but file inspection shows incomplete (per locked #X.10)
17. Context approaches 75% mid-A5.5 → halt at next test-completion boundary, wip-commit, /compact
18. Context approaches 75% mid-A7 → halt; A7 sub-phases (A7.1-A7.5) are individual commits that resume cleanly

---

## §14. References (file:line index — fastest path to any contract)

See [§5 Critical gotchas → File:line reference](#file-line-reference-for-key-contracts) for the complete index. Backend + Frontend + Tests tables span 50+ entries.

### Plan + docs (single-source-of-truth registry)
| File | Purpose |
|---|---|
| `~/.claude/plans/i-want-you-to-jolly-beacon.md` | Plan file — 25 §3 decisions; 8 phases; A5.5+A6+A7 sections active |
| `docs/agent/decisions.md` | 111 prior locked decisions — Engine→UI Display Integration section |
| `docs/agent/ops-runbook.md` §2 | Portfolio Run Integrity Alert engineering response (A1) |
| `docs/agent/handoff-log.md` | Per-phase verbose entries — read last 1-3 |
| `docs/agent/session-state.md` | Current state headline (refresh at sub-session boundary) |
| `docs/agent/demo-script-2026-05-04.md` | Demo script (Step 4 expanded + Steps 4.5/4.6 added in A5) |
| `~/.claude/projects/-Users-saranyaraj-Projects-github-repo-mp2-0/memory/MEMORY.md` | Auto-memory index (auto-loaded) |
| `~/.claude/projects/-Users-saranyaraj-Projects-github-repo-mp2-0/memory/project_engine_ui_display.md` | START HERE memory entry |
| `frontend/e2e/foundation.spec.ts` | Foundation e2e — read for A5.5 helper patterns |
| `frontend/e2e/pilot-features-smoke.spec.ts` | Pilot smoke + axe — read for A5.5 skip/beforeEach pattern |
| `frontend/e2e/cross-browser-smoke.spec.ts` | Cross-browser cells — A5 extended |
| `frontend/e2e/visual-verification.spec.ts` | Visual baselines — A5 extended (lines 990+ for A5 SourcePill baselines) |

### CLAUDE.md + canon (governance)
| File | Purpose |
|---|---|
| `CLAUDE.md` (repo root) | Non-negotiable rules — git protocol + commands + invariants |
| `MP2.0_Working_Canon.md` | Authoritative product/strategy/architecture; deep-read §9.4 + §11.8.3 + §6.3a only when touching governed surfaces |
| `~/.claude/skills/mp2-protocol/SKILL.md` | MP2.0 Session Protocol (auto-loaded; reinforces this prompt's discipline) |

---

## §15. First message to the user (post-boot template)

After §3 pre-flight + §12 mode determination:

```
Booted from post-tag-gap-closure-starter-prompt.md.

HEAD: <commit>          # expected: b21ce7b or later docs-only commit
Pre-flight: <pass/fail per gate>
  - Backend pytest: <count> passed (expected: 872 + 2 skipped)
  - Vitest: <count> in <files> (expected: 230 in 26)
  - Bundle: <kB> gzipped (expected: 269.41 kB; under 290 kB cap)
  - Static guards: <vocab/PII/OpenAPI status>
  - Engine probe: <status>/<run_signature[:8]>; has_links=<bool>; has_rollup=<bool>
    (expected: current/<sig>; both true)
  - Browsers: <chromium/webkit/firefox availability>
Sub-session: #3 remainder (A5 done at bd90cf9; A5.5+A6+A7 remaining)
Phase scope: A5.5 first (NEW frontend/e2e/regression-coverage.spec.ts; 15 tests; ~3-4 hr)
Locked decisions active: §3.12, §3.13, §3.14, §3.20, §3.22, §3.25 (six remaining)

Beginning Phase A5.5 per plan file §A5.5.
```

Wait for user direction. Do not begin code changes until §3 confirmed green AND scope is unambiguous.

---

## §16. Final closer

This work is the foundation for the Mon 2026-05-08 pilot launch. **Production-grade software for a limited user set; no excuses, no cutting corners.** Three things matter most:

1. **Production-quality testing.** A5.5 is the lid on the regression-coverage promise — 15 automated browser tests + 90% coverage gate at A7.4 + Hypothesis property invariants (already shipped A1) + JSON snapshot regression (already shipped A1) + cross-browser cells (already shipped A5) + 3-run baseline stability (already verified A4 + A5) + real-Chrome smoke (A6.1 user manual). The pilot can't surface "but the tests passed" — testing IS the pilot validation. Skipping A5.5 to "save time" trades 3-4 hours of automated coverage for unknown weeks of pilot triage.

2. **Production-quality UX.** SourcePill flips correctly mid-drag (A2 + A5 RiskSlider regression fix); stale overlay focus-trap doesn't escape (A4 mirror DocDetailPanel pattern); integrity alerts route to engineering not advisors (A4 IntegrityAlertOverlay + A1 audit emission). Each detail is paid for in pilot trust. The A5.5 regression suite verifies the 75% of code NOT touched by gap-closure didn't break via cross-cutting changes.

3. **Continuity discipline.** This prompt, the handoff-log, the plan file, the session-state — all are the cross-session memory. Future sessions hydrate from these. If you halt mid-phase, write the handoff entry. If you discover something the plan didn't capture, update the plan file (it's the only file editable in plan mode). The user has been burned by drift; never strand uncommitted work or unrecorded decisions. **At A7 close-out, DELETE this prompt** — the lifecycle is intentional; the next session boots from the freshly-cut tag + the migrated decisions.md + the close-out handoff entry.

The cumulative diff at A7 close-out will be ~14-16 commits past tag `v0.1.2-engine-display`. Each one represents a tested, reviewed, locked-decision-honoring step. The tag `v0.1.3-engine-display-polish` cuts at A7.5 as the clean rollback boundary — pilot can revert to v0.1.2 if A5.5+ regressions surface, or to v0.1.3 if pilot itself surfaces issues.

**Begin with §3 pre-flight. Do not skip ahead.**

> The user pushes Monday morning. Don't push without explicit authorization.
