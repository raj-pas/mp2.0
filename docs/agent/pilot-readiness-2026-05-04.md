# MP2.0 Pilot Readiness — 2026-05-04

**Status:** living doc; updated weekly per `docs/agent/pilot-success-metrics.md` §2 cadence.
**Pilot start:** 2026-05-08 (limited beta)
**Initial cohort:** 3-5 advisors from Steadyhand on real-PII workflows
**Plan close-out commit:** _pending P10 commit_ (Pair 7b sub-agent close-out)
**Pre-tag HEAD at P10 verification:** `928e421` (Pair 7a)
**Tag:** `v0.1.3-pilot-quality-closure` (sister `v0.1.3-engine-display-polish` at tag predecessor)

## §1 — Quantitative success metrics (live snapshot at HEAD `928e421`)

8 bars from `pilot-success-metrics.md` §1, each with concrete query +
current value + week-1 target. Queries executed via
`docker compose exec backend uv run python web/manage.py shell -c "…"`
on 2026-05-05.

### 1. Advisors completing ≥1 client onboarding by Fri 2026-05-15

**Target:** 3 of 5 pilot advisors

**Query (Django ORM):**
```python
from django.db.models import Count
from web.api.models import Household, AdvisorProfile
pilot_advisors = AdvisorProfile.objects.filter(is_pilot=True).values_list("user_id", flat=True)
counts = Household.objects.filter(
    created_at__gte="2026-05-08T00:00:00Z",
    owner_id__in=pilot_advisors,
).values("owner__email").annotate(count=Count("id"))
```

**Audit-event proxy (idempotent):**
```python
from web.audit.models import AuditEvent
from django.db.models import Count
counts = AuditEvent.objects.filter(
    action="review_state_committed",
    created_at__gte="2026-05-08T00:00:00Z",
).values("actor").annotate(count=Count("id"))
```

**Current pre-pilot value:** 0 advisors with committed households post-2026-05-08;
3 households exist in dev DB (Sandra/Mike Chen + 2 R5 wizard smokes).
0 `review_state_committed` audit events recorded.
**Week-1 target:** 3+ advisors with ≥1 commit each

---

### 2. Sev-1 incidents in pilot weeks 1-2

**Target:** < 2 across both weeks

**Query (filesystem + Feedback):**
```bash
ls docs/agent/incidents/ 2>/dev/null | wc -l
```

```python
from web.api.models import Feedback
sev1_count = Feedback.objects.filter(
    severity="blocking",
    created_at__gte="2026-05-08T00:00:00Z",
).count()
```

**Current pre-pilot value:** 0 (no `docs/agent/incidents/` directory; 0 blocking Feedback rows)
**Week-1+2 target:** < 2

---

### 3. Real-PII docs reaching `reconciled` per advisor folder

**Target:** ≥ 90%

**Query (per-advisor):**
```python
from web.api.models import ReviewDocument, ReviewWorkspace, AdvisorProfile
pilot_advisors = AdvisorProfile.objects.filter(is_pilot=True).values_list("user_id", flat=True)
for advisor_id in pilot_advisors:
    workspaces = ReviewWorkspace.objects.filter(owner_id=advisor_id)
    total = ReviewDocument.objects.filter(workspace__in=workspaces).count()
    reconciled = ReviewDocument.objects.filter(workspace__in=workspaces, status="reconciled").count()
    pct = reconciled / total if total else 0
    print(f"{advisor_id}: {pct*100:.1f}% ({reconciled}/{total})")
```

**Current pre-pilot value:** 0/2 (0.0%) on dev-DB R7 fixtures (still in `processing` state).
2026-05-03 R10 sweep against 7 anonymized real-PII folders showed 56/56 reconciled (100%).
**Week-1 target:** ≥ 90% per advisor

---

### 4. Advisor NPS (qualitative; via Feedback severity="suggestion")

**Target:** ≥ 7/10

**Query:**
```python
from web.api.models import Feedback
suggestions = Feedback.objects.filter(
    severity__in=["suggestion", "praise"],
    created_at__gte="2026-05-08T00:00:00Z",
).count()
blocking = Feedback.objects.filter(severity="blocking").count()
# NPS proxy: 10 * (suggestions / total); ops manually extracts qualitative score weekly
```

**Current pre-pilot value:** N/A (pre-pilot; no Feedback rows)
**Week-1 target:** ≥ 7/10 average across pilot advisors

---

### 5. Bedrock spend per advisor / week

**Target:** < $25/week

**Query (AWS Cost Explorer; ops-owned):**
```
Service = Bedrock
Tag = PilotAdvisor:<advisor-uuid>
Date range = current week
Group by = Tag:PilotAdvisor
```

**Backend audit proxy:**
```python
from web.api.models import ReviewDocument
docs_this_week = ReviewDocument.objects.filter(
    workspace__owner_id__in=pilot_advisors,
    created_at__gte=week_start,
).count()
# ~$0.10 per doc Bedrock cost x docs_this_week / advisor count
```

**Current pre-pilot value:** $0.36 cumulative (R10 canary work, see
`bedrock-spend-2026-05-03.md`). P10 verification did NOT add Bedrock
spend (Niesner workspace not present in dev DB; live re-extract
SKIPPED gracefully per §A1.37 P10.3 fallback).
**Week-1 target:** < $25 per advisor

---

### 6. `manual_entry` rate per workspace

**Target:** < 25% docs

**Query:**
```python
from web.api.models import ReviewDocument
total = ReviewDocument.objects.filter(workspace__owner_id__in=pilot_advisors).count()
manual = ReviewDocument.objects.filter(
    workspace__owner_id__in=pilot_advisors,
    status="manual_entry",
).count()
pct = manual / total if total else 0
```

**Current pre-pilot value:** 0/2 (0.0%) — all dev-DB R7 docs in `processing`, none manual.
**Week-1 target:** < 25%

---

### 7. Time-to-first-portfolio per workspace (median)

**Target:** < 30 min

**Query (audit-event timestamps):**
```python
from web.audit.models import AuditEvent
import statistics
durations = []
for ws_id in pilot_workspaces:
    created = AuditEvent.objects.get(action="review_workspace_created", entity_id=ws_id).created_at
    committed = AuditEvent.objects.filter(action="review_state_committed", entity_id=ws_id).order_by("created_at").first()
    portfolio = AuditEvent.objects.filter(
        action__startswith="portfolio_generation_post_",
        entity_id=committed.metadata.get("household_external_id") if committed else None,
    ).order_by("created_at").first()
    if portfolio:
        durations.append((portfolio.created_at - created).total_seconds() / 60)
median = statistics.median(durations) if durations else None
```

**Current pre-pilot value:** N/A (no `portfolio_generation_post_*` events
in dev DB beyond Sandra/Mike auto-seed; no review→commit→generate
chain has been traced end-to-end against pilot advisors yet).
**Week-1 target:** Median < 30 min

---

### 8. Conflict-resolve rate per workspace

**Target:** ≥ 80%

**Query:**
```python
from web.audit.models import AuditEvent
from web.api.models import ReviewWorkspace
for ws in pilot_workspaces:
    total_conflicts = ws.aggregate_conflict_count()  # method on model
    resolved = AuditEvent.objects.filter(
        action="review_conflict_resolved",
        entity_id=ws.external_id,
    ).count()
    pct = resolved / total_conflicts if total_conflicts else 1.0
    print(f"{ws.external_id}: {pct*100:.1f}%")
```

**Current pre-pilot value:** 0 `review_conflict_resolved` events; 0
`account_assigned_to_goals` events (P13 endpoint shipped but not yet
exercised against real-PII workspaces in dev DB).
**Week-1 target:** ≥ 80% per workspace

---

## §2 — Check-in cadence

Per `pilot-success-metrics.md` §2:

- **Monday morning:** ops pulls Feedback report; flags Sev-1; updates this doc + appends to handoff-log.
- **Friday EOW:** ops + Fraser sync on weekly metrics; triage to Linear if any metric off-target. Bedrock spend pulled from AWS console.
- **Mid-week ad-hoc:** if Sev-1 fires, retro within 48h per `pilot-rollback.md` §8.

## §3 — Rollback criteria (off-ramp)

Pause pilot if:
- Sev-1 incident count ≥ 2 in any week
- Real-PII docs reconciled rate < 70% any week
- Bedrock spend > $50 per advisor in any week
- Time-to-first-portfolio median > 60 min any week

Engage `pilot-rollback.md` Sev-1 procedure; revert tag if needed.

## §4 — GA criteria (pilot → broader release)

Per `pilot-success-metrics.md` §3, GA-ready when ALL hold for 2 consecutive weeks:
1. Sev-1 = 0
2. Per-advisor NPS ≥ 8
3. ≥ 50% pilot advisors completed ≥ 3 onboardings
4. Locked #18 perf budget intact (P50 < 250ms / P99 < 1000ms)
5. R10 sweep across all 7 client folders re-passes weekly
6. Manual-entry rate < 15%

## §5 — Audit & verification queries (one-shot, run at pilot launch)

```bash
# Verify advisor accounts provisioned
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 \
  uv run python web/manage.py shell -c "
from web.api.models import AdvisorProfile
for p in AdvisorProfile.objects.filter(is_pilot=True):
    print(f'{p.user.email}: SSO={p.sso_provider}; pilot_start={p.pilot_started_at}')
"

# Verify kill-switch is OFF (engine enabled for pilot)
grep MP20_ENGINE_ENABLED .env  # expect: True or unset

# Verify Bedrock IAM role + ca-central-1 routing
aws sts get-caller-identity
aws bedrock list-foundation-models --region ca-central-1 | jq '.modelSummaries[] | select(.modelId | contains("anthropic"))' | head

# Verify audit-event invariants
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 \
  uv run pytest web/api/tests/test_audit_metadata_invariants.py -v
```

## §6 — Sign-off

- Saranyaraj (technical lead): _____________ (date)
- Fraser (advisor lead): _____________ (date)
- Lori (compliance/copy): _____________ (date)
