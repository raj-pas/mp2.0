# Post-Pilot Improvements (Append-Only Backlog)

**Created:** 2026-05-03 (sub-session #8 onwards)

This doc captures ideas, gaps, and refinements surfaced during
sub-sessions #8-#11 that are deferred to post-pilot iteration.
Ops + Saranyaraj review weekly during pilot weeks 1-2.

Append-only — newest entries on top. Each entry: date, source
sub-session, severity (P0/P1/P2/P3), description, suggested next
step.

---

## Format

```
### YYYY-MM-DD — [P0|P1|P2|P3] — <short title>

**Source:** sub-session #N, phase X.Y
**Description:** <what surfaced>
**Why deferred:** <reason for not closing in this session>
**Suggested next step:** <concrete action>
**Estimated effort:** <S/M/L>
```

---

### 2026-05-03 — P1 — Re-edit-flow upgrade for uncommit (replace v1 delete-on-undo)

**Source:** sub-session #10.6, locked stop-and-ask answered "ship soft-undo for v1, re-edit for v2 post-pilot."

**Description:** v1 soft-undo deletes the linked Household + cascading Person/Account/Goal/PortfolioRun rows on uncommit. The deterministic `Household.external_id = "review_<workspace_id>"` is freed for re-commit. Trade-off: orphan visibility for analyst surfaces is lost; the audit event metadata captures `previous_household_id` + `previous_committed_at` + `uncommit_kind="soft"` for compliance reconstruction.

The re-edit flow (option B in the AskUserQuestion canvass) preserves Household identity across edit cycles via a PATCH-from-household endpoint that seeds a new workspace from the committed state. Reviewed_state + section_approvals + readiness gates copy across; advisor edits + re-commits which UPDATES the Household via per-section snapshot rows (HouseholdSnapshot append-only).

**Why deferred:** The re-edit flow needs ~150 lines (new endpoint + serializer + workspace seeding logic + HouseholdSnapshot per-section diff) + 4-5 backend tests + 1 e2e + a frontend re-edit affordance. Pilot-week-1 advisor mental model is "I made a mistake, let me retry" which the v1 soft-undo handles. If pilot data shows orphan-history value (e.g. analyst forensics on advisor change patterns), v2 re-edit becomes urgent.

**Suggested next step:**
1. Add `POST /api/review-workspaces/from-household/` endpoint accepting `{ household_id }` → creates a new workspace seeded from the household's current state.
2. Modify `commit_reviewed_state` to detect re-edit workspaces (e.g. via a `source_household` FK) and merge updates into the existing Household via HouseholdSnapshot rows instead of creating new.
3. Add a "Re-edit committed household" affordance on the household-detail page that triggers the workspace seed.
4. Migrate the v1 soft-undo deletion semantic to v2 re-edit semantic; preserve the v1 delete behavior under a feature flag for the first 2 weeks of pilot in case the re-edit flow surfaces issues.

**Estimated effort:** L (~5-7 days; subagent-parallel-able for backend + frontend split).

---

### 2026-05-03 — P2 — Demo-restore script needs --dry-run + snapshot mode

**Source:** sub-session #10.5, sandbox blocked the destructive Docker volume wipe.

**Description:** `scripts/reset-v2-dev.sh --yes` is a binary destructive op: either it wipes everything or it doesn't run. There's no way to validate the migration + seed sequence without committing to the destruction.

**Suggested next step:** Add `--dry-run` mode that prints the destructive ops without executing. Add `scripts/snapshot-demo-state.sh` that dumps the committed-state row sets to an out-of-repo SQL file so a targeted restore is possible.

**Estimated effort:** S.

---

### 2026-05-03 — P2 — Phase 9 multi-tool architecture exploration

**Source:** sub-session #9 canary measured +1pp recall recovery vs Phase 4 baseline (well below the design's 20pp aspirational target). The single-wave layered approach (9.1 + 9.2 + 9.3) is shipped; deeper recovery needs the multi-tool architecture (Phase 9.4 design doc) + advisor-productivity validation (Phase 9.5).

**Description:** Define 6 Bedrock tool-use tools (one per canonical schema: household / people / accounts / goals / risk / behavioral_notes); let Bedrock self-orchestrate which to invoke based on doc content. Net: structured + comprehensive; per-section schema definition; behavioral_notes free-form schema captures advisor narrative cleanly.

**Why deferred:** Need pilot-week-1 advisor commit-rate + manual-entry-rate data to validate whether v1 recall is sufficient. Architecture change is non-trivial (~2-3 day sub-session); shipping it without pilot data risks optimizing the wrong thing.

**Suggested next step:** After pilot week 1, review Feedback model rows tagged "blocking" or "friction" + advisor commit-rate metrics. If <50% commit rate, kick off the multi-tool architecture iteration.

**Estimated effort:** M (~2-3 days).

---
