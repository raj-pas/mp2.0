---
title: Troubleshooting common errors
owner: Saranyaraj Rajendran
last_revised: 2026-05-12
status: living
update_when: A new recurring error class is reported by ≥2 new
  contributors (append a new section), an existing fix becomes
  outdated (a tool flag changes, a script path changes), or a CI guard
  begins firing on a new pattern.
---

# Troubleshooting common errors

This guide collects the errors that show up most often during local
setup and day-to-day development, along with their fixes. Keep it
open while you onboard.

## See also

- [`README.md`](README.md) — folder index
- [`onboarding-engineer.md`](onboarding-engineer.md) — references this
  doc inline at each setup step
- [`../agent/ops-runbook.md`](../agent/ops-runbook.md) — production
  operational decision trees (different audience: on-call, not new
  hires)

## Quick triage

| Symptom | First check |
|---|---|
| Backend exits at startup | [§1 — `DATABASE_URL` issues](#1-database_url-issues) |
| Backend rejects upload | [§2 — `MP20_SECURE_DATA_ROOT` issues](#2-mp20_secure_data_root-issues) |
| Bedrock returns 403 | [§3 — Bedrock IAM / region issues](#3-bedrock-iam--region-issues) |
| Worker isn't processing jobs | [§4 — Worker not running](#4-worker-not-running) |
| `reset-v2-dev.sh` refused | [§5 — reset script issues](#5-reset-script-issues) |
| Frontend won't load | [§6 — Frontend / Vite proxy issues](#6-frontend--vite-proxy-issues) |
| Playwright headless passes; real Chrome fails | [§7 — The real-browser smoke gap](#7-the-real-browser-smoke-gap) |
| `pytest` fails with "DATABASE_URL required" | [§1](#1-database_url-issues) |
| Vocab CI guard fires unexpectedly | [§8 — Vocab CI false positive](#8-vocab-ci-false-positive) |
| PII grep CI guard fires unexpectedly | [§9 — PII CI false positive](#9-pii-ci-false-positive) |
| OpenAPI codegen drift error | [§10 — OpenAPI codegen drift](#10-openapi-codegen-drift) |
| Audit-event INSERT raises | [§11 — Audit immutability hit](#11-audit-immutability-hit) |
| `mypy` complains about an R0 module | [§12 — mypy strict on R0 modules](#12-mypy-strict-on-r0-modules) |

## 1. `DATABASE_URL` issues

### Symptom A — missing entirely

```
django.core.exceptions.ImproperlyConfigured:
DATABASE_URL must be set to a Postgres URL
```

**Fix:** copy `.env.example` to `.env` and ensure
`DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20` is present.
For Docker Compose contexts the host is `db`, not `localhost`:
`postgres://mp20:mp20@db:5432/mp20`.

### Symptom B — wrong scheme

```
django.core.exceptions.ImproperlyConfigured:
DATABASE_URL must use postgres:// or postgresql:// scheme
```

**Fix:** the system intentionally rejects non-Postgres backends
(ADR-0008). Don't try to point it at SQLite. If you really need a
different backend for an experiment, branch and supersede ADR-0008
explicitly.

### Symptom C — Postgres not running

```
psycopg.OperationalError: could not connect to server: Connection refused
```

**Fix:**

```bash
docker compose ps
# Verify the db service shows "Up" and "(healthy)"
docker compose up -d db
# Wait for health
docker compose exec db pg_isready -U mp20 -d mp20
```

If the db service is unhealthy, check `docker compose logs db` for
the underlying error.

## 2. `MP20_SECURE_DATA_ROOT` issues

### Symptom A — missing

```
django.core.exceptions.ImproperlyConfigured:
MP20_SECURE_DATA_ROOT is required and must be a path outside the repo
```

**Fix:** set it in `.env`. Must be an existing absolute path.

```bash
mkdir -p "$HOME/mp20-secure-data"
# In .env:
# MP20_SECURE_DATA_ROOT=/Users/yourname/mp20-secure-data
```

### Symptom B — points inside the repo

```
django.core.exceptions.ImproperlyConfigured:
MP20_SECURE_DATA_ROOT cannot be inside the repository (rejected: /Users/.../mp2.0/secure-data)
```

**Fix:** move it outside the repo. The validation is intentional
(canon §11.8.3, ADR-0004). A repo-local path means real client raw
files would land inside git's working copy — too risky.

### Symptom C — path doesn't exist or wrong permissions

```
PermissionError: [Errno 13] Permission denied: '/path/to/secure-data'
```

**Fix:** ensure the directory exists and is writable by the backend
process. In Docker Compose, the path is mounted to `/secure-data`
inside the container; ensure your host path has appropriate
ownership.

## 3. Bedrock IAM / region issues

### Symptom A — 403 AccessDenied on Bedrock invoke

```
botocore.exceptions.ClientError: An error occurred (AccessDeniedException)
when calling the InvokeModelWithResponseStream operation
```

**Fix:** your AWS credentials don't have Bedrock access. Verify:

```bash
aws sts get-caller-identity
# Should show your IAM user / role
aws bedrock list-foundation-models --region ca-central-1 | head
# Should list available models
```

If not, contact Saranyaraj for the IAM grant per
[`real-pii-handling.md`](real-pii-handling.md) §3.

### Symptom B — wrong region

```
ResourceNotFoundException: Could not resolve the foundation model
```

**Fix:** `AWS_REGION` must be `ca-central-1` for real-derived
extraction (ADR-0003). If you're using `us-east-1` somehow, fix the
env var. There is no fallback to other regions; that's intentional.

### Symptom C — synthetic mode but credentials present

This isn't an error, but worth noting: if `data_origin = synthetic`
on a workspace, the extraction client routes to Anthropic-direct
rather than Bedrock. Bedrock credentials are unused. If you're
debugging why a Bedrock call didn't fire, check the workspace's
`data_origin`.

## 4. Worker not running

### Symptom

You upload a document, but it stays `uploaded` forever. The
ProcessingJob never picks up.

```bash
docker compose ps worker
# Worker service status — should be "Up"
docker compose logs worker --tail 100
# Should show "Polling ProcessingJob queue..."
```

**Fix A:** worker service isn't started.

```bash
docker compose up -d worker
```

**Fix B:** worker started but heartbeat is stale.

```bash
docker compose restart worker
```

**Fix C:** worker can't connect to Postgres (most likely if backend
also failed).

See §1 — `DATABASE_URL` issues.

### Symptom — frontend WorkerHealthBanner showing red

The frontend renders a `<WorkerHealthBanner>` when
`worker_health.status` is stale/offline AND active jobs > 0. If you
see it, follow the steps above. If the worker is running but the
banner persists, the heartbeat write may be failing — check worker
logs for ORM-level errors.

## 5. Reset script issues

### Symptom A — refused with safety prompt

```bash
bash scripts/reset-v2-dev.sh
# Output: This is destructive. Use --yes to confirm.
```

**Fix:** `bash scripts/reset-v2-dev.sh --yes`. The `--yes` flag is
mandatory by design (the script wipes the local DB).

### Symptom B — refused in sandbox / restricted Bash

Some Claude Code sessions run in a restricted Bash that refuses
destructive operations.

**Fix:** ask the user to run the reset manually outside the sandbox,
or use `scripts/demo-prep/upload_and_drain.py` for non-destructive
state restoration (per `docs/agent/demo-restore-runbook.md`).

### Symptom C — script completed but Sandra & Mike Chen not visible

The reset clears `web_api_*` tables. Re-seeding is automated
(`load_synthetic_personas` runs as part of the script). If Sandra &
Mike Chen aren't visible after reset:

```bash
docker compose exec backend uv run python web/manage.py load_synthetic_personas
docker compose restart backend worker
```

Refresh the frontend. They should appear.

## 6. Frontend / Vite proxy issues

### Symptom A — `localhost:5173` loads but `/api/*` returns 404

The Vite dev server is up but the proxy isn't reaching the backend.

**Fix:**

```bash
docker compose ps backend
# Verify backend is healthy
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/session/
# Should print 200
```

If backend is up and direct curl works, the Vite proxy may be
misconfigured. Check `frontend/vite.config.ts` for the proxy
target (`VITE_BACKEND_TARGET`); inside Docker Compose this should
be `http://backend:8000`, on the host it's `http://localhost:8000`.

### Symptom B — frontend container failing to install

```
npm ERR! ... ERESOLVE could not resolve ...
```

**Fix:** `frontend/package-lock.json` may have drifted from
`package.json`. Try:

```bash
cd frontend
rm -rf node_modules
npm ci  # uses package-lock.json strictly
```

### Symptom C — TypeScript errors after `npm run codegen`

The codegen regenerates `frontend/src/lib/api-types.ts` from
drf-spectacular's schema. If your local types are stale:

```bash
cd frontend
npm run codegen
npm run typecheck
```

If codegen fails because the backend isn't reachable, ensure
`docker compose ps backend` shows healthy. If it succeeds but
typecheck fails, the backend schema may have drifted from frontend
type expectations — see §10.

## 7. The real-browser smoke gap

### Symptom

Playwright synthetic tests pass green, but the real-browser smoke
walk surfaces a visible bug.

**This is the most important troubleshooting category.** The team
has paid (multiple times) for the lesson:

- The FileList ref race in `DocDropOverlay.handleFilesPicked`.
  Playwright headless never caught it; real Chrome did.
- The DocDropOverlay StrictMode-double-update bug. Same pattern.

**Fix:** never rely on Playwright headless alone. After any frontend
change, walk the affected surface in real Chrome (not headless). Watch
the console. Test the golden path AND the edge cases.

If the test passes in Playwright but you can't reproduce in real
Chrome, ask in Slack before assuming the bug is gone. Often the bug
manifests under StrictMode double-invocation, which Playwright runs
in but real Chrome behaves differently because of timing.

## 8. Vocab CI false positive

### Symptom

`scripts/check-vocab.sh` flags a banned term in a file where the
term is legitimate (e.g., a comment explaining why the term is
banned, or a third-party string).

**Fix:** add a `# canon-vocab-allow` marker on the line (or the
nearest surrounding context). Use sparingly — the discipline is to
avoid the term entirely.

If you find yourself adding many allow markers, you're probably
fighting the rule. Talk to Saranyaraj before adding more than two
in a single PR.

## 9. PII CI false positive

### Symptom

`scripts/check-pii-leaks.sh` flags a code path that uses `str(exc)`
in what looks like a safe context.

**Fix:** the script is intentionally strict (canon §11.8.3,
ADR-0004). Even "safe" `str(exc)` uses get flagged because the
discipline is to use the structured helpers. Use:

- `safe_exception_summary(exc)` — `"ClassName:code"` only.
- `safe_response_payload(exc)` — for DRF response bodies.
- `safe_audit_metadata(exc)` — for audit metadata.
- `failure_code_for_exc(exc)` — for the structured failure code.

All from `web/api/error_codes.py`.

Test files are exempted from the scan, so test fixtures can use
`str(exc)` freely.

## 10. OpenAPI codegen drift

### Symptom

`scripts/check-openapi-codegen.sh` fails with a diff between the
freshly-generated schema and the committed
`frontend/src/lib/api-types.ts`.

**Fix:** the backend schema changed but the frontend types weren't
regenerated.

```bash
cd frontend
npm run codegen
git diff src/lib/api-types.ts
# Review the diff to confirm the changes match your expectation
```

If the diff includes types you didn't intend to touch (e.g., a
serializer change you didn't make is visible), check with whoever
made the backend change — there may be a coordination issue.

The CI guard catches this class of bug before it reaches production
(it was the cost of an earlier enum-drift bug class — see
CHANGELOG.md v0.1.0-pilot "Phase 4.5").

## 11. Audit immutability hit

### Symptom

```
django.db.utils.IntegrityError: audit rows are append-only;
UPDATE/DELETE forbidden
```

Or in Python:

```python
>>> AuditEvent.objects.filter(id=1).delete()
django.db.utils.IntegrityError: audit rows are append-only;
UPDATE/DELETE forbidden
```

**Fix:** this is **working as intended** (ADR-0002, ADR-0013). Audit
rows can't be modified or deleted. If you're trying to:

- **Clean up test data:** use a data migration that explicitly drops
  the trigger, deletes the rows, recreates the trigger. Or use
  `scripts/reset-v2-dev.sh --yes` (clears `web_api_*` tables; audit
  triggers survive but old audit rows persist — unfix-able by design).
- **Update an audit row that has wrong metadata:** you can't.
  Append a new audit event with the correction; the original
  remains as evidence.
- **Soft-delete an audit row:** you can't. The append-only invariant
  has no soft path.

If your test genuinely requires deleting an audit row, isolate it
with a fixture that drops + recreates the trigger within the test
scope. Don't try to bypass the guard globally.

## 12. mypy strict on R0 modules

### Symptom

`uv run mypy engine/risk_profile.py` (or another R0 module) fails
with strict-mode complaints.

The six R0 modules under mypy strict are: `risk_profile`,
`goal_scoring`, `projections`, `moves`, `collapse`, `sleeves`.
Other engine modules (`schemas`, `optimizer`, `frontier`,
`compliance`) are typed but not strict.

**Fix:** strict-mode complaints are mostly:

- Missing return type annotations.
- `Any` usage that strict mode disallows.
- Optional types that should be `T | None`, not bare `T`.

Address each one. The strict bar is intentional and was added in R0
to prevent type-drift in the newest modules.

If you're adding a new engine module, decide upfront whether it
joins strict (recommended) or not. Update `pyproject.toml` `[[tool.mypy.overrides]]`
to add it.

## When you can't find your error here

1. Search `docs/agent/handoff-log.md` — the most recent ~5 entries
   often mention recent friction.
2. Search Linear (`MP20` project) — open issues sometimes match.
3. Ask in `#mp20-pilot` — DM the tech lead if the question involves
   real-PII or sensitive context.
4. Look at the original ADR — if your problem touches the architecture
   it constrains, the supersession path might be relevant.

## Maintenance

This file is append-only by convention. When a new recurring error
class shows up, add a new section here rather than editing existing
ones. Bump `last_revised` in the front-matter.
