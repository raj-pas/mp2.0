---
title: ADR-0001 — Engine as a library (no framework imports)
status: Accepted
decision_date: 2026-04-30
deciders: [Saranyaraj Rajendran, Fraser Stark]
supersedes: []
superseded_by: []
owner: Saranyaraj Rajendran
last_revised: 2026-05-12
update_when: This ADR's supersession-path conditions trigger an update; otherwise revise when the cited canon section, code symbols, or referenced sibling ADRs change.
---

# ADR-0001 — Engine as a library (no framework imports)

**Status:** Accepted
**Decision date:** 2026-04-30 (Round R0)
**Deciders:** Saranyaraj Rajendran (engineering lead); Fraser Stark
(project lead) for product alignment.

## Context

MP2.0's portfolio engine performs efficient-frontier optimization,
projections, risk-profile scoring, and rebalancing-move generation.
Early in Round R0 we faced a choice about where this code should live:

- Option A: as a Django app inside `web/` alongside views and models.
- Option B: as a standalone pure-Python library at `engine/` with no
  framework dependencies.

The same engine code is likely to be invoked from contexts other than
the Django web request cycle: a future Lambda function for batch
recalculation, a Snowflake user-defined function for analytics, a
standalone Python package shipped to Purpose's data team, or a Macro
Insight Layer pipeline running on a different cadence than client
blend updates. If the engine carries Django imports, every one of
those contexts must drag in Django to call `optimize()`.

Canon §9.4.2 calls out engine boundary purity as the #1 architecture
rule. The CI grep-check was listed in `docs/agent/open-questions.md`
"Code Drift" item #8 as a worth-adding Phase B check. Adding it as
part of R0 hardens the rewrite.

## Decision

The `engine/` package contains **pure Python** modules with **zero
imports** from `web/`, `extraction/`, `integrations/`, `django`,
`rest_framework`, `drf_spectacular`, `psycopg`, or `psycopg2`. Allowed
third-party imports are restricted to a fixed allowlist defined as
`ALLOWED_THIRD_PARTY_ROOTS` in `engine/tests/test_engine_purity.py`
(canonical source; check there for the current list). Today's
allowlist: `pydantic` (for schemas), `hypothesis` and `pytest` (for
tests), `scipy` and `numpy` (for math + oracle validation).

A test at `engine/tests/test_engine_purity.py` walks every `.py` file
under `engine/` via AST and asserts the import roots are within the
allowlist. The test runs in the default pytest suite, so a violating
change fails CI.

The engine speaks only `engine.schemas` Pydantic models. The web layer
translates Django models into engine schemas at the boundary via
`web/api/engine_adapter.py`.

## Consequences

### Positive

- The engine is independently extractable to Lambda / Snowflake /
  standalone packaging without dragging Django.
- The engine is independently testable. The full engine test suite
  runs against pure Python primitives — no database, no migrations,
  no DRF client.
- The boundary is enforced at the storage layer (AST), not just by
  convention. A future contributor cannot accidentally couple the
  engine to web code without the test failing.
- The Macro Insight Layer (which updates fund internals at a different
  cadence than client blends) can call the engine independently of the
  web request cycle.
- The engine's input contract is exactly `engine.schemas` — a single
  surface to evolve and version, not a sprawling Django ORM dependency.

### Negative

- Code that needs to flow between engine schemas and Django models
  must go through `engine_adapter.py`. There is no "just import the
  Household model from the engine" shortcut.
- Adding a new dependency to the engine requires updating the
  `ALLOWED_THIRD_PARTY_ROOTS` allowlist in the purity test. This is
  intentional friction.
- New contributors sometimes try to import Django from engine code
  by reflex. The purity test catches this immediately, but the
  failure mode is confusing the first time.

## Alternatives considered

### Alternative A: Engine as a Django app inside `web/`

Rejected. Would require Django imports in optimizer code; would prevent
out-of-Django execution; would couple engine evolution to Django
release cycle.

### Alternative B: Engine as a pure library, but enforce purity by
code review only (no AST test)

Rejected. Code review is not a reliable boundary mechanism for a
multi-contributor codebase. The AST test is ~30 lines and runs in
under a second; the friction is zero compared to the friction of a
boundary violation slipping through.

## Supersession path

If future requirements demand framework integration in the engine
(e.g., the engine needs to emit audit events directly, or read CMA
snapshots from the database), supersede this ADR with one that
specifies the exact framework dependency and the rationale. Sign-off
required from Saranyaraj Rajendran (engineering lead) and a
performance review showing the alternative path (going through the
adapter) was measurably insufficient.

## References

- Canon §9.4.2 — "The engine boundary"
- `engine/tests/test_engine_purity.py` — the AST enforcement
- `web/api/engine_adapter.py` — the translation layer
- `docs/agent/handoff-log.md` 2026-04-30 entry — R0 substrate landing
- `docs/team/glossary.md` — "Engine purity"
- Sibling ADRs:
  - ADR-0005 (link-first engine output) — defines the engine's output
    schema that the adapter produces.
  - ADR-0009 (sync auto-trigger) — relies on engine call being
    in-process Python, not a service hop.
