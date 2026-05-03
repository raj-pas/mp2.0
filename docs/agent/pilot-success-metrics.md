# Pilot Success Metrics + End-Criteria (Living)

**Status:** living doc
**Last updated:** 2026-05-02 (Phase 8.5b)
**Pilot start:** 2026-05-08 (limited beta)
**Initial cohort:** 3-5 advisors from Steadyhand on real-PII workflows

This doc captures the quantitative bars for pilot health, the
weekly check-in cadence, the criteria for transitioning to GA
(General Availability), and the off-ramp conditions for pausing
the pilot. It is the single source of truth for "is the pilot
working." Update in place; do not date-stamp.

---

## 1. Quantitative success metrics

Reviewed weekly by Saranyaraj + Fraser. Pulled from the
`web/api/models.Feedback` model + audit-event queries +
DB integrity invariants.

| Metric | Target | Source / Query |
|---|---|---|
| Advisors completing ≥1 client onboarding by Fri 2026-05-15 | 3 of 5 | `Household.objects.filter(created_at__gte=2026-05-08, owner__in=pilot_advisors).count()` per advisor; OR audit event `household_committed` count |
| Sev-1 incidents in pilot week 1-2 | < 2 | `docs/agent/incidents/` count + `Feedback` where severity="blocking" |
| Real-PII docs reaching `reconciled` per advisor folder | ≥ 90% | per-folder R10-style count from `ReviewDocument.objects.filter(workspace__owner__in=pilot_advisors, status="reconciled")` divided by total |
| Advisor NPS (qualitative; via Feedback severity="suggestion") | ≥ 7 / 10 | weekly Feedback report; manual NPS-equivalent extraction by ops |
| Bedrock spend per advisor / week | < $25 | AWS Cost Explorer filter `Service=Bedrock` + `Tag=PilotAdvisor` (set at IAM role creation) |
| `manual_entry` rate per workspace | < 25% docs | `ReviewDocument.objects.filter(status="manual_entry").count() / total docs` |
| Time-to-first-portfolio per workspace (median) | < 30 min | audit event timestamps: `review_workspace_created` → `household_committed` → `portfolio_run_created` |
| Conflict-resolve rate per workspace | ≥ 80% of conflicts resolved | `review_conflict_resolved` audit count divided by `total conflict count from reviewed_state` |

## 2. Check-in cadence

- **Monday morning:** ops pulls weekly Feedback report
  (`GET /api/feedback/report/?since=<last_monday>` as analyst);
  flags any Sev-1; updates this doc + appends to
  `docs/agent/handoff-log.md`.
- **Friday EOW:** ops + Fraser sync on weekly metrics; triage to
  Linear if any metric is off-target. Bedrock spend pulled from
  AWS console.
- **Mid-week ad-hoc:** if Sev-1 fired, retro within 48h per
  `docs/agent/pilot-rollback.md` §8.

## 3. GA criteria (pilot → broader release)

Pilot transitions to GA-ready when ALL of the following hold for
**2 consecutive weeks**:

1. Sev-1 incidents = 0
2. Per-advisor NPS ≥ 8
3. ≥ 50% of pilot advisors used the system for ≥ 3 client
   onboardings
4. No regressions on the locked decision #18 perf budget
   (P50 < 250ms / P99 < 1000ms across all advisor-facing
   endpoints — validated by `test_perf_budgets.py` benchmark
   suite once Phase 6.9 ships)
5. R10 sweep across all 7 client folders re-passes weekly
   (Phase 9 fact-quality iteration target)
6. Manual-entry rate < 15% docs (down from <25% pilot bar)

## 4. Off-ramp conditions

If ANY of the following hold, **pause the pilot + retro within 48h**:

1. Sev-1 incident in week 1 with no clear root-cause within 24h
2. > 50% of pilot advisors report blocking-severity friction
3. Compliance / legal escalation on PII handling
4. Bedrock spend exceeds $500 for a single week
5. Audit-trail integrity violation (any append-only-invariant
   failure on `AuditEvent`, `HouseholdSnapshot`, `FactOverride`,
   `PortfolioRun`)

**Pause means:** kill-switch via `MP20_ENGINE_ENABLED=0` per
`docs/agent/pilot-rollback.md` §2; advisors notified by ops via
`#mp20-pilot` Slack; retro within 48h; decision tree:

- Root cause known + bounded fix → resume after fix + canary
- Root cause unclear OR scope > 1 week → revert via §3 + plan
  follow-up sprint
- Compliance escalation → halt + Lori-led review before any
  resume decision

## 5. Pilot extension criteria

If 2026-05-15 metrics are middling (e.g., 2 of 5 advisors
completed onboarding; some Sev-2 friction but no Sev-1):

1. **Extend pilot another 2 weeks** instead of GA push
2. Address top-3 Feedback-table items first (sorted by severity
   then created_at; ops triages)
3. Re-evaluate at 2026-05-29
4. If still middling after extension, retro on whether the system
   needs structural changes vs incremental polish

## 6. What Phase 9 owes this doc

Phase 9 fact-quality iteration
(`docs/agent/phase9-fact-quality-iteration.md`) gates on advisor
productivity metrics, not fact-count alone. Specifically:

- 9.1 baseline: capture `time_to_first_portfolio`,
  `manual_entry_rate`, `conflict_resolve_rate` for the 12
  re-extracted docs vs the pre-Phase-4 baseline.
- 9.5: re-run these metrics after each iteration; ship the
  iteration only if metrics improve or hold (no regression).

## 7. Immutable bar

Real-PII discipline (canon §11.8.3) is non-negotiable. NEVER
post real client values to Slack, Linear, audit metadata `detail`
fields, or HTTP response bodies. The pilot pause/end criteria
treat any PII leak as a Sev-1 regardless of advisor productivity
metrics.
