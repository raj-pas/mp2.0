---
title: ADR-0005 — Link-first engine output (GoalAccountLink as optimization unit)
status: Accepted
decision_date: 2026-04-30
deciders: [Saranyaraj Rajendran, Fraser Stark]
supersedes: []
superseded_by: []
owner: Saranyaraj Rajendran
last_revised: 2026-05-12
update_when: This ADR's supersession-path conditions trigger an update; otherwise revise when the cited canon section, code symbols, or referenced sibling ADRs change.
---

# ADR-0005 — Link-first engine output

**Status:** Accepted
**Decision date:** 2026-04-30 (canon v2.3 reframe)
**Deciders:** Saranyaraj Rajendran (engineering lead); Fraser Stark
(project lead).

## Context

A canonical question in goals-based portfolio construction is: at what
level does the optimizer operate?

Three plausible answers:

- **Goal-level.** One blend per goal. Implementation: gather all the
  money mapped to a goal across all accounts, optimize, distribute the
  resulting blend back to the accounts.
- **Account-level.** One blend per account. Implementation: gather
  goal constraints per account, optimize, allocate.
- **Goal-account link-level.** One blend per `GoalAccountLink`.
  Implementation: each link is the optimization unit; per-account and
  per-household rollups derive from link outputs.

Goal-level is the obvious first instinct ("a goal has a target, target
date, risk score — optimize for that"). But it breaks down quickly:

- A retirement goal may span RRSP + TFSA + Non-Reg. The RRSP has
  growth-and-income regulatory_objective; the TFSA has
  growth; the Non-Reg has tax-drag considerations. A single blend
  spread proportionally across these accounts ignores the regulatory
  + tax-drag structure.
- Per-account regulatory_risk_rating sets a ceiling on the riskiness
  of the blend in that account. A goal-level optimizer that disregards
  this risks proposing a blend the account legally can't hold.

Account-level breaks down too: an account often serves multiple goals
with different time horizons and necessity scores. Averaging produces
a blend that suits no goal precisely.

The optimization unit needs to respect both the goal's intent and the
account's regulatory + tax envelope. The atomic unit that satisfies
both is the goal-account link.

## Decision

The engine's optimization unit is the **`GoalAccountLink`**. The
output schema (`engine_output.link_first.v2`) returns:

- `link_recommendations[]` — one entry per `GoalAccountLink`, carrying
  the optimal blend, allocated amount, frontier percentile, expected
  return, volatility, projection, and an advisor-facing summary.
- `goal_rollups{goal_id → Rollup}` — derived per-goal rollup.
- `account_rollups{account_id → Rollup}` — derived per-account rollup.
- `household_rollup` — derived household-level rollup.

The `GoalAccountLink` has a durable `external_id` (UUID-based) that
serves as the engine's stable identifier across runs. The frontend
consumes the link-recommendation list directly; the helpers
`findGoalRollup`, `findHouseholdRollup`, `findGoalLinkRecommendations`,
`findLinkRecommendationRow` in `frontend/src/lib/household.ts`
navigate the structure.

Legacy `Household.last_engine_output` (goal-level) is deprecated and
removed.

## Consequences

### Positive

- Per-link recommendations respect the account's regulatory and
  tax-drag envelope while still serving the goal's intent.
- Tax-aware blending is feasible: an RRSP and a TFSA serving the
  same retirement goal can carry different optimal blends.
- Rollups compose cleanly. Per-link sums to per-account; per-account
  sums to per-household. No accounting ambiguity.
- The frontend can render at any of the three views (household,
  account, goal) from a single engine output payload.
- The whole-portfolio fund collapse logic (canon §4.3b) operates at
  the link level, where it has the data it needs.

### Negative

- The link-level output is larger than a goal-level output. For a
  household with 4 accounts × 3 goals (12 potential links, ~6 actual
  links), the engine produces ~6 recommendations vs. ~3 in a
  goal-level model. Bandwidth + frontend rendering cost are slightly
  higher. Negligible in practice.
- Advisor narrative explanation gets more granular: a multi-link goal
  carries multiple `link_recommendation.advisor_summary` strings.
  The frontend (AdvisorSummaryPanel) collapses these into an
  accordion with the first link expanded by default (locked decision
  #78).
- The realignment + compare UI must reason at the link level, not at
  the goal or account level. The CompareScreen (R6) does this.

## Alternatives considered

### Alternative A: Goal-level optimization (one blend per goal)

Rejected. Doesn't respect per-account regulatory_objective +
regulatory_risk_rating constraints. Tax-drag-aware blending is
infeasible.

### Alternative B: Account-level optimization (one blend per account)

Rejected. Doesn't serve goals with multiple time horizons + necessity
scores well. The account isn't a meaningful planning unit.

### Alternative C: Hybrid (goal-level when single-account, account-level
when single-goal, link-level otherwise)

Rejected. Three execution paths complicate the engine, the adapter,
and the frontend without solving the underlying composition problem
in the multi-link case.

## Supersession path

If a future planning regime introduces a new optimization unit (e.g.,
"household-wide tax-overlay" that operates above the link), supersede
this ADR with one specifying the new unit + rollup math. Sign-off
required from Fraser Stark (product) + Saranyaraj Rajendran.

## References

- Canon Part 12 — engine I/O contract
- Canon §4.3a — "the optimization unit is goal × account"
- `engine/optimizer.py` — `optimize()` entry point
- `engine/schemas.py` — `EngineOutput`, `LinkRecommendation`, `Rollup`
  shapes
- `web/api/engine_adapter.py` — Django model → engine schemas
- `web/api/models.py` — `GoalAccountLink` (with durable `external_id`)
- `frontend/src/lib/household.ts` — the four navigation helpers
- `docs/agent/decisions.md` "Engine→UI Display Integration
  (2026-05-03/04)" — the 111-decision distillation that wired
  link-first output to the frontend
- Sibling ADRs:
  - ADR-0006 (five-point risk scale) — the per-link risk score maps
    to a frontier percentile via this scale.
  - ADR-0009 (sync auto-trigger) — auto-trigger emits a link-first
    PortfolioRun inline.
