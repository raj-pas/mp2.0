# Engine→UI Display Integration — Starter Prompt (Sub-Session #4 Entry, Full Mission Reference)

**Compiled:** 2026-05-04 AM, post-sub-sessions #1+#2+#3 close-out (HEAD `915eec7` after this rewrite).
**Lifecycle:** updated at each sub-session boundary per locked #69; deleted at A6.16 close-out per locked #11+#42 (work + decisions migrated to `docs/agent/decisions.md` per #91).
**Mission:** connect MP2.0 engine's frontier-optimized PortfolioRun output to the advisor's eyes via Goal route + Household route + auto-trigger on every committed-state mutation.
**Plan file (canonical):** `~/.claude/plans/i-want-you-to-jolly-beacon.md` — 111 locked decisions; §X continuity discipline; §Y comprehensive testing matrix; §Z embedded starter (this file's ancestor; predates sub-sessions #1-#3 work).

**This prompt is execution-ready for the entire remaining mission.** Sub-session #4 + #5 are detailed end-to-end (§6, §7) with command sets, sub-agent dispatch templates (§19), recovery procedures (§20), halt checkpoints (§21), final verification gate suite (§22), demo dress rehearsal (§23), rollback smoke (§24), and templates for CHANGELOG (§25), ops-runbook (§26), pilot-rollback (§27), decisions migration (§28), and design-system update (§29). A fresh post-compact session reading this file should be able to ship sub-sessions #4 + #5 without external discovery.

---

## §0. Mission + Hard Deadlines + Mandate

You are the technical lead continuing a 5-sub-session production-quality engineering effort. The engine works (`POST /api/clients/{id}/generate-portfolio/` returns 200 with valid `engine_output.link_first.v2`); sub-sessions #1+#2+#3 wired backend + frontend so the advisor now sees engine recommendations on Goal route + Household route. Sub-sessions #4+#5 add comprehensive testing + visual regression + tag bump + dress rehearsal that locked decision #15 ("ship complete production-quality scope, no cutting corners") requires before pilot launch.

- **Branch:** `feature/ux-rebuild`. As of HEAD `915eec7`, branch is **9 commits ahead of origin** + 11 commits past sub-session-#1 entry baseline `081cfc8`.
- **Demo to CEO + CPO:** Mon **2026-05-04** (TODAY) — runs against current HEAD; Sandra/Mike auto-seeds with PortfolioRun.
- **Pilot launch:** Mon **2026-05-08**.
- **No remote push.** User pushes Monday morning per locked direction.
- **Mandate (locked #15):** "ship complete production quality scope. No excuses or cutting corners." Sub-sessions #4+#5 are NOT optional.

---

## §1. Determine your mode FIRST

This prompt serves two cases. Read the user's last message + recent conversation to determine which:

- **Mode A: Continuing the planning conversation** — user hasn't explicitly approved sub-session #4 to begin executing yet; you're refining, asking questions, exploring edge cases. Do NOT run gates or change code without authorization. Use AskUserQuestion to interview.
- **Mode B: Approved + executing** — user has approved sub-session #4 (typical signals: "go ahead", "start sub-session #4", "let's execute", "proceed"). Run §3 boot, then §8 first concrete action.

If unclear after reading the user's last message: ASK via `AskUserQuestion` "Should I continue planning, or are we approved to begin sub-session #4 execution?" before any code change.

The user's prior-session directive was "Proceed straight through and everything... 'production-grade software for a limited user set'". If that directive carries forward, default to **Mode B**.

---

## §2. Reading list (priority order; ~10 min total)

1. **`MEMORY.md`** at `~/.claude/projects/-Users-saranyaraj-Projects-github-repo-mp2-0/memory/MEMORY.md` — auto-loaded; first entry "START HERE" points at the dossier.
2. **THIS FILE** (`docs/agent/engine-ui-display-starter-prompt.md`) — sub-session #4 boot + full mission reference.
3. **`docs/agent/handoff-log.md` last 5 entries** — sub-sessions #1+#2+#3 close-outs (entries dated 2026-05-03 PM through 2026-05-04 AM). Read in chronological order.
4. **`docs/agent/session-state.md`** — current headline (HEAD `915eec7`; phase line states sub-session #4 is next).
5. **`~/.claude/plans/i-want-you-to-jolly-beacon.md`** — the plan file. Read §1 (111 locked decisions table — focus on #17, #20, #46, #56, #60-#67, #80, #82, #84-#107) + §X (continuity discipline) + §Y (comprehensive testing matrix). Ignore the §Z embedded prompt (predates sub-sessions #1-#3).
6. **`docs/agent/next-session-starter-prompt.md`** (1,153 lines, post-pilot-release scope, complementary to this file) — read §3 (Tier 1 reading list) + §8 (10 anti-patterns burned in across sub-sessions #1-#11).
7. **`docs/agent/production-quality-bar.md`** — §3 test coverage map + §9 per-phase ping format (~400 words verbose ping discipline).
8. **`MP2.0_Working_Canon.md`** — only deep-read §9.4 architecture invariants + §11.8.3 real-PII discipline + §6.3a vocabulary if you're touching surfaces governed by them.

**Code references** (refresh your model of the implementation):
- `web/api/views.py:91-130` — 5 typed exceptions + `_map_engine_value_error`
- `web/api/views.py:621-865` — `_trigger_portfolio_generation` helper
- `web/api/views.py:866-871` — `_actor_for_user`
- `web/api/views.py:873-931` — `_trigger_and_audit` (typed-skip + unexpected-failure paths)
- `web/api/views.py:932-962` — `_trigger_and_audit_for_workspace` (linked_household gate per #27)
- `web/api/serializers.py:109-180` — HouseholdDetailSerializer.latest_portfolio_failure
- `web/api/preview_views.py:495-580` — MovesPreviewView with goal_rollups path + source field
- `frontend/src/lib/household.ts` — Allocation/Rollup/EngineOutput types + 4 helpers
- `frontend/src/goal/RecommendationBanner.tsx`, `AdvisorSummaryPanel.tsx`
- `frontend/src/routes/HouseholdPortfolioPanel.tsx`
- `frontend/src/lib/preview.ts:362-389` — `useGeneratePortfolio` mutation hook

---

## §3. Pre-flight verification (mandatory if Mode B; ~5 min)

**Baseline at HEAD `915eec7`** (verified via `git log` + green test runs in prior session):

```bash
cd /Users/saranyaraj/Projects/github-repo/mp2.0

# 1. HEAD + working tree state
git status --short --branch          # expect: feature/ux-rebuild ahead of origin by 9
git log --oneline -12                # expect newest 11 past 081cfc8: 915eec7 → 64af215 → 46f37e3 → 303e378 → 12a972d → 1462988 → 74e20ce → f003ed6 → c641cbb → b66eaaf → 8bf774b → 081cfc8
git tag -l "v0.1*"                   # expect: v0.1.0-pilot + v0.1.1-improved-intake (v0.1.2-engine-display NOT YET; cut at A6.10 in sub-session #5)

# 2. Backend gate suite (~2 min)
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 \
  uv run python -m pytest \
    scripts/demo-prep/test_r10_sweep.py \
    engine/tests/ extraction/tests/ web/api/tests/ web/audit/tests/ \
    --tb=no -p no:warnings --benchmark-disable
# expect: 869 passed, 7 skipped (was 854 baseline at 081cfc8; +15 net new)

uv run ruff check . && uv run ruff format --check .
bash scripts/check-pii-leaks.sh       # expect: PII grep guard: OK
bash scripts/check-vocab.sh           # expect: vocab CI: OK
bash scripts/check-openapi-codegen.sh # expect: OpenAPI codegen gate: OK
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 \
  uv run python web/manage.py makemigrations --check --dry-run

# 3. Frontend gates (~30s)
cd frontend && npm run typecheck && npm run lint && npm run build && npm run test:unit && cd ..
# expect: 82 Vitest passing in 13 files; bundle 267.21 kB gzipped (under 290 kB threshold per #85)

# 4. Live stack (Docker)
docker compose ps                    # expect: backend + db running. If backend missing, docker compose up -d backend && sleep 8.
curl -s -o /dev/null -w "backend: %{http_code}\n" http://localhost:8000/api/session/
curl -s -o /dev/null -w "frontend: %{http_code}\n" http://localhost:5173/
# expect: 200 / 200

# 5. Playwright (live stack required; ~3-10 min)
cd frontend && set -a && source ../.env && set +a
PLAYWRIGHT_BASE_URL=http://localhost:5173 \
  MP20_LOCAL_ADMIN_PASSWORD=change-this-local-password \
  npx playwright test --project=chromium e2e/foundation.spec.ts --reporter=line
# expect: 13/13 passed
PLAYWRIGHT_BASE_URL=http://localhost:5173 \
  MP20_LOCAL_ADMIN_PASSWORD=change-this-local-password \
  npx playwright test --project=chromium e2e/visual-verification.spec.ts --reporter=line
# EXPECT: 18 passed, 6 failed (Niesner ReviewScreen + ConflictPanel + DocDetailPanel
# tests fail because reset-v2-dev.sh wiped R10 sweep state). NOT A REGRESSION FROM
# SUB-SESSIONS #1-#3 — failures are STATE-DEPENDENT. To get 24/24: run upload_and_drain.py
# for Niesner first. Per locked #95, A6.15 demo dress rehearsal in sub-session #5
# runs FULL reset + re-upload Seltzer/Weryha/Niesner; this restores 24/24 baseline.
# Sub-session #4 should NOT chase these failures.
PLAYWRIGHT_BASE_URL=http://localhost:5173 \
  MP20_LOCAL_ADMIN_PASSWORD=change-this-local-password \
  npx playwright test --project=webkit --project=firefox e2e/cross-browser-smoke.spec.ts --reporter=line
# expect: 10 passed
cd ..

# 6. Live engine probe verification
set -a && source .env && set +a
uv run python -c "
import os, requests
s = requests.Session()
s.get('http://localhost:8000/api/session/').raise_for_status()
csrf = s.cookies.get('csrftoken')
r = s.post('http://localhost:8000/api/auth/login/',
  json={'email':'advisor@example.com','password':os.environ['MP20_LOCAL_ADMIN_PASSWORD']},
  headers={'X-CSRFToken':csrf,'Referer':'http://localhost:8000'})
r.raise_for_status()
r = s.get('http://localhost:8000/api/clients/hh_sandra_mike_chen/')
hh = r.json()
print('latest_portfolio_run.run_signature[:8]:', (hh.get('latest_portfolio_run') or {}).get('run_signature', '')[:8])
print('latest_portfolio_failure:', hh.get('latest_portfolio_failure'))
"
# expect: signature like '62f8cf06' (8-char hex; varies); failure=None
```

**If ANY check is red BEFORE you change anything, halt + AskUserQuestion.** The environment is wrong; do not proceed.

**Critical**: 6 visual-verification failures are EXPECTED and NOT a regression. They unblock at A6.15 (sub-session #5) per locked #95.

---

## §4. What's done (sub-sessions #1+#2+#3) — concise inventory

### Sub-session #1 (5 commits; `8bf774b` → `74e20ce`)

- **A0** — Pre-flight green; **A0.2 latency probe** (10 iterations × 3 households) locked **SYNC-INLINE** path: Sandra/Mike P99=258ms · medium-stress P99=239ms · large-stress P99=235ms; all under 1000ms threshold per locked #56. Stress fixtures persisted at `engine/fixtures/stress_household_{medium,large}.json`. **A0.4 grep audit** identified ~17 affected test files. **A0.3** verified `commit_reviewed_state` line numbers (function@495 / record_event@529 / return household@536; 7-line drift from plan, acceptable).
- **A1** — `personas/sandra_mike_chen/client_state.json` refreshed: RiskProfile (Q1=5/Q2=B/Q3=career/Q4=B → anchor=22.5/score=3/Balanced) + 7 canonical sh_* fund holdings (total $1,308,000) + advisor_pre_ack (disclaimer v1 + tour). `load_synthetic_personas` extended with `_load_risk_profile` + `_load_advisor_pre_ack`. `reset-v2-dev.sh` ordering FIXED: `bootstrap_local_advisor` BEFORE `load_synthetic_personas`. 4 smoke tests in `web/api/tests/test_sandra_mike_fixture_smoke.py`.
- **A2a** — 5 typed exceptions + `_map_engine_value_error` at `web/api/views.py:91-130`. Helper trio: `_trigger_portfolio_generation(household, user, *, source) -> PortfolioRun` (helper-managed atomic per #81; reusable check OUTSIDE atomic so audit emits persist on raise); `_trigger_and_audit(...)` (typed-skip + unexpected-failure audit paths per #9); `_trigger_and_audit_for_workspace(...)` (linked_household_id gate per #27). 4 trigger points wired (review_commit / wizard_commit / override / realignment). `latest_portfolio_failure` SerializerMethodField on `HouseholdDetailSerializer`. 8 regression tests.

### Sub-session #2 (commit `1462988`)

- **A2b** — 4 NEW workspace-level triggers (#5-#8): conflict_resolve (single + bulk variants), defer_conflict, fact_override, section_approve. All gated on `workspace.linked_household_id is None` per locked #27 → silent-skip + emit `portfolio_generation_skipped_post_<source>` audit with `metadata.skipped_no_household=True`.
- **A3a** — `MovesPreviewView` reads `ideal_pct` from `latest_portfolio_run.output.goal_rollups[goal_id]` when run exists; SLEEVE_REF_POINTS calibration as fallback. Response includes `source: "portfolio_run" | "calibration"`. 3 regression tests.

### Sub-session #3 (commits `12a972d`, `303e378`, `46f37e3`)

- **A1+A5 follow-up** — `load_synthetic_personas` auto-seeds initial PortfolioRun for Sandra/Mike at end of fixture load.
- **A3.1 frontend types** — `frontend/src/lib/household.ts`: `Allocation`, `Rollup`, `ProjectionPoint`, `EngineOutput`, `FanChartPoint`, `CurrentPortfolioComparison`, full `LinkRecommendation` shape, `PortfolioRunLinkRow`, `PortfolioRun.output: EngineOutput | null`, `HouseholdDetail.latest_portfolio_failure`. 3 helpers: `findGoalRollup`/`findHouseholdRollup`/`findGoalLinkRecommendations`.
- **A3.5** — `RecommendationBanner.tsx` (140 LoC; 3 states; aria-live="polite" per #109; Sonner toast on failure per #9). `AdvisorSummaryPanel.tsx` (61 LoC). `HouseholdPortfolioPanel.tsx` (150 LoC; mirrors Banner failure pattern per #19).
- **A3.6** — `useGeneratePortfolio` mutation hook in `lib/preview.ts`.
- **A3.7** — ~24 i18n keys under `routes.household.*` + `routes.goal.*` per #75.
- **A3.8 / A4** — RecommendationBanner above Goal KPI strip; AdvisorSummaryPanel below GoalAllocationSection; HouseholdPortfolioPanel between modals + treemap on HouseholdRoute.

### Test counts at HEAD `915eec7`

| Suite | At `081cfc8` baseline | At `915eec7` | Delta |
|---|---|---|---|
| Backend pytest | 854 passed, 7 skipped | **869 passed, 7 skipped** | +15 (4 A1 smoke + 8 A2a auto-trigger + 3 A3a moves) |
| Frontend Vitest | 82 in 13 files | **82 in 13 files** | 0 (no new component tests yet — A6.0 covers) |
| Foundation e2e | 13 in chromium | **13 in chromium** | 0 |
| Visual-verification | 24 in chromium | **18 passed, 6 failed (state-dependent)** | -6 (R10 sweep wiped; A6.15 restores) |
| Cross-browser | 10 in webkit+firefox | 10 (expected stable) | 0 |
| Bundle size gzipped | 258 kB | **267.21 kB** | +9.21 kB (under 290 kB threshold per #85) |

---

## §5. Locked decisions (111 captured; the most-load-bearing for sub-sessions #4+#5)

The plan file §1 has the full table. For sub-sessions #4+#5 work, these are critical:

**Architecture (load-bearing for sub-session #4 testing)**:
- **#14** 8 trigger points (4 original + 4 workspace-level) — already wired
- **#27** Workspace-level triggers gate on linked_household_id None
- **#56** P99 ≤ 1000ms strict threshold (sync-inline locked at A0.2)
- **#74** Sync-inline auto-trigger; response IS truth (no on_commit polling)
- **#80** PostgreSQL pool to 150; verify `max_connections` ≥ 200
- **#81** Helper-managed `transaction.atomic` (Django nested-atomic uses savepoints)
- **#102** Pool capacity regression at 120 concurrent connections

**Testing matrix (load-bearing for sub-session #4)**:
- **#17** Comprehensive Vitest scope (~60-80 unit tests across new components)
- **#20** A6 sub-agent orchestration: 3 sequential rounds, 2 parallel agents per round
- **#55+#84** mockHousehold factory at `frontend/src/__tests__/__fixtures__/household.ts` (byte-for-byte production payload shape per #X.10 lesson)
- **#60** §Y comprehensive testing & regression matrix (14 layers)
- **#61** 85% line coverage gate on touched modules
- **#64** StrictMode double-invoke tests for every new component
- **#71** Test selectors must match accessible-name resolution (aria-label > visible text)
- **#82** Visual-verification spec is single source of truth; A6 round 3 EXTENDS it
- **#92** Sub-session #4 budget: 5-7 hr (sync-inline path)
- **#96** Full advisor lifecycle integration test in A6.3
- **#97** Pre-A2 backwards-compat integration test in A6.3
- **#98** Stale UX 3-layer test
- **#99** Audit-trail Hypothesis property test in A6.4
- **#100** Real-Chrome smoke at every sub-session boundary
- **#101** HouseholdDetail JSON-shape snapshot test
- **#104** A3.1 expectTypeOf type-safety regression tests
- **#106** Vitest cache-invalidation tests for `useGeneratePortfolio`
- **#107** A6 render-perf benchmark
- **#X.10** Sub-agent verification protocol

**Sub-session #5 specific**:
- **#9** Failure surfacing: typed-skip silent + audit; unexpected toast + inline error
- **#11** Tag bump v0.1.2-engine-display + design-system.md update at end of A6
- **#18** Stale state UX: muted run-data + accent-bordered overlay with Regenerate CTA
- **#19** HouseholdPortfolioPanel mirrors RecommendationBanner failure pattern
- **#21** CHANGELOG + ops-runbook entries per A6.13
- **#22** A6.11 real-PII auto-trigger smoke (Niesner)
- **#23** Cross-browser scope: A6 manual gate + documented (NOT CI-integrated)
- **#24** Fan chart: dual-line (engine canonical + calibration what-if) — DEFERRED to sub-session #5 if needed; current AdvisorSummaryPanel sufficient for demo
- **#79+#86** A6.11 Niesner: delete first, then upload + drain + commit
- **#83** CHANGELOG entry version-stamped at A6.13 as `[v0.1.2-engine-display]`
- **#88** Demo dress rehearsal: 10s threshold for trigger steps; 8s for non-trigger
- **#89** OTEL spans wrap helper (no-op locally; backend-ready)
- **#90** Dual-line FanChart includes explicit Legend component (DEFERRED if #24 deferred)
- **#91** A6.16 migrate all 111+ decisions to `decisions.md`
- **#95** A6.15 dress rehearsal: FULL reset + re-upload Seltzer/Weryha/Niesner
- **#103** A6.13c rollback smoke test
- **#108** Trust route-level ErrorBoundary (no per-component boundary)
- **#109** aria-live="polite" on RecommendationBanner + HouseholdPortfolioPanel
- **#110** Verify accent-2 + muted tokens at A3.5 commit time

---

## §6. Sub-session #4 phase scope (A6 round 1+2; estimated 5-7 hr per locked #92)

### A6 Round 1 (parallel sub-agent dispatch per locked #20)

Dispatch 2 sub-agents in a SINGLE message with two Agent tool calls. See **§19** for sub-agent prompt templates.

**Agent A — Hypothesis property suites (3 files; ~300 LoC)**:
1. `web/api/tests/test_auto_trigger_properties.py` — for any random sequence of N committed-state mutations, the PortfolioRun count is N+1 OR fewer (REUSED via signature match); all input/output/cma hashes deterministic; PortfolioRun.save() raises on existing pk preserved.
2. `web/api/tests/test_audit_metadata_invariants.py` (per #99) — `@given(exception_class)` walks all 5 typed exceptions + 3 representative unexpected (ValueError, RuntimeError, KeyError); asserts AuditEvent.count() increments by exactly 1 per trigger fire; metadata.reason_code is the typed exception class name; PII regex grep on metadata JSON returns zero matches for SIN-pattern (`\d{3}-\d{3}-\d{3}`) + account-number pattern + email.
3. `web/api/tests/test_workspace_trigger_gate_properties.py` — for triggers #5-#8: `linked_household_id is None` → emits `portfolio_generation_skipped_post_<source>` audit + returns None; linked → fires + REUSED expected for same-input.

**Agent B — Vitest comprehensive (~60-80 unit tests)**:
- `frontend/src/__tests__/__fixtures__/household.ts` (NEW per locked #84) — mockHousehold + mockPortfolioRun + mockEngineOutput + mockRollup + mockLinkRecommendation; defaults match Sandra/Mike-equivalent shape captured byte-for-byte from live `/api/clients/hh_sandra_mike_chen/` response.
- `frontend/src/goal/__tests__/RecommendationBanner.test.tsx` — render variants (run / no-run / failure / pending) + Generate click + ARIA aria-live + keyboard nav + StrictMode double-invoke per #64.
- `frontend/src/goal/__tests__/AdvisorSummaryPanel.test.tsx` — single-link + multi-link rendering + edge cases.
- `frontend/src/routes/__tests__/HouseholdPortfolioPanel.test.tsx` — same coverage as Banner per #19 mirror.
- `frontend/src/lib/__tests__/household.test.ts` (NEW or extend) — findGoalRollup / findHouseholdRollup / findGoalLinkRecommendations edge cases.
- `frontend/src/lib/__tests__/preview.test.ts` (extend) — useGeneratePortfolio cache-invalidation per #106.
- `frontend/src/lib/__tests__/household.types.test.ts` (NEW) — expectTypeOf assertions per #104.

**Main thread** reviews each agent's output (per #X.10): Read every file the agent claims to have edited; re-run agent's tests locally; spot-check file:line citations; verify locked-decision compliance (no `str(exc)`, no vocab violations); commit each agent's work as a separate logical commit with `subagent: <agent-name>` attribution line.

### A6 Round 2 (parallel sub-agent dispatch)

**Agent C — Concurrency stress + auth/RBAC + pool capacity**:
- Extend `web/api/tests/test_concurrency_stress.py` for the 8 trigger paths (100 parallel each).
- New `web/api/tests/test_connection_pool_capacity.py` per #102.
- Extend `web/api/tests/test_auth_rbac_matrix.py` for the 4 NEW trigger endpoints.

**Agent D — Perf benchmarks + integration tests**:
- Extend `web/api/tests/test_perf_budgets.py` per #56 (P50<250ms / P99<1000ms).
- New `web/api/tests/test_full_advisor_lifecycle_with_auto_trigger.py` per #96.
- New `web/api/tests/test_pre_a2_portfolio_run_compat.py` per #97.
- New `web/api/tests/test_household_detail_serializer_snapshot.py` per #101.

### A6 Round 1+2 close-out (main thread)

After Agent reviews + commits land, dispatch `pr-review-toolkit:code-reviewer` subagent per locked #X.10 + #20. Fix all surfaced findings BEFORE moving to sub-session #5.

Run **full gate suite** at sub-session #4 end (see §22 for the canonical command set).

**Estimated wall-clock**: 5-7 hr per locked #92.

**Checkpoints** (per §21): halt-and-flush eligible after Round 1 commits + Round 2 commits + code-reviewer finding fixes.

---

## §7. Sub-session #5 phase scope (A6 round 3 + close-out; estimated 4-6 hr)

### A6 round 3 — Visual regression baselines (single sub-agent per #20; ~1.5 hr)

**Agent E — Visual regression baselines for engine→UI surfaces**:

Extend `frontend/e2e/visual-verification.spec.ts` with `test.describe("engine→UI display surfaces")` block per locked #82 (~16-20 new tests). Coverage:

- **RecommendationBanner** × 4 states (run / no-run / failure / stale).
- **HouseholdPortfolioPanel** × 4 states.
- **AdvisorSummaryPanel** × 2 states (single-link / multi-link).

Tests use `await expect(page).toHaveScreenshot()`; baselines committed under `frontend/e2e/__screenshots__/` (~10-15 PNG files; ~50-100 kB each; ~500 kB-1.5 MB total — acceptable per locked #63 repo footprint).

State setup: use Playwright's `page.evaluate()` to inject mock `latest_portfolio_run` / `latest_portfolio_failure` shapes into the React Query cache; OR drive via real auto-seed (run state) + DELETE PortfolioRun (no-run state) + simulate failure via env-flagged faulty CMA (failure state).

After Agent E returns, main thread reviews per #X.10 + commits.

### A6.9 — design-system.md update (~15 min)

Append "Engine output consumption" section to `docs/agent/design-system.md` per locked #11. See **§29** for the canonical content to append.

### A6.10 — Tag bump (~5 min)

After ALL gates green (per §22):

```bash
cd /Users/saranyaraj/Projects/github-repo/mp2.0
git tag -a v0.1.2-engine-display -m "Engine output displayed via PortfolioRun on Goal + Household routes; auto-trigger on commit/wizard/override/realignment + linked-HH-only on conflict_resolve/defer_conflict/fact_override/section_approve; latest_portfolio_failure SerializerMethodField; sync-inline auto-trigger per locked #74"
git tag -l "v0.1*"   # confirm: v0.1.0-pilot + v0.1.1-improved-intake + v0.1.2-engine-display
```

**DO NOT push the tag.** User pushes Mon morning per locked direction.

### A6.11 — Real-PII Niesner smoke (~30 min; per locked #79+#86)

Pre-authorized per locked #86: delete Niesner state first, then upload+drain+commit. Bedrock cost ~$0 (pre-paid via earlier sweep).

```bash
cd /Users/saranyaraj/Projects/github-repo/mp2.0
set -a && source .env && set +a

# 1. Reset Niesner state (per locked #86 pre-authorization scope; Sandra/Mike + Seltzer + Weryha unaffected)
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 \
  uv run python web/manage.py shell -c "
from web.api import models
hh_count = models.Household.objects.filter(external_id__icontains='niesner').delete()
ws_count = models.ReviewWorkspace.objects.filter(client_name__icontains='niesner').delete()
print(f'Deleted: {hh_count} households, {ws_count} workspaces')
"

# 2. Upload + drain + commit Niesner via the demo-prep script
uv run python scripts/demo-prep/upload_and_drain.py Niesner --expect-count 12

# 3. Verify auto-trigger fired + PortfolioRun created
uv run python -c "
import os, requests
s = requests.Session()
s.get('http://localhost:8000/api/session/').raise_for_status()
csrf = s.cookies.get('csrftoken')
r = s.post('http://localhost:8000/api/auth/login/',
  json={'email':'advisor@example.com','password':os.environ['MP20_LOCAL_ADMIN_PASSWORD']},
  headers={'X-CSRFToken':csrf,'Referer':'http://localhost:8000'})
r.raise_for_status()
r = s.get('http://localhost:8000/api/clients/?owned=1')
clients = r.json()['clients']
niesner = next((c for c in clients if 'niesner' in c.get('display_name', '').lower()), None)
if niesner is None:
    print('ERROR: Niesner not found post-commit')
else:
    r = s.get(f'/api/clients/{niesner[\"id\"]}/')
    hh = r.json()
    run = hh.get('latest_portfolio_run') or {}
    print(f'Niesner ID: {niesner[\"id\"]}')
    print(f'  PortfolioRun present: {bool(run)}')
    print(f'  signature[:8]: {run.get(\"run_signature\", \"\")[:8]}')
    print(f'  advisor_summary populated: {bool(run.get(\"advisor_summary\"))}')
    print(f'  warnings: {(run.get(\"output\") or {}).get(\"warnings\", [])}')
"
```

Expected: PortfolioRun present, signature populated, advisor_summary populated, no UNMAPPED_HOLDINGS warnings (real-PII data → canonical sh_* funds via the persona load + reconciliation pipeline).

Document results in handoff-log entry with **structural counts only** (per real-PII discipline canon §11.8.3): household external_id, run signature, link count, advisor_summary length, warnings count. NO real-PII content.

### A6.12 — Cross-browser manual gate (~15 min; per locked #23)

Extend `frontend/e2e/cross-browser-smoke.spec.ts` with engine→UI assertions:
- Goal route renders RecommendationBanner with run signature
- Household route renders HouseholdPortfolioPanel with metrics
- Override → Regenerate cycle: banner timestamp updates after override save

Run:
```bash
cd /Users/saranyaraj/Projects/github-repo/mp2.0/frontend && set -a && source ../.env && set +a
PLAYWRIGHT_BASE_URL=http://localhost:5173 \
  MP20_LOCAL_ADMIN_PASSWORD=change-this-local-password \
  npx playwright test --project=webkit cross-browser-smoke.spec.ts --reporter=line
PLAYWRIGHT_BASE_URL=http://localhost:5173 \
  MP20_LOCAL_ADMIN_PASSWORD=change-this-local-password \
  npx playwright test --project=firefox cross-browser-smoke.spec.ts --reporter=line
cd ..
```

Expected: 12-15 passed across both browsers (10 baseline + 2-5 new). Document failures in handoff-log + add to `docs/agent/post-pilot-improvements.md` if Safari/Firefox-specific.

### A6.13 — CHANGELOG.md + ops-runbook entries (~30 min; per locked #21+#83)

See **§25** for CHANGELOG entry template + **§26** for ops-runbook section template. Both are exact templates ready to copy in.

### A6.13b — Pilot-rollback runbook entry (~15 min)

Append to `docs/agent/pilot-rollback.md`. See **§27** for the template.

### A6.13c — Rollback smoke test (~15 min; per locked #103)

See **§24** for the explicit step-by-step procedure. Documented in handoff-log post-execution.

### A6.14 — Code-reviewer subagent dispatch (~30 min review + ~30 min fixes)

Dispatch `pr-review-toolkit:code-reviewer` subagent on the full sub-sessions #1-#5 diff. See **§19** for the dispatch prompt template.

Sub-session #11 (history) found 1 BLOCKING + 5 critical via this pattern. Expect similar volume; fix all surfaced findings in a follow-up commit.

### A6.15 — Demo dress rehearsal (~45 min; per locked #95+#88)

See **§23** for the full step-by-step timed procedure. Captures wall-clock per step in handoff-log.

### A6.16 — Final close-out (~30 min)

1. **Auto-memory file** at `~/.claude/projects/-Users-saranyaraj-Projects-github-repo-mp2-0/memory/project_engine_ui_display.md`:

```markdown
---
name: Engine→UI display integration shipped
description: HEAD v0.1.2-engine-display; engine output (PortfolioRun) displayed via Goal route + Household route + auto-trigger on commit/wizard/override/realignment + linked-HH-only on workspace mutations
type: project
---

[200-300 words capturing the final state, file refs, locked decisions migrated]
```

Update `MEMORY.md` index with pointer to this new file.

2. **Migrate locked decisions** to `docs/agent/decisions.md` per locked #91. See **§28** for the template + grouping convention.

3. **Delete this starter prompt** per locked #11+§X.7 lifecycle:

```bash
rm docs/agent/engine-ui-display-starter-prompt.md
git add -A
git commit -m "docs: delete engine-ui-display-starter-prompt (mission complete; decisions migrated to decisions.md per locked #91)"
```

4. **Update CLAUDE.md** "Useful Project Memory" section to add `docs/agent/decisions.md` engine-UI section pointer.

5. **Cumulative ping** to user — summarize all 5 sub-sessions: total commits + tests added per layer + per-phase highlights + locked decisions honored + Bedrock $ delta + open items for post-pilot. ~600-800 words.

---

## §8. First concrete action (mode-dependent)

### Mode A (continuing planning):
Skim §1 locked decisions in plan file (focus on §5 above's load-bearing list). ASK the user via `AskUserQuestion`: "Sub-sessions #1+#2+#3 shipped (functional core + frontend display surfaces); 869 backend pytest + foundation e2e 13/13 green. Anything to refine before I begin sub-session #4 execution (A6 Hypothesis + Vitest + concurrency + perf + integration)?"

### Mode B (approved + executing):
Run §3 pre-flight in full. If green, dispatch the 2 sub-agents for A6 Round 1 (Agent A Hypothesis + Agent B Vitest) **in a single message with two Agent tool calls so they run in parallel** using the dispatch templates in **§19**. While they run, draft the A6 Round 1 close-out handoff entry. Review each agent's output per locked #X.10 (re-read every file; re-run tests; spot-check citations). Commit each agent's work separately with `subagent:` attribution line.

---

## §9. Stop conditions (halt + AskUserQuestion when these fire)

1. Any prior gate red BEFORE you change anything.
2. HEAD has drifted past `915eec7` between this session's compact and now (re-audit if so).
3. Engine probe at A0.1 returns ≠ 200 with valid output.
4. Coverage gate fails (<85% on touched modules per locked #61).
5. Pool capacity test (#102) reveals < 120 concurrent connections supported.
6. Concurrency stress test reveals IntegrityError or audit-count mismatch.
7. PII grep guard fails on a new commit.
8. Sub-agent reports "complete" but `Read` of files shows scope creep / locked-decision violations — reject + restart with tightened prompt.
9. You're considering pushing to origin — **DO NOT**. User pushes Monday morning.
10. Locked decision in §1 conflicts with code at HEAD `915eec7` — handoff is right; flag + ask before changing.
11. Visual-verification spec reaches 24/24 unexpectedly (means R10 sweep state was somehow restored — verify it's not test pollution).
12. Any new test file lands in `engine/tests/` that imports from `web` or `django` — engine purity violation; move to `web/api/tests/`.
13. Bedrock spend exceeds $10 in any sub-session (sub-session #4 should be $0; sub-session #5 A6.11 should be ~$0 since pre-paid).
14. Real-PII content appears in any commit/log/handoff entry — STOP IMMEDIATELY + scrub via `safe_audit_metadata` from `web/api/error_codes.py`.

---

## §10. Anti-patterns burned in (lessons from sub-sessions #1-#3 — DO NOT REPEAT)

These cost real time during execution; they will cost more if you repeat them.

### From sub-session #1

1. **Engine purity gate catches misplaced tests.** I initially placed `test_sandra_mike_fixture_smoke.py` in `engine/tests/`. The engine purity AST check raised because the test imports django+web. Lesson: any test that uses `call_command(...)`, `@pytest.mark.django_db`, or imports from `web.api` MUST live in `web/api/tests/`, NOT `engine/tests/`.

2. **transaction.atomic rolls back audit emits inside the block.** I initially placed `_record_portfolio_event` for `ambiguous_current_lifecycle` INSIDE the helper's outer `with transaction.atomic():` block. When `raise InvalidCMAUniverse(...)` fired, the atomic rolled back including the audit event. Fix in `f003ed6`: moved reusable check OUTSIDE the atomic.

3. **`reset-v2-dev.sh` ordering matters for advisor pre-ack.** Original: `load_synthetic_personas` BEFORE `bootstrap_local_advisor`. Result: advisor user didn't exist when persona load tried to write `AdvisorProfile`; pre-ack silently skipped. Lesson: bootstrap user creation BEFORE persona load.

4. **`reset-v2-dev.sh` DOWNS all containers; backend needs explicit `up -d`.** Script runs `docker compose down -v` then `docker compose up -d db` (only db). After reset, backend container is NOT running. Run `docker compose up -d backend` then sleep 5-10s.

### From sub-session #2

5. **Workspace-level triggers don't break existing tests but ADD new audit events.** Existing tests assert per-action counts, not totals. Locked #16 single-canonical action naming means new audit kinds don't collide.

### From sub-session #3

6. **Auto-seed creates synthetic_load PortfolioRun; subsequent same-signature trigger calls hit REUSED.** When testing GENERATED path post-auto-seed, mutate household state (`household_risk_score`) to invalidate the run_signature before the trigger call. Fix in `303e378`.

7. **Multiple Playwright instances cause port collisions + stuck processes.** Only ONE Playwright instance at a time. If re-run needed: `pkill -9 -f playwright; pkill -9 -f chromium; sleep 3` first.

8. **R10 sweep state is wiped by `reset-v2-dev.sh`.** Visual-verification 6 ReviewScreen+ConflictPanel+DocDetailPanel tests fail post-reset. **State-dependent failure, not code regression.** A6.15 dress rehearsal restores via `upload_and_drain.py Seltzer/Weryha/Niesner`.

### Cross-cutting (from `next-session-starter-prompt.md` §8 + locked decisions)

9. **`setState((prev) => mutate-closure-array)` StrictMode-double-update class** — per locked #64, every new component needs StrictMode tests. Compute the new list OUTSIDE the updater + pass a pure spread.

10. **Flat-shape mocks vs nested-shape production payload** — per locked #55, `mockHousehold()` factory output must match a real `/api/clients/<id>/` response byte-for-byte.

11. **aria-label vs visible-text divergence** — per locked #71, Playwright `getByRole({ name: /.../i })` resolves to the aria-label NOT the visible text. Use `getByText` for visible-text matches OR less-anchored regex.

12. **Bespoke modal/overlay needs explicit Esc handler + focus restore + click-outside** — per locked #68, `aria-modal=true` is not enough. Mirror DocDetailPanel's pattern.

13. **`str(exc)` anywhere = PII leak risk** — use `safe_audit_metadata` from `web/api/error_codes.py`. PII grep guard catches this.

14. **Subagent gates pass against subagent-written fixtures** — per locked #X.10, after each sub-agent returns: Read every file the agent edited; re-run tests locally; spot-check citations; verify locked-decision compliance.

15. **Re-run FULL foundation e2e after ANY frontend touch** — Vitest passing ≠ no regression.

---

## §11. Per-phase ping format (~400 words verbose; production-quality-bar.md §9 + locked #45)

Every phase exit pings the user with:
1. **What changed** — HEAD commit hash + diff highlights + audit-finding closure refs (specific file:line citations).
2. **What was tested** — new tests by name + invariants pinned + manual smoke + full gate-suite tail (specific count deltas).
3. **What didn't ship** — open items + reason + path forward + which sub-session it lands.
4. **What's next** — phase continuation + estimated scope.
5. **What's the risk** — regression possibilities + how the gates would catch them.
6. **Locked decisions honored** — citation by number.
7. **Continuity check** — session-state.md updated yes/no; this file updated yes/no; MEMORY.md updated yes/no.

---

## §12. Halt protocol (mid-phase compaction discipline; §X.3)

If context approaches 80% mid-phase:
1. Halt at next natural breakpoint (commit point or end of logical sub-task per §21 enumerated checkpoints).
2. Write handoff-log entry covering what's done + what remains.
3. Update session-state.md headline + this starter prompt's "What's done" section.
4. Commit any uncommitted work (`wip:` prefix if mid-phase).
5. Suggest `/compact` with continuation cue: "Sub-session #N partial; rounds <X-Y> remaining. Read `docs/agent/engine-ui-display-starter-prompt.md` to continue."

**Never strand uncommitted work across a halt.**

---

## §13. Communication style

- **Don't overclaim.** "Tests pass" needs the actual count + tail. "Engine works" needs the probe output. "Helper extracted" needs the file:line range.
- **Cite specific evidence** — commit hash, regression test ids, gate-output tail. Never opinions like "looks good".
- **Verbose per-phase pings** with `file_path:line_number` specifics.
- **The user redirects when you drift.** Treat redirects as normal input.
- **When halting**: clean handoff entry + commit any wip + ping via AskUserQuestion. Don't strand work.
- **Match responses to the task**: simple questions get direct answers, not headers. Per-phase ping is the exception (verbose by design).
- **Don't write planning, decision, or analysis documents unless the user asks** — work from conversation context.

---

## §14. First message template (post-boot)

After §3 pre-flight + §1 mode determination:

```
Booted from engine-ui-display-starter-prompt.md (sub-session #4 entry; full mission reference).

HEAD: 915eec7 (or later if HEAD has drifted; halt + ask if so)
Pre-flight: <pass/fail per gate; expected 869 backend + 82 Vitest + 13/13 foundation + 18/24 visual + 10 cross-browser>
Mode: <A: continuing planning | B: approved + executing>
Locked decisions: 111 captured (plan file §1)
Phase scope: Sub-session #4 — A6 round 1+2 (Hypothesis + Vitest comprehensive + concurrency stress + auth/RBAC + perf + integration tests); 5-7 hr per locked #92.
Sub-session #5 preview: A6 round 3 visual regression + A6.9 design-system + A6.10 tag bump v0.1.2-engine-display + A6.11 Niesner smoke + A6.12 cross-browser + A6.13 CHANGELOG/ops-runbook + A6.13c rollback smoke + A6.14 code-reviewer subagent + A6.15 demo dress rehearsal + A6.16 close-out; 4-6 hr.

[If Mode A]: Anything to refine before sub-session #4 execution?
[If Mode B]: Beginning A6 Round 1 — dispatching 2 sub-agents in parallel per locked #20 using dispatch templates in §19. Will commit each agent's work separately with subagent: attribution after Reading every file the agent touched per locked #X.10.
```

Wait for user direction. Do not begin code changes until §3 confirmed green AND mode is unambiguous.

---

## §15. Sub-session-#4 + #5-specific risks

### Sub-session #4

- **Sub-agent context window**: A6 Round 1 dispatches 2 agents in parallel; each gets its own context budget. If an agent reports "partial completion due to context", main thread reads what landed + commits + dispatches a follow-up agent for remaining scope (see §20.1).
- **mockHousehold byte-for-byte fidelity (#55)**: Verify by curling `/api/clients/hh_sandra_mike_chen/` BEFORE Agent B starts and capturing the response shape. Pass that shape to Agent B in the prompt as the canonical reference.
- **Coverage gate (#61)**: 85% on touched modules. Helper has many branches (kill-switch + no-CMA + invalid-CMA + readiness + provenance + reusable + REUSED + GENERATED + REGENERATED_AFTER_DECLINE + HASH_MISMATCH). Round 1+2 tests must hit all branches.
- **`portfolio_runs.order_by("-created_at").first()` idempotency**: helper uses this multiple times. If a test creates two PortfolioRuns with SAME `created_at` (microsecond collision), order is unstable. Use `freezegun` or distinct as_of_dates.
- **Concurrency stress (#80 + #102)**: 100 parallel + headroom test at 120 means test suite hits 220+ concurrent DB connections briefly. Verify Postgres `max_connections=200+` BEFORE Agent C runs.
- **Hypothesis search settings**: `@settings(max_examples=N, deadline=None)` to avoid timing out. Default 100 examples × 5 typed × 8 trigger paths = 4000 trial cases.

### Sub-session #5

- **Visual regression baselines stability**: Playwright screenshots are DPI-sensitive. CI may run on different display DPI than local dev. Set `useDevicePixelRatio: 1` in playwright config OR run baselines on a known DPI machine.
- **Niesner real-PII smoke timing**: A6.11 deletes Niesner state then re-uploads. The Bedrock vision pipeline runs on each upload (~12 docs × ~5-10s each ≈ 1-2 min). If the upload_and_drain script times out or hits a Bedrock throttle, re-run idempotently (per locked #86 the deletion is repeatable).
- **Cross-browser flakes**: Safari + Firefox font rendering can differ slightly. Filter benign noise (font sanitizer warnings, ResizeObserver, ERR_ABORTED on aborted preview-endpoint requests during navigation) from real failures per sub-session #11 pattern.
- **Demo dress rehearsal timing budget**: Steps 4.5 (override → save → regenerate) + Step 7 (commit + auto-trigger fires) should not exceed 10s per locked #88. If they do, flag as engineering follow-up; don't halt the rehearsal.
- **Tag bump timing**: A6.10 cuts the tag locally. If user pushes Monday before all gates green, the tag may be associated with broken state. The full-gate verification in §22 MUST pass before A6.10.
- **Decisions migration completeness (A6.16)**: 111+ decisions distilled to ~110 lines. Cross-references must be accurate (#74 references #56; #99 references #9; etc.). Use the §28 template + grouping convention.

---

## §16. The shape of MP2.0 — for grounding when you context-switch

```
mp2.0/
├── engine/                          # Pure Python; no Django, no DRF (canon §9.4.2)
│   ├── optimizer.py                 # optimize() entry point
│   ├── schemas.py                   # Pydantic models (Household, EngineOutput, ...)
│   ├── frontier.py
│   ├── risk_profile.py              # compute_risk_profile() — Hayes worked example
│   ├── fixtures/
│   │   ├── default_cma_v1.json
│   │   ├── stress_household_medium.json   # NEW (sub-session #1)
│   │   └── stress_household_large.json    # NEW (sub-session #1)
│   └── tests/
│       └── test_engine_purity.py    # AST gate; raises if any test imports django/web
├── extraction/                      # Layer 1-5 LLM extraction (separate from engine)
├── web/
│   ├── api/
│   │   ├── views.py                 # MUTATED: 5 typed exceptions + helper trio + 1/8 trigger sites
│   │   ├── wizard_views.py          # MUTATED: triggers #2/#3/#4 wired
│   │   ├── preview_views.py         # MUTATED: A3a moves preview from goal_rollups
│   │   ├── serializers.py           # MUTATED: latest_portfolio_failure SerializerMethodField
│   │   ├── error_codes.py           # safe_audit_metadata, safe_response_payload, etc.
│   │   ├── management/commands/
│   │   │   ├── load_synthetic_personas.py   # MUTATED: A1+A5 RiskProfile + advisor pre-ack + auto-seed
│   │   │   ├── bootstrap_local_advisor.py
│   │   │   └── seed_default_cma.py
│   │   └── tests/
│   │       ├── test_auto_portfolio_generation.py    # NEW (sub-session #1)
│   │       ├── test_sandra_mike_fixture_smoke.py    # NEW (sub-session #1)
│   │       ├── test_auto_trigger_properties.py      # NEW (sub-session #4 — A6 R1)
│   │       ├── test_audit_metadata_invariants.py    # NEW (sub-session #4 — A6 R1)
│   │       ├── test_workspace_trigger_gate_properties.py  # NEW (sub-session #4 — A6 R1)
│   │       ├── test_connection_pool_capacity.py     # NEW (sub-session #4 — A6 R2)
│   │       ├── test_full_advisor_lifecycle_with_auto_trigger.py  # NEW (sub-session #4 — A6 R2)
│   │       ├── test_pre_a2_portfolio_run_compat.py  # NEW (sub-session #4 — A6 R2)
│   │       ├── test_household_detail_serializer_snapshot.py  # NEW (sub-session #4 — A6 R2)
│   │       └── test_*.py
│   └── audit/
├── frontend/
│   ├── src/
│   │   ├── lib/
│   │   │   ├── household.ts         # MUTATED: engine schema-aligned types + 4 helpers
│   │   │   ├── preview.ts           # MUTATED: useGeneratePortfolio mutation hook
│   │   │   └── ...
│   │   ├── goal/
│   │   │   ├── RecommendationBanner.tsx     # NEW (sub-session #3)
│   │   │   ├── AdvisorSummaryPanel.tsx      # NEW (sub-session #3)
│   │   │   └── __tests__/                   # NEW (sub-session #4 — A6 R1)
│   │   ├── routes/
│   │   │   ├── GoalRoute.tsx        # MUTATED: composition with new components
│   │   │   ├── HouseholdRoute.tsx   # MUTATED: HouseholdPortfolioPanel inserted
│   │   │   ├── HouseholdPortfolioPanel.tsx  # NEW (sub-session #3)
│   │   │   └── __tests__/                   # NEW (sub-session #4 — A6 R1)
│   │   ├── i18n/en.json             # MUTATED: ~24 new keys
│   │   └── __tests__/__fixtures__/
│   │       └── household.ts         # NEW expected (sub-session #4 — A6.0 mockHousehold per #84)
│   └── e2e/
│       ├── foundation.spec.ts       # 13 tests (stable)
│       ├── visual-verification.spec.ts  # 24 tests (18+6 state-dependent → +16-20 in A6 R3 → ~40-44 final)
│       ├── cross-browser-smoke.spec.ts  # 10 tests (+ engine→UI assertions in A6.12)
│       └── __screenshots__/         # NEW expected (sub-session #5 — A6 R3 visual baselines)
├── personas/sandra_mike_chen/client_state.json   # MUTATED: RiskProfile + sh_* funds + pre-ack
├── scripts/reset-v2-dev.sh          # MUTATED: bootstrap before load_synthetic_personas
├── CHANGELOG.md                     # MUTATED in A6.13: [v0.1.2-engine-display] entry
└── docs/agent/
    ├── engine-ui-display-starter-prompt.md   # THIS FILE (deleted at A6.16)
    ├── handoff-log.md
    ├── session-state.md
    ├── decisions.md                 # MUTATED in A6.16: append "Engine→UI Display Integration" section
    ├── design-system.md             # MUTATED in A6.9: append "Engine output consumption" section
    ├── ops-runbook.md               # NEW expected in A6.13
    ├── pilot-rollback.md            # MUTATED in A6.13b: append "Engine→UI Display Rollback" section
    ├── next-session-starter-prompt.md  # complementary; post-pilot-release scope (NOT deleted at A6.16)
    └── ... (other docs)

~/.claude/plans/i-want-you-to-jolly-beacon.md   # 111 locked decisions; canonical
~/.claude/projects/.../memory/
├── MEMORY.md                        # MUTATED in A6.16: pointer to project_engine_ui_display.md
└── project_engine_ui_display.md     # NEW in A6.16
```

---

## §17. If you read only ONE thing

The plan file `~/.claude/plans/i-want-you-to-jolly-beacon.md` §1 (locked decisions table) is the canonical source. If you have time for nothing else: read decisions #14, #74, #81, #96, #99, #X.10. Together those frame sub-session #4's must-do work.

---

## §18. Final note (before appendices)

Sub-sessions #1+#2+#3 shipped the FUNCTIONAL CORE. The advisor sees engine recommendations on Goal route + Household route. Demo Mon 2026-05-04 today runs against current HEAD `915eec7`. Sub-sessions #4+#5 add the testing + validation rounds that locked decision #15's "ship complete production-quality scope" requires before pilot launch Mon 2026-05-08.

Before pilot: 869 backend pytest must grow to ~1080 (+97 tests across A6 rounds 1+2+3); coverage 85% on touched modules; visual-verification 24/24 + 16-20 new (A6 R3 baselines); cross-browser stable; rollback smoke documented; tag `v0.1.2-engine-display` cut at A6.10; decisions migrated to `decisions.md` at A6.16.

You have the plan file + this prompt + the handoff-log + session-state + appendices below. Begin with §3 pre-flight, determine mode, then execute or interview.

**Don't skip ahead.** The discipline is what makes pilot-grade.

The sections below are APPENDICES — execution-ready templates + procedures + recovery flows. Reference them as needed during sub-sessions #4 + #5.

---

# Appendices

## §19. Sub-agent dispatch prompt templates

### §19.1 Agent A — Hypothesis property suites (sub-session #4 Round 1)

```
You are working in the MP2.0 codebase at /Users/saranyaraj/Projects/github-repo/mp2.0
on branch feature/ux-rebuild at HEAD <current-head>. The Engine→UI Display
Integration mission has shipped backend + frontend (sub-sessions #1+#2+#3);
your task is sub-session #4 Round 1 Agent A: write 3 Hypothesis property test
suites for the auto-trigger system.

Context:
- Helper: web/api/views.py:621-865 — _trigger_portfolio_generation(household, user, *, source) -> PortfolioRun
- Caller wrappers: _trigger_and_audit (873-931), _trigger_and_audit_for_workspace (932-962)
- 5 typed exceptions at views.py:91-110: EngineKillSwitchBlocked, NoActiveCMASnapshot,
  InvalidCMAUniverse, ReviewedStateNotConstructionReady, MissingProvenance
- 8 trigger sources: review_commit, wizard_commit, override, realignment,
  conflict_resolve, defer_conflict, fact_override, section_approve
- Existing tests: web/api/tests/test_auto_portfolio_generation.py (8 unit tests)

Deliverables (3 NEW test files in web/api/tests/):

1. test_auto_trigger_properties.py
   @given(num_mutations=st.integers(min_value=1, max_value=10))
   For any random sequence of N committed-state mutations, the PortfolioRun
   count is N+1 OR fewer (REUSED via signature match); all input/output/cma
   hashes deterministic; PortfolioRun.save() raises on existing pk.

2. test_audit_metadata_invariants.py (per locked #99)
   @given(exception_class=st.sampled_from([EngineKillSwitchBlocked, NoActiveCMASnapshot,
     InvalidCMAUniverse, ReviewedStateNotConstructionReady, MissingProvenance,
     ValueError, RuntimeError, KeyError]))
   Asserts AuditEvent.count() increments by exactly 1 per trigger fire;
   metadata.reason_code is the typed exception class name; PII regex grep on
   metadata JSON returns zero matches for SIN-pattern (\d{3}-\d{3}-\d{3}) +
   account-number pattern + email regex.

3. test_workspace_trigger_gate_properties.py
   For triggers #5-#8: linked_household_id is None → emits
   portfolio_generation_skipped_post_<source> audit + returns None;
   linked → fires + REUSED expected for same-input.

Constraints:
- @settings(max_examples=50, deadline=None) — DB-touching tests need no deadline.
- Use @pytest.mark.django_db. Place tests in web/api/tests/ (NEVER engine/tests/
  per engine purity gate).
- No str(exc) in ANY assertion or fixture. Use safe_audit_metadata helper if
  building expected metadata.
- Use existing helper from test_auto_portfolio_generation.py: _bootstrap_full_demo()
  — but mutate household_risk_score before each trigger call to invalidate
  signature (so GENERATED path fires, not REUSED). See lesson #6 in starter
  prompt.

Return: list of files created with line counts; expected pass count.
Run: DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 uv run python -m pytest
  web/api/tests/test_auto_trigger_properties.py
  web/api/tests/test_audit_metadata_invariants.py
  web/api/tests/test_workspace_trigger_gate_properties.py -v
```

### §19.2 Agent B — Vitest comprehensive (sub-session #4 Round 1)

```
You are working in the MP2.0 codebase at /Users/saranyaraj/Projects/github-repo/mp2.0
frontend at HEAD <current-head>. Engine→UI display components shipped at
sub-session #3; your task is sub-session #4 Round 1 Agent B: write
comprehensive Vitest unit tests + the canonical mockHousehold fixture.

Context:
- New components from sub-session #3:
  - frontend/src/goal/RecommendationBanner.tsx (140 LoC, 3 states, aria-live, Sonner toast)
  - frontend/src/goal/AdvisorSummaryPanel.tsx (61 LoC)
  - frontend/src/routes/HouseholdPortfolioPanel.tsx (150 LoC)
- Types in frontend/src/lib/household.ts: Allocation, Rollup, EngineOutput,
  LinkRecommendation, PortfolioRun, HouseholdDetail (with latest_portfolio_failure)
- Helpers: findGoalRollup, findHouseholdRollup, findGoalLinkRecommendations
- Mutation: useGeneratePortfolio in lib/preview.ts

Critical reference shape: BEFORE writing mockHousehold, capture the LIVE shape
from /api/clients/hh_sandra_mike_chen/ via curl. Pass it as canonical. Per
locked #55, mock fidelity must be byte-for-byte (lesson from sub-session #11
cost-key bug).

Deliverables:

1. frontend/src/__tests__/__fixtures__/household.ts (NEW, per locked #84):
   - mockHousehold(overrides?: Partial<HouseholdDetail>): HouseholdDetail
   - mockPortfolioRun(overrides?: Partial<PortfolioRun>): PortfolioRun
   - mockEngineOutput(overrides?: Partial<EngineOutput>): EngineOutput
   - mockRollup, mockLinkRecommendation, mockAllocation factories
   - Defaults match Sandra/Mike-equivalent shape from live curl

2. frontend/src/goal/__tests__/RecommendationBanner.test.tsx (~15-20 tests):
   - Render variants: run / no-run / failure / pending
   - Generate button click → calls mutation
   - aria-live="polite" present on outer div
   - StrictMode double-invoke: button click fires mutation EXACTLY ONCE per #64
   - Keyboard nav (Tab focuses Generate button, Enter clicks)
   - Sonner toast fires once per unique failure.occurred_at (ref dedup)

3. frontend/src/goal/__tests__/AdvisorSummaryPanel.test.tsx (~10-15 tests):
   - Empty array (no LinkRecommendations) → renders nothing
   - Single link renders one section
   - Multi-link goal (3+ links) renders 3+ sections with border-t separators
   - account_type + formatCadCompact(allocated_amount) in header
   - whitespace-pre-line renders newlines correctly

4. frontend/src/routes/__tests__/HouseholdPortfolioPanel.test.tsx (~15-20 tests):
   - Render variants: run / no-run / failure
   - Top 4 funds sorted by weight desc
   - formatPct(weight * 100) format
   - Mirrors RecommendationBanner failure pattern per #19

5. frontend/src/lib/__tests__/household.test.ts (NEW or extend existing):
   - findGoalRollup returns null when no run
   - findGoalRollup returns rollup matching goal_id
   - findHouseholdRollup returns household rollup or null
   - findGoalLinkRecommendations filters by goal_id

6. frontend/src/lib/__tests__/preview.test.ts (extend; per #106):
   - useGeneratePortfolio onSuccess invalidates householdQueryKey
   - useGeneratePortfolio onError shows toast + does NOT invalidate
   - Use MSW or fetch mock to simulate backend

7. frontend/src/lib/__tests__/household.types.test.ts (NEW; per #104):
   - expectTypeOf<HouseholdDetail['latest_portfolio_run']>().toEqualTypeOf<PortfolioRun | null>()
   - expectTypeOf<LinkRecommendation['advisor_summary']>().toEqualTypeOf<string>()
   - expectTypeOf<EngineOutput['schema_version']>().toEqualTypeOf<'engine_output.link_first.v2'>()

Constraints:
- Use @testing-library/react + Vitest patterns.
- Selectors: prefer getByText for visible text; use less-anchored regex when
  matching aria-label per #71.
- StrictMode tests wrap component in <React.StrictMode> per #64.
- Run all tests via npm run test:unit to verify they pass.

Return: file list with LoC + test count; expected total Vitest count delta.
```

### §19.3 Agent C — Concurrency stress + auth/RBAC + pool (sub-session #4 Round 2)

```
[Similar template; deliverables = test_concurrency_stress extension for 8 triggers,
test_connection_pool_capacity (NEW), test_auth_rbac_matrix extension for 4 NEW
trigger endpoints. Constraints: verify Postgres max_connections >= 200 BEFORE
running; @settings deadline=None for stress tests.]
```

### §19.4 Agent D — Perf + integration tests (sub-session #4 Round 2)

```
[Similar template; deliverables = test_perf_budgets extension (P50<250ms /
P99<1000ms benchmarks), test_full_advisor_lifecycle_with_auto_trigger (NEW per
#96), test_pre_a2_portfolio_run_compat (NEW per #97), test_household_detail_serializer_snapshot
(NEW per #101). Constraints: pre-A2 fixture must NOT include latest_portfolio_failure
field (mimics d2abfa1 v0.1.0-pilot shape).]
```

### §19.5 Agent E — Visual regression baselines (sub-session #5 A6 round 3)

```
You are working in the MP2.0 codebase at /Users/saranyaraj/Projects/github-repo/mp2.0
frontend at HEAD <current-head>. Sub-session #4 testing rounds shipped; your
task is sub-session #5 A6 round 3: extend frontend/e2e/visual-verification.spec.ts
with engine→UI surfaces visual regression baselines per locked #82.

Add to visual-verification.spec.ts a new test.describe block:
  test.describe("engine→UI display surfaces (sub-session #5 A6.R3)", () => { ... })

Coverage (~16-20 tests):
- RecommendationBanner × 4 states (run / no-run / failure / pending)
- HouseholdPortfolioPanel × 4 states
- AdvisorSummaryPanel × 2 states (single-link / multi-link)
- (Optional) Goal route + Household route full-page screenshot at each state

State injection: use Playwright's page.evaluate() to inject mock
latest_portfolio_run / latest_portfolio_failure shapes into React Query cache;
OR drive via real auto-seed (run state) + DELETE PortfolioRun (no-run state)
+ simulate failure via MP20_ENGINE_ENABLED=False env flag.

Per locked #110: verify accent-2 + ink-muted tokens render correctly under
light theme.

Per locked #109: verify aria-live="polite" attributes are present on Banner +
HouseholdPortfolioPanel.

Per axe-core a11y gate: run axe on each screenshot state; assert zero violations.

Constraints:
- Use await expect(page).toHaveScreenshot() for baseline generation.
- Baselines committed under frontend/e2e/__screenshots__/.
- Run BEFORE Niesner upload (state-dependent failures from §3 are OK).
- Do NOT regenerate existing 24 baselines (those are stable from sub-session #11).

Return: file list, test count, ~PNG count + total kB, expected pass count.
```

### §19.6 Code-reviewer subagent dispatch (sub-session #5 A6.14)

```
[Dispatch via Agent tool with subagent_type='pr-review-toolkit:code-reviewer'.
Prompt: review the full sub-sessions #1-#5 diff (`git diff 081cfc8..HEAD`) for:
- PII discipline (no str(exc) in DB / API / audit metadata)
- Atomicity (transaction.atomic + select_for_update on workspace root)
- Audit-event regression (one event per kind per state-change)
- Real-PII discipline (no client content in code/commits)
- Accessibility (ARIA labels, keyboard nav, focus management)
- Vocabulary discipline (no reallocation/transfer/move-money)
- Engine purity (no django/web imports in engine/)
Return: list of findings with severity (BLOCKING / CRITICAL / MEDIUM / LOW) +
file:line citations + suggested fixes.
Sub-session #11 found 1 BLOCKING + 5 CRITICAL via this pattern; expect similar volume.]
```

---

## §20. Recovery procedures (when things go wrong)

### §20.1 Sub-agent reports partial completion (context exhausted)

If a sub-agent returns saying "I completed 60% but ran out of context for X, Y, Z":

1. **Read every file the agent claims to have touched** — verify what actually landed.
2. **Run the partial test set** — ensure what landed passes.
3. **Commit the partial work** with `wip(test): partial; remaining: X, Y, Z` commit message.
4. **Dispatch a follow-up sub-agent** with a tighter prompt scoped only to X, Y, Z.
5. **Document in handoff-log** that the original agent partial'd; reference the wip commit.

### §20.2 Test fails unexpectedly mid-execution

1. **Read the failure output** carefully — assertion error vs setup error vs collection error.
2. **Reproduce locally** — `pytest <test_id> -v --tb=long`.
3. **Diagnose root cause** — check git log for recent changes; check if it's state-dependent (Niesner sweep wiped) per lesson #8.
4. **If state-dependent**: document in handoff-log + don't chase; A6.15 restores.
5. **If code regression**: fix at root, NOT by adjusting test expectations. Add a regression test that pins the behavior.
6. **If flaky**: re-run 3x; if 3/3 pass, document in handoff-log + add `@pytest.mark.flaky(reruns=3)` (last resort).

### §20.3 Gates regress between sub-sessions

If you discover backend pytest count dropped from expected baseline:

1. `git diff <last-good-head>..HEAD --stat` — identify which files changed.
2. `git log <last-good-head>..HEAD --oneline` — identify which commits.
3. `pytest --tb=line -k "not slow"` to identify failing tests fast.
4. **Bisect if needed**: `git bisect start; git bisect bad HEAD; git bisect good <last-good-head>`.
5. **Don't disable failing tests**; fix root cause.

### §20.4 R10 sweep state needs restoring

If visual-verification fails 6 ReviewScreen+ConflictPanel+DocDetailPanel tests AND you need them to pass for sub-session #5 A6.15:

```bash
cd /Users/saranyaraj/Projects/github-repo/mp2.0
set -a && source .env && set +a
uv run python scripts/demo-prep/upload_and_drain.py Niesner --expect-count 12
# Optionally also Seltzer + Weryha if their state was wiped
uv run python scripts/demo-prep/upload_and_drain.py Seltzer --expect-count 5
uv run python scripts/demo-prep/upload_and_drain.py Weryha --expect-count 5
```

Each takes ~5-10 min wall-clock. Bedrock cost: ~$0 (pre-paid via earlier sweeps).

### §20.5 Backend container is down

Symptom: `curl http://localhost:8000/api/session/` returns connection refused.

```bash
docker compose ps                       # check status
docker compose logs backend | tail -30  # check recent logs for errors
docker compose up -d backend            # restart if down
sleep 8                                 # wait for autoreload to settle
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/session/  # verify 200
```

### §20.6 Migration is needed (rare; sub-session #4 doesn't add migrations)

If you accidentally add a migration:

1. **Check if it's intentional**: did your code change require a model field change?
2. **If intentional**: add the migration; commit with explicit `migration:` prefix; verify via `python manage.py migrate --plan`.
3. **If accidental**: revert via `git checkout HEAD -- web/api/migrations/<filename>`.

Sub-session #4 + #5 should NOT add migrations. If one appears, halt + investigate.

### §20.7 You accidentally pushed to origin

**STOP IMMEDIATELY.** User direction is no remote push until Mon morning.

1. Tell the user immediately.
2. Do NOT attempt to undo via `git push --force` (that's destructive).
3. Wait for user direction.

### §20.8 A typed exception class needs to change

If sub-session #4 testing reveals one of the 5 typed exceptions needs to change name OR add a new one:

1. **Don't.** The 5 are locked at `web/api/views.py:91-110`; tests expect those specific names.
2. **If absolutely required**: update views.py + test_auto_portfolio_generation.py + any new property tests AT ONCE; commit as a single logical unit.
3. **Document in handoff-log** + flag as a locked-decision change requiring user re-authorization (per §X.11 mid-execution scope-change protocol).

### §20.9 Helper signature needs to change

The helper signatures are locked:
- `_trigger_portfolio_generation(household, user, *, source: str) -> PortfolioRun`
- `_trigger_and_audit(household, user, *, source: str) -> PortfolioRun | None`
- `_trigger_and_audit_for_workspace(workspace, user, *, source: str) -> PortfolioRun | None`

8 callers depend on these signatures. Don't change without:
1. AskUserQuestion explaining why.
2. Coordinated update of all 8 callers + tests.
3. Single logical commit.

### §20.10 Postgres `max_connections` too low for pool capacity test

If A6 R2 Agent C's `test_connection_pool_capacity.py` fails with `OperationalError: too many connections`:

```bash
# 1. Check current setting
docker compose exec db psql -U mp20 -c "SHOW max_connections;"
# 2. Bump in docker-compose.yml (under db service):
#    command: postgres -c max_connections=300
# 3. Restart DB
docker compose down db && docker compose up -d db
# 4. Verify
docker compose exec db psql -U mp20 -c "SHOW max_connections;"
# 5. Re-run the test
```

Per locked #80, Postgres max_connections must be ≥ 200 (we test at 120 with headroom).

---

## §21. Mid-sub-session halt-and-flush checkpoints

These are natural breakpoints where halting + `/compact` is safe:

### Sub-session #4 checkpoints

- **After A6 R1 commits**: Agent A's 3 Hypothesis files committed + Agent B's Vitest files + mockHousehold fixture committed. State: 869 + ~15-30 new backend tests + 82 + ~60-80 new Vitest. Halt-and-flush eligible.
- **After A6 R2 commits**: Agent C's concurrency + pool + RBAC + Agent D's perf + 4 integration tests committed. State: ~20-30 more backend tests. Halt-and-flush eligible.
- **After code-reviewer subagent fixes**: A6.14 findings fixed in follow-up commit. State: all sub-session #4 work reviewed + fixed. Halt-and-flush eligible.
- **After full gate suite green** (per §22): backend + frontend + Playwright + coverage + real-Chrome smoke all green. **Sub-session #4 close-out point.**

### Sub-session #5 checkpoints

- **After A6 R3 visual baselines committed**: Agent E's ~16-20 new visual-verification tests + PNG baselines committed. State: visual-verification ~40-44 total. Halt-and-flush eligible.
- **After A6.9 design-system update**: docs/agent/design-system.md "Engine output consumption" section appended. Halt-and-flush eligible.
- **After A6.10 tag bump**: `v0.1.2-engine-display` tag cut locally. Halt-and-flush eligible.
- **After A6.11 Niesner smoke**: real-PII auto-trigger validated; documented in handoff-log. Halt-and-flush eligible.
- **After A6.12 cross-browser**: Safari + Firefox green. Halt-and-flush eligible.
- **After A6.13 + A6.13b + A6.13c**: CHANGELOG + ops-runbook + pilot-rollback runbook + rollback smoke documented. Halt-and-flush eligible.
- **After A6.14 code-reviewer fixes**: full mission reviewed + critical findings fixed. Halt-and-flush eligible.
- **After A6.15 dress rehearsal**: 8-step demo walkthrough timed; thresholds met or follow-up flagged. Halt-and-flush eligible.
- **After A6.16 close-out**: decisions migrated; auto-memory file created; this starter prompt deleted; cumulative ping sent. **Mission complete.**

At any checkpoint, if context > 80%, follow §12 halt protocol.

---

## §22. Final verification gate suite (pre-tag-bump; before A6.10)

ALL gates must be green BEFORE cutting `v0.1.2-engine-display`. Run in this order:

```bash
cd /Users/saranyaraj/Projects/github-repo/mp2.0

# 1. Static gates (~30s)
uv run ruff check . && uv run ruff format --check .
bash scripts/check-pii-leaks.sh
bash scripts/check-vocab.sh
bash scripts/check-openapi-codegen.sh
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 \
  uv run python web/manage.py makemigrations --check --dry-run

# 2. Backend pytest with coverage gate (~3 min; per locked #61)
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 \
  uv run pytest \
  --cov=web/api/views \
  --cov=web/api/preview_views \
  --cov=web/api/serializers \
  --cov=web/api/wizard_views \
  --cov=web/api/management/commands/load_synthetic_personas \
  --cov-report=term-missing \
  --cov-fail-under=85 \
  scripts/demo-prep/test_r10_sweep.py engine/tests/ extraction/tests/ web/api/tests/ web/audit/tests/ \
  --tb=line -p no:warnings --benchmark-disable
# expect: ~950-1050 passed (post-Round-1 + Round-2); coverage ≥ 85% on listed modules

# 3. Frontend gates (~30s)
cd frontend
npm run typecheck && npm run lint && npm run build
# expect: bundle ≤ 290 kB gzipped (per locked #85)
npm run test:unit -- --coverage
# expect: ~150-160 Vitest passing; coverage ≥ 85% on new components
cd ..

# 4. Playwright e2e against live stack (~5-10 min)
cd frontend && set -a && source ../.env && set +a
PLAYWRIGHT_BASE_URL=http://localhost:5173 \
  MP20_LOCAL_ADMIN_PASSWORD=change-this-local-password \
  npx playwright test --project=chromium e2e/foundation.spec.ts --reporter=line
# expect: 13/13 passed

PLAYWRIGHT_BASE_URL=http://localhost:5173 \
  MP20_LOCAL_ADMIN_PASSWORD=change-this-local-password \
  npx playwright test --project=chromium e2e/visual-verification.spec.ts --reporter=line
# expect: ~40-44 passed (post-A6.R3 + A6.15 R10 sweep restore); 0 failures

PLAYWRIGHT_BASE_URL=http://localhost:5173 \
  MP20_LOCAL_ADMIN_PASSWORD=change-this-local-password \
  npx playwright test --project=webkit --project=firefox e2e/cross-browser-smoke.spec.ts --reporter=line
# expect: ~12-15 passed (10 baseline + 2-5 engine→UI from A6.12)
cd ..

# 5. Perf benchmark (~30s)
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 \
  uv run pytest web/api/tests/test_perf_budgets.py --benchmark-only -v
# expect: P50 ≤ 250ms / P99 ≤ 1000ms on _trigger_portfolio_generation + commit-flow

# 6. Real-Chrome manual smoke (per locked #100; ~10 min)
# Open http://localhost:5173 in actual Chrome (NOT headless). Walk:
#   1. Login as advisor
#   2. ClientPicker → Sandra & Mike Chen
#   3. Verify HouseholdPortfolioPanel renders with metrics + top funds
#   4. Drill into Retirement income goal
#   5. Verify RecommendationBanner shows run signature
#   6. Verify AdvisorSummaryPanel renders with engine narrative
#   7. (Optional) Click Regenerate → banner timestamp updates
#   8. Switch to /review → confirm DocDropOverlay + ReviewQueue render
#   9. Open /methodology → confirm 10 sections render
# Watch console: zero unexpected errors. PilotBanner + WelcomeTour should NOT appear (advisor pre-acked).
```

If ANY gate red: halt + investigate + fix. **Do NOT cut the tag with red gates.**

---

## §23. Demo dress rehearsal procedure (A6.15; per locked #95+#88)

Total wall-clock: ~45 min. Captures wall-clock per step in handoff-log.

### Setup (T-0 to T-15min)

```bash
cd /Users/saranyaraj/Projects/github-repo/mp2.0

# T-0: Full reset (per locked #95 — Sandra/Mike + Seltzer + Weryha + Niesner all re-uploaded)
bash scripts/reset-v2-dev.sh --yes
# expect: clean DB; Sandra/Mike loaded; advisor pre-acked

# T-2: Bring backend up (script DOWNs all containers)
docker compose up -d backend
sleep 10
curl -s -o /dev/null -w "backend: %{http_code}\n" http://localhost:8000/api/session/
# expect: 200

# T-3: Verify Sandra/Mike auto-seeded
set -a && source .env && set +a
uv run python -c "
import os, requests
s = requests.Session()
s.get('http://localhost:8000/api/session/').raise_for_status()
csrf = s.cookies.get('csrftoken')
r = s.post('http://localhost:8000/api/auth/login/',
  json={'email':'advisor@example.com','password':os.environ['MP20_LOCAL_ADMIN_PASSWORD']},
  headers={'X-CSRFToken':csrf,'Referer':'http://localhost:8000'})
r.raise_for_status()
r = s.get('http://localhost:8000/api/clients/hh_sandra_mike_chen/')
hh = r.json()
run = hh.get('latest_portfolio_run') or {}
print(f'Sandra/Mike PortfolioRun: {bool(run)}; signature[:8]: {run.get(\"run_signature\", \"\")[:8]}')
"

# T-5: Re-upload Seltzer (~5 min)
uv run python scripts/demo-prep/upload_and_drain.py Seltzer --expect-count 5

# T-10: Re-upload Weryha (~5 min)
uv run python scripts/demo-prep/upload_and_drain.py Weryha --expect-count 5

# T-15: Re-upload Niesner (uncommitted; ~5 min)
uv run python scripts/demo-prep/upload_and_drain.py Niesner --expect-count 12
```

Verify state: Sandra/Mike committed (with PortfolioRun); Seltzer + Weryha + Niesner in review_ready (3 R10 sweep workspaces).

### Demo flow (T-15 to T-40min) — actual Chrome (NOT headless)

Open `http://localhost:5173/` in real Chrome with stopwatch ready. Each step has a threshold per locked #88: **trigger steps (4.5 + 7) ≤ 10s**; **non-trigger steps ≤ 8s**. Flag any breach for engineering follow-up but DON'T halt.

| Step | Description | Threshold | Captured Wall-Clock |
|---|---|---|---|
| 1 | Login → home renders | 8s | _____ |
| 2 | Pick Sandra/Mike → AUM strip + HouseholdPortfolioPanel + treemap render | 8s | _____ |
| 3 | Drill into Retirement income → 4-tile KPI + RecommendationBanner + AdvisorSummaryPanel + GoalAllocation render | 8s | _____ |
| 4 | Goal allocation panel → engine ideal bars + (calibration fallback if no run) | 8s | _____ |
| 4.5 | Drag risk slider → save override → banner timestamp updates (TRIGGER step) | **10s** | _____ |
| 5 | Switch to /review → DocDropOverlay + ReviewQueue + 3 sweep workspaces visible | 8s | _____ |
| 6 | Open Seltzer workspace → 5/5 reconciled chips + readiness panel | 8s | _____ |
| 7 | Review/approve sections + commit (TRIGGER step; auto-trigger fires) | **10s** | _____ |
| 8 | /methodology page → 10 sections render + canon descriptors | 8s | _____ |

### Close-out (T-40 to T-45min)

Document:
- Per-step wall-clock (filled in above)
- Any threshold breaches (with file:line / function names if engineering follow-up needed)
- Console errors observed (capture full stack traces)
- PilotBanner + WelcomeTour NOT appearing (verify advisor pre-ack works post-reset)

Append to handoff-log under "A6.15 demo dress rehearsal".

---

## §24. Rollback smoke procedure (A6.13c; per locked #103)

Total wall-clock: ~10-15 min. Documented in handoff-log post-execution.

```bash
cd /Users/saranyaraj/Projects/github-repo/mp2.0

# Step 1: Set kill-switch
echo "Setting MP20_ENGINE_ENABLED=False"
docker compose exec backend bash -c "echo 'MP20_ENGINE_ENABLED=False' >> /tmp/kill-switch.env"
# OR temporarily edit .env file:
# Add line: MP20_ENGINE_ENABLED=False
docker compose restart backend
sleep 8

# Step 2: Attempt commit on Sandra/Mike workspace (or use API directly)
set -a && source .env && set +a
uv run python -c "
import os, requests
s = requests.Session()
s.get('http://localhost:8000/api/session/').raise_for_status()
csrf = s.cookies.get('csrftoken')
r = s.post('http://localhost:8000/api/auth/login/',
  json={'email':'advisor@example.com','password':os.environ['MP20_LOCAL_ADMIN_PASSWORD']},
  headers={'X-CSRFToken':csrf,'Referer':'http://localhost:8000'})
r.raise_for_status()
csrf = s.cookies.get('csrftoken')
# Attempt direct generate-portfolio (should be blocked)
r = s.post('http://localhost:8000/api/clients/hh_sandra_mike_chen/generate-portfolio/',
  json={}, headers={'X-CSRFToken':csrf,'Referer':'http://localhost:8000'})
print(f'/api/.../generate-portfolio/ status: {r.status_code}')
print(f'  body: {r.text[:200]}')
# expect: 403 'Portfolio generation is disabled'
"

# Step 3: Verify audit emission via Django shell
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 \
  uv run python web/manage.py shell -c "
from web.audit.models import AuditEvent
recent = AuditEvent.objects.filter(
  action__in=['engine_kill_switch_blocked', 'portfolio_generation_skipped_post_review_commit'],
).order_by('-created_at')[:5]
for e in recent:
  print(f'{e.action}: {e.metadata}')
"
# expect: at least 1 'engine_kill_switch_blocked' event

# Step 4: Load Goal route in browser; verify graceful degradation
# Open http://localhost:5173 in Chrome, navigate to Sandra/Mike Retirement income.
# RecommendationBanner should show "No recommendation generated yet" (graceful, not crash).
# HouseholdPortfolioPanel should show "No recommendation generated yet" with Generate button.
# Click Generate → API returns 403; toast shows error; UI stays usable.

# Step 5: Restore kill-switch + restart
# Remove MP20_ENGINE_ENABLED=False from .env
docker compose restart backend
sleep 8
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/session/
# expect: 200
# Verify Sandra/Mike PortfolioRun still exists (kill-switch doesn't delete data)
```

If any step fails: halt + investigate. The rollback path MUST be exercisable before pilot Sev-1.

---

## §25. CHANGELOG.md entry template (A6.13; per locked #83)

Append to `CHANGELOG.md` (after the existing v0.1.0-pilot section):

```markdown
## [v0.1.2-engine-display] — 2026-05-XX

Engine→UI Display Integration shipped. Advisor sees engine recommendations on Goal route + Household route + auto-trigger on every committed-state mutation.

### Added
- Engine output displayed via PortfolioRun on Goal + Household routes.
- Auto-trigger generate-portfolio on commit / wizard / override / realignment (linked-household-only on conflict_resolve / defer_conflict / fact_override / section_approve per locked #27).
- `RecommendationBanner` (3 states: run / no-run / failure) + `HouseholdPortfolioPanel` + `AdvisorSummaryPanel` with `latest_portfolio_failure` SerializerMethodField surfacing per locked #9.
- `_trigger_portfolio_generation` reusable helper extracted from `GeneratePortfolioView`; `_trigger_and_audit` + `_trigger_and_audit_for_workspace` caller wrappers with typed-skip + unexpected-failure paths.
- 5 typed exceptions: `EngineKillSwitchBlocked`, `NoActiveCMASnapshot`, `InvalidCMAUniverse`, `ReviewedStateNotConstructionReady`, `MissingProvenance`.
- Sandra/Mike Chen synthetic fixture refreshed: RiskProfile (Q1=5/Q2=B/Q3=career/Q4=B → anchor=22.5/score=3/Balanced) + canonical sh_* fund holdings + advisor disclaimer/tour pre-ack on `reset-v2-dev.sh --yes`.
- Auto-seed initial PortfolioRun for Sandra/Mike via `load_synthetic_personas`.
- Stress fixtures: `engine/fixtures/stress_household_{medium,large}.json`.

### Changed
- `/api/preview/moves/` now reads `ideal_pct` from `goal_rollups` when `latest_portfolio_run` exists; `SLEEVE_REF_POINTS` calibration as fallback. Response includes `source: "portfolio_run" | "calibration"`.
- `reset-v2-dev.sh` ordering: `bootstrap_local_advisor` BEFORE `load_synthetic_personas` (was after; pre-ack silently skipped).
- `HouseholdDetailSerializer` exposes `latest_portfolio_failure` (most recent `portfolio_generation_post_*_failed` AuditEvent newer than latest PortfolioRun).
- PostgreSQL connection pool bumped to 150; `max_connections` ≥ 200 in docker-compose.yml.

### Tests
- ~50 backend test additions (Hypothesis property suites + concurrency stress + perf benchmarks + integration tests).
- ~60-80 new Vitest unit tests for engine→UI components.
- 16-20 new visual-verification baselines.
- Real-PII auto-trigger smoke (Niesner; documented in handoff-log).
- Cross-browser engine→UI assertions (Safari + Firefox).

### Architecture
- Sync-inline auto-trigger inside `transaction.atomic` per locked #74 (response IS truth; no on_commit polling).
- Helper-managed atomic with savepoints per locked #81.
- Latency: P99 ≤ 260ms across 3 household sizes (Sandra/Mike + medium-stress + large-stress; locked at A0.2 per #87).

### Locked decisions migrated to docs/agent/decisions.md
See "Engine→UI Display Integration (2026-05-03/04)" section.
```

Replace `2026-05-XX` with the actual date when committing (likely Mon 2026-05-08 pilot launch date).

---

## §26. ops-runbook section template (A6.13; per locked #21)

Create `docs/agent/ops-runbook.md` (NEW file or append if exists):

```markdown
# MP2.0 Operations Runbook

## Recommendation generation failures

### Detection signals
- Advisor reports blank Portfolio panels on Goal or Household routes.
- 5xx surge on `POST /api/clients/<hh>/generate-portfolio/`.
- Audit-log spike: `AuditEvent.objects.filter(action__startswith='portfolio_generation_post_', action__endswith='_failed', created_at__gt=now()-1h).count() > 5`
- Cross-browser smoke red on Safari/Firefox post-deploy.

### Diagnostic queries

```sql
-- Recent failed generation events
SELECT action, entity_id,
       metadata->>'source' AS source,
       metadata->>'reason_code' AS reason,
       metadata->>'failure_summary' AS summary,
       created_at
FROM audit_auditevent
WHERE action LIKE 'portfolio_generation_%_failed'
  AND created_at > now() - interval '1 hour'
ORDER BY created_at DESC;

-- Recent skipped events (typed exceptions)
SELECT action, entity_id,
       metadata->>'source' AS source,
       metadata->>'reason_code' AS reason,
       count(*)
FROM audit_auditevent
WHERE action LIKE 'portfolio_generation_skipped_post_%'
  AND created_at > now() - interval '1 hour'
GROUP BY 1, 2, 3, 4
ORDER BY count(*) DESC;
```

### Decision tree

1. **Skipped + reason_code = "EngineKillSwitchBlocked"** → Check `MP20_ENGINE_ENABLED`; if intentionally disabled, no-op. If unintentional, set to True + restart.
2. **Skipped + reason_code = "NoActiveCMASnapshot"** → Analyst publishes a CMA via Workbench; advisor regenerates.
3. **Skipped + reason_code = "ReviewedStateNotConstructionReady"** → Advisor resolves construction blockers via review screen + re-commits.
4. **Skipped + reason_code = "InvalidCMAUniverse"** → Active CMA failed validation; analyst republishes corrected snapshot.
5. **Skipped + reason_code = "MissingProvenance"** → Real-PII household lacks Bedrock provenance; check extraction pipeline + re-extract.
6. **Skipped + skipped_no_household = true** → Workspace not yet committed; expected for pre-commit advisor edits. No action.
7. **Failed + failure_summary** → Investigate: structured exception class? CMA universe issue? Engine math bug? Escalate to engineering with the audit row + (separately) reproduce locally.

### Escalation criteria
- > 5 failed events per hour → notify on-call engineer.
- Specific advisor blocked > 30 min → reach out to advisor + diagnose.
- Engine kill-switch toggled in production without advance notice → immediate engineering escalation.

### Rollback procedure
See `docs/agent/pilot-rollback.md` "Engine→UI Display Rollback (v0.1.2-engine-display)" section for the kill-switch + revert tag procedure.
```

---

## §27. Pilot-rollback runbook entry template (A6.13b)

Append to `docs/agent/pilot-rollback.md`:

```markdown
## Engine→UI Display Rollback (v0.1.2-engine-display)

### Detection signals
- Advisors report blank Portfolio panels on Goal or Household routes.
- 5xx errors on `/api/clients/<hh>/generate-portfolio/` surge.
- Audit-log spike: `AuditEvent.objects.filter(action__like='portfolio_generation_%_failed', created_at__gt=now()-1h).count() > 5`.
- Cross-browser smoke red on Safari/Firefox post-deploy.

### Rollback procedure (~10 min)

1. **Notify advisors** via established feedback channel: "Recommendation generation temporarily disabled; we're investigating."

2. **Set kill-switch**: `MP20_ENGINE_ENABLED=False` in env; restart backend.
   ```bash
   # Edit .env: add MP20_ENGINE_ENABLED=False
   docker compose restart backend
   sleep 10
   ```
   All auto-triggers + manual generates skip silently. Households remain committed; existing PortfolioRuns visible (may be stale).

3. **If kill-switch insufficient (data corruption)**: revert tag.
   ```bash
   git reset --hard v0.1.0-pilot
   bash scripts/reset-v2-dev.sh --yes
   # LOCAL DB nuke; pilot DB is separate. For pilot DB:
   # ops re-deploys v0.1.0-pilot artifact + applies any migration rollbacks.
   ```

4. **Database state**: PortfolioRun rows from auto-trigger persist post-kill-switch (no destructive change). Safe to keep. AuditEvents are append-only; never delete.

5. **Communication**: send all-pilot Slack: "Recommendation generation rolled back to v0.1.0-pilot tag. Pre-existing committed households + review workflows unaffected. Engineering investigating."

### Recovery
- After fix: re-deploy + flip kill-switch back on; advisors regenerate recommendations manually via Goal route Generate button.
- If migration rollback was needed: verify table indexes + foreign keys are clean post-recovery.
```

---

## §28. Decisions migration template (A6.16; per locked #91)

Append to `docs/agent/decisions.md`:

```markdown
## Engine→UI Display Integration (2026-05-03/04)

Multi-sub-session production-quality engineering effort to connect MP2.0's frontier-optimized PortfolioRun output to the advisor's eyes via Goal route + Household route + auto-trigger on every committed-state mutation. Mission shipped Mon 2026-05-08 pilot launch.

111 locked decisions captured across the planning + execution sessions. Full rationale in (deleted) plan file `~/.claude/plans/i-want-you-to-jolly-beacon.md` + `docs/agent/handoff-log.md` 2026-05-03/04 entries.

### Architecture (8 entries)

- **#9** Auto-trigger error handling: typed exceptions → silent skip + audit; unexpected → catch-all + audit + advisor toast via `latest_portfolio_failure` field + RecommendationBanner inline error.
- **#14** 8 trigger points wired: review_commit / wizard_commit / override / realignment + 4 workspace-level (conflict_resolve / defer_conflict / fact_override / section_approve).
- **#27** Workspace-level triggers gate on `workspace.linked_household_id is None` → silent-skip for pre-commit case.
- **#56** P99 ≤ 1000ms strict threshold; A0.2 confirmed sync-inline path works (P99 < 260ms across 3 household sizes).
- **#74** Sync-inline auto-trigger inside `transaction.atomic`; response IS truth (no `on_commit` polling).
- **#80** PostgreSQL connection pool to 150; `max_connections` ≥ 200 in docker-compose.yml.
- **#81** Helper internally manages `transaction.atomic` (Django nested-atomic uses savepoints).
- **#87** Threading variant fallback if A0.2 reveals P99 > 1000ms (NOT triggered; sync path locked).

### UX (12 entries)

- **#10** HouseholdRoute portfolio panel placement: between AUM strip and treemap.
- **#18** Stale state UX: muted run-data + accent-bordered overlay with Regenerate CTA.
- **#19** HouseholdPortfolioPanel mirrors RecommendationBanner failure pattern.
- **#24** Dual-line FanChart (DEFERRED to post-pilot if calibration fallback sufficient).
- **#68** Bespoke modal/overlay needs Esc + focus restore + click-outside (FeedbackModal pattern).
- **#75** i18n keys distribute under existing feature namespaces (no `engine.*` prefix).
- **#78** AdvisorSummaryPanel multi-link rendering: default-collapsed Radix Accordion (DEFERRED if simple stack works).
- **#88** Demo dress rehearsal: 10s threshold trigger steps; 8s non-trigger.
- **#90** Dual-line FanChart Legend a11y (DEFERRED with #24).
- **#108** Trust route-level ErrorBoundary (no per-component boundary).
- **#109** aria-live="polite" on RecommendationBanner + HouseholdPortfolioPanel.
- **#110** Verify accent-2 + ink-muted tokens at A3.5 commit time.

### Operational (10 entries)

- **#7** Sandra/Mike PortfolioRun auto-seeded at end of `load_synthetic_personas`.
- **#13** `scripts/demo-prep/upload_and_drain.py` extended to auto-seed PortfolioRun post-commit.
- **#26** `frontend/src/i18n/en.json` uncommitted change is user's responsibility (resolved before sub-session #1).
- **#34** `scripts/reset-v2-dev.sh --yes` is pre-authorized; bulk DB modifications otherwise require explicit auth.
- **#69** session-state.md update enforcement at every sub-session boundary.
- **#70** Comprehensive pre-flight command set per `next-session-starter-prompt.md` §2.
- **#79** A6.11 real-PII smoke uses Niesner (preserves Seltzer/Weryha demo state).
- **#86** A6.11 deletes Niesner state before re-upload (pre-authorized; supersedes #34 demo-state preservation for Niesner-only scope).
- **#95** A6.15 demo dress rehearsal: FULL reset + re-upload Seltzer + Weryha + Niesner.
- **#103** A6.13c rollback smoke test (kill-switch + verify graceful degradation + restore).

### Testing (~15 entries — see plan file §1 for full list)

- **#17** Comprehensive Vitest scope (~60-80 unit tests).
- **#20** A6 sub-agent orchestration: 3 sequential rounds, 2 parallel agents per round.
- **#46** Sub-session #1 must-pass gate (met).
- **#55+#84** mockHousehold factory at `frontend/src/__tests__/__fixtures__/household.ts`.
- **#60** §Y comprehensive testing & regression matrix (14 layers).
- **#61** 85% line coverage gate on touched modules.
- **#64** StrictMode double-invoke tests for every new component.
- **#71** Test selectors must match accessible-name resolution.
- **#82** Visual-verification spec is single source of truth.
- **#96** Full advisor lifecycle integration test.
- **#97** Pre-A2 backwards-compat integration test.
- **#98** Stale UX 3-layer test.
- **#99** Audit-trail Hypothesis property test.
- **#101** HouseholdDetail JSON-shape snapshot test.
- **#102** Pool capacity regression at 120 concurrent connections.

### Documentation (8 entries)

- **#11** Tag bump v0.1.2-engine-display + design-system.md update at end of A6.
- **#21** CHANGELOG + ops-runbook entries per A6.13.
- **#42** Dedicated starter prompt for multi-sub-session execution (this file's ancestor).
- **#43** Handoff dossier discipline.
- **#44** Per-phase commit message format with locked-decision citations.
- **#45** Per-phase verbose ~400-word handoff entry format.
- **#83** CHANGELOG entry version-stamped at A6.13.
- **#91** A6.16 migrates all 111+ decisions to this file.

### Continuity (12 entries — see §X in plan file)

- **#X.1** Sub-session boundary protocol.
- **#X.2** Sub-session boot protocol.
- **#X.3** Within-sub-session compaction discipline.
- **#X.4** Per-phase commit message format.
- **#X.5** Per-phase verbose handoff-log entry template.
- **#X.6** MEMORY.md update triggers.
- **#X.7** Starter-prompt lifecycle.
- **#X.8** Sub-session ↔ phase mapping.
- **#X.9** Sub-session #1 must-pass gate (locked decision #46).
- **#X.10** Sub-agent output verification protocol.
- **#X.11** Mid-execution scope-change protocol.

### Meta (6 entries)

- **#15** Ship complete production-quality scope; no demo-bar/pilot-bar split.
- **#X.10 meta-lesson** Subagent gates pass against subagent-written fixtures (lessons from sub-session #11 + this mission's test bug).
- 10 anti-patterns burned in across sub-sessions #1-#11 (see `docs/agent/next-session-starter-prompt.md` §8).
- 8 lessons specific to this mission (see deleted starter-prompt §10).

### Outcomes

- Tests at v0.1.2-engine-display tag: ~1080 backend pytest + ~150 Vitest + 13 foundation + 40-44 visual-verification + ~15 cross-browser. Coverage 85% on touched modules.
- Bundle: ~270-280 kB gzipped (under 290 kB threshold).
- Latency: P99 < 1000ms across all 3 household sizes (sync-inline path).
- Real-PII: Niesner auto-trigger smoke validated (~$0 incremental Bedrock spend; pre-paid).
- Demo Mon 2026-05-04 ran against HEAD `<final>`; pilot launched Mon 2026-05-08.
```

---

## §29. design-system.md update (A6.9; per locked #11)

Append to `docs/agent/design-system.md`:

```markdown
## Engine output consumption (post-v0.1.2-engine-display canon)

The advisor sees engine recommendations via three derived helpers in `frontend/src/lib/household.ts`:

- `findGoalRollup(household, goalId) → Rollup | null` — per-goal dollar-weighted blend (engine pre-computed via `EngineOutput.goal_rollups`).
- `findHouseholdRollup(household) → Rollup | null` — household-level rollup.
- `findGoalLinkRecommendations(household, goalId) → LinkRecommendation[]` — per-account-link recommendations for a goal.

### Components consuming these

- `frontend/src/goal/RecommendationBanner.tsx` — run signature + freshness + Regenerate button + failure surfacing per locked #9.
- `frontend/src/goal/AdvisorSummaryPanel.tsx` — `link_recommendation.advisor_summary` per goal.
- `frontend/src/goal/GoalAllocationSection.tsx` — ideal bars from `goal_rollup.allocations` (calibration fallback when no run).
- `frontend/src/goal/OptimizerOutputWidget.tsx` — improvement metric from `link_recommendations[].expected_return` + `current_comparison`.
- `frontend/src/routes/HouseholdPortfolioPanel.tsx` — household_rollup display (expected_return + volatility + top funds).

### Backend pattern

- `_trigger_portfolio_generation(household, user, *, source)` in `web/api/views.py` — single helper for all 8 trigger sources.
- Typed exceptions for known states (`EngineKillSwitchBlocked`, `NoActiveCMASnapshot`, `InvalidCMAUniverse`, `ReviewedStateNotConstructionReady`, `MissingProvenance`) → silent skip via `portfolio_generation_skipped_post_<source>` audit.
- Unexpected exceptions → `portfolio_generation_post_<source>_failed` audit + `latest_portfolio_failure` field on HouseholdDetailSerializer → `RecommendationBanner` inline-error + Sonner toast.
- `_trigger_and_audit_for_workspace(workspace, user, *, source)` for workspace-level triggers (5-8) with `linked_household_id is None` gate.
- Sync-inline path inside `transaction.atomic` per locked #74; helper-managed atomic per #81.

### Calibration fallback

`useSleeveMix` + `useOptimizerOutput` remain as the what-if surface for slider drag and the cold-start case where no PortfolioRun exists yet. Engine output is canonical; calibration is the teaching anchor.

### Audit invariants

- One audit event per state-changing endpoint per kind. `portfolio_run_generated` (success) + `portfolio_run_reused` (REUSED via signature match) + `portfolio_generation_skipped_post_<source>` (typed exception) + `portfolio_generation_post_<source>_failed` (unexpected exception). Source captured in metadata per locked #16 single-canonical naming.
- `latest_portfolio_failure` SerializerMethodField filters by `created_at > latest_run.created_at` so old failures don't surface after a successful regenerate.
```
