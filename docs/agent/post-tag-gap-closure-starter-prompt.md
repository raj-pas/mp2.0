# Post-tag Gap-Closure — Next-Session Starter Prompt

**Compiled:** 2026-05-04 PM (in planning session); deleted at A7 close-out per locked decision §3.8 lifecycle
**Purpose:** boot loader for sub-session #2 + #3 post-`/compact`. Hand off cleanly.
**Owns:** orientation + reading list + pre-flight gates + first concrete action. **Does NOT own:** implementation details (those are in `~/.claude/plans/i-want-you-to-jolly-beacon.md`).

---

## §0. Mission, deadlines, branch

You are continuing a multi-sub-session production-quality engineering effort: close 5 functional/UX gaps from the original 2,786-line Engine→UI Display Integration plan that shipped at tag `v0.1.2-engine-display` with ~75% of done-criteria. The work lands as additive commits past the tag, then cuts a new tag `v0.1.3-engine-display-polish` at A7 close-out (per §3.22).

- **Branch:** `feature/ux-rebuild` (origin currently equal at `1ea5338`; gap-closure pushes 8 commits past)
- **HEAD on entry:** verify in §3 (sub-session #1 lands A0+A1+A2; sub-session #2 enters at A3)
- **Pilot launch:** Mon **2026-05-08** (~4 days out)
- **No remote push** until explicit user authorization at A7 close-out
- **Mandate:** "production-grade software for a limited user set; no excuses, no cutting corners" (pre-existing locked rule)
- **NEW tag at A7:** `v0.1.3-engine-display-polish` (per §3.22)

---

## §1. Determine your mode FIRST

This prompt serves sub-session #2 and #3. Read the user's last message + recent conversation to determine the mode:

- **Mode A: Continuing planning conversation** — user hasn't asked to execute; refining plan or asking questions. Do NOT call ExitPlanMode without authorization.
- **Mode B: Approved + executing** — user has approved sub-session #2 (typical signal: "go", "continue", "start sub-session #2"). Run §3 boot, then §6 first concrete action.

If unclear: ASK via `AskUserQuestion` "Should I continue planning, or are we approved to begin sub-session #N execution?" before any code change.

---

## §2. Reading list (priority order; ~10 min total)

1. **`MEMORY.md`** — auto-loaded; first entry "START HERE" points at `project_engine_ui_display.md` (post-v0.1.2 state)
2. **`~/.claude/plans/i-want-you-to-jolly-beacon.md`** — gap-closure plan; read §3 table (25 locked-this-session decisions §3.1-§3.25) + the next-phase section
3. **This file** — `docs/agent/post-tag-gap-closure-starter-prompt.md`
4. **`docs/agent/handoff-log.md`** last 3 entries — what shipped most recently + per-phase deltas
5. **`docs/agent/session-state.md`** — current HEAD + phase line; refresh at sub-session boundary per §X.1
6. **`docs/agent/decisions.md`** "Engine→UI Display Integration (2026-05-03/04)" section — 111 pre-existing locked decisions
7. **`docs/agent/ops-runbook.md`** — Phase A1 added "Portfolio Run Integrity Alert" section
8. **`MP2.0_Working_Canon.md`** — only deep-read §9.4 architecture invariants + §11.8.3 real-PII + §6.3a vocabulary if touching governed surfaces

---

## §3. Pre-flight verification (mandatory; ~5 min)

**Baseline at sub-session #2 entry** (post sub-session #1 close-out):
- HEAD: 3 commits past `1ea5338` (A0 + A1 + A2)
- Backend pytest: 854 + 18 (Phase A1) = 872 passed + 2 skipped
- Frontend Vitest: 177 + 17 (Phase A2) = 194 passing in 21 files
- Bundle: ≤ 275 kB gzipped

**Baseline at sub-session #3 entry** (post sub-session #2 close-out):
- HEAD: 5 commits past `1ea5338` (A0 + A1 + A2 + A3 + A4)
- Frontend Vitest: 226 in 22 files
- visual-verification: 36 chromium passing

```bash
cd /Users/saranyaraj/Projects/github-repo/mp2.0

# 1. HEAD + working tree state
git status --short --branch          # expect: feature/ux-rebuild N commits ahead of origin
git log --oneline -5                 # expect HEAD matches sub-session boundary
git tag -l "v0.1*"                   # expect: v0.1.0-pilot + v0.1.1-improved-intake + v0.1.2-engine-display

# 2. Backend gate suite (~3 min)
docker compose exec -T backend bash -c "cd /app && uv run pytest --tb=no --ignore=web/api/tests/test_perf_budgets.py -q"
# expect: count matches sub-session boundary

# 3. Frontend gates (~30s)
cd frontend && npm run typecheck && npm run lint && npm run build && npm run test:unit -- --run && cd ..

# 4. Static guards
bash scripts/check-vocab.sh
bash scripts/check-pii-leaks.sh
bash scripts/check-openapi-codegen.sh

# 5. Live stack
docker compose ps
curl -s -o /dev/null -w "backend: %{http_code}\n" http://localhost:8000/api/session/
curl -s -o /dev/null -w "frontend: %{http_code}\n" http://localhost:5173/
```

**If any gate is red BEFORE you change anything: halt + AskUserQuestion.**

---

## §4. Locked decisions (25 §3 captured this planning session; cite by §3.N in commits)

The plan file's §3 table has all 25. Most-load-bearing for execution:

- **§3.1** Slider drag UX: engine pill on saved view; calibration_drag pill ONLY during slider drag; flips back on save
- **§3.2** Stale-overlay fires on 4 statuses: invalidated/superseded/declined → StaleRunOverlay (Regenerable); hash_mismatch → IntegrityAlertOverlay (engineering-only)
- **§3.5** hash_mismatch backend audit emit on serializer access (rate-limited via `events.filter(...).exists()`)
- **§3.7** Slider state lift: `isPreviewingOverride: boolean` in GoalRoute, propagated via `onPreviewChange` callback to RiskSlider
- **§3.8** Multi-session execution; this prompt is the boot artifact; deleted at A7
- **§3.10** Theme-token grep gate at every commit gate that uses new tokens
- **§3.11** 3x baseline-stability run for visual regression
- **§3.13** PII-focused review pass at A7 in addition to general code-reviewer
- **§3.14** ≥90% line coverage gate (stricter than locked #61's 85%) on touched modules at A7
- **§3.15** Cross-browser extension (webkit + firefox) for new Goal-route surfaces
- **§3.16** Backwards-compat regression for pre-tag households
- **§3.18** Hypothesis property suite for status + audit-dedup invariants
- **§3.20** Automated browser regression coverage replaces manual checklist (15 pre-existing flows)
- **§3.21** API contract snapshot extension (4 state fixtures)
- **§3.22** New tag `v0.1.3-engine-display-polish` at A7
- **§3.25** Pilot dress rehearsal at A6 (locked #95 reactivated)

---

## §5. Phase scope by sub-session

| Sub-session | Phases | Wall-clock |
|---|---|---|
| #1 | A0 + A1 (backend stale + Hypothesis + snapshots + backwards-compat) + A2 (GoalAllocationSection + MovesPanel + SourcePill + slider-drag lift) | 4-5 hr |
| #2 | A3 (OptimizerOutputWidget) + A4 (Stale UX with 4 status variants + IntegrityAlertOverlay + audit emit) | 3-4 hr |
| #3 | A5 (demo + axe + visual baselines + cross-browser ext) + A5.5 (automated regression suite per §3.20) + A6 (real-Chrome smoke + dress rehearsal USER) + A7 (close-out + 2 subagent reviews + 90% coverage + tag v0.1.3) | 5-7 hr |

Halt-and-flush points: end of A2 (sub-session #1 close); end of A4 (sub-session #2 close); end of A7 (sub-session #3 close — push gate).

---

## §6. First concrete action (mode-dependent)

### Mode A (continuing planning):
Skim §3 locked-this-session decisions in plan file, then ASK via `AskUserQuestion`: "Plan has 25 §3 locked-this-session decisions captured + multi-session split + Phase A5.5 regression suite. Anything else to refine, or are we approved to begin sub-session #N execution?"

### Mode B (sub-session #2 starting):
Run §3 pre-flight. Then begin **Phase A3** per plan file (`OptimizerOutputWidget` engine-first refactor; ~75 min; mirrors A2 SourcePill pattern).

### Mode B (sub-session #3 starting):
Run §3 pre-flight. Then begin **Phase A5** per plan file (demo script update + axe coverage + visual baselines + cross-browser).

---

## §7. Stop conditions (halt + AskUserQuestion when these fire)

1. Any prior gate red BEFORE you change anything (expected baselines per §3 above)
2. Engine probe at A0 returns ≠ 200 with valid output
3. Bundle size grows past 290 kB gzipped (locked #85)
4. Vocab CI flags any new copy
5. PII grep guard fails on a new commit
6. Any phase wall-clock exceeds 5 hr per phase
7. Code-reviewer subagent (A7.1) surfaces BLOCKING findings → fix before tag
8. PII-focused review (A7.2) surfaces leak vectors → fix before tag
9. 90% coverage gate (A7.4) fails → add tests before commit
10. Visual baselines drift across 3 consecutive runs (§3.11) → halt; investigate determinism
11. User says "push" before A7 close-out commit + tag → halt; one final commit before push

---

## §8. Per-phase ping format

Every phase exit pings the user with:
1. **What changed** — HEAD + diff highlights + audit-finding closure refs
2. **What was tested** — new tests + invariants pinned + manual smoke + full gate-suite tail
3. **What didn't ship** — open items + reason + path forward
4. **What's next** — phase continuation + estimated scope
5. **What's the risk** — regression possibilities + how the gates would catch them
6. **Locked decisions honored** — citation by §3.N
7. **Continuity check** — session-state.md updated yes/no; handoff-log appended yes/no; this prompt deleted yes/no (only at A7)

---

## §9. Halt protocol

If context approaches 80% mid-phase:
1. Halt at next natural breakpoint (commit point or end of logical sub-task)
2. Write handoff-log entry covering what's done + what remains in this phase
3. Update session-state.md headline
4. Commit any uncommitted work (use `wip:` prefix if mid-phase)
5. Suggest `/compact` to user with continuation cue: "Sub-session #N partial; phases <X-Y> remaining. Read post-tag-gap-closure-starter-prompt.md to continue."

---

## §10. Communication style

- Don't overclaim. "Tests pass" needs the actual count + tail. "Engine works" needs the probe output.
- Cite specific evidence (commit hash, regression test ids, gate-output tail) — never opinions like "looks good".
- Verbose per-phase pings with `file_path:line_number` specifics.
- The user redirects when you drift. Treat redirects as normal input.
- When halting: clean handoff entry + commit any wip + ping via AskUserQuestion. Don't strand uncommitted work across a halt.

---

## §11. First message to the user (post-boot)

After §3 pre-flight and §6 mode determination:

```
Booted from post-tag-gap-closure-starter-prompt.md.

HEAD: <commit>          # expected per sub-session boundary
Pre-flight: <pass/fail per gate>
Mode: <A: continuing planning | B: approved + executing>
Locked decisions: 25 captured (plan file §3)
Phase scope: <next phase based on handoff-log>

[If Mode A]: Anything else to refine, or are we approved to begin sub-session #N?
[If Mode B]: Beginning <next phase> per plan file.
```

Wait for user direction. Do not begin code changes until §3 confirmed green AND mode is unambiguous.

**Begin with §3 pre-flight. Do not skip ahead.**
