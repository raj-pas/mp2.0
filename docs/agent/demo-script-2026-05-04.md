# Demo Script — CEO + CPO, 2026-05-04

**Stage state at HEAD `28628d8`** (or later commit on `feature/ux-rebuild`):

- DB reset clean → Sandra/Mike Chen synthetic + Default CMA seeded
- Seltzer real-PII workspace pre-uploaded + 5/5 docs reconciled, ready for review/commit
- KYC ready ✓; engine_ready/construction_ready ⚠ (advisor decisions remaining)
- Workspace label: `Seltzer review (demo prep)`
- 6 accounts, 4 goals, 18 cross-source conflicts, 1 person identified

## Pre-demo checklist (T-30 min)

- [ ] Run `bash scripts/reset-v2-dev.sh --yes` (clean DB; locked decision #34 pre-authorized)
- [ ] Run `uv run python scripts/demo-prep/upload_and_drain.py Seltzer --expect-count 5` (re-uploads Seltzer + drains worker; ~3-5 min wait for Bedrock)
- [ ] Run `uv run python scripts/demo-prep/upload_and_drain.py Weryha --expect-count 5` (Weryha pre-uploaded as drop-in backup; ~3-5 min wait for Bedrock)
- [ ] Confirm both are `5/5 reconciled`: `curl -s http://localhost:8000/api/review-workspaces/ | python -c "import json,sys; d=json.load(sys.stdin); print([(w['label'], w['status']) for w in d if 'demo prep' in w['label']])"`
- [ ] Open Chrome to `http://localhost:5173/` — login should land on advisor home
- [ ] Open `http://localhost:5173/methodology` once to warm the bundle (~820 KB; closes the cold-load risk on stage when Step 8 opens this page)
- [ ] **Close DevTools / hide font OTS console errors** (cosmetic; don't show on stage)
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

**What to say**: "Notice the small pill in the allocation panel header: 'Engine recommendation' with a run signature. That's the canonical surface — the bars come from the link-first engine's frontier-optimized blend, not calibration reference points. Same pill appears on the optimizer-output widget on the right (improvement % is dollar-weighted across links) and on the moves panel below. If a goal has no engine recommendation yet — say it was never run, or the link is in a degenerate state — these surfaces fall back to calibration with a 'Calibration preview' pill so the advisor always knows the source."

**What to say (override flow)**: "If the advisor wants to override the system-derived risk score for this goal, they pick a band, type a rationale, and save. That fires an audit event with the rationale, advisor, and timestamp — append-only. The engine auto-regenerates synchronously on save."

**Look for**: 'Engine recommendation' pill on allocation + optimizer-output + moves panels (3 distinct pill renders, same component); accent-2 styling distinguishes from calibration variant.

### Step 4.5 — Slider drag → override → engine regenerate (~30s)

**Click**: drag the risk slider to a different band (don't release yet).

**What to say**: "Watch the pills flip while I drag. They go from 'Engine recommendation' to 'Calibration preview (drag mode)' — the bars track the slider live so the advisor can see what the calibration would say at this band. The engine output stays fixed because it's tied to the SAVED config; we don't recompute the frontier on every drag tick."

**Click**: release slider → enter rationale "Demo override per Phase 4.5" → click Save.

**What to say**: "Save fires an AuditEvent and the engine regenerates synchronously — sub-second. Now the pills flip back to 'Engine recommendation' with a NEW run signature; banner timestamp updates within ~500ms. Closed-loop the platform was designed for."

**Look for**: pill flip live during drag (calibration_drag styling, muted); pill flip back to engine post-save with new signature; banner timestamp updates.

### Step 4.6 — CMA republish → stale overlay → regenerate (~60s, optional)

**Click**: open analyst CMA Workbench in another tab (`/cma`); duplicate active CMA; bump expected returns slightly; publish.

**Click**: switch back to Sandra/Mike goal route → reload page.

**What to say**: "Now there's a NEW active CMA, so the run we just generated is invalidated. Notice the engine panels here are dimmed and unfocusable — there's an overlay covering them with 'Recommendation is stale: regenerate to refresh' and a Regenerate button. The advisor cannot act on outdated numbers. The recommendation banner up top also shows a warning chip with the same message. This is the integrity guarantee — the system never lets the advisor commit to recommendations against stale assumptions."

**Click**: click Regenerate inside the overlay.

**What to say**: "Regenerates against the new CMA; overlay dismisses; banner shows fresh run signature. Same closed-loop pattern as the override flow."

**Look for**: muted+pointer-events-none engine panels; warning-bordered overlay with focus on Regenerate; click Regenerate dismisses overlay + reveals fresh engine panels with new run signature in pill.

**Note**: if the integrity check fails (`hash_mismatch` status — e.g. someone tampered with the run row directly), a different overlay fires — danger-bordered, NO Regenerate button, copy says "Engineering has been notified." Backend simultaneously emits an `portfolio_run_integrity_alert` AuditEvent (rate-limited per advisor, per run); ops-runbook §2 documents the engineer response. Advisor cannot act on it; engineering investigates.

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

Pivot to **Weryha** (pre-uploaded in the same DB; drop-in same-shape backup). Open `/review`, click the Weryha row instead of Seltzer, walk steps 5-7 against it. No live processing dead-air. If Weryha also misbehaves, fall back to Sandra/Mike Chen for the household/account/goal flow (steps 2-4 still work) and skip steps 5-7 to go straight to step 8 (methodology).

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
3. Run `uv run python scripts/demo-prep/upload_and_drain.py Seltzer` (~5 min — fill the gap with discussion, OR skip to Sandra/Mike walk-through)
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
