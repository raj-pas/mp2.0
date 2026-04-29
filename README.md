# MP2.0

MP2.0 is the planning-first model portfolio platform described in
[`MP2.0_Working_Canon.md`](MP2.0_Working_Canon.md). This repository currently
contains the Phase 1 runnable scaffold: a Django/DRF backend, React/Vite advisor
shell, pure Python engine stub, synthetic persona, and Claude-first project
memory.

## Current Status

The scaffold is runnable and useful for local development, but the canon has
advanced to v2.3. Next implementation should treat this repo as the base for:

- Phase A: offsite scaffold and Som-demo-grade ingestion -> engine -> reporting
  flow.
- Phase B: pilot hardening and IS validation gates before advisor use.
- Phase C: controlled Steadyhand advisor pilot.

See [`CLAUDE.md`](CLAUDE.md) and [`docs/agent/session-state.md`](docs/agent/session-state.md)
for the current implementation context and known scaffold gaps.

## Local Start

Docker Compose is the canonical path:

```bash
docker compose up --build
```

Then open:

- Frontend: <http://localhost:5173>
- Backend API: <http://localhost:8000/api/clients/>

The backend automatically runs migrations and loads the synthetic Sandra/Mike
Chen persona.

## Local Checks

```bash
uv sync --all-groups
uv run ruff check .
uv run ruff format --check .
uv run pytest

cd frontend
npm install
npm run build
```

## Session Protocol

Before changing code, Claude sessions should read:

1. [`CLAUDE.md`](CLAUDE.md)
2. [`docs/agent/session-state.md`](docs/agent/session-state.md)
3. [`docs/agent/open-questions.md`](docs/agent/open-questions.md)

Update the session state and handoff log after meaningful work.
