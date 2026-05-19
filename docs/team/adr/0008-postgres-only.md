---
title: ADR-0008 — Postgres-only persistence (fail-loud on missing or non-Postgres URL)
status: Accepted
decision_date: 2026-04-30
deciders: [Saranyaraj Rajendran]
supersedes: []
superseded_by: []
owner: Saranyaraj Rajendran
last_revised: 2026-05-12
update_when: This ADR's supersession-path conditions trigger an update; otherwise revise when the cited canon section, code symbols, or referenced sibling ADRs change.
---

# ADR-0008 — Postgres-only persistence

**Status:** Accepted
**Decision date:** 2026-04-30
**Deciders:** Saranyaraj Rajendran (engineering lead).

## Context

Early prototypes of MP2.0 supported both SQLite (for local dev
convenience) and Postgres (for production). The intent was the
standard Django convention: SQLite for the developer's first hour,
Postgres for everything real.

In practice, several invariants started to drift between the two
backends:

- The worker queue uses `select_for_update` + `pg_try_advisory_lock`
  for row-level locking. SQLite doesn't support these; the SQLite
  fallback used a different (broken) concurrency model.
- The audit immutability layer uses Postgres triggers (ADR-0013).
  SQLite has no equivalent; the SQLite path bypassed the trigger
  layer entirely.
- Performance characteristics of the auto-trigger path
  (sync engine.optimize inside `transaction.atomic`) are
  Postgres-specific (ADR-0009 measured P99 < 1 s on Postgres; SQLite
  was an order of magnitude slower under the same load).
- Migrations occasionally diverged: a Postgres-specific index or
  trigger landed without an equivalent SQLite path, producing
  "works on my machine but not in CI" bugs.

By 2026-04-30 the divergence had cost enough debugging that the team
decided to retire SQLite as an active runtime/test fallback.

## Decision

`DATABASE_URL` is **required** and must use the `postgres://` or
`postgresql://` scheme. The application **fails loud at startup** if
either:

- `DATABASE_URL` is unset (missing env var).
- `DATABASE_URL` is set but doesn't use a Postgres scheme.

This applies to:

- Production / pilot deployment.
- Local development (via Docker Compose).
- Test runs (`scripts/test-python-postgres.sh` brings up Compose
  Postgres and waits for health before invoking pytest).
- CI (`.github/workflows/smoke.yml` provisions a Postgres 16 service).

There is **no SQLite fallback path** in active code. Reintroducing one
would require explicit team sign-off (this ADR's supersession).

## Consequences

### Positive

- Concurrency primitives (row-level locking, advisory locks) are
  guaranteed to work everywhere the code runs.
- The audit trigger layer is uniformly present.
- "Works on my machine" bugs class is closed; dev and CI share the
  same backend.
- Migrations are written once for Postgres and tested everywhere.
- The Postgres-backed worker queue (ProcessingJob rows with row
  locking) is the production pattern.

### Negative

- Local dev now requires Docker Compose (or a manually-installed
  Postgres). The friction of "clone, then docker compose up" is real
  but small.
- Tests can't run without a live Postgres. `scripts/test-python-
  postgres.sh` handles this by orchestrating Compose; CI replicates
  via a Postgres service.
- A future deployment target that's hostile to Postgres (e.g., a
  serverless-only platform) would need a serverless Postgres provider
  (Neon, Supabase) rather than a different storage engine.

## Alternatives considered

### Alternative A: Keep SQLite fallback with feature-flagging the
Postgres-only paths

Rejected. The feature-flag surface area would grow as more paths
became Postgres-specific. The drift problem doesn't go away; it just
becomes harder to find.

### Alternative B: Use SQLite in tests only, Postgres in dev + prod

Rejected. Tests are where concurrency bugs surface. Running tests
against a different backend than dev/prod ensures those bugs are
caught only in production.

### Alternative C: Move to a different database (MySQL, CockroachDB,
etc.)

Out of scope. Postgres is the mature choice for the patterns we use.
A future move would require a different ADR; not motivated today.

## Supersession path

If a future deployment context demands a different storage backend
(e.g., a regulatory requirement for a managed database the cloud
provider offers, or a serverless platform that can't host Postgres),
supersede this ADR with one that specifies the new backend + the
migration path. The audit immutability layer (ADR-0013) is
particularly tightly coupled to Postgres triggers; a supersession
must specify the equivalent.

Sign-off required from Saranyaraj Rajendran + the Engineering
Director liaison (for production deployment alignment).

## References

- `web/mp20_web/settings.py` — Postgres URL validation (fails loud
  on missing/non-Postgres URL)
- `.env.example` — `DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20`
- `docker-compose.yml` — `db` service running Postgres 16 with
  healthcheck
- `scripts/test-python-postgres.sh` — orchestrates Compose Postgres
  for test runs
- `.github/workflows/smoke.yml` — Postgres 16 service for CI
- `web/api/management/commands/process_review_queue.py` — uses
  `select_for_update` for the worker queue
- Sibling ADRs:
  - ADR-0002 (append-only audit) + ADR-0013 (DB-trigger backstop)
    — Postgres-trigger-dependent
  - ADR-0009 (sync auto-trigger) — assumes Postgres connection pool
    + performance envelope
