# MP2.0

MP2.0 is the planning-first model portfolio platform described in
[`MP2.0_Working_Canon.md`](MP2.0_Working_Canon.md). This repository currently
contains the Phase 1 runnable scaffold plus the first secure-local real-data
review workflow: a Django/DRF backend, Postgres worker queue, React/Vite advisor
shell, pure Python engine stub, synthetic persona, and Claude-first project
memory.

## Current Status

The scaffold is runnable and useful for local development. The current local
thin slice now supports:

- synthetic Sandra/Mike Chen client list/detail and generate-portfolio flow
- local advisor login
- review workspace creation
- browser multi-file upload into a secure data root outside the repo
- Postgres-backed worker queue via `process_review_queue`
- local parsing for TXT/MD, CSV, XLSX, DOCX, and native-text PDFs
- Bedrock-routed extraction for real-derived text and practical image/scanned
  PDF OCR paths
- reviewed client state, missing-field checklist, section approval, advisory
  matching, and link-or-create commit into the current household tables
- advisor-grade review sections for household, people, accounts, goals,
  goal-account mapping, and risk, with provenance snippets and edit/approval
  notes for overrides
- worker heartbeat/stale visibility, duplicate reconcile suppression, manual
  reconcile, sanitized workspace timeline, strict approval-gated commit, and a
  portfolio engine kill-switch
- immutable audit events at the model and DB-trigger layer

The canon has advanced to v2.3. Next implementation should treat this repo as
the base for:

- Phase A: offsite scaffold and Som-demo-grade ingestion -> engine -> reporting
  flow.
- Phase B: pilot hardening and IS validation gates before advisor use.
- Phase C: controlled Steadyhand advisor pilot.

See [`CLAUDE.md`](CLAUDE.md) and [`docs/agent/session-state.md`](docs/agent/session-state.md)
for the current implementation context and known scaffold gaps.

## Local Start

Create a local `.env` from the example and set a secure upload directory outside
this repository:

```bash
cp .env.example .env
mkdir -p ~/mp20-secure-data
```

Edit `.env` so `MP20_SECURE_DATA_ROOT` points at that outside-repo directory.
Set `MP20_LOCAL_ADMIN_EMAIL` and `MP20_LOCAL_ADMIN_PASSWORD` if you want Docker
Compose to bootstrap a local login automatically.

Docker Compose is the canonical path:

```bash
docker compose up --build
```

Then open:

- Frontend: <http://localhost:5173>
- Backend API: <http://localhost:8000/api/clients/>

The backend automatically runs migrations and loads the synthetic Sandra/Mike
Chen persona. The `worker` service runs `uv run python web/manage.py
process_review_queue` and shares Postgres plus the secure data-root mount with
the backend.

## Real-Data Local Rules

- `MP20_SECURE_DATA_ROOT` is required for upload/review and must be outside the
  repo. Repo-local paths hard fail.
- Real-upload APIs require Postgres by default
  (`MP20_REQUIRE_POSTGRES_FOR_REAL_UPLOADS=1`) so queue claiming and audit
  immutability follow the production-like path.
- Raw uploaded originals are retained only under the secure data root and are
  not served through the app in this tranche.
- Full extracted raw text is transient in worker memory. The DB stores structured
  facts, run metadata, provenance, and minimally redacted evidence quotes.
- Sensitive identifiers are stored as hash plus redacted display, not plaintext.
- Real-derived extraction requires Bedrock env vars:
  `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION=ca-central-1`, and
  `BEDROCK_MODEL`.
- `MP20_ENGINE_ENABLED=0` preserves intake/review but blocks portfolio
  generation.
- Do not copy real client contents into repo files, agent memory docs, CI logs,
  or commit messages.

## Local Login and Worker Commands

For non-Docker local work:

```bash
export MP20_SECURE_DATA_ROOT="$HOME/mp20-secure-data"
export MP20_LOCAL_ADMIN_EMAIL="advisor@example.com"
export MP20_LOCAL_ADMIN_PASSWORD="change-this-local-password"

uv run python web/manage.py migrate
uv run python web/manage.py bootstrap_local_advisor
uv run python web/manage.py process_review_queue
```

For one-off queue processing in tests or debugging:

```bash
uv run python web/manage.py process_review_queue --once
```

To report or delete local raw artifacts whose version metadata is no longer
current:

```bash
uv run python web/manage.py dispose_review_artifacts
uv run python web/manage.py dispose_review_artifacts --delete
uv run python web/manage.py dispose_review_artifacts --retain-reason "active review"
```

## Local Checks

```bash
uv sync --all-groups
uv run ruff check .
uv run ruff format --check .
uv run pytest

cd frontend
npm install
npm run build
npx playwright test e2e/synthetic-review.spec.ts --list
```

CI runs the Python checks, frontend build, and a Docker Compose synthetic
browser E2E. For a local real-bundle browser regression, keep all artifacts under
the secure root:

```bash
export MP20_REAL_BUNDLE_ROOT="/path/outside/repo/to/client-bundles"
export PLAYWRIGHT_OUTPUT_DIR="$MP20_SECURE_DATA_ROOT/e2e-artifacts"
cd frontend
npm run e2e:real
```

## Session Protocol

Before changing code, Claude sessions should read:

1. [`CLAUDE.md`](CLAUDE.md)
2. [`docs/agent/session-state.md`](docs/agent/session-state.md)
3. [`docs/agent/open-questions.md`](docs/agent/open-questions.md)

Update the session state and handoff log after meaningful work.
