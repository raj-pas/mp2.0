# Pilot Rollback Procedure (Sev-1 incidents)

**Status:** living doc — keep current with code as it changes.
**Last updated:** 2026-05-02 (Phase 8.4)
**Pilot release:** `v0.1.0-pilot` tagged at HEAD `<sha>` for
2026-05-08; advisors: 3-5 from Steadyhand on real-PII workflows.

This doc is for ops to execute under incident pressure. It is
deliberately concise, points at live artifacts, and assumes the
reader has shell access to the EC2 instance + `gh` CLI access to
`raj-pas/mp2.0`. It is NOT a debugging guide — Sev-1 means
restore service first, root-cause later.

---

## 1. Severity classification

| Severity | Examples | Response time | First action |
|---|---|---|---|
| **Sev-1** | Real-PII leak in HTTP response or audit log; engine returning fabricated values; advisor cannot commit any household; data corruption (lost workspaces, stale audit rows) | Within 1 hour, 24x7 | Engage kill-switch (§2) + page on-call (§7) |
| **Sev-2** | Single doc-class extraction failing systematically; portfolio-gen failing for >25% of advisors; one advisor blocked but others functional | Within 1 business day | Triage from Feedback model (§7) + plan fix |
| **Sev-3** | Cosmetic UI bug; non-blocking advisor friction; single-doc extraction failure | Next sprint | Add to backlog; advisor uses manual-entry hatch |

**The kill-switch is for Sev-1 only.** Sev-2 typically resolves
via targeted code change + advisor re-route to
manual-entry. Sev-3 doesn't justify pilot disruption.

---

## 2. Engine kill-switch

The fastest possible Sev-1 mitigation: stop the engine from
generating new portfolios. Existing committed households remain
intact + visible; advisors just can't generate new
recommendations.

```bash
# On EC2 instance
ssh ec2-user@<pilot-ec2-private-ip>
cd /srv/mp20
# Edit .env or write to AWS SSM Parameter Store
# (whichever pattern ops chose for env injection)
echo "MP20_ENGINE_ENABLED=0" >> .env
docker compose restart backend worker
```

**Effect:** every `POST /api/clients/<id>/generate-portfolio/`
returns 503 with `{"detail": "Engine paused", "code":
"engine_disabled"}`. Existing PortfolioRun rows + committed
households unchanged.

**Audit trail:** flipping the kill-switch emits no audit event
(it's an env change, not a state change). Note the timestamp +
incident-ID in `docs/agent/incidents/<date>-<slug>.md` for
post-incident review.

**Re-enable:**
```bash
sed -i 's/MP20_ENGINE_ENABLED=0/MP20_ENGINE_ENABLED=1/' .env
docker compose restart backend worker
```

---

## 3. Code revert procedure

If the kill-switch is insufficient (e.g., the bug is in
extraction or audit code, not engine), revert the deploy.

### 3a. Full revert to a known-good tag

```bash
cd /srv/mp20  # or wherever the deploy lives
git fetch origin
git checkout <previous-pilot-tag>  # e.g. v0.1.0-pilot was bad,
                                     # roll back to v0.0.X-pre-pilot
docker compose down
docker compose build --no-cache backend worker
docker compose up -d
```

### 3b. Per-phase revert (preferred when one sub-system regressed)

This session's commits are independently revertable:

| Commit | Phase | Reverts via |
|---|---|---|
| `7a2e252` | 4 (tool-use) | `git revert 7a2e252` (back to JSON-repair path) |
| `413fd02` | 4.5 (codegen) | `git revert 413fd02` (drift gate disabled) |
| `2b28220` | 5a (conflict UI) | `git revert 2b28220` |
| `288c3e7` | 5b.1+5b.6 (banner+feedback+tour) | `git revert 288c3e7` (data preserved; UI hidden) |
| `e952c61` | 5b.2/7/9/14 | `git revert e952c61` |
| `6b0ea9b` | 4-hardening | `git revert 6b0ea9b` (NOTE: causes the canary regression
to come back; only revert if 7a2e252 is also reverted) |

The `feature/ux-rebuild` branch's commit chain since the prior
pilot tag is the source of truth. `git log --oneline <prev-tag>..HEAD`
gives the revert candidates ordered.

After revert, redeploy via 3a's `docker compose down/build/up`.

---

## 4. DB recovery

**Pilot-data caveat:** real client workspaces exist in the DB.
`scripts/reset-v2-dev.sh --yes` is DESTRUCTIVE. Use only when
the alternative is corrupt-data persistence.

### 4a. Targeted recovery (preferred)

If a single advisor's workspace is corrupt:

```bash
ssh ec2-user@<pilot-ec2-private-ip>
docker compose exec backend python web/manage.py shell <<'PY'
from web.api.models import ReviewWorkspace, ProcessingJob
ws = ReviewWorkspace.objects.get(external_id="<wsid>")
print(f"docs={ws.documents.count()} jobs={ws.processing_jobs.count()}")
# Inspect; never bulk-mutate without explicit advisor consent.
# Manual reconcile: ws.processing_jobs.create(...) re-queues.
PY
```

The advisor can also use the manual-entry escape hatch
(`ReviewDocumentManualEntryView`) which marks the doc
`MANUAL_ENTRY` and lets the advisor type values directly.

### 4b. Full reset (Sev-1 + data corruption only)

```bash
ssh ec2-user@<pilot-ec2-private-ip>
docker compose exec backend bash scripts/reset-v2-dev.sh --yes
# Re-run pilot advisor provisioning:
docker compose exec backend python web/manage.py provision_pilot_advisors \
  --config-file=$MP20_SECURE_DATA_ROOT/pilot-advisors-2026-05-08.yml
# Notify all pilot advisors via Slack — their workspaces are gone.
```

**Audit trail caveat:** `reset-v2-dev.sh` clears `web_api_*`
tables but the audit log (`AuditEvent`) is append-only via
Postgres triggers (locked decision #37). The audit history
survives the reset; queries
`AuditEvent.objects.filter(action__in=[...])` still resolve.

---

## 5. Disclaimer + tour state restore

If the User-table changes (Phase 5b.1) are reverted via §3b,
advisors will see PilotBanner + WelcomeTour again on next login.
**This is expected behavior** — the new audit-event-version-aware
acks are tied to the User profile fields. Communicate to advisors
via Slack:

> "We rolled back a recent change. You'll see the pilot banner
> and welcome tour again — please dismiss them. No data loss."

If `AdvisorProfile` rows are intentionally preserved (revert
without DB rollback), advisors won't re-see the prompts even after
the code revert. State is stable.

---

## 6. Frontend bundle revert

Vite build output goes to `frontend/dist/`. Backend serves it
statically. After a code revert (§3), redeploy:

```bash
cd /srv/mp20/frontend
npm install
npm run build
# Backend serves from dist/; restart not strictly required but
# recommended to flush any in-flight render contexts:
docker compose restart backend
```

If the issue is purely frontend (e.g., a chunk that fails to
load): roll back ONLY the frontend bundle by reverting the FE
commit + rebuilding while keeping backend running.

---

## 7. On-call contact list

| Role | Primary | Backup |
|---|---|---|
| Tech lead | Saranyaraj <saranyaraj.rajendran@purpose.ca> | Fraser <fraser@purpose.ca> |
| Compliance | Lori <lori@purpose.ca> | n/a |
| Real-PII / data | Saranyaraj | Amitha <amitha@purpose.ca> |
| Advisor pilot ops | Fraser | Saranyaraj |

**Slack:** `#mp20-pilot` (private; pilot advisors + ops). For Sev-1,
@here in the channel + DM tech lead. Escalate to leadership if
no response in 30 min.

**Linear:** `MP20` project. Open a Sev-1 issue with `incident:
sev-1` label + the `docs/agent/incidents/<date>-<slug>.md` link.

---

## 8. Post-incident audit

Within 48h of a Sev-1 incident:

1. Create `docs/agent/incidents/<date>-<slug>.md` (e.g.,
   `2026-05-12-extraction-fabrication.md`) with:
   - Timeline (UTC) — detection, mitigation, restoration.
   - Root cause analysis.
   - What worked + what failed in detection / response.
   - Action items (engineering + ops).
2. Append a one-line entry to `docs/agent/handoff-log.md` with
   pointer to the incident doc.
3. Run a 30-min retro with on-call + tech lead. Decide:
   - Was the fix sufficient or do we need a deeper change?
   - Should the kill-switch threshold be different?
   - Did the rollback procedure work as documented? Update this
     doc if not.
4. NEVER delete audit-trail rows. The append-only invariant
   (locked decision #37) is load-bearing for compliance.

---

## Pre-pilot dry-run checklist

Run this once before 2026-05-08 to verify the rollback path is
operational:

- [ ] Engine kill-switch tested: set `MP20_ENGINE_ENABLED=0`,
      attempt `POST /generate-portfolio/`, confirm 503.
- [ ] Engine re-enable tested: set `MP20_ENGINE_ENABLED=1`,
      confirm 200.
- [ ] Per-phase revert tested in dev: revert + redeploy + smoke
      test, then re-apply.
- [ ] On-call paths tested: send a test Slack to `#mp20-pilot`,
      open + close a test Linear issue.
- [ ] Backup of `pilot-advisors-2026-05-08.yml` exists outside
      `MP20_SECURE_DATA_ROOT` (in 1Password vault, accessible by
      Saranyaraj + Fraser).
- [ ] EC2 access tested for both Saranyaraj + Fraser.
- [ ] AWS SSM Parameter Store secrets confirmed; rotation
      procedure documented.

---

## Anti-patterns (DO NOT during incident response)

1. **Don't bulk-modify `ProcessingJob` rows from the shell** —
   audit-trail divergence + advisor confusion. Use
   `manage.py requeue_stale_jobs` or the retry endpoint instead.
2. **Don't push to `origin/main` from the EC2 instance** —
   deploys flow `local → CI → tag → deploy`. Hot-fix-on-server
   creates state divergence.
3. **Don't skip the post-incident audit** — even if the fix
   "feels obvious," the retro catches process gaps.
4. **Don't delete audit rows** — locked decision #37 + compliance.
5. **Don't lose the secure-data-root contents** — real-PII raw
   bytes live there; treat as gold.
6. **Don't disable PII grep / OpenAPI drift / vocab CI gates**
   to "ship faster" — those gates exist because regressions in
   their domains were costly historically.

---

## Engine→UI Display Rollback (v0.1.2-engine-display)

Sub-sessions #1-#5 shipped engine recommendations on Goal route +
Household route + 8-trigger auto-trigger + failure-state UX.
Rollback procedure if pilot surfaces engine-display Sev-1 bugs.

### Detection signals

- Advisors report **blank** `Portfolio recommendation` panels on
  Goal or Household routes.
- 5xx surge on `POST /api/clients/<hh>/generate-portfolio/`.
- Audit-log spike: `> 5 portfolio_run_failed` events / hour with
  `failure_code` not seen before.
- Cross-browser smoke red on Safari / Firefox post-deploy.
- RecommendationBanner shows literal i18n keys
  ("goal.no_recommendation_yet" instead of rendered copy) — i18n
  namespace regression.
- Auto-trigger fires + `engine.optimize()` exceeds 5s wall-time
  (locked #56 strict P99<1000ms violated → Sev-2 perf incident).

### Rollback decision tree

#### Option 1 (preferred): Kill-switch only

When the issue is the engine code path (engine.optimize bad output,
helper bug, etc.):

```bash
ssh ec2-user@<pilot-host>
cd /opt/mp20
docker compose exec backend sh -c 'export MP20_ENGINE_ENABLED=false'
docker compose restart backend
```

Effect: all auto-triggers + manual `/generate-portfolio/` calls
emit `portfolio_generation_skipped_post_<source>` audit with
`reason_code=EngineKillSwitchBlocked` + return None / 503. Existing
PortfolioRuns remain visible. Household commits CONTINUE to
succeed. Recovery: investigate + fix → re-deploy → flip kill-switch
back on.

#### Option 2: Frontend-only rollback (Banner / Panel issue)

When the issue is i18n / ARIA / display logic in the new components.
The components render INSIDE the existing route-level ErrorBoundary
per locked #108. Rollback to commit before the buggy frontend
change; redeploy frontend only. Backend auto-trigger continues to
work; advisors don't see the new display surfaces until fix lands.

#### Option 3 (full): Revert to v0.1.0-pilot

When the issue is fundamental:

```bash
ssh ec2-user@<pilot-host>
cd /opt/mp20
git fetch --tags origin
git reset --hard v0.1.0-pilot
docker compose build && docker compose up -d
```

Existing PortfolioRun rows persist (append-only + schema-compatible).
No DB recovery needed.

### Database state (non-destructive rollback)

- No destructive migrations in v0.1.2-engine-display.
- `AdvisorProfile`, `PortfolioRun`, `AuditEvent`, `HouseholdSnapshot`
  all append-only.
- Rollback is FULLY non-destructive.

### Verification

```bash
git tag -l "v0.1*"   # confirm rollback target

curl -s http://localhost:8000/api/session/ -o /dev/null -w "%{http_code}\n"  # 200

# In actual Chrome (NOT headless):
# 1. Navigate to localhost:5173/
# 2. Login advisor → pick Sandra/Mike Chen
# 3. v0.1.0 expected: AUM strip + treemap; NO portfolio-recommendation panel.
```

### Communication

1. Notify advisors within 15min: "Recommendation generation
   temporarily disabled while we investigate. Existing committed
   households + review workflows unaffected."
2. Update `pilot-success-metrics.md`.
3. Post-incident audit within 48h.

### Validated by

- A6.13c rollback smoke test (sub-session #5; documented in
  `handoff-log.md`).
