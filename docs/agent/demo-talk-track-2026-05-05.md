# Demo Talk-Track — 2026-05-05

**Audience:** internal team / stakeholders
**Tag baseline:** `v0.1.3-pilot-quality-closure` (78cc997)
**HEAD:** `7274485` (Phase B1 matcher Tier-2 just committed; v0.1.4-pilot-ux-friction-reduction in flight)
**Branch:** `feature/ux-rebuild` (+18 commits past origin; not yet pushed)

## Time budget: 30 min total
- 10 min — show what works (Sandra/Mike full flow)
- 5 min — show real-PII friction (Niesner pre-UI)
- 5 min — show the matcher Tier-2 fix landed (commit 7274485 + 28 merge candidates surfaced)
- 5 min — walk the plan (37 lock-ins, 8 phases, 14-tier test strategy)
- 5 min — Q&A / next steps

---

## Part 1 (10 min) — What works today: Sandra & Mike Chen synthetic couple

**Login → ClientPicker → Sandra & Mike Chen**

Talk track:
> "This is our synthetic baseline household — couple with 4 accounts, 3 goals, 6 goal-account links. Engine generates a PortfolioRun on every commit; recommendation surfaces inline."

**Walk:**
1. **HouseholdRoute** — RecommendationBanner (run signature `5b69bb6d...`), AUM strip (Steadyhand vs External), Treemap with click-to-drill, Action sub-bar (Realign + Re-open + Re-reconcile), HouseholdPortfolioPanel with engine rollup
2. **Drill into goal** — RecommendationBanner per goal, AdvisorSummaryPanel (engine narrative), AllocationBars, RiskBandTrack with marker
3. **Toggle ModeToggle** group-by-account / group-by-goal
4. **Risk slider drag** — calibration_drag pill flips during drag; engine pill returns on save
5. **HouseholdContext right-rail** — History → Commits sub-tab shows audit timeline

**Key callouts:**
- All numbers come from the engine; AI styles output but never invents financial figures (canon §9.4.5)
- Source-priority hierarchy enforced (KYC > Statement > Planning > Note)
- Append-only audit trail every state change
- Real-PII discipline: no client content in logs/memory/repo

---

## Part 2 (5 min) — Real-PII friction we discovered: Niesner couple workspace

**Switch to /review → Niesner review (demo prep)**

Talk track:
> "This is a real Steadyhand client couple. We uploaded 13 docs through the canon-compliant path. Extraction completed; reviewed_state populated. But end-of-session real-PII verification surfaced something synthetic tests missed."

**Walk:**
1. **DocsPanel** — 13 docs reconciled (KYC + planning + statement)
2. **ConflictPanel** header — "15 unresolved field disagreements"
3. **StatePeekPanel** — **people: 11 / accounts: 30 / goals: 18** (canon expects ~2 / ~5-7 / ~3-4 for a couple)
4. **Why this happened:** real LLM extraction obeys "only emit what's in the doc" (canon §9.4.5); on real client docs, only 6/17 DOBs present + 8/29 account_numbers. Synthetic Hypothesis tests had all fields populated → matcher worked. Real data sparse → matcher Tier-1 (Round 13 #2 LOCKED tightened threshold) refuses to merge name-only matches → over-fragmentation.

**The decision NOT to loosen Tier-1:** loosening re-introduces father+son same-surname false-merges. Wrong fix.

---

## Part 3 (5 min) — The matcher Tier-2 fix just shipped backend (commit 7274485)

Talk track:
> "We solved this with a third state — merge candidates. Tier-1 stays tight; Tier-2 surfaces medium-confidence pairs to the advisor for adjudication. Just landed in the last hour."

**Show the commit:**
```
7274485 feat(p1.1.fix): matcher Tier-2 merge candidates + endpoint + audit + account_type normalize
  9 files changed, 2473 insertions(+), 8 deletions(-)
  102 new + extended tests passing
  PII grep + vocab CI + OpenAPI codegen all clean
```

**Show the matcher firing:**
```
$ python manage.py shell -c "<reconcile_workspace(niesner)>"
people=11 accounts=30 goals=18 merge_candidates=28
Sample candidates:
  people  a=0 b=1 score=90 matched=['name_token', 'last_name']
  people  a=0 b=2 score=90 matched=['name_token', 'last_name']
  ...
```

**Key explanations:**
- Score 90 = strong "probably duplicate" (90/100 Tier-1 threshold)
- `matched_fields=['name_token', 'last_name']` = both have "Mark" + "Niesner" but no DOB or account_number to confirm
- Advisor sees these as a "Possible duplicates" group; clicks Merge → fact re-indexing happens at backend (Round 18 #16); 11 canonicals → 2

**Backend ready; UI is next phase (B2).**

---

## Part 4 (5 min) — The plan: 37 lock-ins, 8 phases, 14-tier test strategy

**Show:** `~/.claude/plans/you-are-continuing-a-playful-hammock.md` (1547 lines)

Talk track:
> "We took the time to interview through every dimension before coding. 7 rounds of explicit lock-ins captured 37 decisions across architecture, UX, semantics, execution discipline, regression detection, spec-fidelity, and operational hygiene."

**Highlight categories:**
- **Round 18 #1-#4** — matcher bands + UX placement + bulk policy + account_type normalize
- **Round 18 #5-#12** — full 8-friction-gap scope + section approval + manual-value entry + N/A + sequence + tag
- **Round 18 #13-#15** — goal-account-link inline accordion + 7-client real-PII matrix + Playwright e2e
- **Round 18 #16-#20** — merge re-indexing + decision-history + section-stays-approved + sequential dispatch + visual-baseline strategy
- **Round 18 #21-#25** — no-default selection + dependency order + link DELETE + 7-point ping + test integrity
- **Round 18 #26-#29** — spec-traceability matrix + visual baseline diff + mutation testing + 3-pass code review
- **Round 18 #30-#37** — failure recovery + workspace retention + dress rehearsal + N=100 stress + per-phase pre-flight + memory updates + decision-history JSON + lazy-load

**Test strategy: T1-T14 tiers**
- T1 pyramid per phase
- T2 cross-phase integration (the missing floor in v0.1.3)
- T3 7-client real-PII matrix
- T4 smoke cadence between phases
- T5 backwards-compat regression
- T6 a11y + keyboard
- T7 audit-event invariants (PII discipline)
- T8 perf budgets per endpoint
- T9 Hypothesis property tests
- T9b spec-traceability matrix
- T10 pre-fix vs post-fix visual baseline diff
- T11 mutation testing
- T12 3-pass code-reviewer dispatch
- T13 per-phase pre-flight gate
- T14 cross-session memory updates

**Phases B1-B7:**
- ✅ B1 — matcher backend (DONE: commit 7274485, 102 tests, 28 Niesner candidates surfaced)
- B2 — MergeCandidate UI components
- B3 — ConflictCard authoritative input + N/A + sequence + undo (Gaps A, G, E, I)
- B4 — SectionApprovalAccordion + compound CTAs + human labels + state preview accordion (Gaps C, D, F, H)
- B5 — 7-client real-PII verification matrix
- B5.5 — Playwright e2e automation
- B6 — final gate + mutation testing + 3-pass code-reviewer
- B7 — commit + CHANGELOG + tag v0.1.4-pilot-ux-friction-reduction

---

## Part 5 (5 min) — Q&A + Next Steps

**Anticipated questions:**

**Q: When does the rest land?**
A: Phase B2 frontend ~4 hours. Phases B3-B4 ~1.5 days. Phases B5-B5.5 ~half day. Phase B6-B7 ~half day. Estimated 3-4 working days for the full v0.1.4 release. Sequential dispatch (Round 18 #19) for safety; per-phase 7-point pings (Round 18 #24) for visibility.

**Q: How do we know there are no more surprises?**
A: 14-tier test pyramid + 7-client real-PII matrix + spec-traceability matrix verifying every Round 18 lock-in has a named test + mutation testing on critical paths + 3-pass code-reviewer dispatch at B7. Pre-fix visual baselines captured at HEAD `87e783d` so any unintended cross-route regression is detectable.

**Q: Could the matcher still over-fragment on a client we haven't tested?**
A: 7-client matrix tests Gumprich, Herman, McPhalen, Niesner, Schlotfeldt, Seltzer, Weryha — diverse data shapes. Plus Hypothesis property tests verify deterministic behavior across random fact distributions. Plus contradicting-field guard ensures father+son cases stay separate.

**Q: What if pilot Sev-1 surfaces post-tag?**
A: pilot-rollback.md procedure: revert tag → kill-switch engine → fall back to v0.1.3-pilot-quality-closure. Append-only audit trail makes incident reconstruction unambiguous.

---

## Demo state setup (run before meeting)

```bash
# Verify Docker stack
docker compose ps

# Verify backend session
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/session/

# Frontend dev server (in separate terminal)
cd frontend && npm run dev

# Login: advisor@example.com / change-this-local-password (env var)

# Niesner workspace URL: navigate via /review → "Niesner review (demo prep)"
# Sandra & Mike URL: navigate via TopBar ClientPicker → "Sandra & Mike Chen"
```

## Risks during demo

- ResizeObserver loop limit warning in Chrome console (acceptable; existing pattern)
- React-router devmode warnings (acceptable)
- Niesner workspace currently has NO merge-candidate UI (Phase B2 not yet shipped) — frame as "matcher Tier-2 backend just shipped 1 hour ago; UI ships next phase"
- If asked about goal_account_mapping for Niesner: links=0 because real-PII planning docs are narrative not structured; Phase B4 ships inline goal-account-link add UI

## Key data points to remember

- v0.1.3-pilot-quality-closure: 1,096 backend pytest passing, 391 Vitest, bundle 278.94 kB
- Phase B1 (just committed): +102 tests = 1,198 backend pytest baseline now
- Tier-2 bands: people 60-99, accounts/goals 50-79
- Niesner pre-fix: 11 people / 30 accounts / 18 goals / 28 merge candidates
- Plan: 1547 lines, 37 lock-ins captured across 7 interview rounds
