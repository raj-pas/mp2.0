# Portfolio V2 Implementation Checklist

**Last updated:** 2026-04-30

## Decisions Implemented

- [x] Build `engine_output.link_first.v2` only; no feature flag and no v1 compatibility path.
- [x] Remove legacy household output storage and mutable `PortfolioRun.status/stale_reason`.
- [x] Keep household and goal risk on the 1-5 contract.
- [x] Treat whole-portfolio funds as optimizer-eligible alongside building-block funds.
- [x] Model onboarding/pending cash explicitly through `Account.cash_state`.
- [x] Treat present-but-unmapped non-cash holdings as diagnostics/warnings, not blockers.
- [x] Refuse to reuse a stored run when input/output/CMA/run-signature verification fails.
- [x] Store run lifecycle as append-only `PortfolioRunEvent` rows.

## Contract And Data

- [x] Engine schema version is `engine_output.link_first.v2`.
- [x] Durable `GoalAccountLink.external_id` is the engine `link_id`.
- [x] CMA funds carry aliases, asset-class weights, geography weights, and whole-fund metadata.
- [x] Default CMA fixture maps legacy holding names such as `income_fund`, `equity_fund`,
  `global_equity_fund`, and `cash_savings` to active CMA funds.
- [x] Run manifest includes model version, as-of date, eligible funds, whole-portfolio funds,
  goal-account link ids, hashes, and provenance warnings.
- [x] Local v2 reset/reseed script exists at `scripts/reset-v2-dev.sh --yes`.

## Runtime Rules

- [x] Block generation when there is no active CMA.
- [x] Block generation when the active CMA universe is invalid.
- [x] Block generation when real-derived households lack committed reviewed-state provenance.
- [x] Block generation for ambiguous current lifecycle state.
- [x] Warn for synthetic/seeded missing provenance.
- [x] Warn for missing or unmapped current holdings.
- [x] Warn for incomplete fund metadata.
- [x] Reuse same-input runs only after hash verification.
- [x] Record hash mismatch, decline, regeneration, invalidation, reuse, export, and failure events.

## Advisor Console

- [x] Household console with account/goal grouping toggle and household blend.
- [x] Account console with account selection, account metrics, funded goals, current vs recommended.
- [x] Goal console with 1-5 risk, blended recommendation, and by-account legs.
- [x] Recommendation cards show direct fund weights first and label building-block vs whole-portfolio funds.
- [x] Diagnostics use structured mapping/current-vs-ideal warnings instead of the old blanket message.
- [x] Audit drawer exposes verification, hashes, diagnostics, lifecycle events, and sanitized export.
- [x] Portfolio run mutation state is scoped to the selected household to avoid client-state leakage.

## Verification Coverage

- [x] Engine unit coverage for v2 schema, durable link ids, 1-5 risk, warnings, and alias mapping.
- [x] API coverage for v2 generation, same-input reuse, hash mismatch regeneration, decline regeneration,
  CMA invalidation, planning invalidation, and sanitized audit export.
- [x] Frontend typecheck/build passes after the console changes.
- [x] Full Postgres Python regression passed through `scripts/test-python-postgres.sh`.
- [x] Synthetic browser regression passed through `npm run e2e:synthetic`.

## Remaining Follow-Ups

- [ ] Add richer projection visualization to the Goal tab.
- [ ] Replace placeholder CMA numerical assumptions before pilot recommendations.
- [ ] Add DB-level triggers for the new append-only portfolio event tables if production hardening requires
  database enforcement beyond model guards.
- [ ] Run `npm run e2e:real` manually under a secure real-data root before any real-derived use.
