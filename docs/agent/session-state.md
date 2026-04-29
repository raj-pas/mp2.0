# MP2.0 Session State

**Last updated:** 2026-04-28
**Branch:** `main`
**Phase:** Phase 1 scaffold implemented; canon v2.3 now points to Phase A/B/C
delivery
**Status:** Scaffold is runnable locally; memory refreshed against
`MP2.0_Working_Canon.md` v2.3

## Current Goal

Use the existing scaffold as the base for the canon v2.3 build sequence:

- DB-backed synthetic Sandra/Mike Chen persona
- client list/detail in the advisor shell
- generate-portfolio call through DRF into the pure Python engine stub
- light audit events for core actions
- smoke tests and CI

Canon v2.3 raises the next bar substantially:

- Phase A: Som-demo-grade offsite foundation across ingestion, engine, reporting.
- Phase B: pilot hardening and IS validation before any advisor logs in.
- Phase C: 3-5 Steadyhand advisors using the system with bounded real-client pilot
  data.

## Active Handoff

Phase 1 scaffold has landed and the `$NaN` detail-card bug was fixed. Prior
verification passed:

- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run pytest`
- `npm run build`
- `docker compose config`
- `uv run python web/manage.py check`
- `uv run python web/manage.py migrate --noinput`
- `uv run python web/manage.py load_synthetic_personas`

The local machine has Node 20, while the project targets Node 22. The frontend
still built successfully locally; Docker Compose and CI target Node 22.

Current `git status --short --branch` at the start of the canon review showed
`main...origin/main` with no uncommitted files.

## Canon v2.3 Context To Carry Forward

- The optimization unit is `GoalAccountLink`, not goal-alone. Engine output must
  become per-link first, then per-account and household rollups.
- Risk is a 5-point snap-to-grid scale mapped to percentiles 5/15/25/35/45.
  Advisor-visible risk should expose household component, goal component, and
  combined score.
- The three-tab household/account/goal view is the central advisor UX. Every tab
  reconciles to the same total AUM and toggles fund vs asset-class look-through.
- Extraction is no longer a distant placeholder for pilot planning. The five
  layers, provenance, temporal `Fact` extraction, and Layer 5 advisor review are
  load-bearing for Phase A/B.
- Real client PII is in scope only after hard blockers are resolved: Lori/Amitha
  authorization, Bedrock ca-central-1 enablement, data classification, encrypted
  machine posture, pseudonymization, scrub-pass, and routing controls.
- Pilot launch is gated by Phase B exit criteria, including real auth/RBAC,
  pilot disclaimer, feedback channel, kill-switch, compliance mapping, CMA admin
  view, and an end-to-end real tier-2 persona review with Lori.

## Known Scaffold Drift From Canon

- Engine schemas/output are still Phase 1 goal-level placeholders.
- Household risk remains 1-10 in code; canon uses 1-5 client/advisor language.
- `Goal.target_amount` is required in code; canon says future-dollar targets are
  optional secondary inputs.
- Extraction/LLM providers are stubs and do not enforce `data_origin` routing.
- Audit log is real but not append-only via DB trigger and does not capture full
  input/output snapshots.
- Auth/RBAC is Phase 0 only; all permissions currently allow access.
- Frontend lacks the three-tab pivot, click-through assignment, current-vs-ideal
  allocation, fan chart, and pilot-mode disclaimer.

## Next Recommended Work

1. Convert engine schemas and output to the canon v2.3 per-link contract.
2. Implement the five-layer extraction path on synthetic documents first.
3. Add PII guardrail infrastructure before any real raw client files are copied.
4. Build the three-tab household/account/goal UI around current Sandra/Mike data.
5. Add Phase B pilot gates: real auth/RBAC, disclaimer, kill-switch, feedback
   channel, richer audit records, and CMA admin boundary.

## Notes for Parallel Sessions

- Use light handoffs; no file-level locking.
- Start by checking `git status` and reading this file.
- Update this file and append to `handoff-log.md` after meaningful work.
