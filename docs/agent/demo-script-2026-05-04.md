# Demo Script — CEO + CPO, 2026-05-04

**Stage state at HEAD `28628d8`** (or later commit on `feature/ux-rebuild`):

- DB reset clean → Sandra/Mike Chen synthetic + Default CMA seeded
- Seltzer real-PII workspace pre-uploaded + 5/5 docs reconciled, ready for review/commit
- KYC ready ✓; engine_ready/construction_ready ⚠ (advisor decisions remaining)
- Workspace label: `Seltzer review (demo prep)`
- 6 accounts, 4 goals, 18 cross-source conflicts, 1 person identified

## Pre-demo checklist (T-30 min)

- [ ] Run `bash scripts/reset-v2-dev.sh --yes` (clean DB; locked decision #34 pre-authorized)
- [ ] Run `uv run python /tmp/demo-prep-seltzer.py` (re-uploads Seltzer + drains worker; ~3-5 min wait for Bedrock)
- [ ] Confirm Seltzer is `5/5 reconciled`: `curl -s http://localhost:8000/api/review-workspaces/?label_contains=Seltzer ...`
- [ ] Open Chrome to `http://localhost:5173/` — login should land on advisor home
- [ ] **Close DevTools / hide font OTS console errors** (cosmetic; don't show on stage)
- [ ] Have a backup Seltzer-equivalent folder ready (Weryha, same shape) in case of unexpected failure
- [ ] Worker NOT running (queue is drained; no background activity to confuse the demo)

## The 8 steps on stage

### Step 1 — Login + advisor home (~30s)

**Click**: type credentials → Sign in.

**What to say**: "Advisor logs in. Top bar shows their identity, the household picker, and shortcuts to methodology and reports — same chrome on every screen. We'll come back to the methodology page in a minute."

**Look for**: TopBar render, no console errors, advisor email visible.

### Step 2 — Pick Sandra/Mike Chen (~45s)

**Click**: `Select a client` dropdown → `Sandra Chen` (or whichever surfaces).

**What to say**: "This is our synthetic test household. The advisor sees an AUM split, a treemap broken down by goal, and a context panel on the right. Every panel here is computed server-side from the link-first portfolio engine — there's no client-side math duplication."

**Look for**: AUM strip renders, treemap renders, context panel populates.

### Step 3 — Drill into account → goal (~60s)

**Click**: tap an account in the treemap → tap a goal in the account view.

**What to say**: "From the treemap I can drill into any account. The account view shows a fund-composition ring + top-funds bars. Drilling into a goal shows the risk-band marker, projection fan chart, and the optimizer's current-vs-ideal recommendation."

**Look for**: 4 KPI tiles, fan chart renders cleanly (no Chart.js errors), RiskSlider visible.

### Step 4 — Goal allocation panel (~45s)

**What to say**: "If the advisor wants to override the system-derived risk score for this goal, they pick a band, type a rationale, and save. That fires an audit event with the rationale, advisor, and timestamp — append-only. The optimizer recomputes against the override and the moves panel updates."

**Optional click**: drag the slider to a different band to show live recompute (don't save unless rehearsed).

### Step 5 — Switch to /review (~30s)

**Click**: top-bar `Review` link OR navigate to `/review`.

**What to say**: "This is where the document-driven onboarding lives. Drop the client's KYC, statements, and notes — the AI extracts structured facts, surfaces conflicts, and lets the advisor review before commit. Real client data; nothing leaves the secure local environment unless the advisor explicitly commits."

**Look for**: Review queue + DocDropOverlay both render.

### Step 6 — Open Seltzer workspace (~60s)

**Click**: `Seltzer review (demo prep)` row in the queue.

**What to say**: "Here's a real client folder we onboarded earlier. 5 documents — DOB, address, KYC profile, statements, and meeting notes — all extracted via Bedrock in ca-central-1. You can see each document was classified as identity, KYC, or meeting note; all 5 reconciled cleanly with zero failures."

**Look for**:
- 5 reconciled chips (green)
- 0 failed chips
- KYC ready ✓ in readiness panel
- Engine ready / Construction ready ⚠ (engineering: shows the gates correctly identify what's still pending advisor decision)

### Step 7 — Review + approve sections (~90s)

**What to say**: "The advisor sees what was extracted, sees the conflicts where two sources disagreed, and resolves them. For the demo, I'll just walk through the readiness panel — it's flagging what still needs an advisor decision: household type and how the 6 accounts map to the 4 goals. In production, the advisor would resolve via a state-edit panel, then approve each of the 6 required sections."

**Optional**: click `Approve` on `risk` section just to show the button works (it'll fail with "Plain approval is blocked while conflicts remain" — that's a feature, not a bug, but worth NOT clicking unless rehearsed).

### Step 8 — Methodology page (~30s)

**Click**: `Σ Methodology` button in top bar.

**What to say**: "Every score, projection, and recommendation in this app traces back to a documented formula and worked example. The methodology page covers all 10 sections — risk profile, anchor, goal-level scoring, horizon caps, sleeve mix interpolation, lognormal projections, rebalance moves, realignment, archive snapshots — all in canon-aligned vocab. This is what we hand to compliance and what advisors learn from when ramping."

**Look for**: Methodology page renders. (R8 work just shipped.)

## Backup plans

### If Seltzer doesn't render

Fallback to Sandra/Mike Chen for the household/account/goal flow (steps 2-4 still work). Skip steps 5-7 (review pipeline) and go straight to step 8 (methodology).

### If a network blip happens during steps 5-7

Reload, re-pick Seltzer. State is committed in DB so the workspace stays.

### If Bedrock is unavailable on demo day

Pre-uploaded state means no Bedrock calls happen during the demo. Only risk: if something needs re-processing, drop steps 5-7 and use fallback above.

### If the worker accidentally got started

`pkill -f process_review_queue` from the terminal. The demo doesn't need the worker — Seltzer is already reconciled.

## What NOT to demo (per locked decisions)

- **Don't open DevTools** during the demo — cosmetic font OTS errors are unfixed (P0 cosmetic, locked decision #22d).
- **Don't click "Commit household"** on Seltzer mid-demo — there are unresolved conflicts and missing advisor decisions; clicking will surface a 400 with the specific blockers (this is *correct* behavior but the toast may distract from the narrative).
- **Don't try to push** to remote — branch is 13+ commits ahead of origin and not user-authorized for push.
- **Don't quote real client names** when narrating — say "the client" or "this household."

## Known limitations to acknowledge if asked

- **Conflict-resolution UI cards** (P0 #2) — engine surfaces the conflicts; advisor-action UI is a near-term ship. Today the advisor would resolve via state-edit panel in the same screen.
- **fr-CA i18n** — scaffold exists; translations land post-pilot (locked decision #12).
- **MFA + audit-browser UI** — Phase B; not part of this rewrite (P0 #6 + #7).
- **Real-PII first-week pilot bugs** — 2 catalogued (workspace status flip + zero-value accounts); fix plan being scoped by a scheduled agent on 2026-05-06.

## Recovery procedure if something goes badly wrong on stage

1. **Don't apologize at length** — say "let me reset to a clean state" and:
2. Open terminal, run `bash scripts/reset-v2-dev.sh --yes` (~30s)
3. Run `uv run python /tmp/demo-prep-seltzer.py` (~5 min — fill the gap with discussion, OR skip to Sandra/Mike walk-through)
4. Refresh browser
5. Resume the flow

If the failure is unrecoverable, fall through to a code/architecture walkthrough using the dossier (`docs/agent/post-r7-handoff-2026-05-01.md`) — there's enough material there for a 20-min architecture talk that doesn't need a working app.

## After the demo

- [ ] `git status` — capture any uncommitted state
- [ ] `git log --oneline -5` — confirm HEAD
- [ ] Update `docs/agent/handoff-log.md` with: who attended, key questions, decisions made, any new bugs surfaced
- [ ] Triage feedback for release on 2026-05-08
- [ ] The scheduled agent fires Wed 2026-05-06 09:00 Winnipeg with a fix-plan proposal for the 2 catalogued bugs

---
*Generated 2026-05-01 during demo prep. Update if state changes before demo day.*
