# MP2.0 Session State

**Last updated:** 2026-04-28
**Branch:** `main`
**Phase:** Phase 1 scaffold plus secure-local real-data review tranche
**Status:** Local thin slice supports authenticated upload/review to
`engine_ready` and link-or-create commit

## Current Goal

Use the existing scaffold as the base for the canon v2.3 build sequence while
moving real-data intake through a secure local review gate:

- DB-backed synthetic Sandra/Mike Chen persona
- client list/detail in the advisor shell
- generate-portfolio call through DRF into the pure Python engine stub
- light audit events for core actions
- smoke tests and CI
- authenticated local advisor review workspace
- browser multi-file upload into `MP20_SECURE_DATA_ROOT` outside the repo
- Postgres-backed worker queue and parser/extraction pass
- reviewed client state, missing-field checklist, section approval, matching,
  and versioned commit to current household tables

Canon v2.3 raises the next bar substantially:

- Phase A: Som-demo-grade offsite foundation across ingestion, engine, reporting.
- Phase B: pilot hardening and IS validation before any advisor logs in.
- Phase C: 3-5 Steadyhand advisors using the system with bounded real-client pilot
  data.

## Active Handoff

Secure-local review tranche has landed in the working tree. Current verification
passed:

- `uv run ruff check .`
- `uv run pytest`
- `npm run build`

Implemented pieces:

- secure-root validation rejects missing or repo-local upload roots
- `.env.example`, README, Docker Compose backend/worker env and mounts updated
- local advisor bootstrap command added
- review models/migration added for workspaces, documents, queue jobs, facts,
  state versions, section approvals, readiness, and match candidates
- upload API stores originals under secure root, sha256-dedupes per workspace,
  and enqueues processing jobs
- worker command claims queued jobs transactionally, retries twice after the
  first attempt, parses local formats, routes real-derived extraction through
  Bedrock, stores structured facts only, and reconciles reviewed state
- sensitive identifiers are converted to hash plus redacted display; evidence
  quotes redact account/SIN/SSN/card-like identifiers
- review UI includes login, workspace creation, upload/status, active job list,
  facts, quick-fill edits, section approvals, readiness, match candidates, retry,
  and link-or-create commit

This tranche should be committed locally after checks pass; do not push unless
explicitly asked.

## Canon v2.3 Context To Carry Forward

- The optimization unit is `GoalAccountLink`, not goal-alone. Engine output must
  become per-link first, then per-account and household rollups.
- Risk is a 5-point snap-to-grid scale mapped to percentiles 5/15/25/35/45.
  Advisor-visible risk should expose household component, goal component, and
  combined score.
- The three-tab household/account/goal view is the central advisor UX. Every tab
  reconciles to the same total AUM and toggles fund vs asset-class look-through.
- Extraction/review is now a first secure-local scaffold. It is not yet the full
  five-layer canon system and still needs richer reconciliation, IS validation,
  source-review UX, pseudonymization, and retention/disposal workflow.
- Real client PII must only enter through the authenticated browser upload with
  `MP20_SECURE_DATA_ROOT` outside the repo. Do not copy real contents into agent
  memory, repo files, CI, or logs.
- Pilot launch is gated by Phase B exit criteria, including real auth/RBAC,
  pilot disclaimer, feedback channel, kill-switch, compliance mapping, CMA admin
  view, and an end-to-end real tier-2 persona review with Lori.

## Known Scaffold Drift From Canon

- Engine schemas/output are still Phase 1 goal-level placeholders.
- Household risk remains 1-10 in code; canon uses 1-5 client/advisor language.
- `Goal.target_amount` is required in code; canon says future-dollar targets are
  optional secondary inputs.
- Extraction/LLM routing now enforces Bedrock env for real-derived facts and
  keeps raw text transient, but pseudonymization and CI PII checks are pending.
- Audit log is real but not append-only via DB trigger and does not capture full
  input/output snapshots.
- Auth/RBAC is Phase 0 only; all permissions currently allow access.
- Frontend lacks the three-tab pivot, click-through assignment, current-vs-ideal
  allocation, fan chart, and pilot-mode disclaimer.

## Next Recommended Work

1. Exercise the review workflow on the first household bundle through browser
   upload only; do not paste real contents into memory docs.
2. Convert engine schemas and output to the canon v2.3 per-link contract.
3. Harden extraction/reconciliation into the canon five-layer flow with IS
   validation and better source-review UX.
4. Build the three-tab household/account/goal UI around current reviewed state.
5. Add Phase B pilot gates: real auth/RBAC, disclaimer, kill-switch, feedback
   channel, richer audit records, and CMA admin boundary.

## Notes for Parallel Sessions

- Use light handoffs; no file-level locking.
- Start by checking `git status` and reading this file.
- Update this file and append to `handoff-log.md` after meaningful work.
