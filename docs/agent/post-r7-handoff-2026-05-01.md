# Post-R7 Handoff Dossier — Extraction Hardening for Demo & Release

**Author:** Claude Code session 2026-05-01
**Branch:** `feature/ux-rebuild`
**HEAD:** `ec98596` — `fix(R7): live FileList ref race in DocDropOverlay + locked-#28b real-PII checkpoint`
**Mission:** Make the doc-drop → review → commit → portfolio pipeline production-grade for a limited-user pilot.
**Hard deadlines (per user, 2026-05-01):**
- **Demo to CEO + Chief Product Officer in 3 days** (target 2026-05-04)
- **Release in 1 week** (target 2026-05-08)

---

## How To Use This Document

If you are a fresh Claude Code session inheriting this work:

1. Read this file end-to-end. It is the single source of truth for state and next steps.
2. Then, in this order:
   - `~/.claude/plans/post-r7-extraction-hardening.md` (the action plan with sub-tasks)
   - `~/.claude/plans/i-want-you-to-rosy-mccarthy.md` (the v36 master rewrite plan with 39 locked decisions)
   - `docs/agent/session-state.md` (live phase status)
   - `docs/agent/handoff-log.md` (most recent entry: 2026-05-01 Foundation rebuild + locked-#28b)
   - `docs/agent/decisions.md` (canon decision history; full file is large — search for relevant phase)
   - `MP2.0_Working_Canon.md` (canon v2.8 — authoritative product/strategy/architecture)
   - Memory: `~/.claude/projects/-Users-saranyaraj-Projects-github-repo-mp2-0/memory/MEMORY.md` (auto-loaded; provides project context shortcuts)
3. Then run the smoke procedure (see [§7](#7-how-to-run-the-stack)) to verify your environment matches what was working at the end of this session.
4. Then start [§9 (the next task)](#9-the-next-task--p0-1-extraction-quality-hardening).

**Do not start coding before §3.** A correct mental model of what is broken AND what is working is the difference between adding to the foundation and re-introducing the bugs we just spent a day finding.

---

## 1. Why This Document Exists

The user pushed back on R7 ship-quality after lived experience: "I can't upload docs and the whole flow isn't working at all. The ingestion pipeline isn't usable at all (robustness seems so far away for you)."

That pushback was not a perception issue. The R7 commit shipped with **a critical, latent file-input race condition** that survived 10/10 Playwright e2e + 103 web pytest + ruff/typecheck/lint/build. The bug was hidden because Playwright's headless Chrome happened to win the race in CI, while real-browser usage lost it deterministically.

The 2026-05-01 session fixed that bug, ran the locked-decision #28b real-PII checkpoint that R7 had deferred, and surfaced a second tier of extraction-quality issues (xlsx + large-PDF Bedrock failures) that need work before the pipeline is demo-ready.

**This dossier is the persistent state for completing that work.** A fresh session must be able to land at HEAD and make production-quality progress without re-deriving context. Any context loss between sessions on a 3-day fuse is a project risk.

---

## 2. Mission, Constraints, and Definition of Done

### Mission

Take the doc-drop → review-screen → commit → portfolio-generation pipeline from "mechanically works on synthetic, partially works on real PII" to "advisor uploads a real client folder, the system extracts cleanly, surfaces conflicts, gets approved, commits, and produces a portfolio recommendation — every single time."

### Hard constraints

- **Branch:** all work continues on `feature/ux-rebuild`. Do not merge to `main` until R10 ship per locked decision #33.
- **Real-PII discipline:** real client folders at `/Users/saranyaraj/Documents/MP2.0_Clients/` (Gumprich, Herman, McPhalen, Niesner, Schlotfeldt, Seltzer, Weryha). Routing references only — never quote contents in code, commits, memory, or chat. Use Bedrock ca-central-1 only for `data_origin: real_derived`. `MP20_SECURE_DATA_ROOT=/private/tmp/mp20-secure-data` outside repo.
- **AI-numbers rule (canon §9.4.5):** AI extracts and styles, never invents financial numbers. If extraction can't satisfy a field, surface the gap to the advisor — do not fabricate.
- **Engine purity (canon §9.4.2):** `engine/` must not import Django, DRF, `web/`, `extraction/`, or `integrations/`.
- **Vocabulary discipline (canon §6.3a + §16):** building-block fund (not "sleeve") in product/UX surfaces; re-goaling, never reallocation; canon-aligned risk descriptors (Cautious / Conservative-balanced / Balanced / Balanced-growth / Growth-oriented).
- **No bulk-modifying jobs/workspaces the agent didn't create** without explicit user authorization. Locked decision #34 pre-authorizes `scripts/reset-v2-dev.sh --yes`; anything narrower needs confirmation.

### What demo-ready means (3 days)

When the user opens the app in front of CEO + CPO, the following must work without surprises:

1. Login → land at `/`.
2. Pick a synthetic household (Sandra/Mike) → see treemap + AUM strip + KPIs.
3. Drill into account → goal → see RiskSlider + projection fan chart + moves.
4. Open `/wizard/new` → walk 5 steps → commit → land on the new household.
5. Open `/review` → drag a real client folder → all docs upload, all visible in queue.
6. Click into the workspace → watch processing complete (not stuck at "processing").
7. See readiness gates flip green; section approvals visible; commit produces a household.
8. Generate portfolio → output appears in advisor console.

The **failure mode that breaks the demo** is step 6 stalling or step 7 failing on a doc the CEO can see.

### What release-ready means (1 week)

Demo-ready PLUS:

- All 7 client folders complete the full flow without manual intervention.
- Conflict-resolution UI exists (today the engine surfaces conflicts but advisor can't act on them).
- Manual-entry escape hatch when extraction fails for a doc.
- OpenAPI-typescript codegen wired (locked decision #26b) so contract drift can't repeat.
- All P0 items in [§5 (the backlog)](#5-the-p0-backlog-ranked-for-demo--release) are complete except #6 (auth) and #7 (audit immutability), which the user explicitly deferred.

---

## 3. Where We Are At Exactly

### Branch + commits (newest first)

```
ef81915 fix(R8 followups #3 + #4): demo backup script + pre-checklist hardening      ← HEAD
43c1d55 test(R8 followup #1): real-browser smoke covers /methodology overlay
219f0c4 fix(R8 followup #2): cross-verify methodology worked examples vs engine
abafecf docs(post-R8): pre-compaction continuity — followups + dossier refresh
cfe941c feat(R8): methodology overlay + demo lock-down for 2026-05-04 demo
28628d8 test(R7): pre-demo critical-test pass — manual-entry UX + real-PII commit
edecadf docs(R7): post-R7 extraction-hardening complete + R10 sweep 55/55 reconciled
96ba736 feat(R7): manual-entry escape hatch for advisor when extraction fails
826cdb1 fix(R7): typed BedrockExtractionError hierarchy + structured failure_code
52e3327 fix(R7): Bedrock max_tokens 4096→16384 closes Niesner extraction truncation
03ce247 docs(R7): next-session kickoff prompt for extraction-hardening
c07acc8 docs(R7): handoff dossier + extraction-hardening plan for demo + release
ec98596 fix(R7): live FileList ref race in DocDropOverlay + locked-#28b real-PII checkpoint
4643bb5 fix(R7): close 6 doc-drop pipeline contract drifts caught by deep dig
3416143 Phase R7: doc-drop + review-screen for v36 UI/UX rewrite                              ← R7 ship
... (R0–R7 history same as before)
```

`feature/ux-rebuild` is **6 commits ahead** of `origin/feature/ux-rebuild` at HEAD. Do not push without explicit user authorization. (This count fluctuates — origin doesn't auto-track all our commits; treat as "do not push.")

### Local DB state (as of post-R8 + demo lock)

- **Sandra/Mike Chen** — synthetic, 1 household, fresh from `scripts/reset-v2-dev.sh --yes` reseed.
- **`Seltzer review (demo prep)`** — real_derived workspace, **5/5 reconciled** (workspace ID dynamic; lookup by label). 1 person, 6 accounts, 4 goals, 18 conflicts, 0 failures. KYC ready ✓; engine_ready/construction_ready remain ⚠ (advisor decisions pending — by design for the demo flow).
- **2 incidental e2e leftover artifacts** — 1 R7 e2e doc-drop workspace with a queued job, 1 wizard-created household. Demo flow won't surface either; cleanup not blocking.
- Local advisor: `advisor@example.com` (password in `.env` at `MP20_LOCAL_ADMIN_PASSWORD`). Analyst: `analyst@example.com`.

### Live stack as left

- Postgres in Docker (`mp20-db-1`) — healthy.
- Backend in Docker (`mp20-backend-1`) — running on `:8000`, auto-reloads.
- Vite on host — running on `:5173`.
- Worker on host — **idle**; queue is drained except for 1 leftover R7 e2e doc job that doesn't matter for demo.

### What's at HEAD (ef81915)

- **R7 phase**: complete (commit `3416143`)
- **Post-R7 hardening**: 3.A max_tokens, 3.B typed errors, 3.E manual-entry hatch — all shipped
- **R10 sweep**: 55/55 reconciled across 7 client folders, 2,304 facts, 0 new failures
- **Pre-demo critical testing**: 5/5 items, 1 fix shipped (engine_adapter case-norm), 2 bugs catalogued for post-demo
- **R8 methodology overlay**: shipped — 10 sections, canon-aligned descriptors, ~70 i18n keys, e2e covers section render + descriptors + Goal_50-hidden invariant + TOC scroll
- **Post-R8 followups**: all 4 closed — Item #2 surfaced + fixed 3 i18n bugs in s3/s6/s7 (worked examples now math-verified against engine via new regression test); Item #1 extends real-browser smoke to /methodology with 10-section H2 + TOC scroll assertions; Items #3+#4 ship a durable parameterized prep script + Weryha drop-in backup + cache-warm pre-checklist line
- **Demo lock-down**: clean DB + Seltzer 5/5 pre-uploaded + demo script at `docs/agent/demo-script-2026-05-04.md`

### Verified-working (as of HEAD `ef81915`)

- 216 engine pytest + 122 web pytest + 2 audit pytest + 1 R8 regression set (8 tests) = **341 passing**
- **11/11 Playwright foundation e2e** (R8 methodology spec included)
- ruff check + ruff format check clean
- frontend: `npm run typecheck`, `npm run lint`, `npm run build` clean
- `scripts/check-vocab.sh` OK
- `makemigrations --check --dry-run` clean
- Legacy-label runtime tripwire OK (caught + fixed one Fraser reference during R8 build)
- Niesner real-PII pipeline 12/12 reconciled with 493 facts
- R10 sweep 55/55 reconciled with 2,304 facts
- Real-browser smoke clean against pre-uploaded Seltzer (0 unexpected console signals); /methodology coverage extended (executes against live server with secure root + Bedrock env)
- Real-PII commit + portfolio gen validated end-to-end (Niesner)
- New `engine/tests/test_r8_worked_examples_match_engine.py` (8 tests): pins methodology.s* worked-example numbers to engine output; future drift fails CI before the methodology page lies on stage

### Scheduled follow-up

A remote agent is scheduled for **Wed 2026-05-06 09:00 America/Winnipeg** (`2026-05-06T14:00:00Z`) — trigger ID `trig_018jTLBFnRJ8oTAiZbyQXwBv` — to scope fix plans for the 2 catalogued bugs:
1. Workspace status doesn't flip to COMMITTED after successful commit
2. Zero/null-value accounts cause optimizer ValueError

Output will land at `docs/agent/post-pilot-bugfix-proposal.md` (committed to `feature/ux-rebuild`, not pushed). Manage at https://claude.ai/code/routines/trig_018jTLBFnRJ8oTAiZbyQXwBv

### Demo timing

- **Demo to CEO + CPO: Mon 2026-05-04**
- **Release: Mon 2026-05-08**
- **Bugfix-proposal agent fires: Wed 2026-05-06**
- Playwright: `cd frontend && PLAYWRIGHT_BASE_URL=http://localhost:5173 ... npx playwright test e2e/foundation.spec.ts` → 10/10 passing
- Synthetic full pipeline (workspace create → upload → worker → reconcile → state PATCH → 6 approvals → commit → portfolio gen) verified end-to-end via curl.
- Real-PII Niesner checkpoint: 12 docs uploaded, 10 reconciled, 2 failed (bounded), 285 facts, 25 conflicts surfaced.

### Known broken / parked / incomplete

See [§4 (bugs found and fixed)](#4-bugs-found-and-fixed-this-session) and [§5 (open backlog)](#5-the-p0-backlog-ranked-for-demo--release).

---

## 4. Bugs Found and Fixed This Session

These are the user-blocking issues that were live at the start of the session and are now resolved at HEAD `ec98596`.

### 4.1 Live FileList ref race in DocDropOverlay (CRITICAL)

**File:** [`frontend/src/modals/DocDropOverlay.tsx`](../../frontend/src/modals/DocDropOverlay.tsx)
**User-visible symptom:** Click "Start review", button greys out, **nothing happens**. No toast. No console error.
**Root cause:** `event.target.files` is a *live* FileList reference; clearing the input via `event.target.value = ""` empties it. The original code queued `setFiles((prev) => [...prev, ...Array.from(picked)])` (deferred under React 18 batching) and *then* cleared the input. By the time the deferred callback ran, `picked` was empty, so React state stayed `[]`, the file count counter stayed `0 FILES READY TO UPLOAD`, and the Start button stayed disabled forever.

The R7 e2e Playwright spec ran the same sequence but won the race in headless mode — classic flake masquerading as green CI.

**Fix:** snapshot `Array.from(picked)` synchronously *before* clearing the input. Same fix on `handleDrop` (DataTransfer.files is also live).

```ts
// ANTI-PATTERN (the bug)
const picked = event.target.files;
setFiles((prev) => [...prev, ...Array.from(picked)]);  // deferred; picked may be empty by now
event.target.value = "";

// CORRECT (the fix)
const picked = event.target.files;
if (picked === null || picked.length === 0) return;
const snapshot = Array.from(picked);  // capture synchronously
event.target.value = "";
setFiles((prev) => [...prev, ...snapshot]);
```

**Regression guard:** `frontend/e2e/foundation.spec.ts` R7 spec now asserts `1 FILE READY TO UPLOAD` before clicking Start, deterministically catching any regression of this class.

### 4.2 Frontend ProcessingJobStatus enum drift (HIGH)

Backend emits `"queued" | "processing" | "completed" | "failed"`; frontend shipped `"queued" | "running" | "done" | "failed"`. The `useReviewWorkspace` polling guard `job.status === "running"` never matched, so the UI stopped polling the moment the worker claimed a job → workspace looked frozen at "processing" forever.

**Fixed in commit `4643bb5`** — types in [`frontend/src/lib/review.ts`](../../frontend/src/lib/review.ts) aligned to backend wire shape.

### 4.3 SectionApproval status enum drift + DocumentStatus widening

Backend has `needs_attention` and `not_ready_for_recommendation`; frontend shipped `not_ready`. DocumentStatus on the wire includes more values than the frontend type. Both fixed in `4643bb5` in [`frontend/src/lib/review.ts`](../../frontend/src/lib/review.ts).

### 4.4 Section-approval list mismatch (CRITICAL)

Backend `ENGINE_REQUIRED_SECTIONS` (in [`web/api/review_state.py:47-54`](../../web/api/review_state.py)) is `["household", "people", "accounts", "goals", "goal_account_mapping", "risk"]`. Frontend hardcoded `["people", "accounts", "goals", "risk", "planning"]`. Result: `household` and `goal_account_mapping` had **no Approve button** — commit always 400'd with a generic "could not commit household" toast.

**Fixed in `4643bb5`** by exposing `required_sections` in [`web/api/review_serializers.py`](../../web/api/review_serializers.py) ReviewWorkspaceSerializer (single source of truth = `ENGINE_REQUIRED_SECTIONS`) and driving [`frontend/src/modals/ReviewScreen.tsx`](../../frontend/src/modals/ReviewScreen.tsx) `SectionApprovalPanel` + commit-disabled gate off the server-provided list.

### 4.5 Worker stale-job auto-recovery missing (HIGH)

`claim_next_job()` only filtered `status=QUEUED`; a worker that crashed mid-job left rows in `PROCESSING` indefinitely → workspace polled forever. **Fixed in `4643bb5`** in [`web/api/review_processing.py`](../../web/api/review_processing.py): added `requeue_stale_jobs()` that finds rows where `locked_at < now - MP20_WORKER_STALE_SECONDS` and either pushes back to QUEUED (if attempts remain) or marks FAILED. Called from `claim_next_job()` on every cycle. Emits `review_job_auto_recovered` audit events.

### 4.6 Upload partial failure 500'd entire batch (HIGH)

A single bad file (disk error, FS perms, oversize) aborted the upload loop. **Fixed in `4643bb5`** in [`web/api/views.py`](../../web/api/views.py) `ReviewWorkspaceUploadView.post()`: each file iteration is wrapped in its own `try/except + transaction.atomic()`. Failed files land in `ignored` with `failure_code` instead of bubbling. Each failure fires `review_document_upload_failed` audit; empty-batch fires `review_upload_empty_rejected`. Frontend toasts a partial-success summary.

### 4.7 Commit error response had no actionable detail (MEDIUM)

Generic "Could not commit household" toast. **Fixed in `4643bb5`** in [`web/api/views.py`](../../web/api/views.py) `ReviewWorkspaceCommitView`: returns `{detail, code, readiness, missing_approvals, required_sections}` on 400. `code` is one of `engine_not_ready | construction_not_ready | sections_not_approved | unknown`. Frontend [`api-error.ts`](../../frontend/src/lib/api-error.ts) carries the structured body; `ReviewScreen` keys off `e.code` for actionable copy.

### 4.8 Approvals not invalidated on state PATCH (MEDIUM, silent corruption)

Advisor could approve `goals`, then PATCH to remove a required field, and the approval persisted → silent commit-gate evasion. **Fixed in `4643bb5`** in [`web/api/views.py`](../../web/api/views.py) `ReviewWorkspaceStateView.patch()`: after `create_state_version` returns, walks approvals and flips status to `NEEDS_ATTENTION` for sections with fresh blockers. Response includes `invalidated_approvals: string[]`.

### 4.9 6 new pytest tests guarding the above

In [`web/api/tests/test_review_ingestion.py`](../../web/api/tests/test_review_ingestion.py):

- `test_workspace_serializer_exposes_required_sections`
- `test_state_patch_invalidates_stale_section_approval`
- `test_commit_returns_structured_error_with_missing_approvals`
- `test_worker_auto_recovers_stale_processing_job`
- `test_upload_partial_failure_does_not_500_whole_batch`
- `test_full_pipeline_upload_to_commit` (full happy path through commit)

---

## 5. The P0 Backlog Ranked For Demo + Release

User has explicitly **deferred** auth (#6) and audit-immutability (#7) to post-pilot. The remaining P0 items, in execution order:

| # | Item | Demo-blocking? | Release-blocking? | Effort |
|---|------|---|---|---|
| 1 | **Extraction-quality hardening** (xlsx + large-PDF + failure-code taxonomy + manual-entry hatch) | YES | YES | 1-2 days |
| 2 | **Conflict-resolution UI** (cards with candidate values + source attribution + redacted evidence + rationale capture) | maybe | YES | 1-1.5 days |
| 3 | **Manual-entry escape hatch per failed doc** | maybe | YES | 0.5 day |
| 4 | **Real-browser manual smoke playbook** (the FileList-class bug Playwright misses) | YES (run before demo) | YES | 0.5 day |
| 5 | **OpenAPI-typescript codegen + drift CI** (kills contract-drift bug class — locked #26b) | NO (already shipped one round of fixes) | strongly recommended | 0.5 day |
| 8 | **R10 full-folder sweep across all 7 clients** (catches whatever P0 #1-#5 missed) | NO | YES (release gate) | 1-2 days |

The remaining list lives in [§13 (Phase B follow-ups)](#13-phase-b-follow-ups-not-blocking-pilot). Items 6 (auth) and 7 (audit-immutability validation) are in Phase B per user's 2026-05-01 decision.

---

## 6. Real-PII Niesner Checkpoint Results (Locked Decision #28b)

Run on 2026-05-01 against `/Users/saranyaraj/Documents/MP2.0_Clients/Niesner/` with `data_origin: real_derived`. Workspace external_id `d689fe68-c335-44ae-bbb3-104974b7e764`, label "Niesner real-PII checkpoint".

### Outcome (anonymized to structural counts)

- 12 files uploaded (a 13th xlsx with a comma in its filename failed to upload via curl; not a server bug — see [§14.4](#144-curl-filename-with-comma-bug))
- **10/12 docs reconciled** (PDFs: DOB / Profile / KYC / Address / Retirement Guide / one Plan-projections xlsx; DOCX: Client Notes)
- **285 structured facts** extracted across the 10 reconciled docs
- **25 cross-source conflicts** surfaced (correct source-priority reconciliation per canon §11.4)
- 2 people, 8 accounts, 2 goals, 1 household, risk profile present in reviewed_state
- Readiness correctly identifies the *only* remaining blockers: goal time-horizon + goal-account mapping. Both are advisor-decision territory per canon §9.4.5; the AI cannot fabricate them.
- 2 docs failed gracefully and bounded:
  - 6.2MB Finalized Financial Plan PDF → `Bedrock did not return valid JSON` after 3 attempts. Likely token-limit truncation of Bedrock response mid-JSON.
  - 1 of 3 xlsx files (planning projections) → same `Bedrock did not return valid JSON`. Likely Bedrock returns markdown tables for spreadsheet content; `json_payload_from_model_text` repair can't recover.
- **No queue lockup.** `max_attempts=3 → marked FAILED → next doc claimed.** The whole batch drained in ~7 minutes wall-clock.
- **UI surfaces it correctly:** all 12 doc rows visible, 2 failed-status chips, readiness panel populated, all 6 required section-approval buttons visible, missing-required panel listing the advisor blockers.

### What this means

- Pipeline is **mechanically sound for real PII**.
- **Two extraction-quality bugs** are real and blocking demo credibility:
  - Tabular content in xlsx files
  - PDFs above the effective Bedrock token budget at `MP20_TEXT_EXTRACTION_MAX_CHARS=24000`
- The R10 sweep across all 7 folders will systematically expose these patterns — every advisor folder has at least one Plan PDF and at least 1-3 xlsx projection sheets.

These two bugs are the load-bearing target of P0 #1 (the next task).

---

## 7. How To Run The Stack

### Repo + env setup

```bash
cd /Users/saranyaraj/Projects/github-repo/mp2.0
git status                                        # confirm on feature/ux-rebuild
git log --oneline -5                              # confirm HEAD is ec98596 (or later)
set -a && source .env && set +a                   # load env (passwords, MP20_SECURE_DATA_ROOT, AWS, etc.)
echo "MP20_SECURE_DATA_ROOT=$MP20_SECURE_DATA_ROOT"  # should print /private/tmp/mp20-secure-data
```

`.env` is gitignored. Required env vars (see `.env.example`):

- `DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20`
- `MP20_SECURE_DATA_ROOT=/private/tmp/mp20-secure-data` (must be outside repo)
- `MP20_LOCAL_ADMIN_EMAIL=advisor@example.com`
- `MP20_LOCAL_ADMIN_PASSWORD=<set in .env>`
- `MP20_LOCAL_ANALYST_EMAIL=analyst@example.com`
- `MP20_LOCAL_ANALYST_PASSWORD=<set in .env>`
- `MP20_REVIEW_TEAM_SLUG=steadyhand`
- `MP20_WORKER_NAME=local-worker`
- `MP20_WORKER_STALE_SECONDS=60`
- `MP20_OCR_MAX_PAGES=12`
- `MP20_TEXT_EXTRACTION_MAX_CHARS=24000`
- `MP20_ENGINE_ENABLED=1`
- `AWS_ACCESS_KEY_ID=<set>`
- `AWS_SECRET_ACCESS_KEY=<set>`
- `AWS_REGION=ca-central-1`
- `BEDROCK_MODEL=global.anthropic.claude-sonnet-4-6`

### Stack startup (host-mode, recommended for active dev)

Postgres in Docker, everything else on host. This is what worked during the session.

```bash
# 1. Bring up Postgres only
docker compose up -d db
docker compose ps                                 # confirm db is healthy

# 2. Apply migrations + reseed if needed (only if reset is appropriate)
# scripts/reset-v2-dev.sh --yes                   # NUKES DB; use only when authorized

# 3. Start backend on host (auto-reloads on file change)
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 \
  uv run python web/manage.py runserver 127.0.0.1:8000 &

# 4. Start Vite on host (auto-HMR)
cd frontend && npm run dev -- --host 127.0.0.1 > /tmp/mp20-vite.log 2>&1 &
cd ..

# 5. (When needed) Start worker on host
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 \
  uv run python web/manage.py process_review_queue > /tmp/worker.log 2>&1 &
# Or `--once` for a single pass.
```

### Stack startup (full Docker, simpler but slower iteration)

```bash
docker compose up --build
```

This starts Postgres + backend + worker. Frontend still runs on host via `npm run dev` for fast HMR.

**Caveat:** the backend container's image bakes the Python deps, so when `pyproject.toml` changes you must `docker compose build backend`. Code changes auto-reload via volume mount.

### Quick sanity probe

```bash
curl -s http://localhost:8000/api/session/ -w "\n%{http_code}\n"
# Expect: {"authenticated":false,"csrf_token":"...","user":null}\n200

curl -s http://localhost:5173/ -o /dev/null -w "%{http_code}\n"
# Expect: 200
```

### Login via curl (for backend smoke)

```bash
cd /tmp && rm -f cookies.txt
curl -s http://localhost:8000/api/session/ -c cookies.txt -o /dev/null
CSRF=$(grep csrftoken cookies.txt | awk '{print $7}')
PW=$(grep "^MP20_LOCAL_ADMIN_PASSWORD=" /Users/saranyaraj/Projects/github-repo/mp2.0/.env | cut -d= -f2-)
curl -s -X POST http://localhost:8000/api/auth/login/ \
  -c cookies.txt -b cookies.txt \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF" \
  -H "Referer: http://localhost:8000/" \
  -d "{\"email\":\"advisor@example.com\",\"password\":\"$PW\"}"
# Expect 200 with authenticated:true
```

`cookies.txt` is now your authenticated session for further curl probes.

---

## 8. Gates Before Any Commit

```bash
cd /Users/saranyaraj/Projects/github-repo/mp2.0

# Backend
uv run ruff check .                                                 # lint
uv run ruff format --check .                                        # format
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 \
  uv run python -m pytest engine/tests/ web/api/tests/ web/audit/tests/ -q
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 \
  uv run python web/manage.py makemigrations --check --dry-run

# Frontend
cd frontend
npm run typecheck                                                   # TS strict + noUncheckedIndexedAccess
npm run lint                                                        # eslint --max-warnings=0
npm run build
cd ..

# Vocab CI
scripts/check-vocab.sh

# Live e2e (requires backend + Vite running)
cd frontend
set -a && source ../.env && set +a
PLAYWRIGHT_BASE_URL=http://localhost:5173 \
  MP20_LOCAL_ADMIN_EMAIL=$MP20_LOCAL_ADMIN_EMAIL \
  MP20_LOCAL_ADMIN_PASSWORD=$MP20_LOCAL_ADMIN_PASSWORD \
  MP20_LOCAL_ANALYST_EMAIL=$MP20_LOCAL_ANALYST_EMAIL \
  MP20_LOCAL_ANALYST_PASSWORD=$MP20_LOCAL_ANALYST_PASSWORD \
  npx playwright test e2e/foundation.spec.ts --reporter=line
cd ..
```

**Expected at HEAD `ec98596`:** 319 pytest + 10/10 Playwright, all other gates green. If any gate is red BEFORE you change anything, environment is wrong — fix that first.

---

## 9. The Next Task — P0 #1: Extraction-Quality Hardening

**Detail:** see `~/.claude/plans/post-r7-extraction-hardening.md` (this file is referenced from there).

**Summary of sub-tasks** (in execution order):

### 9.1 Investigate the actual Bedrock failure modes

DO NOT FIX BLIND. The "did not return valid JSON" message is a generic catch-all. The actual response from Bedrock for the failing docs is what tells you whether to:
- Tweak the prompt (cheap)
- Switch to Bedrock structured-output mode (medium)
- Bypass Bedrock for tabular content with rule-based extraction (medium-high)
- Chunk-and-merge for large PDFs (medium-high)

**Steps:**

1. Add a temp instrumentation hook in [`extraction/llm.py`](../../extraction/llm.py) that, when `MP20_DEBUG_BEDROCK_RESPONSES=1` is set, writes raw Bedrock text to a debug log inside `MP20_SECURE_DATA_ROOT/<workspace_id>/debug/<doc_id>.log`. Never to stdout. Never to repo.
2. Re-run the 2 Niesner failing docs (the 6.2MB PDF, the failed xlsx) by calling `useRetryDocument` via API or directly running `process_document(document)` in a Django shell. Capture raw Bedrock response.
3. Read the response (manually, in Django shell — never paste into chat) and characterize the failure mode for each doc. Likely:
   - **Large PDF**: response truncated mid-JSON because output token budget exceeded
   - **xlsx**: Bedrock returns markdown table or prose preamble before JSON

### 9.2 Fix the xlsx path

Likely interventions, ordered by simplicity:

**Option A (cheapest): Tighter prompt for tabular content.** Detect xlsx in the calling code, use a prompt template that explicitly forbids markdown tables and demands minified JSON.

**Option B (medium): Pre-normalize xlsx before prompting.** Today [`extraction/parsers.py:73-95`](../../extraction/parsers.py) emits `[sheet Sheet1]\n[Sheet1!1] colA | colB | ...`. This is already structured. If Bedrock chokes on it, try emitting a tiny JSON pre-payload (`{"sheets": [{"name": ..., "rows": [...]}]}`) and prompt Bedrock to interpret structured data, not raw cells.

**Option C (most robust): Bypass Bedrock for xlsx entirely.** Use openpyxl + a rule-based fact extractor (advisor data in spreadsheets typically has known headers like "Account", "Balance", "Date of Birth"). Risk: misses unstructured content. Reward: deterministic, free, fast.

**Decision criteria:** if the actual xlsx files in advisor folders mostly look like structured tables (which is likely — they're projection spreadsheets), Option C is best. Validate the call by spot-checking 2-3 xlsx files from different folders.

### 9.3 Fix the large-PDF path

Most likely root cause: Bedrock response token budget exceeded → JSON truncates mid-output. Fixes:

**Option A: Reduce input → leave more output budget.** Lower `MP20_TEXT_EXTRACTION_MAX_CHARS` to 12000 OR add an explicit `max_output_tokens=4096` in the Bedrock call. Cheap, may sacrifice extraction completeness on long docs.

**Option B: Chunk-and-merge.** Split text at section boundaries (page breaks for native PDFs), call Bedrock per chunk, merge fact lists with deduplication. Medium effort, robust.

**Option C: Bedrock structured output mode.** If the Anthropic Bedrock SDK supports tool/function-calling with a JSON schema response, use that — eliminates JSON parsing entirely. Check [`extraction/llm.py`](../../extraction/llm.py) for current invocation.

**Recommendation:** start with A (cheapest, fastest to ship). If A still fails on the 6.2MB PDF, escalate to B.

### 9.4 Failure-code taxonomy

Today [`web/api/review_processing.py`](../../web/api/review_processing.py) `_fail_or_retry` sets `failure_code = exc.__class__.__name__`. That's `ValueError`, `OSError`, etc. — not actionable.

**Replace with structured codes:**

| Code | Cause | Advisor next-step |
|---|---|---|
| `bedrock_token_limit` | Response truncated mid-JSON | Retry with chunked extraction OR manual entry |
| `bedrock_non_json` | Response had no parseable JSON | Retry once, then manual entry |
| `bedrock_schema_mismatch` | JSON parsed but wrong shape | File a model-tuning ticket; manual entry |
| `parser_dependency_missing` | pymupdf / openpyxl / python-docx unavailable | Ops issue; not advisor-fixable |
| `secure_root_invalid` | `MP20_SECURE_DATA_ROOT` misconfig | Ops issue |
| `bedrock_unavailable` | Bedrock API error / 5xx | Wait + retry |
| `unsupported_extension` | File extension not in SUPPORTED_EXTENSIONS | Convert file format |

[`extraction/llm.py`](../../extraction/llm.py) raises `ValueError("Bedrock extraction did not return valid JSON.")` — replace with a typed exception (`BedrockNonJsonError(Exception)`) that the worker maps to `bedrock_non_json` failure code. Same pattern for token-limit detection.

### 9.5 UI surface for failure codes

[`frontend/src/modals/ReviewScreen.tsx`](../../frontend/src/modals/ReviewScreen.tsx) `ProcessingPanel` currently just renders `doc.status` as a chip. Update to render the `failure_code` with i18n-keyed advisor copy (`review.failure_code.bedrock_token_limit` etc.) and a context-aware retry/manual-entry CTA.

### 9.6 Validation

After each sub-task:

1. Re-run the 2 Niesner failing docs via the retry endpoint.
2. Verify the targeted failure mode is resolved.
3. Add a pytest test in [`web/api/tests/test_review_ingestion.py`](../../web/api/tests/test_review_ingestion.py) that mocks the failure (e.g., monkey-patch `extract_facts_for_document` to raise `BedrockNonJsonError`) and asserts the structured failure_code lands in `document.processing_metadata`.
4. Add a Playwright e2e check: failed-doc row shows the new copy + retry CTA.

### 9.7 Stop conditions

Demo is in 3 days. **Stop and re-plan with the user if:**

- Bedrock structured-output mode requires a major rewrite of [`extraction/llm.py`](../../extraction/llm.py)
- Chunk-and-merge logic is more than ~150 lines
- The xlsx rule-based path is missing more facts than the Bedrock path on the same files

In any of those cases the simpler sub-task (smaller chunk, shorter prompt) is the right demo-window choice.

---

## 10. Real-PII Discipline (LOAD-BEARING — DO NOT VIOLATE)

This is canon §11.8.3 and locked decisions #28 + #4. Violations have caused real incidents in past pilots.

### Rules

- **Never** copy real client raw text or fact values into chat, code comments, commit messages, memory files, CI logs, or screenshots that leave the secure root.
- **Never** quote a client's name, account number, dollar value, address, DOB, or any extracted field. Routing references (folder names) are documented in [§6](#6-real-pii-niesner-checkpoint-results-locked-decision-28b) only because the master plan file `~/.claude/plans/i-want-you-to-rosy-mccarthy.md` lists them as routing references.
- All real-PII testing happens through the authenticated browser-upload pipeline → `MP20_SECURE_DATA_ROOT`. Never `cp` real client files into the repo.
- Real-derived extraction routes through Bedrock in `ca-central-1` only. The current `bedrock_config_from_env(getattr(settings, "AWS_REGION", "ca-central-1"))` silently defaults — that is a Phase B item per [§13](#13-phase-b-follow-ups-not-blocking-pilot). Do not add region drift.
- When debugging Bedrock responses, write debug logs to `MP20_SECURE_DATA_ROOT/.../debug/`. Never to repo, stdout, or chat.
- Do not paste extracted facts into chat. If you need to characterize what's in the extraction, say "field X has Y candidates from Z sources" — never the values.

### Enforcement signals

- Pre-commit hook scrubs `.env` from staging.
- `extraction/llm.py` has a `data_origin` flag that fail-closes if Bedrock isn't configured for `real_derived`.
- Audit guards via Django model `save()` overrides + Postgres BEFORE UPDATE/DELETE triggers.
- Manual review per commit: scan diff for any field name + value pattern that could be PII.

### When in doubt

Ask the user. Do not proceed without explicit authorization for any new path that touches real client files.

---

## 11. Locked Decisions That Govern The Next Work

From the v36 master plan (`~/.claude/plans/i-want-you-to-rosy-mccarthy.md`). Search for the decision number in that file for full context.

Most relevant to extraction-quality hardening:

- **#2** — Server roundtrip on every interaction (no frontend math duplication).
- **#5** — Canon-aligned client-facing risk labels (Cautious / Conservative-balanced / Balanced / Balanced-growth / Growth-oriented). Retired the mockup labels.
- **#6** — Goal_50 internal-only; API surface returns canon 1-5 + descriptor + flags + derivation. Override flow operates on canon 1-5, never raw 0-50.
- **#11** — External-holdings risk-tolerance dampener deferred to Phase B (Fraser-confirmed formula needed). Projection-time penalty (μ × 0.85, σ × 1.15) IS implemented.
- **#14** — Vocab CI guard scope: `frontend/src/`, `web/api/serializers.py`, `web/api/management/commands/`, `web/api/migrations/`, `engine/fixtures/`, plus DRF view error/success messages. Forbidden: `\breallocation\b`, `\btransfer\b` (in goal-realignment context), `\bmove money\b`, retired risk labels.
- **#18** — P50 < 250ms / P99 < 1000ms budget. No backend cache layer; rely on TanStack Query (staleTime 5min, gcTime 30min). 300ms debounce on slider/text inputs.
- **#22a-e** — TS strict + noUncheckedIndexedAccess + zero `any`; mypy strict on engine + new preview endpoints; django-csp; self-host fonts; ESLint + Prettier + pre-commit.
- **#26** — Backend test depth: full request → DRF → engine → DB integration tests; OpenAPI-driven contract tests via `openapi-typescript`; query-count guards; Hypothesis property tests.
- **#28b** — R7 = first real-PII checkpoint with one client folder. **Done in this session via Niesner.** R10 = full sweep across all 7.
- **#29** — `react-hook-form` + zod for all forms.
- **#30** — Concurrent-edit safety via `transaction.atomic() + select_for_update()` on the workspace root before reading/writing dependent rows.
- **#34** — Local DB only; reset is pre-authorized via `scripts/reset-v2-dev.sh --yes`.
- **#37** — Audit-event regression suite — exactly one AuditEvent of expected kind per state-changing endpoint.
- **#39** — 5-minute Playwright smoke + R10 manual mockup-parity checklist + R10 DB state diff.

---

## 12. Code Pointers (Where Things Live)

### Engine (pure library; no framework imports)

- [`engine/risk_profile.py`](../../engine/risk_profile.py) — Q1-Q4 → tolerance/capacity/anchor → canon 1-5
- [`engine/goal_scoring.py`](../../engine/goal_scoring.py) — Goal_50 (internal) → canon 1-5 + descriptor + horizon cap + override resolution
- [`engine/projections.py`](../../engine/projections.py) — μ/σ from score, lognormal quantiles, drift penalty for current vs ideal
- [`engine/moves.py`](../../engine/moves.py) — Δ → buy/sell rebalance moves with $100 rounding
- [`engine/collapse.py`](../../engine/collapse.py) — building-block → whole-portfolio fund collapse suggestions (canon §4.3b)
- [`engine/sleeves.py`](../../engine/sleeves.py) — v36 8-fund universe + SLEEVE_REF_POINTS calibration table
- [`engine/frontier.py`](../../engine/frontier.py) — efficient frontier optimizer; Pareto filter (drift item #12 fix landed in `38670fc`)
- [`engine/schemas.py`](../../engine/schemas.py) — Pydantic models, schema_version `engine_output.link_first.v2`

### Web layer

- [`web/api/views.py`](../../web/api/views.py) — DRF views for review pipeline + preview endpoints + clients/CMA. Critical:
  - `ReviewWorkspaceUploadView` (multipart upload, per-file try/except)
  - `ReviewWorkspaceCommitView` (structured 400 with code + missing_approvals)
  - `ReviewWorkspaceStateView` (PATCH with approval invalidation)
  - `ReviewWorkspaceSectionApprovalView`
- [`web/api/review_processing.py`](../../web/api/review_processing.py) — worker entry, `claim_next_job` + `requeue_stale_jobs`, `process_document`, `reconcile_workspace`, `_fail_or_retry`
- [`web/api/review_state.py`](../../web/api/review_state.py) — `ENGINE_REQUIRED_SECTIONS`, `readiness_for_state`, `section_blockers`, `apply_state_patch`, `commit_reviewed_state`
- [`web/api/review_serializers.py`](../../web/api/review_serializers.py) — workspace + document + job serializers (now with `required_sections`)
- [`web/api/review_security.py`](../../web/api/review_security.py) — `secure_data_root` validation, `write_uploaded_file`, `assert_real_upload_backend_ready`
- [`web/api/review_redaction.py`](../../web/api/review_redaction.py) — evidence quote redaction, sensitive-ID hashing
- [`web/api/models.py`](../../web/api/models.py) — `ReviewWorkspace`, `ReviewDocument`, `ProcessingJob`, `SectionApproval`, `Household`, `PortfolioRun`, `AuditEvent`-related guards
- [`web/api/access.py`](../../web/api/access.py) — `team_households`, `linkable_households`, role helpers
- [`web/audit/`](../../web/audit/) — audit model + writer, append-only enforcement
- [`web/api/management/commands/process_review_queue.py`](../../web/api/management/commands/process_review_queue.py) — worker loop entrypoint

### Extraction

- [`extraction/parsers.py`](../../extraction/parsers.py) — PDF (pymupdf), DOCX (python-docx), XLSX (openpyxl), CSV, TXT
- [`extraction/classification.py`](../../extraction/classification.py) — adaptive classifier (heuristic + Bedrock fallback)
- [`extraction/llm.py`](../../extraction/llm.py) — Bedrock invocation, JSON repair, fail-closed for `real_derived`
- [`extraction/pipeline.py`](../../extraction/pipeline.py) — orchestration (parse → classify → extract facts)
- [`extraction/reconciliation.py`](../../extraction/reconciliation.py) — source-priority hierarchy (canon §11.4); `current_facts_by_field`, `conflicts_for_facts`, `field_section`, `advisor_label`
- [`extraction/schemas.py`](../../extraction/schemas.py) — `ParsedDocument`, `Fact`, `Confidence`, `SUPPORTED_EXTENSIONS`

### Frontend

- [`frontend/src/modals/DocDropOverlay.tsx`](../../frontend/src/modals/DocDropOverlay.tsx) — multi-file dropzone (FileList race fix here)
- [`frontend/src/modals/ReviewScreen.tsx`](../../frontend/src/modals/ReviewScreen.tsx) — workspace detail + readiness + approval + commit
- [`frontend/src/routes/ReviewRoute.tsx`](../../frontend/src/routes/ReviewRoute.tsx) — `/review` host
- [`frontend/src/lib/review.ts`](../../frontend/src/lib/review.ts) — TanStack Query hooks for the 11 review endpoints; types mirror DRF wire shape
- [`frontend/src/lib/api.ts`](../../frontend/src/lib/api.ts) — fetch wrapper (FormData detection, CSRF on unsafe methods, ApiError)
- [`frontend/src/lib/api-error.ts`](../../frontend/src/lib/api-error.ts) — `normalizeApiError` carries structured body + code
- [`frontend/src/i18n/en.json`](../../frontend/src/i18n/en.json) — all user-visible strings
- [`frontend/src/index.css`](../../frontend/src/index.css) — `@font-face` declarations (broken — see [§14.5](#145-self-hosted-fonts-broken))
- [`frontend/src/App.tsx`](../../frontend/src/App.tsx) — router + auth gate
- [`frontend/src/chrome/TopBar.tsx`](../../frontend/src/chrome/TopBar.tsx) — top bar
- [`frontend/vite.config.ts`](../../frontend/vite.config.ts) — `/api` + `/static` proxy to backend

### Tests

- [`engine/tests/`](../../engine/tests/) — 216 passing
- [`web/api/tests/test_review_ingestion.py`](../../web/api/tests/test_review_ingestion.py) — 38 tests including the 6 new in this session
- [`frontend/e2e/foundation.spec.ts`](../../frontend/e2e/foundation.spec.ts) — 10 R2-R7 e2e tests
- [`frontend/e2e/real-bundle-regression.spec.ts`](../../frontend/e2e/real-bundle-regression.spec.ts) — real-bundle path; manual run via `npm run e2e:real`

### Scripts

- [`scripts/reset-v2-dev.sh`](../../scripts/reset-v2-dev.sh) — full DB reset + reseed (locked #34 pre-authorized)
- [`scripts/test-python-postgres.sh`](../../scripts/test-python-postgres.sh) — Postgres-backed pytest harness
- [`scripts/check-vocab.sh`](../../scripts/check-vocab.sh) — vocab CI guard

---

## 13. Phase B Follow-Ups (Not Blocking Pilot)

These are real bugs / debt explicitly deferred until after the pilot ships:

1. **Auth/RBAC hardening** — MFA, session timeout, lockout, password reset, real role governance, pilot disclaimer surface. P0 #6.
2. **Audit immutability validation** — Postgres BEFORE UPDATE/DELETE triggers exist; e2e tests against them don't yet. P0 #7.
3. **Bedrock region fail-closed enforcement** — currently silently defaults to ca-central-1 if env unset. Should raise if `real_derived` and region != ca-central-1.
4. **Cross-class conflict advisor visibility** — source-priority drops the lower-class fact silently per canon §11.4 (correct), but advisor has no visibility into which source was dismissed. Add an advisory badge.
5. **Append-only commit** — `_merge_household_state` deletes-then-creates Person/Account/Goal rows. Atomic so no partial state, but violates canon append-only intent. Rewrite as upsert + explicit deletion audit events.
6. **Reconcile job race** — `enqueue_reconcile()` check-then-create not atomic; multiple parallel processed-document jobs can queue duplicates.
7. **External-holdings risk-tolerance dampener** — locked decision #11 deferred. Awaits Fraser-confirmed formula.
8. **Audit browser UI** — currently advisor sees timeline in workspace context; full browser UI is separate workstream.
9. **fr-CA i18n population** — locked #12 scaffold exists; `fr.json` is empty. Translation pass post-pilot.
10. **Self-hosted fonts download** — `frontend/public/fonts/*.woff2` empty; locked #22d's manual download step still TODO. Browser console spams "OTS parsing error" on each page load. UX is fine via fallback.
11. **Bundle splitting** — single 800KB chunk warning on `npm run build`. Code-splitting would help.
12. **R10 mockup-parity checklist** (`docs/agent/r10-mockup-parity.md` per locked #39b) — manual feature-by-feature walkthrough vs the v36 mockup.
13. **R10 DB state diff** — before+after snapshot of all 7 client folders post-commit; assert no orphan rows / broken FK / stale state.
14. **Disposal + retention tooling** — workspace-level + household-tree disposal, configurable retention, GDPR-style right-to-erasure.
15. **Performance + scale testing** — 50-doc workspace, 100MB upload, long-form PDFs, concurrent uploads.

---

## 14. Known Gotchas / Anti-Patterns From This Session

### 14.1 React 18 Strict Mode + live event references

The FileList ref bug ([§4.1](#41-live-filelist-ref-race-in-docdropoverlay-critical)) is part of a class: any handler that captures a *live* DOM/event reference and then calls a state setter with a deferred callback that re-reads the reference, while *also* synchronously mutating the source, is subject to this race. React 18 Strict Mode double-invokes effects and setter callbacks, magnifying the timing window.

**Pattern to avoid:**

```ts
const live = event.target.files;
setX((prev) => transform(live));   // deferred; live may mutate before this runs
event.target.value = "";           // mutates the live ref
```

**Pattern to use:**

```ts
const snapshot = Array.from(event.target.files);  // copy NOW
event.target.value = "";
setX((prev) => [...prev, ...snapshot]);
```

Same applies to `event.dataTransfer.files`, `event.dataTransfer.items`, mutation observer callbacks, and any other live DOM collection.

### 14.2 Frontend/backend enum drift

Status enums on the wire MUST match between TypeScript types and Django `TextChoices`. Today:

- `ProcessingJob.Status`: `queued | processing | completed | failed`
- `SectionApproval.Status`: `approved | approved_with_unknowns | needs_attention | not_ready_for_recommendation`
- `ReviewDocument.Status`: `uploaded | classified | text_extracted | ocr_required | facts_extracted | reconciled | extracted | failed | unsupported | skipped`
- `ReviewWorkspace.Status`: `draft | processing | review_ready | engine_ready | committed | archived`
- `ReviewWorkspace.DataOrigin`: `synthetic | real_derived`

Without `openapi-typescript` codegen (locked decision #26b — not yet shipped), these have to be hand-synchronized. The frontend types live in [`frontend/src/lib/review.ts`](../../frontend/src/lib/review.ts).

### 14.3 Server-driven required-sections list

[`web/api/review_state.py:47`](../../web/api/review_state.py) `ENGINE_REQUIRED_SECTIONS` is the canonical list. Frontend reads it from `workspace.required_sections` (added to ReviewWorkspaceSerializer in commit `4643bb5`). Do not hardcode this list on the frontend ever again.

### 14.4 curl filename-with-comma bug

curl's `-F file=@...` parser interprets commas as field separators. Filenames like `"Alternate _ Sell home, keep vacation..."` fail with curl exit 26. Browser FormData handles this correctly; only operational smoke harnesses are affected. Worth a note in the README. NOT a server bug.

### 14.5 Self-hosted fonts broken

`frontend/public/fonts/*.woff2` files were never downloaded (locked #22d's manual step). Browser console spams `OTS parsing error: invalid sfntVersion` on every page load. UI renders fine via system fallback. Cosmetic only.

### 14.6 Stale workspace queue accumulation

Without periodic cleanup, ProcessingJobs from prior sessions accumulate in the local DB (54 stale jobs were found at session start). New uploads queue at the back of FIFO. The only safe cleanup paths:

1. Full reset via `scripts/reset-v2-dev.sh --yes` (locked #34 pre-authorizes)
2. Drain by running `process_review_queue` (real_derived hits Bedrock, costs $)
3. Selective admin cancel — requires explicit user authorization per session

Do not bulk-modify ProcessingJob rows from prior sessions without authorization.

### 14.7 Backend Docker container bakes deps

`mp20-backend` Docker image bakes the Python dep set at build time. Volume mount means code reloads automatically, but `pyproject.toml` changes require `docker compose build backend`. Easier path during active dev: run backend on host (see [§7](#7-how-to-run-the-stack)).

### 14.8 Vite HMR can desync from disk

Multi-hour Vite HMR runs sometimes serve stale module versions even after disk changes. If you suspect HMR is wrong (e.g., a test that recently passed now fails inexplicably), restart Vite cleanly. The user must approve killing the Vite PID — see [§7](#7-how-to-run-the-stack) for the start command.

### 14.9 Bedrock config probe AttributeError

The `BedrockConfig` returned by `bedrock_config_from_env()` does not have `.region` or `.model_id` attributes — the actual fields are different. Verify `bedrock OK` print without dereferencing fields blindly:

```python
try:
    cfg = bedrock_config_from_env('ca-central-1')
    print('bedrock OK')
except Exception as e:
    print(f'FAIL: {type(e).__name__}: {e}')
```

### 14.10 The R7 e2e spec was a flake, not a guarantee

The 10/10 Playwright pass at the end of the previous session was misleading — the FileList race could have lost on any run. The new assertion `await expect(page.getByText(/1 FILE READY TO UPLOAD/i)).toBeVisible()` makes the file-attach behavior deterministic. Apply the same pattern (assert intermediate state explicitly) for any new pipeline step.

---

## 15. What "Production-Grade for Limited Pilot" Means In This Codebase

Per the user's 2026-05-01 ask, before demo + release the pipeline must:

- Upload reliably for synthetic AND real-derived data origins. ✅ (post FileList fix)
- Process every doc through the worker without stuck-state risk. ✅ (post stale-job fix)
- Provide actionable failure UX when extraction can't recover. ❌ (P0 #1 sub-tasks)
- Surface conflicts to the advisor with resolution affordance. ❌ (P0 #2)
- Allow manual entry when extraction is impossible for a doc. ❌ (P0 #3)
- Pass a real-browser smoke playbook before each release. ❌ (P0 #4)
- Not ship contract drift between FE/BE. ❌ (P0 #5)
- Pass the full 7-folder real-PII sweep without manual intervention. ❌ (P0 #8 / R10)

P0 items #6 (auth) and #7 (audit immutability) are deferred per user.

The closer you stay to "every doc, every advisor, every time" as the bar — and the further you stay from "happy path correctness" as a substitute for it — the better this ships.

---

## 16. Open Questions / Decisions Needed From User

When the next session starts, confirm:

1. **xlsx fix preference (A/B/C from [§9.2](#92-fix-the-xlsx-path)):** prompt tweak / pre-normalize / rule-based bypass?
2. **Large-PDF fix preference (A/B/C from [§9.3](#93-fix-the-large-pdf-path)):** smaller input window / chunk-and-merge / structured output?
3. **Conflict-resolution UI scope for P0 #2:** minimum viable (single accept/reject per conflict) vs full mockup parity (rationale capture + evidence tooltips)?
4. **R10 sweep timing:** day 5 of the 1-week window (after P0 #1-#5)? Or run sweep earlier in parallel with UI work?
5. **Demo content:** which client folder for the live CEO demo? Recommend one of the smaller folders (Seltzer, Weryha) to minimize Bedrock latency on stage. Niesner has known bugs that #1 should fix.
6. **Push remote:** `feature/ux-rebuild` is 4 commits ahead of origin. Push at any milestone? User has not yet authorized push.

---

## 17. Memory + Documentation Index

### Repo-committed (durable)

- `docs/agent/post-r7-handoff-2026-05-01.md` — **THIS FILE** (the master)
- `docs/agent/session-state.md` — live phase status (always reflect HEAD)
- `docs/agent/handoff-log.md` — append-only chronological dated entries
- `docs/agent/decisions.md` — distilled implementation decisions from canon
- `docs/agent/open-questions.md` — tracked unresolved decisions + drift items

### User-local (NOT in repo)

- `~/.claude/plans/i-want-you-to-rosy-mccarthy.md` — v36 master rewrite plan with 39 locked decisions across R0-R10
- `~/.claude/plans/post-r7-extraction-hardening.md` — **the immediate action plan for P0 #1 (this session)**
- `~/.claude/projects/-Users-saranyaraj-Projects-github-repo-mp2-0/memory/MEMORY.md` — auto-loaded project memory index
- Memory files referenced from MEMORY.md (per-phase patterns, current state, drift signals)

### External (per memory `project_v36_rewrite.md`)

- `MP2.0_Working_Canon.md` (canon v2.8) at repo root — authoritative product/strategy/architecture
- `/Users/saranyaraj/Downloads/MP2_Advisor_Console_v36.html` — visual design source (16,320 lines)
- `/Users/saranyaraj/Documents/MP2.0_Clients/` — real client folders (PII; outside repo, never copy contents)

---

## 18. Final Notes For The Next Session

- Read this file first. Do not skip ahead.
- Run [§7 (stack startup)](#7-how-to-run-the-stack) and [§8 (gates)](#8-gates-before-any-commit) before ANY code change. If gates aren't green at HEAD `ec98596` BEFORE you change anything, the environment is wrong — fix that first.
- The user is more frustrated than usual. They burned a session believing the pipeline worked, and it didn't. Be candid about uncertainty; don't overclaim test coverage; demand verifiable evidence per change.
- When in doubt about scope, choose the smaller, more defensible intervention. The 3-day demo fuse means a robust 80% solution beats a polished 100% solution that doesn't ship.
- Real-PII discipline is non-negotiable. If a step might violate it, ask before proceeding.
- Update this file at the end of each session — replace [§3 "Where We Are At Exactly"](#3-where-we-are-at-exactly), append a new entry to handoff-log, and update memory if state changed materially.

If you are stuck:

1. Re-read [§4 (bugs found and fixed)](#4-bugs-found-and-fixed-this-session) and [§14 (gotchas)](#14-known-gotchas--anti-patterns-from-this-session). The bug class probably matches one of these.
2. Check the linked file at the file:line you're touching — gotchas live close to the code that has them.
3. Use the existing test patterns ([§9.6 validation](#96-validation)) before inventing new ones.
4. Ask the user. They prefer a clarifying question over a wrong execution.

---
*Document version: 2026-05-01. Update when state changes.*
