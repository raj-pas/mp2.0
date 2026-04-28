# CLAUDE.md — MP2.0

This file is the primary Claude Code entrypoint for MP2.0 implementation
sessions. The working canon remains authoritative for product, strategy,
regulatory, and architecture intent: `MP2.0_Working_Canon.md`.

## Start Every Session

1. Run `git status --short --branch`.
2. Read `docs/agent/session-state.md`.
3. Check `docs/agent/open-questions.md` for blockers that affect your task.
4. Preserve user or parallel-session changes; do not reset or overwrite them.

## Current Phase

Phase 1 builds a runnable local thin slice:

- Django/DRF + Postgres backend
- React/Vite advisor shell
- pure Python engine stub
- synthetic Sandra/Mike Chen persona
- light audit logging
- repo-persistent agent memory

## Non-Negotiable Architecture Rules

- Engine is a library, not a service.
- `engine/` must not import Django, DRF, `web/`, `extraction/`, or `integrations/`.
- Web code translates DB models into `engine.schemas` Pydantic models at the boundary.
- External systems stay behind adapters in `integrations/`.
- AI can extract and style; it must not invent financial numbers.
- Keep real client raw files out of git.

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
