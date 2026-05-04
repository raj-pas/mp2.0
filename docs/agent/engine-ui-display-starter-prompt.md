# Engine→UI Display Integration — Starter Prompt (Sub-Session #4 Entry)

**Compiled:** 2026-05-04 AM, post-sub-sessions #1+#2+#3 close-out (HEAD `46f37e3`).
**Lifecycle:** updated at each sub-session boundary per locked #69; deleted at A6.16 close-out per locked #11+#42 (work + decisions migrated to `docs/agent/decisions.md` per #91).
**Mission:** connect MP2.0 engine's frontier-optimized PortfolioRun output to the advisor's eyes via Goal route + Household route + auto-trigger on every committed-state mutation.
**Plan file (canonical):** `~/.claude/plans/i-want-you-to-jolly-beacon.md` — 111 locked decisions; §X continuity discipline; §Y comprehensive testing matrix; §Z embedded starter (this file's ancestor).

---

## §0. Mission + Hard Deadlines + Mandate

You are the technical lead continuing a 5-sub-session production-quality engineering effort. The engine works (`POST /api/clients/{id}/generate-portfolio/` returns 200 with valid `engine_output.link_first.v2`); sub-sessions #1+#2+#3 wired backend + frontend so the advisor now sees engine recommendations on Goal route + Household route. Sub-sessions #4+#5 add comprehensive testing + visual regression + tag bump + dress rehearsal that locked decision #15 ("ship complete production-quality scope, no cutting corners") requires before pilot launch.

- **Branch:** `feature/ux-rebuild`. As of HEAD `46f37e3`, branch is **8 commits ahead of origin** + 9 commits past sub-session-#1 entry baseline `081cfc8`.
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

The user's last directive in the prior session was "Proceed straight through and everything... 'production-grade software for a limited user set'". If that directive carries forward, default to **Mode B**.

---

## §2. Reading list (priority order; ~10 min total)

1. **`MEMORY.md`** at `~/.claude/projects/-Users-saranyaraj-Projects-github-repo-mp2-0/memory/MEMORY.md` — auto-loaded; first entry "START HERE" points at the dossier.
2. **THIS FILE** (`docs/agent/engine-ui-display-starter-prompt.md`) — sub-session #4 boot.
3. **`docs/agent/handoff-log.md` last 5 entries** — sub-sessions #1+#2+#3 close-outs (entries dated 2026-05-03 PM through 2026-05-04 AM). Read in chronological order to understand evolution.
4. **`docs/agent/session-state.md`** — current headline (HEAD `46f37e3`; phase line states sub-session #4 is next).
5. **`~/.claude/plans/i-want-you-to-jolly-beacon.md`** — the plan file. Read §1 (111 locked decisions table — focus on #17, #20, #46, #56, #60-#67, #80, #82, #84-#107) + §X (continuity discipline) + §Y (comprehensive testing matrix). Ignore the §Z embedded prompt (predates sub-sessions #1-#3).
6. **`docs/agent/next-session-starter-prompt.md`** (1,153 lines, post-pilot-release scope, complementary to this file) — read §3 (Tier 1 reading list) + §8 (10 anti-patterns burned in across sub-sessions #1-#11).
7. **`docs/agent/production-quality-bar.md`** — §3 test coverage map + §9 per-phase ping format (~400 words verbose ping discipline).
8. **`MP2.0_Working_Canon.md`** — only deep-read §9.4 architecture invariants + §11.8.3 real-PII discipline + §6.3a vocabulary if you're touching surfaces governed by them. Most of sub-session #4 is testing; canon work is minimal.

**Code references to read** (refresh your model of the implementation):
- `web/api/views.py:91-130` — 5 typed exceptions + `_map_engine_value_error`
- `web/api/views.py:621-865` — `_trigger_portfolio_generation` helper (engine optimize + run create + REUSED path)
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

**Baseline at HEAD `46f37e3`** (verified-by-prior-session via `git log` + green test runs):

```bash
cd /Users/saranyaraj/Projects/github-repo/mp2.0

# 1. HEAD + working tree state
git status --short --branch          # expect: feature/ux-rebuild ahead of origin by 8
git log --oneline -10                # expect newest 9: 46f37e3 → 303e378 → 12a972d → 1462988 → 74e20ce → f003ed6 → c641cbb → b66eaaf → 8bf774b → 081cfc8
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
# SUB-SESSIONS #1-#3 — the failures are STATE-DEPENDENT. To get 24/24: run
# upload_and_drain.py for Niesner first. Per locked #95, A6.15 demo dress rehearsal
# in sub-session #5 runs FULL reset + re-upload Seltzer/Weryha/Niesner; this restores
# the 24/24 baseline. Sub-session #4 should NOT chase these failures.
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

- **A0** — Pre-flight green; **A0.2 latency probe** (10 iterations × 3 households) locked **SYNC-INLINE** path: Sandra/Mike P99=258ms · medium-stress P99=239ms · large-stress P99=235ms; all under 1000ms threshold per locked #56. Stress fixtures persisted at `engine/fixtures/stress_household_{medium,large}.json`. **A0.4 grep audit** identified ~17 affected test files (broader than plan's 8). **A0.3** verified `commit_reviewed_state` line numbers (function@495 / record_event@529 / return household@536; 7-line drift from plan, acceptable).
- **A1** — `personas/sandra_mike_chen/client_state.json` refreshed: RiskProfile (Q1=5/Q2=B/Q3=career/Q4=B → anchor=22.5/score=3/Balanced) + 7 canonical sh_* fund holdings (sh_income/sh_equity/sh_global_equity/sh_builders/sh_founders/sh_savings/sh_small_cap_equity; total $1,308,000) + advisor_pre_ack (disclaimer v1 + tour). `load_synthetic_personas` extended with `_load_risk_profile` + `_load_advisor_pre_ack`. `reset-v2-dev.sh` ordering FIXED: `bootstrap_local_advisor` BEFORE `load_synthetic_personas`. 4 smoke tests in `web/api/tests/test_sandra_mike_fixture_smoke.py`.
- **A2a** — 5 typed exceptions + `_map_engine_value_error` at `web/api/views.py:91-130`. Helper trio: `_trigger_portfolio_generation(household, user, *, source) -> PortfolioRun` (helper-managed atomic per #81; reusable check OUTSIDE atomic so audit emits persist on raise); `_trigger_and_audit(...)` (typed-skip + unexpected-failure audit paths per #9); `_trigger_and_audit_for_workspace(...)` (linked_household_id gate per #27). 4 trigger points wired (review_commit / wizard_commit / override / realignment). `latest_portfolio_failure` SerializerMethodField on `HouseholdDetailSerializer`. 8 regression tests.

### Sub-session #2 (commit `1462988`)

- **A2b** — 4 NEW workspace-level triggers (#5-#8): conflict_resolve (single + bulk variants), defer_conflict, fact_override, section_approve. All gated on `workspace.linked_household_id is None` per locked #27 → silent-skip + emit `portfolio_generation_skipped_post_<source>` audit with `metadata.skipped_no_household=True` for un-linked workspaces.
- **A3a** — `MovesPreviewView` reads `ideal_pct` from `latest_portfolio_run.output.goal_rollups[goal_id]` when run exists; `SLEEVE_REF_POINTS` calibration as fallback. Response includes `source: "portfolio_run" | "calibration"`. 3 regression tests.

### Sub-session #3 (commits `12a972d`, `303e378`, `46f37e3`)

- **A1+A5 follow-up** — `load_synthetic_personas` auto-seeds initial PortfolioRun for Sandra/Mike at end of fixture load. Live verified: `reset-v2-dev.sh --yes` produces Sandra/Mike with PortfolioRun.
- **A3.1 frontend types** — `frontend/src/lib/household.ts` types aligned with engine schema: `Allocation`, `Rollup`, `ProjectionPoint`, `EngineOutput`, `FanChartPoint`, `CurrentPortfolioComparison`, `LinkRecommendation` (full engine shape), `PortfolioRunLinkRow` (DB persisted subset), `PortfolioRun.output: EngineOutput | null`, `HouseholdDetail.latest_portfolio_failure`. 3 helpers: `findGoalRollup` / `findHouseholdRollup` / `findGoalLinkRecommendations`. Renamed `findLinkRecommendation` → `findLinkRecommendationRow`.
- **A3.5** — `RecommendationBanner.tsx` (140 LoC; 3 states; aria-live="polite" per #109; Sonner toast on failure per #9). `AdvisorSummaryPanel.tsx` (61 LoC). `HouseholdPortfolioPanel.tsx` (150 LoC; mirrors Banner failure pattern per #19).
- **A3.6** — `useGeneratePortfolio` mutation hook in `lib/preview.ts`.
- **A3.7** — ~24 i18n keys under `routes.household.*` + `routes.goal.*` per #75.
- **A3.8 / A4** — RecommendationBanner above Goal KPI strip; AdvisorSummaryPanel below GoalAllocationSection; HouseholdPortfolioPanel between modals + treemap on HouseholdRoute.

### Test counts at HEAD `46f37e3`

| Suite | At `081cfc8` baseline | At `46f37e3` | Delta |
|---|---|---|---|
| Backend pytest | 854 passed, 7 skipped | **869 passed, 7 skipped** | +15 (4 A1 smoke + 8 A2a auto-trigger + 3 A3a moves) |
| Frontend Vitest | 82 in 13 files | **82 in 13 files** | 0 (no new component tests yet — A6.0 covers) |
| Foundation e2e | 13 in chromium | **13 in chromium** | 0 (no regressions) |
| Visual-verification | 24 in chromium | **18 passed, 6 failed (state-dependent)** | -6 (R10 sweep wiped; A6.15 restores) |
| Cross-browser | 10 in webkit+firefox | 10 (not re-run; expected stable) | 0 |
| Bundle size gzipped | 258 kB | **267.21 kB** | +9.21 kB (under 290 kB threshold per #85) |

---

## §5. Locked decisions (111 captured; the most-load-bearing for sub-session #4)

The plan file §1 has the full table. For sub-session #4 work, these are critical:

- **#17** Comprehensive Vitest scope (~60-80 unit tests across new components: render variants, critical interactions, ARIA, keyboard nav, multi-link goal grouping, edge cases).
- **#20** A6 sub-agent orchestration: 3 sequential rounds. Round 1: Hypothesis property suites (Agent A) + Vitest comprehensive (Agent B) in parallel.
- **#46** Sub-session #1 must-pass gate ALREADY MET; no further must-pass between sub-sessions #2-#5 unless stop conditions fire.
- **#55 + #84** mockHousehold factory at `frontend/src/__tests__/__fixtures__/household.ts` — must mirror production `/api/clients/<id>/` payload shape byte-for-byte (lesson from sub-session #11 cost-key bug).
- **#56** P99 ≤ 1000ms strict threshold; A0.2 confirmed sync-inline path works.
- **#60** §Y comprehensive testing & regression matrix — 14 layers covering full coverage.
- **#61** 85% line coverage gate on touched modules (web/api/views, web/api/preview_views, web/api/serializers, web/api/wizard_views, web/api/management/commands/load_synthetic_personas).
- **#64** StrictMode double-invoke tests for every new component (lesson from `bca0112` DocDropOverlay regression).
- **#71** Test selectors must match accessible-name resolution: aria-label overrides visible text in Playwright `getByRole({name})`; use less-anchored regex or `getByText` for visible-text matches.
- **#80** PostgreSQL connection pool to 150; verify Postgres `max_connections` ≥ 200 in `docker-compose.yml`.
- **#82** Visual-verification spec is single source of truth; A6 round 3 EXTENDS it with engine→UI surfaces (~16-20 new tests; total ~40-44).
- **#92** Sub-session #4 budget: 5-7 hr (sync-inline path locked at A0.2 per #87; threading not needed).
- **#96** Full advisor lifecycle integration test in A6.3 (~200 LoC, walks every trigger sequentially, asserts cumulative PortfolioRun lifecycle).
- **#97** Pre-A2 backwards-compat integration test in A6.3 (loads a pre-A2 PortfolioRun fixture; asserts HouseholdDetail renders correctly).
- **#98** Stale UX 3-layer test: backend integration + Vitest mock + Playwright extension.
- **#99** Audit-trail Hypothesis property test in A6.4 — `@given(exception_class)` walks all 5 typed + 3 representative unexpected; asserts AuditEvent.count() increments by exactly 1; metadata reason_code structured; PII grep on metadata JSON.
- **#100** Real-Chrome smoke at every sub-session boundary (5 passes total). Sub-session #4 boundary smoke: foundation e2e + manually open `localhost:5173/` in Chrome (NOT headless) for 60s — verify Sandra/Mike auto-seeds + RecommendationBanner + HouseholdPortfolioPanel render.
- **#101** HouseholdDetail JSON-shape snapshot test in A2.5 (DEFERRED to sub-session #4 from sub-session #1 scope; commit fixture + serializer test together).
- **#102** Pool capacity regression at 120 concurrent connections.
- **#104** A3.1 expectTypeOf type-safety regression tests via vitest.
- **#106** Vitest cache-invalidation tests for `useGeneratePortfolio` (onSuccess invalidates; onError doesn't; uses MSW or fetch mock).
- **#107** A6 render-perf benchmark: HouseholdPortfolioPanel < 100ms; treemap < 300ms; total page TTI < 1500ms with stress-large fixture (per #77).
- **#X.10** Sub-agent verification protocol: Read every file the agent claims to have edited; re-run agent's tests locally; spot-check file:line citations; verify locked-decision compliance.

---

## §6. Sub-session #4 phase scope (A6 round 1+2; estimated 5-7 hr)

### A6 Round 1 (parallel sub-agent dispatch per locked #20)

Dispatch 2 sub-agents in a SINGLE message with two Agent tool calls:

**Agent A — Hypothesis property suites (3 files; ~300 LoC)**:
1. `web/api/tests/test_auto_trigger_properties.py` — for any random sequence of N committed-state mutations, the PortfolioRun count is N+1 OR fewer (REUSED via signature match); all input/output/cma hashes deterministic; PortfolioRun.save() raises on existing pk preserved.
2. `web/api/tests/test_audit_metadata_invariants.py` (per #99) — `@given(exception_class)` walks all 5 typed exceptions + 3 representative unexpected (ValueError, RuntimeError, KeyError); asserts AuditEvent.count() increments by exactly 1 per trigger fire; metadata.reason_code is the typed exception class name; PII regex grep on metadata JSON returns zero matches for SIN-pattern (`\d{3}-\d{3}-\d{3}`) + account-number pattern + email.
3. `web/api/tests/test_workspace_trigger_gate_properties.py` — for triggers #5-#8: `linked_household_id is None` → emits `portfolio_generation_skipped_post_<source>` audit + returns None; linked → fires + REUSED expected for same-input.

**Agent B — Vitest comprehensive (~60-80 unit tests across new components)**:
- `frontend/src/__tests__/__fixtures__/household.ts` (NEW — per locked #84) — mockHousehold + mockPortfolioRun + mockEngineOutput + mockRollup + mockLinkRecommendation; defaults match Sandra/Mike-equivalent shape.
- `frontend/src/goal/__tests__/RecommendationBanner.test.tsx` — render variants (run / no-run / failure / pending) + Generate click + ARIA aria-live + keyboard nav + StrictMode double-invoke per #64.
- `frontend/src/goal/__tests__/AdvisorSummaryPanel.test.tsx` — single-link + multi-link rendering + edge cases.
- `frontend/src/routes/__tests__/HouseholdPortfolioPanel.test.tsx` — same coverage as Banner per #19 mirror.
- `frontend/src/lib/__tests__/household.test.ts` (NEW or extend) — findGoalRollup / findHouseholdRollup / findGoalLinkRecommendations edge cases.
- `frontend/src/lib/__tests__/preview.test.ts` (extend) — useGeneratePortfolio cache-invalidation per #106.
- `frontend/src/lib/__tests__/household.types.test.ts` (NEW) — expectTypeOf assertions per #104.

**Main thread** reviews each agent's output (per #X.10): Read every file the agent claims to have edited; re-run agent's tests locally; spot-check file:line citations; verify locked-decision compliance. Commit each agent's work as a separate logical commit with `subagent: <agent-name>` attribution line.

### A6 Round 2 (parallel sub-agent dispatch)

**Agent C — Concurrency stress + auth/RBAC matrix updates**:
- Extend `web/api/tests/test_concurrency_stress.py` for the 8 trigger paths (100 parallel each); assert no IntegrityError + audit count == success count + REUSED events for duplicate signatures.
- New `web/api/tests/test_connection_pool_capacity.py` per #102 — 120 parallel ThreadPoolExecutor workers; each opens DB cursor + holds for ~500ms; assert no `OperationalError: too many connections` + pool returns to baseline.
- Extend `web/api/tests/test_auth_rbac_matrix.py` for the 4 NEW trigger endpoints (5-8); assert anonymous → 401, advisor-out-of-team → 403, advisor-in-team → 200 + auto-trigger fires (or skip if no linked HH).

**Agent D — Perf benchmarks + integration tests**:
- Extend `web/api/tests/test_perf_budgets.py`: benchmark `_trigger_portfolio_generation(sandra_mike, ...)` directly; benchmark end-to-end commit-flow with auto-trigger; assert P50<250ms / P99<1000ms (matches A0.2 measurements).
- New `web/api/tests/test_full_advisor_lifecycle_with_auto_trigger.py` per #96 (~200 LoC) — walks wizard create → upload+drain → review → conflict resolve → fact override → defer → bulk resolve → section approve → commit → override → realignment on a single household; asserts cumulative PortfolioRun count + monotonic GENERATED/REUSED chain + AuditEvent count == trigger fire count + no IntegrityError.
- New `web/api/tests/test_pre_a2_portfolio_run_compat.py` per #97 — loads pre-A2 PortfolioRun fixture (manually crafted JSON matching `d2abfa1` v0.1.0-pilot shape, no `latest_portfolio_failure` field); walks GET /api/clients/<id>/ + override-create + regenerate; asserts fields render correctly + override triggers regeneration.
- New `web/api/tests/test_household_detail_serializer_snapshot.py` per #101 — pin HouseholdDetail JSON shape; asserts all expected fields present + no field rename.

### A6 Round 1+2 close-out (main thread)

After Agent reviews + commits land, dispatch `pr-review-toolkit:code-reviewer` subagent per locked #X.10 + #20 mirror (sub-session #11 pattern surfaced 1 BLOCKING + 5 critical findings). Fix all surfaced findings BEFORE moving to sub-session #5.

Run **full gate suite** at sub-session #4 end:
- Backend pytest with `--cov-fail-under=85` (per locked #61) on touched modules.
- Vitest with `npm run test:unit -- --coverage` — verify 85% on new components.
- ruff/format/PII/vocab/OpenAPI/migrations.
- Foundation e2e + visual-verification (still 18/24; will hit 24/24 at A6.15).
- Cross-browser (10 webkit+firefox).
- Real-Chrome smoke per #100.

**Estimated wall-clock**: 5-7 hr per locked #92.

---

## §7. Sub-session #5 phase scope (preview; estimated 4-6 hr)

After sub-session #4 lands cleanly:
- **A6 round 3** — Visual regression baselines for engine→UI surfaces, extending `frontend/e2e/visual-verification.spec.ts` per locked #82 (~16-20 new tests). Baselines under `frontend/e2e/__screenshots__/`.
- **A6.9** — Append "Engine output consumption" section to `docs/agent/design-system.md`.
- **A6.10** — Cut tag `v0.1.2-engine-display` (lightweight; NOT pushed).
- **A6.11** — Real-PII Niesner smoke per locked #79 + #86 (delete Niesner first; upload + drain + commit; assert auto-trigger fires).
- **A6.12** — Cross-browser Safari + Firefox spot-check per #23.
- **A6.13** — `CHANGELOG.md` entry `[v0.1.2-engine-display]` + new `docs/agent/ops-runbook.md` "Recommendation generation failures" section.
- **A6.13b** — Pilot-rollback runbook entry to `docs/agent/pilot-rollback.md`.
- **A6.13c** — Rollback smoke per locked #103 (`MP20_ENGINE_ENABLED=False`; verify graceful skip + audit + UI degradation).
- **A6.14** — Code-reviewer subagent dispatch.
- **A6.15** — Demo dress rehearsal per #95: full `reset-v2-dev.sh --yes` + `upload_and_drain.py Seltzer/Weryha/Niesner` + 8-step demo flow with stopwatch (10s threshold for trigger steps; 8s non-trigger per #88).
- **A6.16** — Final close-out: migrate all 111+ decisions to `docs/agent/decisions.md` per #91; delete this file; update CLAUDE.md "Useful Project Memory"; cumulative ping summarizing all 5 sub-sessions.

---

## §8. First concrete action (mode-dependent)

### Mode A (continuing planning):
Skim §1 locked decisions in plan file (focus on #17, #20, #60, #80, #82, #96-#107). ASK the user via `AskUserQuestion`: "Sub-sessions #1+#2+#3 shipped (functional core + frontend display surfaces); 869 backend pytest + foundation e2e 13/13 green. Anything to refine before I begin sub-session #4 execution (A6 Hypothesis + Vitest + concurrency + perf + integration)?"

### Mode B (approved + executing):
Run §3 pre-flight in full. If green, dispatch the 2 sub-agents for A6 Round 1 (Agent A Hypothesis + Agent B Vitest) **in a single message with two Agent tool calls so they run in parallel**. While they run, draft the A6 Round 1 close-out handoff entry in `docs/agent/handoff-log.md`. Review each agent's output per locked #X.10. Commit each agent's work separately with `subagent:` attribution line.

---

## §9. Stop conditions (halt + AskUserQuestion when these fire)

1. Any prior gate red BEFORE you change anything (expected baseline: 869 backend + 82 Vitest + 13/13 foundation + 18/24 visual-verification + 10 cross-browser).
2. HEAD has drifted past `46f37e3` between this session's compact and now (re-audit if so).
3. Engine probe at A0.1 returns ≠ 200 with valid output.
4. Coverage gate fails (<85% on touched modules per locked #61).
5. Pool capacity test (#102) reveals < 120 concurrent connections supported.
6. Concurrency stress test reveals IntegrityError or audit-count mismatch — investigate atomicity pattern.
7. PII grep guard fails on a new commit.
8. Sub-agent reports "complete" but `Read` of files shows scope creep / locked-decision violations — reject + restart with tightened prompt.
9. You're considering pushing to origin — **DO NOT**. User pushes Monday morning.
10. Locked decision in §1 conflicts with code at HEAD `46f37e3` — handoff is right; flag + ask before changing.
11. Visual-verification spec reaches 24/24 unexpectedly (means R10 sweep state was somehow restored — verify it's not test pollution).
12. Any new test file lands in `engine/tests/` that imports from `web` or `django` — engine purity violation; move to `web/api/tests/`.

---

## §10. Anti-patterns burned in (lessons from sub-sessions #1-#3 — DO NOT REPEAT)

These cost real time during execution; they will cost more if you repeat them.

### From sub-session #1

1. **Engine purity gate catches misplaced tests.** I initially placed `test_sandra_mike_fixture_smoke.py` in `engine/tests/`. The engine purity AST check at `engine/tests/test_engine_purity.py` raised because the test imports `django.contrib.auth` + `web.api`. Lesson: any test that uses `call_command(...)`, `@pytest.mark.django_db`, or imports from `web.api` MUST live in `web/api/tests/`, NOT `engine/tests/`. Engine tests must be pure (stdlib + pydantic + engine.* only).

2. **transaction.atomic rolls back audit emits inside the block.** I initially placed the `_record_portfolio_event` call for `ambiguous_current_lifecycle` INSIDE the helper's outer `with transaction.atomic():` block. When `raise InvalidCMAUniverse(...)` fired, the atomic rolled back — including the audit event. Lesson: emit audit events that must persist on raise OUTSIDE the atomic that might roll back. The fix in commit `f003ed6` moved the reusable check OUTSIDE the atomic.

3. **`reset-v2-dev.sh` ordering matters for advisor pre-ack.** Original ordering ran `load_synthetic_personas` BEFORE `bootstrap_local_advisor`. Result: advisor user didn't exist when persona load tried to write `AdvisorProfile`; pre-ack silently skipped (no error, just no rows). Lesson: management-command ordering in `scripts/reset-v2-dev.sh` is load-bearing; bootstrap user creation BEFORE persona load.

4. **`reset-v2-dev.sh` DOWNS all containers; backend needs explicit `up -d`.** The script runs `docker compose down -v` then `docker compose up -d db` (only db, not backend). After reset, the backend container is NOT running. Run `docker compose up -d backend` then sleep 5-10s. Don't waste time debugging "why is the engine probe failing" when the answer is "backend is down."

### From sub-session #2

5. **Workspace-level triggers don't break existing tests but ADD new audit events.** When I wired triggers #5-#8, the audit-event count went UP for tests exercising conflict_resolve / defer_conflict / fact_override / section_approve. Existing tests didn't fail because they assert per-action counts, not totals. Lesson: locked #16 single-canonical action naming (`portfolio_run_generated` vs `portfolio_generation_skipped_post_<source>`) means new audit kinds don't collide with existing per-kind assertions.

### From sub-session #3

6. **Auto-seed creates a synthetic_load PortfolioRun; subsequent same-signature trigger calls hit REUSED.** My `test_trigger_and_audit_success_emits_portfolio_run_generated_audit` initially called `_trigger_and_audit(hh, ...source='review_commit')` after `_bootstrap_full_demo()` (which calls `load_synthetic_personas` which now auto-seeds). Same household, same risk_score, same CMA → same run_signature → REUSED path → audit action becomes `portfolio_run_reused`, NOT `portfolio_run_generated` (the test's expected action). The test broke. Lesson: when testing the GENERATED path post-auto-seed, mutate household state (e.g., `household_risk_score`) to invalidate the run_signature before the trigger call. Fix in commit `303e378`.

7. **Multiple Playwright instances cause port collisions + stuck processes.** I started visual-verification.spec.ts as a background task multiple times while waiting on output. Each instance tried to bind to the same Playwright internal ports + stomp on each other's browser instances. Result: all instances hung, output files stayed empty for minutes. Lesson: **only ONE Playwright instance at a time.** If you need to re-run, `pkill -9 -f playwright; pkill -9 -f chromium; sleep 3` first. Don't background Playwright runs unless you're sure no other instance is running.

8. **R10 sweep state is wiped by `reset-v2-dev.sh`.** `visual-verification.spec.ts` has 6 tests for ReviewScreen + ConflictPanel + DocDetailPanel that depend on a Niesner workspace with conflicts. After `reset-v2-dev.sh --yes`, that workspace doesn't exist. The 6 tests fail with timeouts trying to find Niesner-related elements. Lesson: this is **state-dependent failure, not code regression**. Restoring requires `upload_and_drain.py Niesner`. Per locked #95, A6.15 demo dress rehearsal in sub-session #5 does the full restore. Sub-session #4 should NOT chase these failures.

### Cross-cutting (from `next-session-starter-prompt.md` §8 + locked decisions)

9. **`setState((prev) => mutate-closure-array)` StrictMode-double-update class** — per locked #64, every new component needs StrictMode tests. Compute the new list OUTSIDE the updater + pass a pure spread.

10. **Flat-shape mocks vs nested-shape production payload** — per locked #55, `mockHousehold()` factory output must match a real `/api/clients/<id>/` response byte-for-byte. Verify by capturing curl response shape during A6.0 fixture creation.

11. **aria-label vs visible-text divergence** — per locked #71, Playwright `getByRole({ name: /.../i })` resolves to the aria-label NOT the visible text. Use `getByText` for visible-text matches OR less-anchored regex.

12. **Bespoke modal/overlay needs explicit Esc handler + focus restore + click-outside** — per locked #68, `aria-modal=true` is not enough. If sub-session #5 implements stale-state overlay (locked #18), it MUST mirror DocDetailPanel's pattern.

13. **`str(exc)` anywhere = PII leak risk** — use `safe_audit_metadata` from `web/api/error_codes.py`. PII grep guard catches this; don't disable it.

14. **Subagent gates pass against subagent-written fixtures** — per locked #X.10, after each sub-agent returns: Read every file the agent claims to have edited; re-run agent's tests locally; spot-check file:line citations; verify locked-decision compliance.

15. **Re-run FULL foundation e2e after ANY frontend touch** — Vitest passing ≠ no regression. Foundation spec catches StrictMode bug class that subagent gates miss.

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
1. Halt at next natural breakpoint (commit point or end of logical sub-task).
2. Write handoff-log entry covering what's done + what remains.
3. Update session-state.md headline + this starter prompt's "What's done" section.
4. Commit any uncommitted work (`wip:` prefix if mid-phase).
5. Suggest `/compact` with continuation cue: "Sub-session #4 partial; rounds <X-Y> remaining. Read `docs/agent/engine-ui-display-starter-prompt.md` to continue."

**Never strand uncommitted work across a halt.** The starter prompt + handoff-log are the durable contract.

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
Booted from engine-ui-display-starter-prompt.md (sub-session #4 entry).

HEAD: 46f37e3 (or later if HEAD has drifted; halt + ask if so)
Pre-flight: <pass/fail per gate; expected 869 backend + 82 Vitest + 13/13 foundation + 18/24 visual + 10 cross-browser>
Mode: <A: continuing planning | B: approved + executing>
Locked decisions: 111 captured (plan file §1)
Phase scope: Sub-session #4 — A6 round 1+2 (Hypothesis + Vitest comprehensive + concurrency stress + auth/RBAC + perf + integration tests); 5-7 hr per locked #92.

[If Mode A]: Anything to refine before sub-session #4 execution?
[If Mode B]: Beginning A6 Round 1 — dispatching 2 sub-agents in parallel per locked #20 (Agent A Hypothesis property suites; Agent B Vitest comprehensive). Will commit each agent's work separately with subagent: attribution after Reading every file the agent touched per locked #X.10.
```

Wait for user direction. Do not begin code changes until §3 confirmed green AND mode is unambiguous.

---

## §15. Sub-session-#4-specific risks

- **Sub-agent context window**: A6 Round 1 dispatches 2 agents in parallel; each gets its own context budget. If an agent reports "partial completion due to context", main thread reads what landed + commits + dispatches a follow-up agent for the remaining scope.
- **mockHousehold byte-for-byte fidelity (#55)**: Verify by curling `/api/clients/hh_sandra_mike_chen/` BEFORE Agent B starts and capturing the response shape. Pass that shape to Agent B in the prompt as the canonical reference.
- **Coverage gate (#61)**: 85% on touched modules. The auto-trigger helper has many branches (kill-switch + no-CMA + invalid-CMA + readiness + provenance + reusable + REUSED + GENERATED + REGENERATED_AFTER_DECLINE + HASH_MISMATCH). Round 1 + Round 2 tests must hit all branches.
- **`portfolio_runs.order_by("-created_at").first()` idempotency**: helper uses this multiple times. If a test creates two PortfolioRuns with the SAME `created_at` (microsecond collision), order is unstable. Use `freezegun` or distinct as_of_dates to disambiguate.
- **Concurrency stress (#80 + #102)**: 100 parallel + headroom test at 120 means the test suite hits 220+ concurrent DB connections briefly. Verify Postgres `max_connections=200+` BEFORE Agent C runs; bump in `docker-compose.yml` if needed.
- **Hypothesis search settings**: large search spaces with `@given` need `@settings(max_examples=N, deadline=None)` to avoid timing out. Default 100 examples × 5 typed exceptions × 8 trigger paths = 4000 trial cases. Set `deadline=None` for DB-touching tests.
- **Real-Chrome smoke (#100)**: sub-session #4 boundary smoke is light because no new UI surfaces ship in this round (all testing). Run foundation e2e + manually open `localhost:5173/` in Chrome (NOT headless) for 60s — verify Sandra/Mike auto-seeds + RecommendationBanner + HouseholdPortfolioPanel render.

---

## §16. The shape of MP2.0 — for grounding when you context-switch

```
mp2.0/
├── engine/                          # Pure Python; no Django, no DRF (canon §9.4.2)
│   ├── optimizer.py                 # optimize() entry point
│   ├── schemas.py                   # Pydantic models (Household, EngineOutput, ...)
│   ├── frontier.py                  # compute_frontier()
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
│   │   ├── views.py                 # MUTATED: 5 typed exceptions + helper trio + 1 of 8 trigger sites
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
│   │   │   └── AdvisorSummaryPanel.tsx      # NEW (sub-session #3)
│   │   ├── routes/
│   │   │   ├── GoalRoute.tsx        # MUTATED: composition with new components
│   │   │   ├── HouseholdRoute.tsx   # MUTATED: HouseholdPortfolioPanel inserted
│   │   │   └── HouseholdPortfolioPanel.tsx  # NEW (sub-session #3)
│   │   ├── i18n/en.json             # MUTATED: ~24 new keys
│   │   └── __tests__/__fixtures__/
│   │       └── household.ts         # NEW expected (sub-session #4 — A6.0 mockHousehold per locked #84)
│   └── e2e/
│       ├── foundation.spec.ts       # 13 tests (stable)
│       ├── visual-verification.spec.ts  # 24 tests (18 pass + 6 state-dependent fails)
│       └── cross-browser-smoke.spec.ts  # 10 tests
├── personas/sandra_mike_chen/client_state.json   # MUTATED: RiskProfile + sh_* funds + pre-ack
├── scripts/reset-v2-dev.sh          # MUTATED: bootstrap before load_synthetic_personas
└── docs/agent/
    ├── engine-ui-display-starter-prompt.md   # THIS FILE
    ├── handoff-log.md
    ├── session-state.md
    ├── next-session-starter-prompt.md  # complementary; post-pilot-release scope
    ├── production-quality-bar.md
    └── ... (other docs)

~/.claude/plans/i-want-you-to-jolly-beacon.md   # 111 locked decisions; canonical
```

---

## §17. If you read only ONE thing

The plan file `~/.claude/plans/i-want-you-to-jolly-beacon.md` §1 (locked decisions table) is the canonical source. If you have time for nothing else: read decisions #14 (8 trigger points), #74 (sync inline), #81 (helper-managed atomic), #96 (full lifecycle test), #99 (audit-trail Hypothesis), #X.10 sub-agent verification protocol. Together those frame sub-session #4's must-do work.

---

## §18. Final note

Sub-sessions #1+#2+#3 shipped the FUNCTIONAL CORE. The advisor sees engine recommendations on Goal route + Household route. Demo Mon 2026-05-04 today runs against current HEAD `46f37e3`. Sub-sessions #4+#5 add the testing + validation rounds that locked decision #15's "ship complete production-quality scope" requires before pilot launch Mon 2026-05-08.

Before pilot: 869 backend pytest must grow to ~1080 (+97 tests across A6 rounds 1+2+3 per plan §3 phase summary); coverage 85% on touched modules; visual-verification 24/24 (A6.15 restore); cross-browser stable; rollback smoke documented; tag `v0.1.2-engine-display` cut at A6.10.

You have the plan file + this prompt + the handoff-log + session-state. Begin with §3 pre-flight, determine mode, then execute or interview.

**Don't skip ahead.** The discipline is what makes pilot-grade.
