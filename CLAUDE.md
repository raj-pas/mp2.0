# CLAUDE.md — MP2.0

This file is the primary Claude Code entrypoint for MP2.0 implementation
sessions. The working canon remains authoritative for product, strategy,
regulatory, and architecture intent: `MP2.0_Working_Canon.md`.

## Start Every Session

1. Run `git status --short --branch`.
2. Read `docs/agent/session-state.md`.
3. Check `docs/agent/open-questions.md` for blockers that affect your task.
4. Preserve user or parallel-session changes; do not reset or overwrite them.

## Current Status

The Phase 1 runnable scaffold is implemented on `main`:

- Django/DRF + Postgres backend
- React/Vite advisor shell
- pure Python engine stub
- synthetic Sandra/Mike Chen persona
- light audit logging
- repo-persistent agent memory

The working canon is now v2.3. It reframes the next work as Phase A/B/C:

- Phase A: offsite scaffold and Som-demo-grade foundation.
- Phase B: pilot hardening and IS validation before any advisor pilot use.
- Phase C: controlled pilot with 3-5 Steadyhand advisors using real clients.

Important: the current scaffold is useful foundation code, not pilot-grade
software. Treat the gap between the scaffold and canon v2.3 as the next
implementation backlog.

## Non-Negotiable Architecture Rules

- Engine is a library, not a service.
- `engine/` must not import Django, DRF, `web/`, `extraction/`, or `integrations/`.
- Web code translates DB models into `engine.schemas` Pydantic models at the boundary.
- The engine contract is moving from goal-level output to goal-account-link output.
  The optimization unit is `GoalAccountLink`, then account and household rollups.
- External systems stay behind adapters in `integrations/`.
- AI can extract and style; it must not invent financial numbers.
- Keep real client raw files out of git.
- No real client PII enters any machine, repo folder, staging server, or LLM call
  until the canon's REAL-PII BLOCKERS are resolved.
- Real-derived personas route only to Bedrock in ca-central-1 under Purpose's AWS
  account. Anthropic direct is synthetic-only.
- Audit logs are separate from observability logs. Writes exist now; immutability
  triggers and richer input/output snapshots are still pending.
- Client-visible risk vocabulary uses cautious / conservative-balanced /
  balanced / balanced-growth / growth-oriented, not low / medium / high.
- CMA editing and efficient-frontier visualization are admin-only surfaces.

## Current Scaffold Gaps vs Canon v2.3

- Engine still returns Phase 1 goal-level blends; canon requires per-link blends,
  per-account rollups, resolved risk per link, fund-of-funds collapse suggestions,
  fan chart data per link, tax-drag/CMA audit trace, and compliance ratings.
- Risk is currently a 1-10 placeholder; canon locks a 5-point snap-to-grid scale
  mapped to optimizer percentiles 5/15/25/35/45.
- Extraction layers are interface stubs. Canon v2.3 makes the five-layer
  extraction/review flow load-bearing for Phase A/B.
- Auth is Phase 0 only. Phase B requires per-advisor accounts, password reset,
  MFA, session timeout, lockout, and real RBAC.
- UI is a Phase 1 advisor shell. Canon requires the household/account/goal
  three-tab view, fund vs asset-class toggle, click-through goal-account
  assignment, current-vs-ideal allocation, and pilot disclaimer surfaces.
- PII guardrails are incomplete: scrub-pass hook, data-origin routing,
  pseudonymization storage, Bedrock enforcement, and CI PII checks are not built.

## Build Commands

```bash
docker compose up --build

uv sync --all-groups
uv run ruff check .
uv run ruff format --check .
uv run pytest

cd frontend
npm install
npm run build
```

## Git Protocol

- Work directly on `main` unless instructed otherwise.
- Make logical local commits after checks pass.
- Do not push unless explicitly asked.
- Update `docs/agent/session-state.md` and append to
  `docs/agent/handoff-log.md` after meaningful implementation or research.

## Useful Project Memory

- `docs/agent/session-state.md` — current implementation state and next work
- `docs/agent/handoff-log.md` — append-only dated handoffs
- `docs/agent/decisions.md` — implementation decisions distilled from the canon
- `docs/agent/open-questions.md` — tracked unresolved decisions
