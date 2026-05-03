# Demo-State Restore Runbook

**Audience:** Saranyaraj (or any operator) preparing demo state on
Mon 2026-05-04 morning, OR after an incident that destroys the
local DB.

**Why a runbook (not an automated script):** the reset wipes
Docker volumes and re-incurs ~$0.5-1 of Bedrock spend. It's
deliberately gated behind explicit sandbox permission so that a
session agent doesn't wipe locked demo state autonomously.

---

## Pre-reset state snapshot (captured 2026-05-03 at HEAD `8af7104`)

Structural-only counts; no values, no quotes (canon §11.8.3):

| Table | Count |
|---|---|
| ReviewWorkspace | 6 |
| ReviewDocument | 27 |
| ProcessingJob | 48 |
| ExtractedFact | 713 |
| Household | 4 |
| Person | 5 |
| Account | 8 |
| Goal | 6 |
| PortfolioRun | 1 |

The 4 households are: Sandra/Mike (synthetic) + 3 real-PII
committed (Niesner / Seltzer / Weryha pre-Phase 9 from earlier
sessions). The 6 workspaces include those 4 committed + 2 in
review_ready / processing flux.

---

## Reset procedure

### 1. Wipe + reseed (Sandra/Mike + bootstrap advisor)

```bash
cd /Users/saranyaraj/Projects/github-repo/mp2.0
bash scripts/reset-v2-dev.sh --yes
```

Sandbox note: this requires an explicit Claude Code bash
permission rule for ``scripts/reset-v2-dev.sh --yes``. The
locked decision #34 pre-authorizes the COMMAND but the bash
sandbox tracks per-command permission rules separately and may
prompt for a rule on first invocation in a new session.

Expected wall-clock: ~60-90s (compose down -v ~5s; compose up db
~10s; healthcheck poll ~10-30s; migrate ~10-15s; seed_default_cma
~5s; load_synthetic_personas ~5-15s; bootstrap_local_advisor ~2s).

Expected post-reset DB state:

| Table | Expected count |
|---|---|
| ReviewWorkspace | 0 |
| ReviewDocument | 0 |
| ProcessingJob | 0 |
| ExtractedFact | 0 |
| Household | 1 (Sandra/Mike committed via synthetic personas) |
| Person | 2 (Sandra + Mike) |
| Account | varies (3-5 per persona seed file) |
| Goal | varies (per persona seed file) |
| PortfolioRun | 0 |
| User | 2-3 (advisor@example.com + analyst@example.com + maybe a default superuser) |

### 2. Pre-upload Seltzer + Weryha for demo

```bash
set -a && source .env && set +a
unset AWS_SESSION_TOKEN AWS_SECURITY_TOKEN

# Seltzer (5 docs)
uv run python scripts/demo-prep/upload_and_drain.py Seltzer

# Weryha (4 docs)
uv run python scripts/demo-prep/upload_and_drain.py Weryha
```

Each script logs in as advisor@example.com, creates a
``real_derived`` workspace, uploads every supported file, spawns
a worker, polls every 15s until the queue drains, then prints
the final demo state.

Expected wall-clock per folder: ~3-5 minutes.

Expected demo state post-prep (per Phase 9 canary at HEAD
`8af7104`, see `docs/agent/r10-sweep-results-2026-05-03.md`):

**Seltzer (5 docs):**
- Docs reconciled: 5/5
- Facts extracted: ~95 (mix of vision_native_pdf + text paths)
- Conflicts: 0-2 (depending on per-doc agreement)

**Weryha (4 docs):**
- Docs reconciled: 4/4
- Facts: ~80-100 (similar mix)
- Conflicts: 0-2

Each script exits 0 if reconciled == total + failed == 0.

### 3. Verify demo path manually

Open `localhost:5173` in Chrome (not headless):

- Login as advisor@example.com
- Navigate to ClientPicker; confirm Sandra/Mike + Seltzer + Weryha
  visible
- Open Sandra/Mike; confirm three-tab pivot + treemap render
- Open /review; confirm two pre-upload workspaces in review_ready
- Click into Seltzer workspace; confirm doc list + facts grouped
  by section
- Click a doc row; confirm DocDetailPanel slides in from right
- Walk one section approval flow without committing
- /methodology overlay end-to-end

### 4. Capture structural counts post-prep

```bash
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 \
  uv run python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web.mp20_web.settings')
django.setup()
from web.api import models
print('=== Post-restore DB structural counts ===')
print(f'Workspaces: {models.ReviewWorkspace.objects.count()}')
print(f'Documents: {models.ReviewDocument.objects.count()}')
print(f'ExtractedFacts: {models.ExtractedFact.objects.count()}')
print(f'Households: {models.Household.objects.count()}')
"
```

Expected post-restore counts (pre-pilot demo state):

| Metric | Sandra/Mike only | + Seltzer | + Weryha |
|---|---|---|---|
| Workspaces | 0 (committed only) | 1 (review_ready) | 2 (review_ready) |
| Documents | 0 | ~5 | ~9 |
| ExtractedFacts | 0 | ~95 | ~175-200 |
| Households | 1 | 1 | 1 |

Sandra/Mike is committed at seed time via
`load_synthetic_personas`; Seltzer + Weryha stay in review_ready
(advisor commits them during the demo if the flow exercises
commit).

---

## Rollback (Sev-1 incident)

If the demo state restore is broken at reset time and the demo
is imminent, see `docs/agent/pilot-rollback.md` §"DB recovery"
for the targeted-recovery vs full-reset decision tree.

---

## Procedural validation (this session, 2026-05-03)

Sub-session #10.5 was scoped to "actually run reset + restore +
capture wall-clock". The bash sandbox refused both attempts at
the destructive Docker volume wipe (rightly so — the conversation
authorization didn't translate to the per-command permission
rule the sandbox enforces).

What was validated procedurally:
- The reset script's contents (`scripts/reset-v2-dev.sh`, lines
  1-52) are unchanged from the prior locked-state run that
  produced the 130e211 demo restore. The `compose down -v` →
  `compose up db` → migrate → seed sequence is byte-identical.
- The `upload_and_drain.py` script (`scripts/demo-prep/upload_and_drain.py`,
  unchanged since 2026-05-02) handles per-doc upload + worker
  drain + final-state-check identically.
- The new code paths (Phase 9 prompts + native-PDF dispatch)
  have been canary-validated under the same
  `extract_facts_for_document` flow that the worker invokes —
  see `docs/agent/r10-sweep-results-2026-05-03.md` Seltzer + Niesner
  results from the in-process Bedrock canaries.
- All gate suites pass at HEAD: 819 pytest + 52 Vitest + ruff
  clean + PII grep + vocab CI green.

Conclusion: the reset script + demo-prep script + the Bedrock
codepath the worker uses are all individually validated. The
gap is the end-to-end integration test of the three components
chained, which is the runbook above.

---

## Next-time-this-runs improvements (post-pilot)

1. Pre-flight check: ``scripts/reset-v2-dev.sh --dry-run`` mode
   that prints the destructive ops without executing.
2. Snapshot/restore: ``scripts/snapshot-demo-state.sh`` dumps the
   committed-state row sets to an out-of-repo SQL file so a
   targeted restore is possible without full re-extraction.
3. Per-step error handling: the reset script's `set -e` + the
   inline migrate + seed steps don't have rollback. If migrate
   fails halfway, the DB is in an undefined state. Future
   improvement: wrap each step in a transaction + bail cleanly.
