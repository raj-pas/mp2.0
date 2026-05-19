---
title: ADR-0009 — Synchronous auto-trigger inside mutation transactions
status: Accepted
decision_date: 2026-05-04
deciders: [Saranyaraj Rajendran, Fraser Stark]
supersedes: []
superseded_by: []
owner: Saranyaraj Rajendran
last_revised: 2026-05-12
update_when: This ADR's supersession-path conditions trigger an update; otherwise revise when the cited canon section, code symbols, or referenced sibling ADRs change.
---

# ADR-0009 — Synchronous auto-trigger inside mutation transactions

**Status:** Accepted
**Decision date:** 2026-05-04 (locked decision #74 in the engine→UI
display integration session)
**Deciders:** Saranyaraj Rajendran (engineering lead); Fraser Stark
(project lead).

## Context

When an advisor commits a household, generates a wizard commit,
overrides a goal's risk score, applies a realignment, resolves a
conflict, defers a conflict, applies a fact override, or approves a
section, the system needs to (re)generate the portfolio
recommendation. There are three architectural choices for when this
happens:

- **Async background queue.** The mutation commits; a Celery / RQ /
  Postgres-job worker picks up the work and produces the
  recommendation. The frontend polls or receives a server-sent event
  when ready.
- **Async on-commit hook.** `transaction.on_commit(generate)` runs
  the engine after the DB commit succeeds. The frontend still has to
  poll for the result.
- **Synchronous inside the mutation transaction.** The engine call
  runs inline in the request handler; the response carries the new
  PortfolioRun directly.

The async paths are conventional and have benefits at scale (the
request handler returns quickly; engine load is decoupled from
request latency). But they impose two costs:

1. **Polling complexity.** The frontend has to poll for the engine
   result or implement SSE. UX is degraded — "click commit, see a
   spinner, refresh later."
2. **Failure visibility.** An engine failure in async-land is silent
   to the advisor until they re-fetch. The advisor doesn't know
   their commit succeeded but the engine failed.

Phase A0.2 latency measurement (locked decision #56) showed
`engine.optimize()` runs in **~270ms cold + ~10–30ms REUSED** on
Sandra & Mike's synthetic. The 1 s strict P99 budget held with
substantial headroom.

## Decision

Portfolio generation runs **synchronously inside the mutation
transaction**. The canonical set of `source` values is defined in
the `_trigger_portfolio_generation` docstring at the top of the
helper trio in `web/api/views.py`; treat that docstring as the
authoritative list (it includes at least `manual` for the explicit
Generate / Regenerate CTA path, plus the auto-trigger sources
`review_commit`, `wizard_commit`, `override`, `realignment`,
`conflict_resolve`, `defer_conflict`, `fact_override`,
`section_approve`, `goal_assignment`, and the synthetic-load path).
Every committed-state mutation calls
`_trigger_and_audit(household, user, source=…)` inline within
`transaction.atomic`.

The helper trio in `web/api/views.py`:

- `_trigger_portfolio_generation` — invokes `engine.optimize()`;
  raises one of the 5 typed exceptions or unexpected.
- `_trigger_and_audit` — typed-skip + unexpected-failure audit paths;
  commit always succeeds, engine failure is captured as an audit
  event.
- `_trigger_and_audit_for_workspace` — workspace-scoped variant with
  a `linked_household_id is None` silent-skip gate.

The response payload includes the new PortfolioRun inline (when
generated) or a `latest_portfolio_failure` field (when the engine
raised a typed/unexpected exception).

The kill-switch (`MP20_ENGINE_ENABLED=0`) causes
`_trigger_portfolio_generation` to raise `EngineKillSwitchBlocked`,
which the helper catches and audits as
`portfolio_generation_skipped_post_<source>`. The mutation still
commits — only new generation is blocked.

## Consequences

### Positive

- **UX is immediate.** The advisor clicks commit; the response carries
  the new PortfolioRun + advisor summary. No spinner, no refresh.
- **Failure is visible.** A typed engine failure (e.g., `NoActiveCMASnapshot`)
  surfaces inline as `latest_portfolio_failure` with a structured
  `failure_code` + advisor-friendly message via
  `friendly_message_for_code`.
- **The response IS truth.** No race between commit and engine; no
  "what if I refresh and the engine still hasn't run?" question.
- **Audit chain is clean.** Every mutation's audit event is
  immediately followed by either `portfolio_generation_post_X_succeeded`
  or `portfolio_generation_post_X_skipped` / `_failed` in the same
  transaction.
- **Engine purity (ADR-0001) makes this feasible.** Because the engine
  is in-process Python (not a service hop), there's no network
  latency or service-discovery overhead.

### Negative

- **Connection pool pressure.** Each mutation transaction holds a
  Postgres connection for the ~270 ms cold engine run. At pilot scale
  this is fine (Postgres `max_connections` raised to 200, Django pool
  to 150 per locked decision #80); at GA scale we may need to
  revisit.
- **Engine failure blocks no mutations.** This is by design: the
  mutation persists, the engine failure audits. But it means an
  underlying engine bug can produce a flood of skip-audit events
  without anyone noticing. The ops runbook's escalation criterion
  (> 5 `portfolio_run_failed` events / hour → page) addresses this.
- **Connection-pool capacity test** (`test_connection_pool_capacity.py`)
  pins 120 concurrent successfully. If production exceeds this, the
  ops runbook escalates to bumping `max_connections` or introducing
  throttling.

## Alternatives considered

### Alternative A: Async background queue (Celery / RQ / Postgres-job worker)

Rejected for pilot scope. The UX degradation (poll for engine
result) was the dominant cost; the throughput benefit doesn't apply
at 3–5-advisor scale. Revisit if connection-pool pressure becomes
sustained.

### Alternative B: `transaction.on_commit(generate)` hook

Rejected. Doesn't solve the polling problem (the engine still runs
after the request returns). Plus, on-commit hooks run outside the
transaction, so an engine failure can't roll the commit back —
which we don't want anyway, but the on-commit boundary doesn't add
value.

### Alternative C: Sync for the manual Generate button; async for the auto-triggers

Rejected. Two paths means two failure modes to understand, two test
matrices, two audit-event lifecycles. Single path is simpler.

## Supersession path

Connection-pool exhaustion would be the trigger. If `pg_stat_activity`
sustained connection count > 130 in production, supersede with an
async strategy. The ops runbook §2 specifies the detection criteria.

Alternatively, if engine.optimize P99 starts to drift above 1 s
(currently ~530 ms cold), the sync model becomes more expensive.
The perf budget test (`test_perf_budgets.py`) pins this.

Sign-off required from Saranyaraj Rajendran + the Engineering
Director liaison.

## References

- Canon §4.7 — engine + CMA workbench mechanics
- `web/api/views.py` — the helper trio. Find via grep:
  `def _trigger_portfolio_generation`, `def _trigger_and_audit`,
  `def _trigger_and_audit_for_workspace`. (Line numbers omitted —
  the file is ~5K lines and earlier insertions invalidate pinned
  lines.)
- `web/api/error_codes.py` — the 5 typed exceptions +
  `friendly_message_for_code`
- `web/api/tests/test_perf_budgets.py` — pinned P50/P99 budgets
- `web/api/tests/test_connection_pool_capacity.py` — pinned 120
  concurrent
- `docs/agent/ops-runbook.md` §2 — connection pool exhaustion
  detection + escalation
- `docs/agent/decisions.md` "Engine→UI Display Integration
  (2026-05-03/04)" — 111-decision distillation including locked #74
- Sibling ADRs:
  - ADR-0001 (engine as a library) — makes in-process sync feasible
  - ADR-0008 (Postgres-only) — provides the connection-pool envelope
  - ADR-0002 (append-only audit) — every trigger emits an audit event
