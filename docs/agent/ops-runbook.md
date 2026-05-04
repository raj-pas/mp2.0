# MP2.0 Ops Runbook

Operational procedures for the MP2.0 limited-beta pilot. Created
2026-05-04 alongside `v0.1.2-engine-display`. Read this BEFORE
opening a Sev-1 ticket.

For pilot-wide rollback (kill-switch / code revert / DB recovery /
on-call escalation), see [`pilot-rollback.md`](pilot-rollback.md).
This runbook covers in-flight operational concerns: detection,
diagnosis, decision trees, and escalation criteria for specific
failure modes.

---

## §1. Recommendation generation failures

The auto-trigger fires synchronously inside `transaction.atomic`
on every committed-state mutation (commit / wizard / override /
realignment / conflict_resolve / defer_conflict / fact_override /
section_approve). Per locked decision #74, the response IS truth —
no `transaction.on_commit`, no polling. If generation fails, the
mutation still commits; the failure is captured in
`HouseholdDetail.latest_portfolio_failure` and surfaced to the
advisor via inline error + Sonner toast (per locked #9).

### §1.1 Detection signals

- **Advisor reports** "Recommendation generation failed" or
  "No recommendation generated yet" persisting after Retry.
- **Sonner toast surfaces** with reason_code on Goal route.
- **Audit log spike** of `portfolio_generation_skipped_post_*`
  or `portfolio_generation_post_*_failed` events:

```sql
-- Failures in the last hour
SELECT
  action,
  metadata->>'source' AS source,
  metadata->>'reason_code' AS reason_code,
  count(*) AS n
FROM audit_auditevent
WHERE created_at > now() - interval '1 hour'
  AND action ~ '^portfolio_(run|generation)_'
GROUP BY action, source, reason_code
ORDER BY n DESC;
```

- **5xx spike** on `/api/clients/<id>/generate-portfolio/` (manual
  Generate / Regenerate path) — the auto-trigger path doesn't
  surface 5xx because failures are caught + audited; only the
  explicit endpoint can return 5xx.

### §1.2 Diagnostic queries

```sql
-- Last 5 failures across ALL households
SELECT
  action,
  entity_id,
  metadata->>'source' AS source,
  metadata->>'reason_code' AS reason_code,
  metadata->>'failure_code' AS failure_code,
  created_at
FROM audit_auditevent
WHERE action ~ '^portfolio_(run|generation)_(skipped|failed)'
ORDER BY created_at DESC
LIMIT 5;

-- Per-household failure history
SELECT *
FROM audit_auditevent
WHERE action ~ '^portfolio_(run|generation)_(skipped|failed)'
  AND entity_id = '<household_external_id>'
ORDER BY created_at DESC;

-- Workspace-skip frequency (linked_household_id is None — common pre-commit)
SELECT
  metadata->>'source' AS source,
  count(*) AS skips_no_household
FROM audit_auditevent
WHERE action ~ '^portfolio_generation_skipped_post_'
  AND (metadata->>'skipped_no_household')::boolean = true
GROUP BY source;
```

### §1.3 Decision tree

Each failure routes through one of 4 decision branches based on
`metadata.reason_code`:

#### Branch A: `reason_code = "EngineKillSwitchBlocked"`

- **Cause**: `MP20_ENGINE_ENABLED=False` is set in the backend env.
- **Diagnosis**: `docker compose exec backend printenv | grep MP20_ENGINE`.
- **Action**:
  - If kill-switch was set deliberately (Sev-1 rollback in flight per
    `pilot-rollback.md`): confirm with on-call before re-enabling.
  - If unintentional: `docker compose exec backend sh -c 'export MP20_ENGINE_ENABLED=true'`
    + restart container; advisors regenerate manually via Goal route
    Generate button.
- **Advisor copy**: "Recommendation generation is temporarily
  disabled. Engineering has been notified."

#### Branch B: `reason_code = "NoActiveCMASnapshot"`

- **Cause**: No `CMASnapshot.Status.ACTIVE` row exists; analyst hasn't
  published.
- **Diagnosis**:
  ```sql
  SELECT external_id, status, version, created_at
  FROM api_cmasnapshot
  WHERE status IN ('active', 'draft')
  ORDER BY created_at DESC LIMIT 3;
  ```
- **Action**:
  - **Default state for fresh dev**: run `python web/manage.py seed_default_cma --force`.
  - **Pilot context**: notify Fraser (CMA owner) to publish the next
    CMA via the Workbench. Audit-emitting via `cma_snapshot_published`.
- **Advisor copy**: "An analyst needs to publish the latest CMA
  before recommendations can be generated."

#### Branch C: `reason_code = "ReviewedStateNotConstructionReady"`

- **Cause**: Committed state can't pass engine readiness rules
  (insufficient holdings, missing risk profile, no goals, etc.).
- **Diagnosis**: read `metadata.failure_code` for the specific
  blocker. Common values: `no_holdings`, `no_risk_profile`,
  `no_goals`, `holdings_below_minimum`, `unmapped_holdings`.
- **Action**:
  - Advisor uses the review screen to resolve blockers
    (re-upload missing data / complete the wizard / re-trigger
    extraction); re-commits.
  - If the blocker is data-quality (e.g., missing fund mappings):
    flag to the extraction-pipeline owner.
- **Advisor copy**: rendered automatically by
  `friendly_message_for_code` from `web/api/error_codes.py`.

#### Branch D: `reason_code = "InvalidCMAUniverse"` or `"MissingProvenance"`

- **Cause**: CMA failed `_validate_cma_snapshot` OR real-derived
  household lacks Bedrock provenance for facts.
- **Diagnosis**:
  - InvalidCMAUniverse: check `CMASnapshot.universe` JSONField for
    schema drift. Common: a fund_id referenced by a holding doesn't
    exist in the active CMA's universe.
  - MissingProvenance: real-PII upload finished but extraction
    didn't capture provenance. Bedrock API issue OR extraction
    pipeline regression.
- **Action**:
  - InvalidCMAUniverse: fix CMA universe via Workbench draft → publish
    cycle. Existing PortfolioRuns remain valid.
  - MissingProvenance: re-run extraction on the affected workspace
    (drain reset). Engineering escalation if extraction is the
    real bug.
- **Advisor copy**: "Recommendation can't be generated. Engineering
  has been notified."

#### Branch E: Unexpected exception (catch-all in `_trigger_and_audit`)

- **Cause**: Any non-typed exception from engine / DB / framework.
- **Diagnosis**: `metadata.failure_code` is the exception class name
  (sanitized via `safe_audit_metadata`). Example: `ValueError`,
  `IntegrityError`, `RuntimeError`. Raw exc message NOT in metadata
  per locked PII discipline.
- **Action**:
  - Reproduce locally with the affected household state (real-PII
    households need explicit advisor + on-call coordination).
  - Engineering investigation; ticket logged with the
    `entity_id` + `metadata.failure_code` + `created_at`.
- **Advisor copy**: "Recommendation generation failed unexpectedly.
  Engineering has been notified."

### §1.4 Escalation criteria

- > 5 `portfolio_run_failed` events / hour → page on-call.
- > 3 distinct households with `latest_portfolio_failure` not
  cleared within 30min → page on-call.
- Specific advisor blocked > 30min on Generate / Regenerate →
  contact advisor + escalate.
- Engine kill-switch toggled in production without prior
  authorization → immediate engineering page (Sev-1).
- Catch-all `failure_code` not seen before → log a ticket with
  reproducer.

---

## §2. Connection pool exhaustion

Postgres `max_connections` is set to 200 per locked decision #80
(was 100 default). Django connection pool to 150. Sync-inline
auto-trigger per locked #74 means each request transaction holds
a connection until `engine.optimize()` completes (~270ms cold +
~10-30ms REUSED).

### §2.1 Detection

```sql
-- Concurrent connection count
SELECT
  state,
  count(*)
FROM pg_stat_activity
WHERE datname = 'mp20'
GROUP BY state;
```

`> 130` active connections sustained → approaching pool exhaustion.

### §2.2 Action

- Log spike with `pg_stat_activity` snapshot.
- Engineering review: is the spike from realistic concurrent commit
  load (commit storm), or a leaked-connection bug (long idle
  transactions)?
- Test cover: `web/api/tests/test_connection_pool_capacity.py` pins
  120 concurrent successfully. If production exceeds this, escalate
  to bump `max_connections` further OR introduce throttling.

---

## §3. Workspace state drift

`_trigger_and_audit_for_workspace` silent-skips workspaces with
`linked_household_id is None`. This is the COMMON pre-commit case
(workspaces are unlinked until commit succeeds). Workspaces emit
`portfolio_generation_skipped_post_<source>` audit with
`metadata.skipped_no_household=True` for observability.

A LARGE volume of `skipped_no_household=True` events is normal —
not an alert condition. The audit volume is intentional for
post-pilot analysis (locked #27).

### §3.1 Detection

If ZERO `skipped_no_household=True` events for 24 hours despite
known workspace mutations: the gate may have regressed. Page on-call.

```sql
-- Workspace-skip rate per source over the last 24h
SELECT
  metadata->>'source' AS source,
  count(*) AS skipped_no_household
FROM audit_auditevent
WHERE action ~ '^portfolio_generation_skipped_post_'
  AND (metadata->>'skipped_no_household')::boolean = true
  AND created_at > now() - interval '24 hours'
GROUP BY source;
```

---

## §4. Real-PII handling

Per canon §11.8.3: never quote real client content in code, commits,
chat, or any artifact escaping `MP20_SECURE_DATA_ROOT`. Audit metadata
records structured codes only (`failure_code` = exception class name);
raw exception text never reaches DB columns / response bodies / audit
rows. CI guard `scripts/check-pii-leaks.sh` enforces this.

If you find raw client content in any artifact: STOP. Don't commit.
Don't push. Page on-call. The leak is a Sev-1.

---

## §5. Demo state restore

For Mon 2026-05-04 demo + advisor onboarding sessions, the canonical
demo state is:

- Sandra/Mike Chen synthetic with PortfolioRun (auto-seeded via
  `load_synthetic_personas`)
- Seltzer + Weryha real-PII workspaces in `review_ready` status
  (5/5 reconciled each)
- Niesner real-PII workspace (12 docs) in `review_ready` status

Restore procedure:

```bash
cd /Users/saranyaraj/Projects/github-repo/mp2.0
bash scripts/reset-v2-dev.sh --yes  # Sandra/Mike auto-seeds
set -a && source .env && set +a
uv run python scripts/demo-prep/upload_and_drain.py Seltzer --expect-count 5
uv run python scripts/demo-prep/upload_and_drain.py Weryha --expect-count 5
uv run python scripts/demo-prep/upload_and_drain.py Niesner --expect-count 12
```

Validation:

```bash
uv run python -c "
import os, requests
s = requests.Session()
s.get('http://localhost:8000/api/session/').raise_for_status()
csrf = s.cookies.get('csrftoken')
s.post('http://localhost:8000/api/auth/login/',
  json={'email':'advisor@example.com','password':os.environ['MP20_LOCAL_ADMIN_PASSWORD']},
  headers={'X-CSRFToken':csrf,'Referer':'http://localhost:8000'}).raise_for_status()
hh = s.get('http://localhost:8000/api/clients/hh_sandra_mike_chen/').json()
print('Sandra/Mike PortfolioRun:', (hh.get('latest_portfolio_run') or {}).get('run_signature', '')[:8])
clients = s.get('http://localhost:8000/api/clients/?owned=1').json()['clients']
for name in ['Seltzer', 'Weryha', 'Niesner']:
    match = next((c for c in clients if name.lower() in c.get('display_name','').lower()), None)
    print(f'{name}:', match['id'] if match else 'NOT FOUND')
"
```

---

## §6. References

- [`pilot-rollback.md`](pilot-rollback.md) — Sev-1 rollback procedure
- [`pilot-success-metrics.md`](pilot-success-metrics.md) — KPIs +
  off-ramp criteria
- [`production-quality-bar.md`](production-quality-bar.md) — UX +
  test coverage standards
- [`decisions.md`](decisions.md) — Engine→UI Display Integration
  section (111 locked decisions distilled)
- `~/.claude/plans/i-want-you-to-jolly-beacon.md` — full plan with
  decisions table (canonical source until A6.16 close-out migrates
  decisions to `decisions.md`)
