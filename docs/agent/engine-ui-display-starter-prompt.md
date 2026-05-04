
# Engine→UI Display Integration — Next-Session Starter Prompt

**Compiled:** 2026-05-03 (in planning session, embedded in `~/.claude/plans/i-want-you-to-jolly-beacon.md` §Z)
**Purpose:** boot loader for the next post-`/compact` session. Hand off cleanly.
**Owns:** orientation + reading list + pre-flight gates + first concrete action. **Does NOT own:** implementation details (those are in the plan file).

## §0. Mission, deadlines, branch

You are continuing a multi-sub-session production-quality engineering effort: connect the MP2.0 engine's frontier-optimized `PortfolioRun` output to the advisor's eyes via Goal route + Household route + auto-trigger on every committed-state mutation. The engine works (`POST /api/clients/{id}/generate-portfolio/` returns 200 with valid `engine_output.link_first.v2`); the frontend never reads it. This work closes that gap.

- **Branch:** `feature/ux-rebuild` (15+ commits ahead of origin; user pushes Monday morning)
- **HEAD on entry:** `95af4b5` (verify in §3); after this work: `v0.1.2-engine-display` tag
- **Demo to CEO + CPO:** Mon **2026-05-04**
- **Pilot launch:** Mon **2026-05-08**
- **No remote push.** User pushes Monday morning per locked direction.
- **Mandate:** "ship complete production quality scope. No excuses or cutting corners" (locked decision #15)

## §1. Determine your mode FIRST

This prompt serves two cases. Read the user's last message + recent conversation to determine which:

- **Mode A: Continuing the planning conversation** — user hasn't approved the plan yet; you're refining, asking questions, exploring edge cases. Do NOT call ExitPlanMode without user authorization. Use AskUserQuestion to interview.
- **Mode B: Approved + executing** — user has approved the plan (typical signal: "go ahead", "start implementing", "let's execute"). Run §3 boot, then §6 first concrete action.

If unclear after reading the user's last message: ASK via `AskUserQuestion` "Should I continue planning, or are we approved to begin execution?" before any code change.

## §2. Reading list (priority order; ~10 min total)

1. **`MEMORY.md`** — auto-loaded; first entry "START HERE" points at the dossier
2. **`~/.claude/plans/i-want-you-to-jolly-beacon.md`** — this plan file (this prompt is embedded as §Z; read §1 locked decisions table + §X continuity + §Y testing + the next-phase section in detail)
3. **`docs/agent/next-session-starter-prompt.md`** (1,153 lines, rewritten 2026-05-03 PM at commit `081cfc8`) — **complementary** to this prompt; covers post-pilot-release scope: Mon morning runbook, pilot week 1-2 ops, post-pilot backlog, 10 anti-patterns. Read §3 (Tier 1 reading list), §4 (vision/long-term intent), §8 (anti-patterns) — these inform the engine→UI mission too.
4. **`docs/agent/handoff-log.md`** last 5 entries — what shipped most recently (verification-pass entry + visual-verification spec + FeedbackModal Esc fix all in last 5)
5. **`docs/agent/session-state.md`** — current state line + phase line. **WARNING: stale at `081cfc8`** (claims HEAD `3d16134`); A0 must update it as part of phase 0 boot per locked decision #69.
6. **`docs/agent/production-quality-bar.md`** §1.10 + §3 + §9 — UX polish + test coverage map + per-phase ping format
7. **`frontend/e2e/visual-verification.spec.ts`** (committed at `efbe58d`+`b14a199`; 24 tests) — A6 round 3 EXTENDS this with engine→UI surfaces; do not write a parallel spec
8. **`MP2.0_Working_Canon.md`** — only deep-read §9.4 architecture invariants + §11.8.3 real-PII + §6.3a vocabulary if you're touching surfaces governed by them

## §3. Pre-flight verification (§X.2 boot protocol; mandatory, ~5 min)

**Baseline updated 2026-05-03 PM after HEAD drift to `081cfc8`** — sub-session-#11 verification pass continued past the original plan baseline (`95af4b5`) with 3 additive commits: `efbe58d` (visual-verification spec, 17 tests), `b14a199` (8 more tests + FeedbackModal Esc fix — see locked decision #68), `081cfc8` (1,153-line `next-session-starter-prompt.md` rewrite for pilot release). Mirror that prompt's §2 comprehensive pre-flight.

```bash
cd /Users/saranyaraj/Projects/github-repo/mp2.0

# 1. HEAD + working tree state
git status --short --branch          # expect: feature/ux-rebuild ahead of origin by 1+
git log --oneline -5                 # expect: 081cfc8 → b14a199 → efbe58d → 95af4b5 → b887b18
git tag -l "v0.1*"                   # expect: v0.1.0-pilot + v0.1.1-improved-intake (this work adds v0.1.2-engine-display at A6.10)

# 2. Backend gate suite (~2 min)
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 \
  uv run python -m pytest \
    scripts/demo-prep/test_r10_sweep.py \
    engine/tests/ extraction/tests/ web/api/tests/ web/audit/tests/ \
    --tb=no -p no:warnings --benchmark-disable
# expect: 854 passed, 7 skipped
uv run ruff check . && uv run ruff format --check .
bash scripts/check-pii-leaks.sh       # expect: PII grep guard: OK
bash scripts/check-vocab.sh           # expect: vocab CI: OK
bash scripts/check-openapi-codegen.sh # expect: OpenAPI codegen gate: OK
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 \
  uv run python web/manage.py makemigrations --check --dry-run

# 3. Frontend gates (~30s)
cd frontend && npm run typecheck && npm run lint && npm run build && npm run test:unit && cd ..
# expect: 82 Vitest passing in 13 files

# 4. Live stack (Docker)
docker compose ps                    # expect: backend + db running
curl -s -o /dev/null -w "backend: %{http_code}\n" http://localhost:8000/api/session/
curl -s -o /dev/null -w "frontend: %{http_code}\n" http://localhost:5173/
# expect: 200 / 200

# 5. Playwright (live stack required; foundation + visual + cross-browser; ~2 min)
cd frontend && set -a && source ../.env && set +a
PLAYWRIGHT_BASE_URL=http://localhost:5173 \
  MP20_LOCAL_ADMIN_PASSWORD=change-this-local-password \
  npx playwright test --project=chromium e2e/foundation.spec.ts e2e/visual-verification.spec.ts --reporter=line
# expect: 13 + 24 = 37 passed
PLAYWRIGHT_BASE_URL=http://localhost:5173 \
  MP20_LOCAL_ADMIN_PASSWORD=change-this-local-password \
  npx playwright test --project=webkit --project=firefox e2e/cross-browser-smoke.spec.ts --reporter=line
# expect: 10 passed
cd ..

# 6. Env + secure root
echo "MP20_SECURE_DATA_ROOT=$MP20_SECURE_DATA_ROOT"
ls /Users/saranyaraj/Documents/MP2.0_Clients/ | head -8
# expect: secure root resolvable; 7 client folders present
```

**Expected at HEAD `081cfc8`:**
- **854 backend pytest passing** (7 skipped)
- **82 frontend Vitest passing** in 13 files
- **13 foundation e2e + 24 visual-verification = 37 chromium Playwright passing**
- **10 cross-browser Playwright passing** (webkit + firefox)
- All static gates clean (ruff/format/typecheck/lint/build/vocab/PII/OpenAPI/migrations)
- **Total: 983 tests passing**

Post-A6 target: ~1080 tests (+97 from this work — ~30 backend + ~60 Vitest + ~5 visual-verification + integration suite).

If any gate is red BEFORE you change anything: **halt + AskUserQuestion**. The environment is wrong; do not proceed.

## §4. Locked decisions (111 captured; cite by number in commits + pings)

The plan file §1 has the full table of 111 locked decisions across this session. Most-load-bearing for execution:

- **#9** Auto-trigger error handling: typed exceptions → silent skip + audit; unexpected → catch-all + audit + advisor toast via `latest_portfolio_failure` field + RecommendationBanner inline error
- **#14 + #27** 8 trigger points (4 original + 4 workspace-level); workspace-level fire only when `linked_household_id` exists
- **#15** No demo-bar/pilot-bar split; ship complete scope
- **#18 + #19 + #68** Stale state UX: muted + accent-bordered overlay with Regenerate CTA; mirror RecommendationBanner failure pattern; **bespoke overlay needs Esc handler + focus restore + click-outside per FeedbackModal Esc fix at b14a199**
- **#20** Sub-agent orchestration: 3 sequential rounds (Hypothesis+Vitest → concurrency+perf → visual regression)
- **#24** Dual-line fan chart: engine canonical (solid accent-2) + calibration what-if (dotted muted)
- **#28 + #29** State precedence: failure > stale > success; multi-link goal: dollar-weighted P50 single line
- **#42-#45** Continuity discipline (this prompt + per-phase pings + decision-log + dossier rewrite per sub-session)
- **#46** Sub-session #1 must-pass gate before #2
- **#56** Strict 1000ms threshold: > 1000ms = switch to threading
- **#60** §Y comprehensive testing & regression matrix
- **#61** 85% coverage gate on new code
- **#64** StrictMode double-invoke tests for every new component (lessons from `bca0112` DocDropOverlay bug class)
- **#68** Bespoke modal/overlay a11y: aria-modal=true is not enough; need explicit Esc + focus restore + click-outside (FeedbackModal Esc fix at b14a199; mirror DocDetailPanel pattern)
- **#69** session-state.md update enforcement at every sub-session boundary; currently stale (claims HEAD `3d16134`, actual `081cfc8`); A0 refreshes before any work
- **#70** Comprehensive pre-flight command set (per `next-session-starter-prompt.md` §2): includes test_r10_sweep.py + visual-verification + cross-browser + secure-root verification + Docker live-stack curls
- **#71** Test selectors must match accessible-name resolution: `aria-label` overrides visible text in Playwright role-name matching; use less-anchored regex (`/save.*draft/i`) or `getByText` for visible-text matches (lesson from b14a199 visual-verification gap closure)

## §5. Phase scope by sub-session (§X.8)

| Sub-session | Phases | Wall-clock |
|---|---|---|
| #1 | A0 + A1 + A2a (helper extraction + 4 trigger points) | 4-5 hr |
| #2 | A2b (4 new triggers + linked-HH gate) + A2c (~50 test updates) + A3a (backend moves) | 5-7 hr |
| #3 | A3b (frontend type fix + Goal view + components + i18n) + A4 + A5 | 4-6 hr |
| #4 | A6 round 1 (Hypothesis + Vitest comprehensive) + A6 round 2 (concurrency + perf + integration) | 5-7 hr |
| #5 | A6 round 3 (visual regression) + A6.9-A6.16 (design-system + tag + smoke + cross-browser + dress rehearsal + decisions migration + close-out) | 4-6 hr |

Halt-and-flush points: end of A2a (must-pass gate); end of A3a (backend complete); end of A4+A5 (demo-bar substantively complete); end of A6 round 2 (after code-reviewer findings fixed).

## §6. First concrete action (mode-dependent)

### Mode A (continuing planning):
Skim §1 locked decisions in plan file, then ASK the user via `AskUserQuestion`: "Plan has 111 locked decisions captured + §X continuity + §Y testing matrix. Anything else to refine, or are we approved to begin execution?"

### Mode B (approved; executing):
Run §3 pre-flight. Then begin **A0.-1** (read verification-pass-gaps addendum at `git show 95af4b5` + read the now-COMMITTED `frontend/e2e/visual-verification.spec.ts` at HEAD `081cfc8` to understand the 24-test scope my A6 round 3 will EXTEND with engine→UI surfaces). Then **A0.0** — extract this §Z verbatim to `docs/agent/engine-ui-display-starter-prompt.md` (different filename from the post-pilot-release `next-session-starter-prompt.md` rewritten at `081cfc8`; both coexist; my engine-ui-display starter is mission-scoped + deleted at A6.16). Commit. Then proceed with A0.1 verification + handoff entry. **Per locked decision #69**, A0.1 also refreshes the stale `session-state.md` to reflect HEAD `081cfc8` before any code change.

After A0: enter Phase A1 (Sandra/Mike fixture refresh). Plan file §"Phase A1" has full details.

## §7. Stop conditions (halt + AskUserQuestion when these fire)

1. Any prior gate red BEFORE you change anything (expected baseline: 983 tests at HEAD `081cfc8`)
2. Engine probe at A0 returns ≠ 200 with valid output
3. `optimize()` wall-time > 1000ms (per locked #56) — switch to threading variant; ASK before implementing
4. A2 helper extraction grows beyond ~250 lines
5. A2 test-update churn exceeds ~50 file edits
6. HEAD has drifted past `081cfc8` between plan-write and execution (this PM the drift was 3 commits past `95af4b5` → `081cfc8`; if HEAD is past `081cfc8` when execution begins, re-audit per the protocol the user used in this round)
7. PII grep guard or vocab CI fails on a new commit
8. You discover regression vs HEAD `081cfc8` baseline
9. You're considering pushing to origin — DO NOT
10. Locked decision in §1 conflicts with code — handoff is right; flag + ask before changing
11. visual-verification.spec.ts goes red on any commit (it's the canonical full-checklist regression spec at HEAD `081cfc8`; 24 tests must stay green)

## §8. Anti-patterns (do not repeat)

These are augmented from `next-session-starter-prompt.md` §8 — every one cost real time during sub-sessions #1-#11. Don't repeat them.

- **"Tests pass = ship-ready"** — sub-session #11 verification pass found StrictMode bug class that subagent gates missed; foundation e2e is the catch (always re-run `foundation.spec.ts` + `visual-verification.spec.ts` after ANY frontend touch)
- **"Subagent says it's done"** — verify by Reading every file the subagent touched (per §X.10); subagent gates pass against subagent-written fixtures, not against `foundation.spec.ts`
- **Mock fixtures that don't mirror production payload shape** — caused the cost-key bug at `2bd77d3`; verify `mockHousehold()` matches actual `/api/clients/<id>/` response byte-for-byte (locked decision #55)
- **`setState((prev) => mutate-closure-array)` StrictMode-double-update class** — caused DocDropOverlay regression at `bca0112`; the setState updater MUST be pure; compute new list OUTSIDE the updater (per locked decision #64)
- **`aria-label` text vs visible text divergence** — Playwright `getByRole({ name: /.../i })` resolves to the aria-label NOT the visible text; use less-anchored regex (`/save.*draft/i`) or `getByText` for visible-text matches (locked decision #71; lesson from b14a199 visual-verification gap closure)
- **Bespoke modal/overlay needs explicit Esc handler + focus restore + click-outside** — `aria-modal=true` is not enough; FeedbackModal had role=dialog + aria-modal but no Esc handler → keyboard-trap bug fixed at b14a199; mirror DocDetailPanel pattern (locked decision #68)
- **`str(exc)` anywhere in DB columns / API response bodies / audit metadata** (use `safe_audit_metadata` from `web/api/error_codes.py`; PII leak risk — Bedrock errors carry extracted client text)
- **Hardcoded fund_ids on frontend** — use canonical `sh_*` from CMA fixture
- **Auto-regenerate on `INVALIDATED_BY_CMA` event** — manual regenerate per canon §4.7.3 (locked decision #37)
- **Auto-COMMIT households during R10 sweep or auto-trigger paths** — my plan auto-TRIGGERS portfolio generation on already-committed-or-being-committed households; it does NOT auto-commit ungated workspaces. Don't conflate (per `next-session-starter-prompt.md` §8 anti-pattern #9)
- **Honest audit when user pushes back** — three rounds of "Is everything done?" each surfaced a real bug; user's pushback is signal, not noise; don't restate confidence — re-run higher-level tests + surface gaps explicitly
- **Skip the per-phase verbose ping discipline** — production-quality-bar.md §9 + locked decision #44

## §9. Per-phase ping format (verbose ~400 words; production-quality-bar.md §9 + locked decision #45)

Every phase exit pings the user with:
1. **What changed** — HEAD + diff highlights + audit-finding closure refs
2. **What was tested** — new tests + invariants pinned + manual smoke + full gate-suite tail
3. **What didn't ship** — open items + reason + path forward + which sub-session it lands
4. **What's next** — phase continuation + estimated scope
5. **What's the risk** — regression possibilities + how the gates would catch them
6. **Locked decisions honored** — citation by number
7. **Continuity check** — session-state.md updated yes/no; dossier §3 updated yes/no; MEMORY.md updated yes/no

## §10. Halt protocol (§X.3 mid-phase compaction discipline)

If context approaches 80% mid-phase:
1. Halt at next natural breakpoint (commit point or end of logical sub-task)
2. Write handoff-log entry covering what's done + what remains in this phase
3. Update session-state.md headline + dossier §3
4. Commit any uncommitted work (use `wip:` prefix if mid-phase)
5. Suggest `/compact` to user with continuation cue: "Sub-session #N partial; phases <X-Y> remaining. Read engine-ui-display-starter-prompt.md to continue."

## §11. Communication style (per user-stated working style)

- Don't overclaim. "Tests pass" needs the actual count + tail. "Engine works" needs the probe output.
- Cite specific evidence (commit hash, regression test ids, gate-output tail) — never opinions like "looks good".
- Verbose per-phase pings with `file_path:line_number` specifics.
- The user redirects when you drift. Treat redirects as normal input.
- When halting: clean handoff entry + commit any wip + ping via AskUserQuestion. Don't strand uncommitted work across a halt.

## §12. First message to the user (post-boot)

After §3 pre-flight and §6 mode determination:

```
Booted from engine-ui-display-starter-prompt.md.

HEAD: <commit>          # expected: 081cfc8 (or later if HEAD has drifted)
Pre-flight: <pass/fail per gate; expected total 983 passing>
Mode: <A: continuing planning | B: approved + executing>
Locked decisions: 111 captured (plan file §1)
Phase scope: <next phase based on handoff-log>

[If Mode A]: Anything else to refine, or are we approved to begin execution?
[If Mode B]: Beginning A0.-1 (verification-pass gaps reading) per plan §"Phase A0".
```

Wait for user direction. Do not begin code changes until §3 confirmed green AND mode is unambiguous.

