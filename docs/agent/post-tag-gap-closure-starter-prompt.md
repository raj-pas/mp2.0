# Post-tag Gap-Closure — High-Fidelity Starter Prompt

**Compiled:** 2026-05-04 PM (post sub-session #1 close-out)
**Authoritative for:** sub-session #2 + #3 post-`/compact` boot
**Lifecycle:** deleted at A7 close-out per locked decision §3.8
**Owns:** mission + vision + reading list + pre-flight gates + per-phase deliverable specs + anti-patterns + first concrete action
**Does NOT own:** Implementation line-by-line (in `~/.claude/plans/i-want-you-to-jolly-beacon.md`); historical narrative (in `docs/agent/handoff-log.md`)

> **Read in order. Do not skim. Do not skip ahead. The user has been burned by "I'll just glance" — this document exists because the dossier is load-bearing.**

---

## §0. Mission — what this work is, why it matters, what's at stake

### The narrow mission
Close 5 unaddressed functional/UX gaps from the original 2,786-line Engine→UI Display Integration plan (`/Users/saranyaraj/Documents/tmp_Engine to UI Display Integration Plan_Demo and Pilot.md`) that shipped at tag `v0.1.2-engine-display` with **~75%** of its done-criteria. The work lands as **8 additive commits past the tag**, then cuts a NEW tag `v0.1.3-engine-display-polish` at Phase A7 close-out per locked §3.22.

### The 5 gaps (audited against the original plan; verified at HEAD `1ea5338`)
1. **`GoalAllocationSection` ideal bars still calibration** — done-criteria #5 + locked #5 unfulfilled. Advisor saw `useSleeveMix(effectiveScore)` (calibration reference points) instead of `findGoalRollup(household, goal.id).allocations` (engine's frontier-optimized blend). **THIS IS THE HIGHEST-LEVERAGE GAP**: it directly contradicts the plan's "engine output is canonical; calibration is the teaching anchor" framing.
2. **`OptimizerOutputWidget` improvement still calibration** — same pattern: calibration math instead of engine-derived `link_recommendations[].expected_return + current_comparison`.
3. **Stale-state UX entirely absent** — done-criteria #8 + #10 + locked #18. When CMA republishes invalidate a run, advisor sees old run rendered IDENTICALLY to a fresh run. No muted overlay, no Regenerate CTA, no integrity-alert path.
4. **Demo script not updated for engine→UI** — done-criteria #15. Pre-engine→UI talk-track; no Step 4.5 (override→regenerate) or Step 4.6 (CMA republish → stale overlay).
5. **axe coverage missing on new surfaces** — done-criteria #19. axe runs on `/` + `/review` only; Goal route + Household route uncovered.

### Vision — why these gaps must close before pilot

**Pilot launches Mon 2026-05-08** with 3-5 advisors using REAL client data. The advisor's mental model — established in v0.1.2-engine-display sub-sessions #1-#5 — is:
- Open household → see engine `HouseholdPortfolioPanel` rollup + treemap (✓ shipped)
- Drill into goal → see `RecommendationBanner` (✓ shipped) + engine ideal bars (**❌ gap #1**) + engine improvement (**❌ gap #2**) + `AdvisorSummaryPanel` (✓ shipped)
- Drag risk slider → live what-if; on save, engine auto-regenerates synchronously (✓ shipped via locked #74)
- Analyst republishes CMA → previous run goes stale; advisor sees overlay + Regenerate CTA (**❌ gap #3**)

Without gap-closure, an advisor walks into pilot and sees calibration "Reference points" labelled identically to before the engine→UI work — the engine output appears only as the new banner + advisor summary, leaving the most prominent allocation table showing the wrong source. The pilot would surface this in week 1 as "but the ideal column shows the wrong number" and erode trust in the entire engine→UI integration.

### Long-term intent — what this work pays forward
This isn't just gap-closure for v0.1.3-engine-display-polish. The gap-closure work establishes:
- **Shared `<SourcePill>` abstraction** (sub-session #1 A2; consumed by GoalAllocationSection + MovesPanel + Phase A3 OptimizerOutputWidget) — single visual contract for "engine vs calibration" that future advisor surfaces will inherit
- **Stale-lifecycle backend contract** (sub-session #1 A1; 5 status semantics + integrity-alert audit emission with dedup + Hypothesis property invariants + JSON snapshot regression + ops-runbook §2 engineering response procedure) — the foundation the frontend Phase A4 stale UX consumes; engineers grep the audit log when integrity violations surface in production
- **Production-quality test bars** — 90% line coverage gate (locked §3.14, stricter than original locked #61's 85%); cross-browser tests for new Goal-route surfaces (locked §3.15); automated browser regression suite for 15 pre-existing flows (locked §3.20); 3x baseline-stability run for visual regression (locked §3.11). These bars become the standard for every future advisor surface.

The work is **production-grade software for a limited user set; no excuses, no cutting corners** (pre-existing locked rule).

---

## §1. What sub-session #1 already shipped (so you don't re-do it)

**4 commits past tag `v0.1.2-engine-display` at `e5cd859`:**

| Commit | Phase | Summary | Tests added |
|---|---|---|---|
| `f6e2ef8` | A0 | Starter prompt + 2 baseline fixes (OpenAPI codegen drift + missing `warning` token) | 0 (pre-flight only) |
| `95dfd01` | A1 | Backend status semantics + integrity-alert audit emission + Hypothesis invariants + backwards-compat + JSON snapshots | +18 backend (8 status + 5 Hypothesis + 2 backwards-compat + 3 snapshots) |
| `c5a7e02` | A2 | SourcePill + GoalAllocationSection engine-first + MovesPanel pill + slider-drag state lift | +18 Vitest (5 SourcePill + 9 GoalAllocationSection + 4 MovesPanel) |
| `987f8f8` | (close-out) | Sub-session #1 handoff entry + session-state refresh | 0 (docs only) |

**Test bars at HEAD `987f8f8`** (verified):
- **872 backend pytest passing** + 2 skipped (was 854 baseline; +18 net new)
- **195 Vitest in 22 files** (was 177 in 19; +18 net new)
- Bundle: **268.13 kB gzipped** (was 267.55; +0.58 kB; under 290 kB cap per locked #85)
- All static gates clean (vocab + PII + OpenAPI + ruff + format + typecheck + lint + makemigrations)

**Code shipped (specific contracts the next agent depends on):**
- `frontend/src/goal/SourcePill.tsx` — shared component with 3 variants (`engine`/`calibration`/`calibration_drag`); `role="status"` + `aria-label`; 8-char run-signature prefix is `aria-hidden`
- `frontend/src/goal/GoalAllocationSection.tsx` — engine-first decision tree per locked §3.1 (drag → calibration_drag; rollup → engine; fallback → calibration)
- `frontend/src/goal/MovesPanel.tsx` — reads `query.data.source` (backend already emits)
- `frontend/src/components/ui/RiskSlider.tsx` — accepts `onPreviewChange?: (isPreviewing: boolean) => void` callback
- `frontend/src/routes/GoalRoute.tsx` — owns `isPreviewingOverride: boolean` state lifted from RiskSlider
- `web/api/serializers.py` — `PortfolioRunSummarySerializer.get_status` emits `portfolio_run_integrity_alert` AuditEvent on `hash_mismatch` (rate-limited via `events.filter(...).exists()`)
- `web/api/views.py:551` — `ClientDetailView.get` passes `context={"request": request}` to `HouseholdDetailSerializer`
- `frontend/tailwind.config.ts` — added `warning: "#B87333"` color token
- `docs/agent/ops-runbook.md` §2 "Portfolio Run Integrity Alert" — engineering response procedure
- New i18n keys in `frontend/src/i18n/en.json` under `goal_allocation.*`: `from_run`, `from_calibration`, `from_calibration_drag`, `run_source`

---

## §2. What sub-sessions #2 + #3 must ship

### Sub-session #2 (3-4 hr; HEAD on entry: `987f8f8`)

#### Phase A3 — `OptimizerOutputWidget` engine-first refactor (~75 min)
**Why:** done-criteria implicit + plan §A3.3. The "improvement" + ideal/current dollar metrics still come from `useOptimizerOutput` calibration; engine has authoritative numbers via `link_recommendations[].expected_return + current_comparison.expected_return`.

**Files:**
- MODIFY: [frontend/src/goal/OptimizerOutputWidget.tsx](frontend/src/goal/OptimizerOutputWidget.tsx)
- NEW: `frontend/src/goal/__tests__/OptimizerOutputWidget.test.tsx` (~150 LoC, 7 tests)

**Logic** (mirror A2 GoalAllocationSection pattern):
```tsx
const links = findGoalLinkRecommendations(household, goal.id);  // engine
const calibration = useOptimizerOutput(householdId, goalId);    // fallback (always called)
const useEngine = links.length > 0 && !isPreviewingOverride;

if (useEngine) {
  const totalAllocated = links.reduce((s, l) => s + l.allocated_amount, 0);
  const idealReturn = links.reduce((s, l) => s + l.expected_return * l.allocated_amount, 0) / totalAllocated;
  const currentReturn = links.reduce((s, l) => {
    const cur = l.current_comparison?.expected_return ?? l.expected_return;  // null-guard
    return s + cur * l.allocated_amount;
  }, 0) / totalAllocated;
  const improvement_pct = idealReturn - currentReturn;
}
```

**UI:** mirror A2 — `<SourcePill source={source} runSignature={runSig}/>` in widget header. Existing 4-stat grid layout unchanged.

**Vitest coverage** (7 tests):
1. Renders engine improvement when `link_recommendations.length > 0` AND `!isPreviewingOverride`
2. Renders calibration improvement when no link recs (fallback)
3. Renders calibration_drag pill when `isPreviewingOverride === true` (consistent with A2)
4. `current_comparison.expected_return === null` path uses `link.expected_return` as "current" baseline
5. Multi-link goal: dollar-weighted blend matches expected
6. StrictMode double-invoke (per locked #64)
7. Empty `links` array does not throw; falls to calibration

**Wire from `GoalRoute.tsx`:** pass `isPreviewingOverride={isPreviewingOverride}` + `household={household}` to `<OptimizerOutputWidget>`.

**Gates:**
- Vitest 195 + 7 = **202 passing**
- typecheck/lint/build clean
- Bundle ≤ 275 kB gzipped
- Theme-token grep clean (`accent-2` + `muted` already verified in A0)

**Commit:** `feat(goal): OptimizerOutputWidget consumes link_recommendations via SourcePill (engine-derived improvement + calibration fallback)`

#### Phase A4 — Stale-state UX (4 status variants + IntegrityAlertOverlay) (~150 min)
**Why:** done-criteria #8 + #10 + locked #18 + locked-this-session §3.2 + §3.5. Plan called for a single overlay; planning interview clarified 4 status variants — 3 advisor-actionable ("Stale" + Regenerate) + 1 engineering-only ("Integrity check failed", no Regenerate, audit emit already shipped in A1).

**Files:**
- NEW: `frontend/src/goal/StaleRunOverlay.tsx` (~150 LoC) — bespoke advisor-actionable overlay
- NEW: `frontend/src/goal/IntegrityAlertOverlay.tsx` (~80 LoC) — engineering-only overlay; NO Regenerate
- MODIFY: `frontend/src/goal/RecommendationBanner.tsx` — add 4 stale-status branches + chip variants (warning color for stale; danger color for integrity)
- MODIFY: `frontend/src/routes/HouseholdPortfolioPanel.tsx` — mirror banner stale chip patterns (per locked #19)
- MODIFY: `frontend/src/routes/GoalRoute.tsx` — wrap GoalAllocationSection + OptimizerOutputWidget + MovesPanel in stale wrapper (`opacity-40 pointer-events-none aria-hidden`) when status is non-current
- MODIFY: `frontend/src/i18n/en.json` — 9 new keys (titles + bodies + buttons + chip labels)
- NEW: `frontend/src/goal/__tests__/StaleRunOverlay.test.tsx` (~180 LoC, 10 tests)
- NEW: `frontend/src/goal/__tests__/IntegrityAlertOverlay.test.tsx` (~120 LoC, 6 tests)
- MODIFY: existing `RecommendationBanner.test.tsx` (+5 tests for 4 status branches + integrity)
- MODIFY: existing `HouseholdPortfolioPanel.test.tsx` (+4 tests)

**Status mapping (per locked §3.2):**
- `invalidated` → `<StaleRunOverlay status="invalidated">` with copy "Stale: regenerate to refresh"
- `superseded` → same overlay; same copy
- `declined` → `<StaleRunOverlay status="declined">` with copy "Run was declined; regenerate to retry"
- `hash_mismatch` → `<IntegrityAlertOverlay>` with copy "Integrity check failed; engineering has been notified" — **NO Regenerate button**

**StaleRunOverlay focus model** (mirror [DocDetailPanel.tsx:56-67](frontend/src/modals/DocDetailPanel.tsx#L56) + [FeedbackButton.tsx:65-74](frontend/src/chrome/FeedbackButton.tsx#L65) per locked #68):
- `useEffect` mount: capture `previousFocusRef.current = document.activeElement`; auto-focus Regenerate button
- `useEffect` unmount: restore `previousFocusRef.current?.focus()` (per A2 interview answer)
- `useEffect` window keydown listener:
  - `Escape` → `e.stopPropagation()`; blur active element (does NOT dismiss — informational, not modal)
  - `Tab` → focus stays on Regenerate (only focusable element); `e.preventDefault()`
- ARIA: `role="alertdialog" aria-modal="true" aria-labelledby="stale-title" aria-describedby="stale-body"`

**IntegrityAlertOverlay** (engineering-only, NO advisor action):
- ARIA: `role="alert" aria-labelledby="integrity-title" aria-describedby="integrity-body"` (NOT alertdialog — no buttons inside)
- No focus-trap (no focusable elements)
- Renders run signature + ops-runbook §2 reference for engineer triage
- Backend audit emission ALREADY SHIPPED in A1 (`web/api/serializers.py:298-340`); no backend work needed in A4

**Vitest StaleRunOverlay (10 tests):**
1. Renders with role="alertdialog" + aria-modal + aria-labelledby + aria-describedby
2. Auto-focuses Regenerate button on mount
3. Restores previous focus on unmount
4. Esc does NOT dismiss; does blur active element
5. Tab cycles within overlay (only Regenerate is focusable)
6. Click Regenerate fires `onRegenerate`
7. Disabled during `isPending`
8. Renders "stale" copy for `status="invalidated"`
9. Renders "stale" copy for `status="superseded"`
10. Renders "declined" copy for `status="declined"`

**Vitest IntegrityAlertOverlay (6 tests):**
1. Renders with role="alert"
2. Does NOT render Regenerate button (advisor-not-actionable)
3. Renders run signature reference
4. Esc does NOT dismiss
5. ARIA: aria-labelledby + aria-describedby resolve to translated text
6. StrictMode double-invoke

**Visual regression baseline:**
- Extend `frontend/e2e/visual-verification.spec.ts` with `test("Goal route — stale overlay covers engine panels")` and `test("Goal route — integrity overlay (engineering-only)")`. Set up state by inserting `INVALIDATED_BY_CMA` / `HASH_MISMATCH` event via Django mgmt-shortcut. 2 new screenshot baselines.

**3x baseline stability per §3.11:** after `--update-snapshots`, run spec 2 more times without; 0 pixel diffs across 3 runs.

**Gates:**
- Vitest 202 + 10 + 6 + 5 + 4 = **227 passing**
- visual-verification 32 + 2 = 34 chromium passing (baseline-stable across 3 runs)
- typecheck/lint/build clean; bundle ≤ 285 kB gzipped (currently 268.13)
- Theme-token grep: `accent-2` + `warning` + `muted` (warning was added in A0)
- vocab CI clean (no "reallocation/transfer/move-money")

**Commit:** `feat(goal): stale-state overlay (4 status variants) + integrity-alert overlay for hash_mismatch`

**Halt-and-flush gate at end of A4:** all stale-state tests green; visual baselines committed; manual smoke (browser): publish new CMA via Workbench → reload Sandra/Mike goal route → see overlay → click Regenerate → confirm overlay dismisses + new run renders fresh. Separately: insert HASH_MISMATCH event via Django shell → reload → see integrity overlay → confirm NO Regenerate button + audit row created in DB.

---

### Sub-session #3 (5-7 hr; HEAD on entry: post-A4 commit)

#### Phase A5 — Demo script + axe coverage + visual baselines + cross-browser (~75 min)
**Files:**
- MODIFY: [docs/agent/demo-script-2026-05-04.md](docs/agent/demo-script-2026-05-04.md) — append Step 4.5 (override→regenerate) + Step 4.6 (CMA republish → stale overlay) + engine→UI talking points per the original A5 spec
- MODIFY: [frontend/e2e/pilot-features-smoke.spec.ts](frontend/e2e/pilot-features-smoke.spec.ts) — add `test("goal route has zero axe-core WCAG 2.1 AA violations")` and `test("household route has zero axe-core WCAG 2.1 AA violations")` mirroring lines 35-58 pattern
- MODIFY: `frontend/e2e/visual-verification.spec.ts` — 2 new baselines for engine pills on GoalAllocationSection + OptimizerOutputWidget engine state
- MODIFY: `frontend/e2e/cross-browser-smoke.spec.ts` — add 3 new tests × 2 non-chromium browsers (webkit + firefox) per locked §3.15: engine pill renders / stale overlay focus model / integrity overlay

**Gates:**
- Playwright: 13 foundation + 36 visual-verification + 4 pilot-features + 30 cross-browser = **83 passing**
- Baseline stability per §3.11: 0 pixel diffs across 3 runs

**Commit:** `feat(demo+a11y+cross-browser): demo script engine→UI talk-track + axe coverage + visual baselines + cross-browser stale/integrity coverage`

#### Phase A5.5 — Automated browser regression coverage (per §3.20) (~3-4 hr) ⚠️ HEAVIEST PHASE
**Why:** §3.20 explicitly chose automated browser regression testing over manual checklist. The 75% of the codebase NOT touched by gap-closure could regress via cross-cutting changes.

**File:** NEW `frontend/e2e/regression-coverage.spec.ts` (~700-900 LoC, 15 tests)

**Test inventory** (specific flows that must NOT break):
1. Login → home → client picker pagination
2. Wizard Step 1-5 full flow
3. ReviewWorkspace doc upload + drain + reconcile
4. ConflictPanel single resolve
5. **DocDetailPanel slide-out + Esc close** (regression guard for b14a199)
6. Bulk conflict resolve
7. Defer + auto-resurface
8. Section approve
9. Household commit + auto-trigger PortfolioRun
10. Override → regenerate cycle
11. CMA Workbench draft → publish
12. Methodology page renders 10 sections
13. **FeedbackModal Esc close** (regression guard for b14a199)
14. PilotBanner ack flow (Phase 5b.1)
15. WelcomeTour ack flow

**Pattern:**
```ts
test.describe("Regression coverage — pre-existing flows", () => {
  test.beforeEach(async ({ page }) => {
    await loginAdvisor(page);  // existing helper
  });

  test("DocDetailPanel Esc close regression guard (b14a199)", async ({ page }) => {
    await page.goto("/review/<workspace_id>");
    await page.locator('[data-testid="doc-row"]').first().click();
    await expect(page.getByRole("complementary", { name: /document detail/i })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("complementary", { name: /document detail/i })).not.toBeVisible();
  });
});
```

**Setup:** `bash scripts/reset-v2-dev.sh --yes` in session-scoped hook for known synthetic state.

**Gates:**
- Playwright regression-coverage 15 passing
- Run twice; zero flakes
- Total chromium Playwright: 13 + 36 + 4 + 15 = **68 chromium**

**Commit:** `test(e2e): automated regression coverage for 15 pre-existing high-traffic flows (per §3.20)`

#### Phase A6 — Real-Chrome smoke + pilot dress rehearsal (USER MANUAL — ~45-60 min, no commit)
**Phase A6.1 — Real-Chrome smoke (locked #100, ~20-30 min):** present user with checklist; user runs in real Chrome (NOT headless, NOT DevTools-open). Covers all engine→UI surfaces touched in A2-A4 + console-clean check.

**Phase A6.2 — Pilot dress rehearsal (locked #95 reactivated per §3.25, ~45 min):** present 8-step demo flow; user runs in actual Chrome with stopwatch; flag any step >threshold (8s non-trigger / 10s trigger) per locked #88.

User reports back via AskUserQuestion. If any step fails, halt + ping for diagnostic.

#### Phase A7 — Close-out + 2 subagent reviews + 90% coverage gate + tag (~60-90 min)
**Files:**
- MODIFY: `docs/agent/session-state.md` — headline reflects gap-closure complete + new tag
- MODIFY: `docs/agent/handoff-log.md` — append per-phase verbose entry
- MODIFY: `docs/agent/decisions.md` — add sub-section "Post-tag gap-closure (2026-05-04 PM)" under existing "Engine→UI Display Integration (2026-05-03/04)"; distill 25 §3 locked-this-session decisions to 1-line entries
- MODIFY: `~/.claude/projects/-Users-saranyaraj-Projects-github-repo-mp2-0/memory/project_engine_ui_display.md` — note all 5 gaps closed past tag
- DELETE: `docs/agent/post-tag-gap-closure-starter-prompt.md` (per §3.8 lifecycle — THIS FILE)

**A7.1 Code-reviewer subagent** (per earlier interview answer):
- Dispatch `pr-review-toolkit:code-reviewer` on cumulative diff `1ea5338..HEAD` covering all 7 phase commits
- Expected check coverage: PII discipline (no `str(exc)` in audit metadata), atomicity, audit-event regression, accessibility (ARIA, keyboard nav, focus management), vocabulary discipline
- Fix all surfaced findings in a follow-up commit

**A7.2 PII-focused subagent review** (per §3.13):
- Specifically checks: new audit metadata fields, new i18n strings, frontend payload reads
- Run `bash scripts/check-pii-leaks.sh` one final time at HEAD

**A7.3 Pre-push CI smoke** (per §3.12):
- Final cumulative gates (parallel where independent):
  - Backend: 872 passed + 2 skipped (was 854; +18 from A1)
  - Backend perf: 9/9 in isolation
  - Frontend Vitest: 227 in 24 files (was 177 in 19; +50 net new across A2/A3/A4)
  - Frontend typecheck/lint/build: clean; bundle ≤ 285 kB
  - Playwright: 13 foundation + 36 visual + 4 pilot-features + 30 cross-browser + 15 regression = **98 passing**
  - Static: ruff + format + vocab + PII + OpenAPI + migrations all clean
- Re-run 3x baseline stability check on Phase A4 + A5 baselines

**A7.4 Coverage gate** (per §3.14, ≥ 90%):
- Backend: `pytest --cov=web/api/serializers --cov=web/api/audit --cov=web/api/views --cov-fail-under=90` on touched modules
- Frontend: `vitest --run --coverage --coverage.thresholds.lines=90` on 8 new/modified component files

**A7.5 Tag cut** (per §3.22):
```bash
git tag -a v0.1.3-engine-display-polish -m "Engine→UI display polish — closes 5 done-criteria gaps from v0.1.2-engine-display:
- GoalAllocationSection consumes engine goal_rollup (locked #5)
- OptimizerOutputWidget consumes link_recommendations (A3.3)
- Stale-state UX with 4 status variants + IntegrityAlertOverlay for hash_mismatch (locked #18, §3.2)
- MovesPanel pill via shared SourcePill (§3.3)
- Demo script + axe + cross-browser + automated regression coverage"
```

**Push gate:** wait for explicit user authorization. Do NOT push (or push tags) unless user says "push to origin."

**Commit:** `docs(engine-ui): close-out — gap-closure handoff + decisions update + session-state refresh + starter-prompt deleted`

---

## §3. Pre-flight verification (mandatory; ~5 min)

**Run BEFORE any code change. Halt + AskUserQuestion if any gate red.**

### Sub-session #2 entry baseline (HEAD: `987f8f8`)
```bash
cd /Users/saranyaraj/Projects/github-repo/mp2.0

# 1. HEAD + working tree state
git status --short --branch          # expect: clean tree at 987f8f8 (only .claude/ + test-results/ untracked)
git log --oneline -5                 # expect: 987f8f8 → c5a7e02 → 95dfd01 → f6e2ef8 → 1ea5338
git tag -l "v0.1*"                   # expect: v0.1.0-pilot + v0.1.1-improved-intake + v0.1.2-engine-display

# 2. Backend gate suite (~3 min)
docker compose exec -T backend bash -c "cd /app && uv run pytest --tb=no --ignore=web/api/tests/test_perf_budgets.py -q"
# expect: 872 passed, 2 skipped
docker compose exec -T backend bash -c "cd /app && uv run pytest web/api/tests/test_perf_budgets.py --tb=no -q"
# expect: 9 passed (isolated; full-suite run flaky on busy box)

# 3. Frontend gates (~30s)
cd frontend && npm run typecheck && npm run lint && npm run build && npm run test:unit -- --run && cd ..
# expect: 195 Vitest in 22 files; bundle 268.13 kB gzipped

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
    jq '.latest_portfolio_run | {external_id, status, run_signature}'
# expect: status="current"; non-null external_id + run_signature
```

### Sub-session #3 entry baseline (HEAD: post-A4 commit)
- Backend: 872 passed (unchanged from sub-session #2)
- Frontend: 227 Vitest in 24 files (was 195 + 32 from A3/A4)
- Bundle: ≤ 285 kB gzipped
- visual-verification: 34 chromium passing

---

## §4. Locked decisions reference

### 25 §3 locked-this-session decisions (full table in `~/.claude/plans/i-want-you-to-jolly-beacon.md`)

Most-load-bearing for sub-session #2 + #3:

- **§3.1** Slider drag UX: engine pill on saved view; calibration_drag pill ONLY during slider drag; flips back on save (engine auto-regenerates per locked #74)
- **§3.2** Stale-overlay fires on 4 statuses: `invalidated/superseded/declined → StaleRunOverlay` (regenerable); `hash_mismatch → IntegrityAlertOverlay` (engineering-only)
- **§3.3** MovesPanel source pill in scope at A2 (DONE in sub-session #1)
- **§3.4** Stale chip + overlay copy: "Stale: regenerate to refresh" (technical-precise)
- **§3.5** hash_mismatch backend audit emit on serializer access, rate-limited via `events.filter(...).exists()` (DONE in sub-session #1 A1)
- **§3.6** NO per-stale-view audit emit (status field in JSON is enough)
- **§3.7** Slider state lift: `isPreviewingOverride` lifted from `RiskSlider.isOverrideDraft` to `GoalRoute` via `onPreviewChange` callback (DONE in A2)
- **§3.8** Multi-session execution; THIS prompt is the boot artifact; deleted at A7
- **§3.9** English-only codebase confirmed; new keys land in `en.json` only
- **§3.10** Theme-token grep gate at every commit gate that uses new tokens
- **§3.11** 3x baseline-stability run for visual regression
- **§3.12** Pre-push CI smoke at A7 close-out
- **§3.13** PII-focused review pass at A7 (in addition to general code-reviewer)
- **§3.14** ≥90% line coverage gate (stricter than locked #61's 85%)
- **§3.15** Cross-browser extension (webkit + firefox) for new Goal-route surfaces
- **§3.16** Backwards-compat regression for pre-tag households (DONE in A1)
- **§3.17** Full ops-runbook entry for integrity-alert engineering response (DONE in A1)
- **§3.18** Hypothesis property suite for status + audit-dedup invariants (DONE in A1)
- **§3.19** NO new perf benchmarks; trust existing 9-test perf budget suite
- **§3.20** Automated browser regression coverage for 15 pre-existing flows
- **§3.21** API contract snapshot extension (4 state fixtures) (DONE in A1)
- **§3.22** New tag `v0.1.3-engine-display-polish` at A7
- **§3.23** NO frontend telemetry / Sentry breadcrumbs for stale overlay views
- **§3.24** NO backend rate limit on `/generate-portfolio/` (trust isPending + locked #74 sync timing)
- **§3.25** Pilot dress rehearsal at A6 (locked #95 reactivated)

### 111 prior locked decisions (in `docs/agent/decisions.md` "Engine→UI Display Integration (2026-05-03/04)")
Most relevant for sub-session #2:
- **#9** Failure surfacing: typed-skip silent + audit; unexpected → catch-all + audit + `latest_portfolio_failure` SerializerMethodField + Banner inline + Sonner toast
- **#18** Stale state UX: muted run-data + accent-bordered overlay with Regenerate CTA (Phase A4 implements)
- **#19** HouseholdPortfolioPanel mirrors RecommendationBanner failure pattern (Phase A4 implements)
- **#56** Strict P99 ≤ 1000ms threshold; sync engine.optimize() inline (Sandra/Mike P99=258ms)
- **#64** StrictMode double-invoke tests for every new component
- **#68** Bespoke modal/overlay a11y: aria-modal=true is NOT enough — explicit Esc + focus restore + click-outside; mirror DocDetailPanel pattern
- **#74** Auto-trigger SYNCHRONOUS inside `transaction.atomic`; response IS truth (not `transaction.on_commit`)
- **#85** Bundle size cap < 290 kB gzipped
- **#100** Real-Chrome smoke is USER manual (cannot be automated)
- **#X.10** Sub-agent verification protocol — Read every file the agent edited; re-run tests; spot-check citations; verify locked-decision compliance

---

## §5. Critical gotchas learned in sub-session #1 (specific code-level facts)

These are FACTS the next agent will hit. Read them BEFORE writing tests or code; the user has paid for these lessons via prior bug-finding rounds.

### Backend test infrastructure
- **`web.audit.AuditEvent` table is APPEND-ONLY via PL/pgSQL trigger** (`web/audit/migrations/0002_audit_immutability.py`). Cannot DELETE rows. **Pattern:** capture before/after counts, assert delta. Don't `AuditEvent.objects.filter(...).delete()` in tests — it raises.
- **`PortfolioRunEvent` IS deletable** (no immutability trigger). Safe to `run.events.all().delete()` between Hypothesis examples.
- **Hypothesis with Django:** use `transactional_db` fixture (NOT `db`) when running multiple `@given` examples within one test; `db` (transaction=False) wraps the whole test in one transaction → cross-example state leaks. Pattern: `@pytest.mark.django_db(transaction=True)` + UUID-unique advisor emails per example to avoid append-only audit dedup carryover.
- **Hypothesis text noise:** `st.text()` generates `\x00` null bytes which Postgres rejects in text columns. Filter: `st.text(alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00"), ...)`.

### Vitest test infrastructure
- **react-i18next is mocked in `frontend/src/test/setup.ts`** to return the i18n KEY itself (not the resolved English text). Tests assert on key strings: `screen.getByText("goal_allocation.from_run")` not `screen.getByText("Engine recommendation")`.
- **Vitest globals are NOT auto-imported** despite `globals: true` in `vitest.config.ts`. Must explicitly `import { beforeEach, describe, expect, it, vi } from "vitest"` — otherwise typecheck + lint fail.
- **`mockHousehold` factory at `frontend/src/__tests__/__fixtures__/household.ts`** is byte-for-byte against live Sandra/Mike payload (locked #55 verified). Already includes `latest_portfolio_run.status` field. Pattern: `mockHousehold({ latest_portfolio_run: mockPortfolioRun({ status: "invalidated", ... }) })`.
- **`@typescript-eslint/no-non-null-assertion` is enforced.** `movesState.data!.source` fails lint. Use `if (movesState.data) movesState.data.source = ...` or alternative narrowing.

### Backend serializer context propagation
- **`HouseholdDetailSerializer.get_latest_portfolio_run` MUST pass `context=self.context`** to nested `PortfolioRunSerializer(run, context=self.context).data`. Otherwise the nested serializer can't extract the requesting advisor's email for audit emission. Same for `get_portfolio_runs`. Fixed in A1 commit `95dfd01`.
- **`ClientDetailView.get` MUST pass `context={"request": request}`** to `HouseholdDetailSerializer(household, context={"request": request}).data`. Otherwise no request flows to nested serializers. Fixed in A1.

### Frontend tooling
- **Tailwind tokens at `frontend/tailwind.config.ts`** (not in a separate `tokens.css`). Theme-token grep: `grep -E "(accent.*2|warning|danger|muted)" frontend/tailwind.config.ts`. `warning` was missing pre-A0 and silently no-op'd; A0 added `warning: "#B87333"`.
- **No `@radix-ui/react-focus-scope` in package.json.** Bespoke modal focus management uses manual `useEffect` + `window.addEventListener("keydown")` + `ref.focus()` per [DocDetailPanel.tsx:56-67](frontend/src/modals/DocDetailPanel.tsx#L56) and [FeedbackButton.tsx:65-74](frontend/src/chrome/FeedbackButton.tsx#L65).
- **i18n FR file (`frontend/src/i18n/fr.json`) is a placeholder** with single `_comment` field. Per locked §3.9, English-only path; new keys land in `en.json` only.

### File:line reference for key contracts
- `_portfolio_run_status` — `web/api/serializers.py:317-340`
- Integrity-alert audit emission — `web/api/serializers.py:298-340` (new in A1)
- `findGoalRollup` / `findHouseholdRollup` / `findGoalLinkRecommendations` — `frontend/src/lib/household.ts:291-309`
- `<SourcePill>` — `frontend/src/goal/SourcePill.tsx`
- `mockHousehold` factory — `frontend/src/__tests__/__fixtures__/household.ts`
- `OptimizerOutputWidget` (Phase A3 target) — `frontend/src/goal/OptimizerOutputWidget.tsx`
- DocDetailPanel pattern (Phase A4 Esc handler reference) — `frontend/src/modals/DocDetailPanel.tsx:56-67`
- FeedbackButton pattern (alternative reference) — `frontend/src/chrome/FeedbackButton.tsx:65-74`
- Tailwind tokens — `frontend/tailwind.config.ts` (accent.2, warning, danger, muted)
- `RiskSlider.onPreviewChange` callback — `frontend/src/components/ui/RiskSlider.tsx:60-92`
- `GoalRoute.isPreviewingOverride` state — `frontend/src/routes/GoalRoute.tsx:38-50`
- AuditEvent immutability trigger — `web/audit/migrations/0002_audit_immutability.py`
- `_record_current_run_invalidations` (dedup pattern reference) — `web/api/views.py:3068+`

---

## §6. Reading list (priority order; ~15 min total)

1. **`MEMORY.md`** at `~/.claude/projects/-Users-saranyaraj-Projects-github-repo-mp2-0/memory/MEMORY.md` — auto-loaded; first entry "START HERE" points at `project_engine_ui_display.md`
2. **THIS FILE** — `docs/agent/post-tag-gap-closure-starter-prompt.md` — full context boot
3. **`~/.claude/plans/i-want-you-to-jolly-beacon.md`** — gap-closure plan; read §3 table (25 locked-this-session decisions §3.1-§3.25) + the next-phase section (A3 / A4 / A5 / A5.5 / A6 / A7)
4. **`docs/agent/handoff-log.md`** last 1-3 entries — sub-session #1 close-out (Phases A0+A1+A2 specifics)
5. **`docs/agent/session-state.md`** — current HEAD + phase line; **REFRESH at sub-session boundary per §X.1**
6. **`docs/agent/decisions.md`** "Engine→UI Display Integration (2026-05-03/04)" section — 111 pre-existing locked decisions
7. **`docs/agent/ops-runbook.md`** §2 "Portfolio Run Integrity Alert" — engineering response procedure (consumed by Phase A4 IntegrityAlertOverlay copy)
8. **`MP2.0_Working_Canon.md`** — only deep-read §9.4 architecture invariants + §11.8.3 real-PII + §6.3a vocabulary if touching governed surfaces
9. **`frontend/src/goal/SourcePill.tsx`** + **`frontend/src/goal/GoalAllocationSection.tsx`** — read these BEFORE Phase A3 (mirror the SourcePill pattern)
10. **`frontend/src/modals/DocDetailPanel.tsx:56-67`** + **`frontend/src/chrome/FeedbackButton.tsx:65-74`** — read these BEFORE Phase A4 (mirror the focus-trap pattern per locked #68)

---

## §7. Anti-patterns — DO NOT REPEAT

These bug classes have been paid for (in real time) by the user. Each cost a round of "Is everything REALLY done?" pushback in prior sessions.

| Anti-pattern | Reality |
|---|---|
| **"Tests pass = ship-ready"** | sub-session #11 verification pass found StrictMode bug class that subagent gates missed; foundation e2e is the catch (always re-run after ANY frontend touch) |
| **"Subagent says it's done"** | Verify by Reading every file the subagent touched (per locked #X.10); subagent gates pass against subagent-written fixtures, not against `foundation.spec.ts`. mockHousehold cost-key bug at `2bd77d3` was exactly this. |
| **Mock fixtures that don't mirror production payload shape** | mockHousehold byte-for-byte verified locked #55. Refresh fixture if drift suspected. |
| **`setState((prev) => mutate-closure-array)` StrictMode-double-update class** | Caused DocDropOverlay regression at `bca0112`; the setState updater MUST be pure; compute new list OUTSIDE the updater (per locked #64). Phase A4 overlay state changes must follow this discipline. |
| **`aria-label` text vs visible text divergence** | Playwright `getByRole({ name: /.../i })` resolves to aria-label NOT visible text; use less-anchored regex (`/save.*draft/i`) or `getByText` for visible-text matches (locked #71). |
| **Bespoke modal/overlay needs explicit Esc handler + focus restore + click-outside** | `aria-modal=true` is NOT enough; FeedbackModal Esc bug at `b14a199` was exactly this. Phase A4 StaleRunOverlay MUST mirror DocDetailPanel pattern (locked #68). |
| **`str(exc)` anywhere in DB columns / API response bodies / audit metadata** | Use `safe_audit_metadata` from `web/api/error_codes.py`. Bedrock errors carry extracted client text → PII leak risk. Phase A1 already followed this; future audit emissions must too. |
| **Hardcoded fund_ids on frontend** | Use canonical `sh_*` from CMA fixture; never hardcode `equity_fund` etc. |
| **Auto-regenerate on `INVALIDATED_BY_CMA` event** | Manual regenerate per canon §4.7.3 (locked #37). Phase A4 Regenerate is advisor-clicked, not automatic. |
| **Auto-COMMIT households during R10 sweep or auto-trigger paths** | This plan auto-TRIGGERS portfolio generation on already-committed households; does NOT auto-commit ungated workspaces. Don't conflate. |
| **Honest audit when user pushes back** | Three rounds of "Is everything done?" each surfaced a real bug; user's pushback is signal, not noise. Don't restate confidence — re-run higher-level tests + surface gaps explicitly. |
| **Skip the per-phase verbose ping discipline** | Production-quality-bar.md §9 + locked decision #44 require ~400-word verbose pings. Don't shortcut. |
| **Skip Phase A6 because "tests pass"** | The FileList ref race + Esc handler bug class only surface in real Chrome (NOT headless Playwright). Locked #100 is mandatory. |
| **`AuditEvent.objects.filter(...).delete()` in tests** | Audit table has PL/pgSQL append-only trigger. Cannot delete. Use before/after count delta pattern. |
| **`@pytest.mark.django_db(transaction=False)` + Hypothesis** | Cross-example state leaks. Use `transaction=True` + UUID-unique data per example. |
| **`movesState.data!.source = "X"` in Vitest tests** | `@typescript-eslint/no-non-null-assertion` is enforced. Use `if (movesState.data) movesState.data.source = "X"`. |

---

## §8. Per-phase ping format (verbose ~400 words; locked #45 + production-quality-bar.md §9)

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

If context approaches 80% mid-phase OR you hit a stop condition:

1. **Halt at next natural breakpoint** — typically completion of current logical sub-task (one Vitest file done, one component refactored, one test list completed)
2. **Commit progress** with explicit `wip:` prefix if phase is incomplete: `wip(goal): OptimizerOutputWidget refactor; 5/7 Vitest tests written; remaining 2 + StrictMode test pending`
3. **Write handoff-log entry** covering what's done + what remains within this phase + specific `file:line` resumption point
4. **Update session-state.md** headline
5. **Suggest `/compact`** with continuation cue: "Phase A<N> partial; <X-Y> remaining. Read post-tag-gap-closure-starter-prompt.md to continue."

NEVER strand uncommitted work across a halt. Plan file + handoff-log are the durable contract; mid-phase context loss is recoverable only via these.

---

## §10. Continuity discipline (per locked §X.1)

### At every sub-session boundary (END of A2, A4, A7):
1. Commit any uncommitted work
2. Update `docs/agent/session-state.md` headline paragraph
3. Append per-phase verbose handoff-log entry per §X.5 template
4. Update MEMORY.md ONLY at A7 close-out (sub-session boundaries when state changes materially)
5. Commit docs as a single commit: `docs(engine-ui): handoff-log + session-state for sub-session #N`
6. Suggest `/compact` to user

### At every sub-session START (post-`/compact`):
1. Read `MEMORY.md` (auto-loaded)
2. Read THIS FILE
3. Read `docs/agent/handoff-log.md` last 1-3 entries
4. Read `docs/agent/session-state.md`
5. Read plan §3 + next-phase section
6. Run §3 pre-flight verification
7. Output status post under 100 words confirming: dossier read, HEAD matches expected, gates green, understanding of next phase

If steps 1-7 fail, halt + ask user. Never proceed against a broken or unexpected baseline.

---

## §11. Communication style (per user-stated preferences)

- **Cite specific evidence** (commit hash, regression test ids, gate-output tail) — never opinions like "looks good" / "should work" / "ready to ship"
- **Verbose per-phase pings with `file_path:line_number`** specifics
- **Specific test counts only AFTER the suite runs** (use "let me check" until then)
- **Latency claims only after measurement**
- **Don't overclaim.** "Tests pass" needs the actual count + tail. "Engine works" needs the probe output.
- **The user redirects when you drift.** Treat redirects as normal input; reset cleanly.
- **When halting:** clean handoff entry + commit any wip + ping via AskUserQuestion. Don't strand uncommitted work across a halt.
- **Per-phase ping discipline:** every phase exit pings with §8 format. No shortcuts.

---

## §12. First concrete action (mode-dependent)

### Mode A (continuing planning conversation):
Skim §3 locked-this-session decisions in plan file (`~/.claude/plans/i-want-you-to-jolly-beacon.md`), then ASK via `AskUserQuestion`:
> "Plan has 25 §3 locked-this-session decisions captured + multi-session split + Phase A5.5 regression suite. Sub-session #1 shipped at HEAD `987f8f8` (872 backend + 195 Vitest passing). Anything else to refine, or are we approved to begin sub-session #N execution?"

### Mode B (sub-session #2 starting; HEAD: `987f8f8`):
1. Run §3 pre-flight (~5 min)
2. Output status post under 100 words confirming dossier + gates + mode
3. Begin **Phase A3** per plan file (`OptimizerOutputWidget` engine-first refactor; mirrors A2 SourcePill pattern; ~75 min; 7 Vitest tests)
4. After A3 commit + halt-and-flush gate green, proceed to **Phase A4** (Stale-state UX with 4 status variants + IntegrityAlertOverlay; ~150 min; 25 new Vitest tests + 2 visual baselines)
5. End sub-session #2 with close-out commit (handoff-log + session-state) → suggest `/compact`

### Mode B (sub-session #3 starting; HEAD: post-A4 commit):
1. Run §3 pre-flight
2. Begin **Phase A5** (demo + axe + visual + cross-browser; ~75 min)
3. **Phase A5.5** (15 automated browser regression tests; ~3-4 hr; HEAVIEST)
4. **Phase A6** USER MANUAL — present checklist + dress rehearsal; collect user smoke results
5. **Phase A7** close-out — 2 subagent dispatches + 90% coverage gate + tag `v0.1.3-engine-display-polish` + delete THIS FILE per §3.8 lifecycle
6. Wait for explicit user authorization to push

---

## §13. Stop conditions (halt + AskUserQuestion when these fire)

1. Phase A0/A3/A5 baseline gate red BEFORE any code change
2. Engine probe at sub-session entry returns ≠ 200 with valid output
3. Bundle size grows past 290 kB gzipped (locked #85)
4. Vocab CI flags any new copy
5. PII grep guard fails on a new commit
6. Any phase wall-clock exceeds 5 hr
7. Code-reviewer subagent (A7.1) surfaces BLOCKING findings → fix before tag
8. PII-focused review (A7.2) surfaces leak vectors → fix before tag
9. 90% coverage gate (A7.4) fails → add tests before commit
10. Visual baselines drift across 3 consecutive runs (§3.11) → halt; investigate determinism
11. Phase A6 user smoke flags console warnings, visual regressions, or focus-trap escapes
12. Phase A6 dress rehearsal flags any step > threshold (8s non-trigger / 10s trigger per locked #88)
13. User says "push" before A7.5 tag cut → halt; one final commit + tag before push
14. HEAD has drifted unexpectedly past expected sub-session entry baseline
15. Sub-agent claims work done but file inspection shows incomplete (per locked #X.10)

---

## §14. References (file:line index — fastest path to any contract)

### Backend
| File:line | Purpose |
|---|---|
| `web/api/serializers.py:317-340` | `_portfolio_run_status` (5-state computation) |
| `web/api/serializers.py:298-340` | Integrity-alert audit emission (A1, new) |
| `web/api/serializers.py:148-150` | `get_latest_portfolio_run` with context propagation (fixed in A1) |
| `web/api/views.py:551` | `ClientDetailView.get` passing context (fixed in A1) |
| `web/api/views.py:3068+` | `_record_current_run_invalidations` (dedup pattern reference) |
| `web/api/views.py:1226-1278` | `CMASnapshotPublishView.post` (CMA publish → INVALIDATED_BY_CMA fan-out) |
| `web/api/models.py:338-350` | `PortfolioRunEvent.EventType` (9 event types) |
| `web/audit/writer.py:8-22` | `record_event` signature |
| `web/audit/migrations/0002_audit_immutability.py` | PL/pgSQL append-only trigger (DON'T DELETE audit rows) |

### Frontend
| File:line | Purpose |
|---|---|
| `frontend/src/lib/household.ts:291-309` | `findGoalRollup` / `findHouseholdRollup` / `findGoalLinkRecommendations` |
| `frontend/src/lib/household.ts:65-85` | `Allocation` / `Rollup` / `LinkRecommendation` types |
| `frontend/src/lib/household.ts:222-228` | `latest_portfolio_failure` field |
| `frontend/src/lib/preview.ts:280-291` | `MovesResponse` type (with `source` field) |
| `frontend/src/lib/preview.ts:117-129` | `useSleeveMix` hook |
| `frontend/src/lib/preview.ts:362-394` | `useGeneratePortfolio` mutation |
| `frontend/src/goal/SourcePill.tsx` | Shared engine/calibration/calibration_drag pill (A2) |
| `frontend/src/goal/GoalAllocationSection.tsx` | Engine-first ideal bars (A2) |
| `frontend/src/goal/MovesPanel.tsx` | Source pill + engine signature (A2) |
| `frontend/src/goal/RecommendationBanner.tsx` | 3 states; A4 adds 4 stale-status branches |
| `frontend/src/goal/AdvisorSummaryPanel.tsx` | Per-link advisor summaries |
| `frontend/src/goal/OptimizerOutputWidget.tsx` | **A3 TARGET** — currently calibration-only |
| `frontend/src/routes/GoalRoute.tsx:38-50` | `isPreviewingOverride` state ownership |
| `frontend/src/routes/HouseholdPortfolioPanel.tsx` | Engine rollup display; A4 adds stale chip |
| `frontend/src/components/ui/RiskSlider.tsx:60-92` | `onPreviewChange` callback |
| `frontend/src/modals/DocDetailPanel.tsx:56-67` | Esc handler + focus restore pattern (A4 reference) |
| `frontend/src/chrome/FeedbackButton.tsx:65-74` | Esc handler pattern (A4 alt reference) |
| `frontend/src/__tests__/__fixtures__/household.ts` | mockHousehold byte-for-byte fixture (locked #55) |
| `frontend/src/test/setup.ts` | Vitest setup (i18n mock returns key-as-text) |
| `frontend/tailwind.config.ts` | Theme tokens (accent, accent-2, warning, danger, muted) |
| `frontend/src/i18n/en.json` | i18n keys; `goal_allocation.*` namespace already populated for A2 |

### Plan + docs
| File | Purpose |
|---|---|
| `~/.claude/plans/i-want-you-to-jolly-beacon.md` | Plan file (25 §3 decisions; 8 phases) |
| `docs/agent/decisions.md` | 111 prior locked decisions |
| `docs/agent/ops-runbook.md` §2 | Portfolio Run Integrity Alert engineering response |
| `docs/agent/handoff-log.md` | Per-phase verbose entries |
| `docs/agent/session-state.md` | Current state headline (refresh at sub-session boundary) |
| `docs/agent/demo-script-2026-05-04.md` | Demo script (Phase A5 updates) |

---

## §15. First message to the user (post-boot template)

After §3 pre-flight + §12 mode determination:

```
Booted from post-tag-gap-closure-starter-prompt.md.

HEAD: <commit>          # expected: 987f8f8 (sub-session #2 entry) | post-A4 commit (sub-session #3 entry)
Pre-flight: <pass/fail per gate>
  - Backend pytest: <count> passed (expected: 872 + 2 skipped at sub-session #2 entry)
  - Vitest: <count> in <files> (expected: 195 in 22)
  - Bundle: <kB> gzipped (expected: ≤ 285 kB; current 268.13)
  - Static guards: <vocab/PII/OpenAPI status>
  - Engine probe: <status>/<run_signature[:8]> (expected: current/<sig>)
Mode: <A: continuing planning | B: approved + executing>
Phase scope: <next phase based on handoff-log>
Locked decisions: 25 §3 captured (plan §3) + 111 prior (decisions.md)

[If Mode A]: Anything else to refine, or are we approved to begin sub-session #N?
[If Mode B]: Beginning Phase <A3 | A5> per plan file.
```

Wait for user direction. Do not begin code changes until §3 confirmed green AND mode is unambiguous.

---

## §16. Final closer

This work is the foundation for the May 8 pilot. **Production-grade software for a limited user set; no excuses, no cutting corners.** Three things matter most:

1. **Production-quality testing.** 90% coverage gate, Hypothesis property invariants, JSON snapshot regression, automated browser regression of pre-existing flows, cross-browser stale UX, real-Chrome smoke. The pilot can't surface "but the tests passed" — testing IS the pilot validation.

2. **Production-quality UX.** SourcePill flips correctly mid-drag; stale overlay focus-trap doesn't escape; integrity alerts route to engineering not advisors. Each detail is paid for in pilot trust.

3. **Continuity discipline.** This prompt, the handoff-log, the plan file, the session-state — all are the cross-session memory. Future sessions hydrate from these. If you halt mid-phase, write the handoff entry. If you discover something the plan didn't capture, update the plan file (it's the only file editable in plan mode). The user has been burned by drift; never strand uncommitted work or unrecorded decisions.

**Begin with §3 pre-flight. Do not skip ahead.**
