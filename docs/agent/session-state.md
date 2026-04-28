# MP2.0 Session State

**Last updated:** 2026-04-28
**Branch:** `main`
**Phase:** Phase 1 — runnable MVP scaffold + Claude memory
**Status:** Implemented locally, pending user review / optional push

## Current Goal

Maintain and extend the first runnable thin slice:

- DB-backed synthetic Sandra/Mike Chen persona
- client list/detail in the advisor shell
- generate-portfolio call through DRF into the pure Python engine stub
- light audit events for core actions
- smoke tests and CI

## Active Handoff

Phase 1 scaffold has landed as additive local changes. Verification passed:

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
`docker compose up --detach` is running the backend, frontend, and Postgres.
Backend logs show successful 200 responses for client list, client detail, and
generate-portfolio calls.

## Next Recommended Work

1. Review the local commit for the Phase 1 scaffold.
2. Start Phase 2 extraction/review work from the committed scaffold.
3. Expand PII/extraction rules before any real raw client files are added.

## Notes for Parallel Sessions

- Use light handoffs; no file-level locking.
- Start by checking `git status` and reading this file.
- Update this file and append to `handoff-log.md` after meaningful work.
