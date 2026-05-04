# Next-Session Starter Prompt

**Authored:** 2026-05-03 (HEAD `b14a199`, branch `feature/ux-rebuild`)
**Audience:** the next Claude Code session — fresh agent, no carry-over context
**Purpose:** bring you up to speed on MP2.0's state, vision, and the work that lands Mon-Wed 2026-05-04 → 2026-05-08

This prompt is **load-bearing**. Read it carefully. Three independent
"Is everything done?" challenges from the user during the prior
session each surfaced a real production bug that automated gates
missed. Your default posture is honest audit, not confident
restatement.

---

## 1. Five-second context

You are continuing the **MP2.0 limited-beta pilot release** for
Steadyhand Investment Counsel. MP2.0 is an advisor-facing console
that:

- Replaces manual intake with **AI document extraction** (Bedrock
  ca-central-1, tool-use API, Sonnet 4.6) feeding a structured
  reviewed-state.
- Surfaces **multi-source conflicts** to the advisor for resolution
  before commit.
- Drives an **engine-as-library** portfolio optimizer that produces
  goal-account-link recommendations (link-first contract).
- Captures every advisor decision in an **append-only audit trail**.

You are the technical lead. The user is **Saranyaraj Rajendran**.
Collaborators: Fraser (product), Lori (compliance/vocab), Amitha
(canon), Raj (ops). Pilot is **3-5 Steadyhand advisors on real
client data** for ~2 weeks beginning 2026-05-08.

**Hard deadlines:**
- Demo to CEO + CPO: **Mon 2026-05-04**
- Limited-beta pilot release: **Mon 2026-05-08**

**Do NOT push during this session.** The user pushes Mon morning
per locked direction. Branch is `feature/ux-rebuild`, ahead of
`origin` by **16 commits past the prior starter-prompt baseline
(`8bb96c0`)** + 92 commits past `main`.

---

## 2. Pre-flight — run these before any code change

```bash
cd /Users/saranyaraj/Projects/github-repo/mp2.0

# 1. Branch + HEAD
git status --short --branch          # expect: feature/ux-rebuild, clean
git log --oneline -5
# Expected newest:
#   b14a199 visual-verification: full-checklist alignment + FeedbackModal Esc fix
#   efbe58d e2e: comprehensive visual-verification spec (17 tests, 17/17 pass)
#   95af4b5 docs: handoff log addendum for the verification-pass gaps
#   b887b18 test: DocDropOverlay StrictMode tests pin the admitFiles fix
#   bca0112 fix: DocDropOverlay StrictMode-double-update + foundation e2e + R10 nested-key tests

git tag -l "v0.1.0*"                 # expect: v0.1.0-pilot

# 2. Backend gate suite (~2 min)
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 \
  uv run python -m pytest \
    scripts/demo-prep/test_r10_sweep.py \
    engine/tests/ extraction/tests/ web/api/tests/ web/audit/tests/ \
    --tb=no -p no:warnings --benchmark-disable
# expect: 854 passed, 7 skipped

uv run ruff check .
uv run ruff format --check .
bash scripts/check-pii-leaks.sh      # expect: PII grep guard: OK
bash scripts/check-vocab.sh          # expect: vocab CI: OK
bash scripts/check-openapi-codegen.sh  # expect: OpenAPI codegen gate: OK
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 \
  uv run python web/manage.py makemigrations --check --dry-run

# 3. Frontend gates (~30s)
cd frontend
npm run typecheck && npm run lint && npm run build && npm run test:unit
# expect: typecheck/lint/build clean; 82 Vitest passing in 13 files
cd ..

# 4. Live stack (Docker)
docker compose ps                    # expect: backend + db running
curl -s -o /dev/null -w "backend: %{http_code}\n" http://localhost:8000/api/session/
curl -s -o /dev/null -w "frontend: %{http_code}\n" http://localhost:5173/
# expect: 200 / 200

# 5. Playwright e2e (foundation + cross-browser + visual; ~2 min)
cd frontend
set -a && source ../.env && set +a
PLAYWRIGHT_BASE_URL=http://localhost:5173 \
  MP20_LOCAL_ADMIN_PASSWORD=change-this-local-password \
  npx playwright test --project=chromium e2e/foundation.spec.ts e2e/visual-verification.spec.ts --reporter=line
# expect: 13 + 24 = 37 passed
PLAYWRIGHT_BASE_URL=http://localhost:5173 \
  MP20_LOCAL_ADMIN_PASSWORD=change-this-local-password \
  npx playwright test --project=webkit --project=firefox e2e/cross-browser-smoke.spec.ts --reporter=line
# expect: 10 passed
cd ..

# 6. Env + secure root
echo "MP20_SECURE_DATA_ROOT=$MP20_SECURE_DATA_ROOT"
ls /Users/saranyaraj/Documents/MP2.0_Clients/ | head -8
# expect: secure root resolvable; 7 client folders present
```

**If ANY check is red BEFORE you change anything, halt and ping
the user.** Environment is wrong; do not "fix" it under autopilot.

Total tests when all green: **983 passing** = 854 backend + 82
Vitest + 13 foundation + 10 cross-browser + 24 visual.

---

## 3. Read in this order

The docs are the source of truth. If anything in this prompt
conflicts with them, **the docs win.**

### Tier 0 — auto-loaded by every session (already in your context)

1. `CLAUDE.md` — project rules; non-negotiable architecture rules
   live there.
2. `~/.claude/projects/-Users-saranyaraj-Projects-github-repo-mp2-0/memory/MEMORY.md`
   — index of project memories; auto-read on session start.

### Tier 1 — load-bearing for ANY work this session

3. **`docs/agent/handoff-log.md`** — read the **last 5 entries**
   (most recent first). The verification-pass entry at the
   bottom captures the StrictMode regression + cost-key bug + 3
   rounds of pushback. **Read this first.**
4. **`docs/agent/sub-sessions-8-11-plan.md`** — single roadmap;
   sub-session #8/9/10/11 statuses + actuals + exit criteria.
5. **`docs/agent/production-quality-bar.md`** — the durable
   quality bar. Per-surface checklist + UX inspirations + test
   coverage matrix + anti-patterns.

### Tier 2 — required for advisor-facing work

6. `docs/agent/ux-spec.md` — UX dimensions taxonomy A-M, design
   principles, canonical flows, decision log.
7. `docs/agent/design-system.md` — tokens + component inventory
   + patterns + ErrorBoundary architecture + focus-management
   patterns + mutation-hook patterns.

### Tier 3 — required for backend / pipeline / pilot work

8. `docs/agent/extraction-audit.md` — extraction subsystem audit
   (addressed + open + Phase B items).
9. `docs/agent/phase9-fact-quality-iteration.md` — Phase 9
   layered design + the multi-tool architecture (Phase 9.4) that
   remains post-pilot work.
10. `docs/agent/r10-sweep-results-2026-05-03.md` — full 7-folder
    real-PII sweep results: 56/56 reconciled, 1,122 facts,
    $0.8639 spend.
11. `docs/agent/bedrock-spend-2026-05-03.md` — append-only spend
    ledger. Add an entry for any new Bedrock canary you run.

### Tier 4 — pilot operations + rollback

12. `docs/agent/pilot-rollback.md` — Sev-1 rollback procedure
    (kill-switch, code revert, DB recovery).
13. `docs/agent/pilot-success-metrics.md` — pilot KPIs + GA
    criteria + off-ramp conditions.
14. `docs/agent/demo-restore-runbook.md` — Mon-morning demo
    restore procedure.
15. `docs/agent/post-pilot-improvements.md` — append-only
    deferred backlog (re-edit flow v2, Phase 9.4 multi-tool,
    demo-restore --dry-run, etc.).

### Tier 5 — canon + master plan

16. `MP2.0_Working_Canon.md` — product / strategy / regulatory /
    architecture canon. Reference §6.3a + §16 (vocabulary),
    §9.4.2 (engine purity), §9.4.5 (AI-numbers rule), §11.4
    (source-priority), §11.8 (audit append-only), §11.8.3
    (real-PII discipline).
17. `~/.claude/plans/you-are-continuing-a-playful-hammock.md`
    — master multi-sub-session plan with 50+ user-locked
    decisions. Skim only when a decision needs verification.

---

## 4. Vision + long-term intent

MP2.0 is the third attempt at a Steadyhand advisor console. The
previous two attempts failed because they tried to **automate the
advisor away** instead of **supporting the advisor's judgment**.
MP2.0's design principle is the inverse: **AI extracts; advisor
reviews; engine optimizes; audit captures.** Every code decision
should reinforce that hierarchy.

### The five-year arc

| Phase | Surface | Status |
|---|---|---|
| 0 | Synthetic-data scaffold | shipped 2026-04-28 |
| A | Limited-beta pilot (3-5 advisors, real PII) | **launches 2026-05-08** |
| B | Steadyhand-wide rollout (~30 advisors) | post-pilot |
| C | Multi-tenant (Purpose-affiliated firms) | 2027 |
| D | Engine-as-service (broker-adjacent) | 2028+ |

Phase A is what you are shipping. Everything in this codebase is
tuned for **3-5 advisors on real PII** — not for scale. Quality,
audit-trail integrity, and advisor productivity dominate cost +
latency optimizations. When in doubt, **slow + correct + auditable**
beats fast + clever.

### What MP2.0 explicitly is NOT

- Not a robo-advisor. The advisor commits every household.
- Not a CRM. Croesus + Steadyhand's existing systems remain SoR.
- Not an extraction-as-a-service product. The extraction is a
  back-of-house pipeline; the advisor never sees raw model
  output.
- Not a marketplace. One firm, one engine, one set of CMA inputs
  per environment.

### Engine-is-library (canon §9.4.2 — non-negotiable)

`engine/` must not import Django, DRF, `web/`, `extraction/`, or
`integrations/`. Web code translates DB models into
`engine.schemas` Pydantic models at the boundary. The engine is
testable headless with no Postgres connection. Violating this
breaks Phase B+ (engine-as-service) and is a hard refactor
multiplier.

### Real-PII discipline (canon §11.8.3 — non-negotiable)

The pilot is the first time MP2.0 touches real client data. Every
code decision around extraction / persistence / logging /
committed docs must honor:

- Real-derived extraction routes through Bedrock **ca-central-1**.
  Anthropic direct is synthetic-only.
- **Never** quote real client content in code, commits, memory,
  chat, or any logs that escape `MP20_SECURE_DATA_ROOT`. Use
  structural counts only.
- `str(exc)` NEVER appears in DB columns / API response bodies /
  audit metadata. Use `web/api/error_codes.py:safe_response_payload`
  + `safe_audit_metadata` instead.
- Folder names in `MP2.0_Clients/<surname>/` are operator-typed
  paths, not extracted content. Existing spend-ledger entries
  use surnames as stable identifiers (matches user practice). For
  externally-shareable artefacts, use the
  `--anonymize-folders` flag in `scripts/demo-prep/r10_sweep.py`.

---

## 5. What shipped — multi-sub-session run #8 → #11 + deferred-work follow-up

The 16 commits past `8bb96c0` ship the work below. Read the
referenced files when touching adjacent surfaces.

### Sub-session #8 — OCR/vision foundation (commits `2d61cc0` + `735ecae`)

**Problem:** Croesus CRM exports many KYC / DOB / address pages as
image-only PDFs. The text-only path returned 0 facts, forcing
advisors to manually type 30+ facts per doc.

**Fix:**
- `extraction/parsers.py:is_likely_image_pdf` — dual-signal
  detection (`method=="ocr_required"` OR text-page ratio < 0.5
  OR avg chars/page < 50).
- `extraction/llm.py:extract_pdf_facts_with_bedrock_native` —
  native PDF document block via `AnthropicBedrock` SDK
  (InvokeModel API; **NOT Converse** — Converse drops to
  text-only without forced citations).
- `extraction/llm.py:estimate_bedrock_cost_usd` — prefix-matched
  pricing helper (Sonnet 4.6 / Opus 4.6/4.7 / Haiku 4.5).
- `extraction/pipeline.py` — dispatcher: image-likely PDF →
  native; non-PDF image → image-blocks fallback; text-rich → text.

**Real-PII canary (sub-session #8.5):** 5 Niesner image-PDFs that
previously returned 0 facts now extract 4-13 facts each.
$0.1391 / 22.8K input + 4.7K output tokens / 53s wall-clock.

### Sub-session #9 — Phase 9 fact-quality recovery (commit `8af7104`)

**Problem:** Phase 4 tool-use migration eliminated hallucinations
(canon §9.4.5 quality WIN) at the cost of total fact count
(Seltzer 168 → 94, −44%).

**Fix (layered iteration):**
- 9.1 — `extraction/prompts/base.py:NO_FABRICATION_BLOCK` (v3):
  STRONG-signal section ("EXTRACT eagerly when…") + SOFT-inference
  section. Forbidden-inversion list preserved.
- 9.2 — All per-type PROMPT_VERSION strings bumped to `v3_tooluse`.
- 9.3 — `extraction/validation.py:filter_inferred_facts_by_evidence`
  drops inferred facts whose evidence_quote does not have ≥60%
  longest-common-substring overlap with the source.
- 9.4 — Re-canary: Seltzer 94 → 95 (+1pp). **Below the 20pp
  aspirational target** but structural quality preserved (zero
  defaulted facts, zero hallucinated paths, zero evidence drops).

**Phase 9.4 multi-tool architecture is post-pilot.** See
`docs/agent/phase9-fact-quality-iteration.md` for the design.
Pilot week-1 commit-rate + manual-entry-rate decide whether to
ship it.

### Sub-session #10 — Tier 1 advisor friction (commit `35a7eba`)

Six items shipped across `frontend/` + `web/api/`:

1. **Inline edit polish + canonical-field autocomplete**
   (`frontend/src/lib/canonical-fields.ts` NEW — 35-entry
   schema-driven map). DocDetailPanel `FactEditForm` renders
   `<input type="date">` for DOB paths, `<input type="number">`
   with bounds for currency/score fields, `<select>` for enums.
2. **Progress indicator + ETA in ProcessingPanel** —
   `frontend/src/modals/ReviewScreen.tsx` shows "Doc N of total —
   extracting M (~Xs remaining)". 15s/doc heuristic from
   sub-session #8.5 + #9 timings.
3. **Holistic commit preview** — `StatePeekPanel` replaced its
   1200-char JSON dump with a 6-row structured "About to commit"
   summary (people / accounts / goals / links / risk / household).
4. **Demo-state restore runbook** —
   `docs/agent/demo-restore-runbook.md` (sandbox refused the
   destructive `compose down -v`; runbook is for the operator).
5. **Soft-undo for committed workspaces** —
   `web/api/views.py:ReviewWorkspaceUncommitView`. Atomic +
   `select_for_update(of=("self",))`. Cascade-deletes Household +
   Person/Account/Goal/PortfolioRun. Frees the deterministic
   external_id slot for re-commit. Audit event with
   `previous_household_id`.
6. **Re-edit flow v2 deferred** —
   `docs/agent/post-pilot-improvements.md` captures the
   PATCH-from-household design.

**Locked stop-and-ask answered:** soft-undo v1 for pilot;
re-edit flow v2 post-pilot.

### Sub-session #11 first pass — Tier 2 high-leverage (commit `af627b3`)

- **Audit timeline visible to advisor** —
  `web/api/views.py:ReviewWorkspaceAuditTimelineView` +
  `frontend/src/lib/review.ts:useAuditTimeline` +
  `AuditTimelinePanel` in ReviewScreen right rail.
  i18n-mapped action labels (e.g. `review_state_committed` →
  "Committed to household").
- **Synthetic data-origin badge** — ReviewScreen header shows a
  "Synthetic" chip (text + visual cue, NOT color-only) when
  `workspace.data_origin === "synthetic"`. Advisors don't
  mistake a dev workspace for real-PII committed.
- **Missing-field guidance** — verified existing backend
  `readiness_for_state` already produces specific per-field
  blocker labels; MissingPanel renders them.

### Sub-session #11 deferred follow-up (commits `f86dcfd`, `cb408cc`, `5cb91c0`, `1428555`, `df6363f`, `2bd77d3`, `bca0112`, `b887b18`, `95af4b5`, `efbe58d`, `b14a199`)

**R10 7-folder Playwright sweep automation** —
`scripts/demo-prep/r10_sweep.py` (~570 lines + 21 unit tests):
- Worker subprocess wrapped in try/finally (caught the worker-leak
  during the live run review).
- Per-doc + per-folder cost ceiling enforced INSIDE polling loop.
- `--anonymize-folders` flag substitutes folder names with
  `client_<sha256-prefix>` ids in committed docs; surname-to-id
  map only inside `MP20_SECURE_DATA_ROOT/_debug/`.
- `--force-append` overrides the per-day idempotency guard
  (`_today_section_already_present`).
- Cleanup-on-failure: orphaned workspaces best-effort DELETE'd
  via the new `ReviewWorkspaceDetailView.delete` endpoint.

**Cross-browser smoke** —
`frontend/e2e/cross-browser-smoke.spec.ts` (5 tests). Playwright
config gains webkit + firefox projects. Filters known noise
(Firefox font sanitizer, ResizeObserver, ERR_ABORTED). Both
browsers 5/5 pass.

**Tier 3 polish — 4 bundles via parallel subagents:**
- **Bundle A** — ClientPicker debounce + empty-state CTA;
  AccountRoute / GoalRoute skeleton + Retry; Intl en-CA
  currency via `formatCurrencyCAD` + `formatDateLong` helpers.
- **Bundle B** — DocDropOverlay strengthened drop-zone (4px
  dashed + accent ring); Wizard 5-step progress indicator;
  explicit "Save as draft" button + timestamped resume banner.
- **Bundle C** — ConflictPanel visual progression states
  (unresolved → resolving → resolved; mutation-hook driven;
  no new state machinery); resolved-cards collapsible group
  with localStorage persistence.
- **Bundle D** — RealignModal "What's about to change" preview;
  Radix tooltip wrapper at `frontend/src/components/ui/tooltip.tsx`
  (300ms delayDuration); Truncated component at
  `frontend/src/components/Truncated.tsx`.

**Workspace DELETE endpoint** —
`web/api/views.py:ReviewWorkspaceDetailView.delete`. Required for
the sweep cleanup-on-failure path; also useful for ops cleanup of
abandoned workspaces. Refuses COMMITTED workspaces (returns 409
with code `committed_workspace_not_deletable`).

**Live R10 7-folder sweep results** (committed `2bd77d3` after
recompute):
- 56/56 docs reconciled (100%)
- 1,122 ExtractedFact rows
- 117 conflicts surfaced
- $0.8639 total spend (151K input + 27K output tokens)
- Per-folder cost $0.0851-$0.1484 (max single-doc cost ~$0.04)
- Zero evidence-quote drops; zero defaulted facts; zero
  hallucinated paths
- Path mix: 27 text + 29 vision_native_pdf
- All 7 sweep workspaces left in `review_ready` (NOT
  auto-committed; demo state preserved)

**Three rounds of "Is everything done?" caught real bugs:**
- Round 1 → R10 sweep cost-key bug (mocks were flat-shape;
  pipeline stores nested under `processing_metadata.extraction.*`).
  Fix: `_doc_extraction_meta` helper + 6 nested-key regression
  tests.
- Round 2 → DocDropOverlay StrictMode-double-update regression
  (Tier 3 bundle B mutated closure-captured arrays inside
  `setFiles((prev) => …)` → 1 file became 2 in dev). Same
  FileList-race class from R7 history. Fix: dedup OUTSIDE the
  updater; 3 Vitest cases mount inside `<StrictMode>`. Plus 2
  stale e2e selectors fixed.
- Round 3 → No DocDropOverlay test existed; FeedbackModal Esc
  handler missing. Fix: `frontend/src/modals/__tests__/DocDropOverlay.test.tsx`
  (3 tests) + `useEffect`-bound Esc handler in FeedbackButton.

**Visual verification spec** —
`frontend/e2e/visual-verification.spec.ts` (24 tests, 24/24 pass
on real Chrome). 24 screenshots captured. Covers every
advisor-facing surface across sub-sessions #1-#11.

---

## 6. Locked decisions / canon constraints (non-negotiable)

| ID | Decision | File:line where it bites |
|---|---|---|
| canon §9.4.2 | Engine-is-library; no Django imports in `engine/` | `engine/optimize.py` etc. |
| canon §9.4.5 | AI never invents financial numbers / names / dates; `derivation_method="defaulted"` is forbidden | `extraction/llm.py:_facts_from_tool_use_response` |
| canon §11.4 | Source-priority: SoR > structured > note-derived; cross-class silent; same-class surfaces conflicts; advisor override (FactOverride) is highest | `extraction/reconciliation.py` |
| canon §11.8 | Audit events are append-only via DB triggers + model `save()` guards | `web/audit/models.py:AuditEvent.save` |
| canon §11.8.3 | Real-PII never quoted in committed artefacts; structural counts only | applies everywhere |
| locked #18 | API perf budget P50 < 250ms / P99 < 1000ms | `web/api/tests/test_perf_budgets.py` |
| locked #30 | Workspace `select_for_update()` before reading/writing dependent rows | new endpoints in `web/api/views.py` |
| locked #34 | `scripts/reset-v2-dev.sh --yes` pre-authorized; nothing else bulk-modifies DB | reset script |
| locked #37 | Exactly one AuditEvent of expected kind per state-changing endpoint | every view that mutates state |
| locked #38 | Real-PII pilot is authorized; defense-in-depth regime governs | `extraction/llm.py:_bedrock_client` |
| op-locked | No push during the session; user pushes Mon morning | git push |

**Append-only models** (verify `save()` raises on existing pk):
`HouseholdSnapshot`, `FactOverride`, `PortfolioRunEvent`,
`AuditEvent`.

---

## 7. Patterns to reuse (don't reinvent)

### Backend

- **PII-safe error helpers** — `web/api/error_codes.py`:
  `failure_code_for_exc`, `safe_exception_summary`,
  `safe_response_payload(exc, **extra)`,
  `safe_audit_metadata(exc, **extra)`,
  `friendly_message_for_code`. Use these instead of `str(exc)`.
- **Atomic state-changing endpoint pattern:**
  ```python
  @transaction.atomic
  def post(self, request, ...):
      workspace = (
          _review_workspace_queryset()
          .select_for_update(of=("self",))   # CRITICAL — see §8 anti-patterns
          .filter(external_id=..., pk__in=team_workspaces(request.user).values("pk"))
          .first()
      )
      if workspace is None:
          return Response(..., status=404)
      # ... mutate inside the atomic block ...
      record_event(action=..., entity_type=..., entity_id=..., actor=..., metadata=...)
  ```
  See `ReviewWorkspaceConflictResolveView`, `ReviewWorkspaceUncommitView`,
  `ReviewWorkspaceFactOverrideView` for templates.
- **Append-only invariant** — mirror the pattern in
  `HouseholdSnapshot.save`: raise on existing pk; never UPDATE
  state-changing rows.
- **Audit-event regression guard** — every state-changing
  endpoint test asserts `AuditEvent.objects.filter(action=...).count() == pre + 1`.

### Extraction

- **Prompt module dispatcher** — `extraction/prompts/__init__.py:build_prompt_for(document_type, classification)`
  routes to per-type modules (kyc / statement / meeting_note /
  planning / generic). Multi-schema-sweep classifications route to
  `generic.build_prompt`.
- **Bedrock tool-use call shape:**
  ```python
  client.messages.create(
      model=config.model,
      max_tokens=_bedrock_max_tokens(),
      tools=[FACT_EXTRACTION_TOOL],
      tool_choice={"type": "tool", "name": "fact_extraction"},
      messages=[{"role": "user", "content": prompt_or_blocks}],
  )
  ```
- **Cost-tracking metadata** — every Bedrock call writes
  `processing_metadata.extraction.{bedrock_input_tokens,
  bedrock_output_tokens, bedrock_cost_estimate_usd, extraction_path,
  bedrock_model}` per
  `extraction/llm.py:extract_pdf_facts_with_bedrock_native`.
  **Note the nested key path** — see §8 anti-patterns for the
  cost-key bug history.
- **Phase 9 evidence validator** —
  `extraction/validation.py:filter_inferred_facts_by_evidence(facts, parsed_text)`
  returns `(kept, dropped)` based on 60% LCS overlap. Inferred
  facts only; extracted facts pass through.

### Frontend

- **Mutation hook patterns** — see `docs/agent/design-system.md`
  "Mutation Hook Patterns". TanStack Query `useMutation` with
  `onSuccess: invalidateQueries(reviewWorkspaceKey(workspaceId))`
  + structured error → toast.
- **Schema-driven inputs** —
  `frontend/src/lib/canonical-fields.ts:getCanonicalFieldShape(field_path)`
  returns `{kind: "date" | "number" | "enum" | "text", min?, max?,
  step?, enum_options?}`. Use it for any new field-edit affordance.
- **Modal a11y pattern** —
  ```tsx
  useEffect(() => {
      function onKeyDown(event: KeyboardEvent) {
          if (event.key === "Escape") {
              event.stopPropagation();
              onClose();
          }
      }
      window.addEventListener("keydown", onKeyDown);
      return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);
  ```
  See `DocDetailPanel.tsx` + `FeedbackButton.tsx` for templates.
- **Focus management** — `useEffect + ref` for imperative focus
  (NOT `autoFocus` attr; jsx-a11y/no-autofocus rule fires).
- **Tooltip + truncation** — wrap long text in
  `<Truncated text={...} max={80} />` from
  `frontend/src/components/Truncated.tsx`. Default 300ms hover
  delay via the Radix wrapper.
- **OpenAPI codegen** — backend serializer changes require
  `cd frontend && npm run codegen` to regenerate
  `frontend/src/lib/api-types.ts`. CI gate
  `scripts/check-openapi-codegen.sh` enforces drift.

### R10 sweep automation

- **Anonymization** — `_maybe_anonymize(folders, enabled=True)`
  returns `(anon_list, mapping)` + writes the surname-to-id map to
  `MP20_SECURE_DATA_ROOT/_debug/r10_sweep_anon_map_<ts>.txt`. Map
  never enters the repo.
- **Stop conditions** — per-doc cost > $0.50 OR per-folder cost
  > $10 OR wall-clock > 30 min → halt + terminate worker + log.
- **Idempotency** — `_today_section_already_present` guards
  doc/ledger appends; `--force-append` overrides.

---

## 8. Anti-patterns burned in (the bug + the lesson)

Each item below cost real time during the prior session. **Do not
repeat them.**

### 1. `setState((prev) => mutate-closure-array)` — StrictMode-double-update class

**Bug:** Tier 3 bundle B's `admitFiles` pushed into a
closure-captured `accepted` array INSIDE `setFiles((prev) => …)`.
React 18 StrictMode invokes the updater twice in dev to surface
impurities. Result: 1 file became 2 in the picker.

**Lesson:** **The setState updater must be pure.** Compute the
new list OUTSIDE the updater + pass a pure spread:
```ts
// CORRECT
const accepted = computeOutsideUpdater(currentFiles, incoming);
setFiles((prev) => [...prev, ...accepted]);

// WRONG
const accepted: File[] = [];
setFiles((prev) => {
  for (const f of incoming) accepted.push(f);  // mutates closure!
  return [...prev, ...accepted];
});
```

This was the same FileList-race class from R7 history. **Foundation
e2e is the only thing that caught it** — Vitest didn't because no
DocDropOverlay test existed (now fixed at
`src/modals/__tests__/DocDropOverlay.test.tsx`). Pin StrictMode
behavior with a `<StrictMode>`-wrapped test for any new
multi-state-update code path.

### 2. Flat-shape mocks vs nested-shape production payload

**Bug:** R10 sweep helper read `processing_metadata.bedrock_cost_estimate_usd`;
production stores it nested under `processing_metadata.extraction.*`.
Unit tests passed because mocks were flat-shape.

**Lesson:** **Mock fidelity must mirror production shape.** When
adding a helper that reads a payload, grep for the actual
producer's write path + use that shape in tests. The
`_doc_extraction_meta` helper in `scripts/demo-prep/r10_sweep.py`
is the canonical access pattern; reuse it for any future
processing_metadata reads.

### 3. Subagent gates pass against subagent-written fixtures

**Pattern:** Tier 3 polish bundles A/B/C/D each ran their own
"all gates green" report. None of them re-ran `foundation.spec.ts`
after their changes. Result: bundle B regressed R7 doc-drop e2e;
bundle C left 2 stale i18n selectors.

**Lesson:** **Re-run the FULL existing e2e suite after any
frontend touch.** Subagent reports + Vitest passing ≠ no
regression. Add this to your per-phase gate suite:
```bash
cd frontend && set -a && source ../.env && set +a
PLAYWRIGHT_BASE_URL=http://localhost:5173 \
  MP20_LOCAL_ADMIN_PASSWORD=change-this-local-password \
  npx playwright test --project=chromium e2e/ --reporter=line
```

### 4. `aria-label` text vs visible text divergence

**Bug:** Visual-verification spec searched for
`getByRole("button", { name: /save as draft/i })`. The button's
`aria-label` is "Save the current wizard state as a draft" + visible
text "Save as draft". Playwright's accessible-name resolution
prioritizes aria-label, so `/save as draft/i` (consecutive words)
didn't match the long-form aria-label.

**Lesson:** **When writing test selectors, check what the actual
accessible name resolves to.** Use a less-anchored regex
(`/save.*draft/i`) for matches across both forms. For a visible
text match, use `getByText(...)` instead of `getByRole`.

### 5. Modal a11y: `aria-modal=true` is not enough

**Bug:** FeedbackModal had `role="dialog" aria-modal="true"` but
didn't close on Escape. Advisors who opened it accidentally were
keyboard-trapped.

**Lesson:** **Custom modals need imperative Esc handlers + focus
return + click-outside-overlay handlers.** Use
`@radix-ui/react-dialog` when possible (gets all of these for
free); when a bespoke modal is unavoidable, mirror the
DocDetailPanel pattern (Esc + focus restore).

### 6. `str(exc)` anywhere = PII leak risk

**Pattern:** Bedrock errors may carry extracted client text in
their messages. Persisting them to DB columns / API response
bodies / audit metadata exposes real-PII outside the secure root.

**Lesson:** **Never write `str(exc)` directly to user-visible
surfaces.** Map to a structured `failure_code` via
`web/api/error_codes.py:safe_exception_summary` first. CI grep
guard at `scripts/check-pii-leaks.sh` enforces this; do NOT
disable it.

### 7. Bedrock Converse vs InvokeModel for vision

**Bug-class avoided:** Anthropic's Converse API for Bedrock drops
to text-only when `tool_choice` is forced; InvokeModel preserves
the document content block. The `AnthropicBedrock` SDK uses
InvokeModel by default — **don't switch to Converse** without
verifying tool-use + native-PDF support is preserved.

### 8. `budget_tokens` deprecated on Sonnet 4.6 / Opus 4.6/4.7

**Pattern:** Older Anthropic models accepted
`thinking={"type": "enabled", "budget_tokens": N}`. New models
(Sonnet 4.6, Opus 4.6, Opus 4.7) use **adaptive thinking**:
`thinking={"type": "adaptive"}`. Don't switch to an older model
just because someone mentions budget_tokens.

### 9. Don't auto-commit households during R10 sweep

**Pattern:** The R10 sweep script leaves all 7 workspaces in
`review_ready`. Auto-committing them would pollute demo state +
pre-empt the advisor review-and-commit flow. Operator commits
selectively if needed.

### 10. Honest audit when the user pushes back

**Pattern:** Three rounds of "Is everything done?" each surfaced a
real bug. The user's pushback is signal, not noise.

**Lesson:** **When challenged, don't restate confidence —
audit.** Run higher-level tests (foundation e2e, visual
verification, real-browser checks). Distinguish "tests pass" from
"verified working." Surface gaps explicitly + close them.

---

## 9. Mon 2026-05-04 morning runbook (the operator's path)

The operator (you / Saranyaraj) runs these in order Mon morning.

### Demo-state restore (per `docs/agent/demo-restore-runbook.md`)

```bash
cd /Users/saranyaraj/Projects/github-repo/mp2.0
# 1. Wipe + reseed (Sandra/Mike + bootstrap advisor)
bash scripts/reset-v2-dev.sh --yes
# Sandbox may prompt for permission rule; locked decision #34
# pre-authorizes this command but the bash sandbox tracks per-rule.

# 2. Pre-upload Seltzer + Weryha for demo
set -a && source .env && set +a && unset AWS_SESSION_TOKEN AWS_SECURITY_TOKEN
uv run python scripts/demo-prep/upload_and_drain.py Seltzer
uv run python scripts/demo-prep/upload_and_drain.py Weryha

# 3. Verify demo path manually in real Chrome
open -a "Google Chrome" http://localhost:5173/
# Walk: login → ClientPicker → Sandra/Mike → Treemap → Account →
# Goal → /methodology → /review → Seltzer → ConflictPanel →
# (don't commit; demo state)

# 4. Capture post-restore counts
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 \
  uv run python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web.mp20_web.settings')
django.setup()
from web.api import models
print('Workspaces:', models.ReviewWorkspace.objects.count())
print('Households:', models.Household.objects.count())
print('Facts:', models.ExtractedFact.objects.count())
"
```

Expected post-restore counts:
- Workspaces: 2 (Seltzer + Weryha review_ready)
- Households: 1 (Sandra/Mike committed)
- Facts: ~170-200

### Push to origin

**Verify gate suite green ONE MORE TIME** before push.

```bash
# Final gate run
cd /Users/saranyaraj/Projects/github-repo/mp2.0
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 \
  uv run python -m pytest \
    scripts/demo-prep/test_r10_sweep.py \
    engine/tests/ extraction/tests/ web/api/tests/ web/audit/tests/ \
    --tb=no -p no:warnings --benchmark-disable
# expect: 854 passed, 7 skipped

cd frontend && npm run typecheck && npm run lint && npm run build && npm run test:unit
# expect: 82 Vitest passing

# Push
git push origin feature/ux-rebuild --tags
```

After push, monitor CI for any environment-specific failures.

### If demo restore fails

See `docs/agent/pilot-rollback.md`. Decision tree for partial
recovery vs full reset.

---

## 10. Pilot week 1-2 ops cheat sheet

Pilot launches 2026-05-08. The next sub-session likely focuses on
**triaging real-advisor feedback** + **fixing surfaced bugs**.

### Where to look

- **Feedback model rows:** `Feedback.objects.filter(status="new").order_by("-created_at")`
  via Django shell, OR `GET /api/feedback/report/?status=new`
  endpoint (analyst-only).
- **Audit event volume:** `AuditEvent.objects.filter(action="review_state_committed").count()`
  by day → tells you commit cadence.
- **Bedrock spend:** check
  `docs/agent/bedrock-spend-2026-05-03.md` against AWS console; flag
  if any folder exceeds $0.50/doc.
- **Worker health:** `ProcessingJob.objects.filter(status="processing", locked_at__lt=now-5min)`
  catches stale workers.

### Triage cadence

Per `docs/agent/pilot-success-metrics.md`:
- Mon AM: ops reviews Feedback report; flags Sev-1; updates
  `docs/agent/handoff-log.md` with weekly metrics.
- Fri EOW: Saranyaraj + Fraser sync; triage to Linear if needed.

### Sev-1 triggers (kill-switch + retro)

- Real-PII leak detected (PII grep guard fails OR audit row carries
  raw exception text)
- Audit-event regression (count != expected per locked #37)
- Engine generates obvious-wrong recommendations
- Bedrock spend > $500 in a single week

Pull `MP20_ENGINE_ENABLED=0` env flag to halt portfolio
generation; advisors see the kill-switch banner; retro within 48h.

---

## 11. Post-pilot work (deferred, in priority order)

These are explicitly captured in
`docs/agent/post-pilot-improvements.md`. Pilot data informs
priority.

| P | Item | Trigger |
|---|---|---|
| P1 | **Re-edit flow v2** (replaces soft-undo) | If pilot feedback shows orphan-history value |
| P2 | **Phase 9.4 multi-tool architecture** | If pilot recall < 80% pre-Phase-4 baseline |
| P2 | **Demo-restore --dry-run + snapshot** | If reset script needs validation pre-execution |
| P2 | **Tier 3 visual regression suite** (Playwright screenshot diffs) | Pilot week 1 surfaces a CSS regression |
| P3 | **Mobile responsive audit** | Advisor reports mobile usage |
| P3 | **Color-blind palette spot-check** | Manual review with Sim Daltonism |
| P3 | **Conflict-rule heuristics** (saved-rule support) | Advisor reports repetitive conflict patterns |
| P3 | **Audit browser UI** (analyst surface) | Compliance asks |
| P3 | **fr-CA i18n population** | Quebec advisor onboarded |

---

## 12. Stop-and-ask points (locked)

You halt + `AskUserQuestion` only on:

| When | Question |
|---|---|
| Sev-1 incident in pilot | Should we kill-switch (pull `MP20_ENGINE_ENABLED=0`)? Roll back? Hot-fix? |
| Pilot recall < 80% pre-Phase-4 baseline (week 1 data) | Ship Phase 9.4 multi-tool now or defer? |
| Bedrock spend > $200/sub-session | Halt + retro before continuing |
| Real-PII anomaly detected | Halt + diagnose before further code change |
| Code change > 150 lines OR > 3 files | Confirm scope before continuing |
| Anything that touches push to origin | User pushes; never agent |

**Don't ask:**
- "Should I add a regression test?" — yes, always.
- "Should I run gates before committing?" — yes, always.
- "Which gate suite step?" — run all of them.
- "Is this ready to ship?" — answer with verifiable evidence,
  not opinion.

---

## 13. Success criteria for the next session

The next session ships when:

1. **Mon 2026-05-04 demo state restored cleanly** — Sandra/Mike +
   Seltzer + Weryha pre-uploaded; the 8-step demo flow runs
   end-to-end in real Chrome without console errors or visible
   friction; advisor disclaimer + tour pre-acked for the demo
   user.

2. **`feature/ux-rebuild` pushed to origin** with the
   `v0.1.0-pilot` tag included; CI green on the push.

3. **Pilot launches Mon 2026-05-08** with all 5 advisors
   provisioned (per
   `web/api/management/commands/provision_pilot_advisors.py` —
   commit list of advisors lives outside the repo).

4. **Pilot week 1 runs without a Sev-1 incident** OR if one
   surfaces, it's triaged + resolved within 24h with a
   handoff-log entry.

5. **Per-advisor weekly Bedrock spend < $25** (pilot success
   metrics target).

6. **Daily handoff-log entries during pilot week 1** capturing
   what advisors reported + what was fixed.

The pilot transitions to GA-ready when ALL of:
- Sev-1 incidents = 0 for 2 consecutive weeks
- Per-advisor NPS ≥ 8
- ≥ 50% of pilot advisors used the system for ≥3 client onboardings
- No regressions on locked #18 perf budget
- R10 sweep across all 7 folders re-passes weekly

---

## 14. Communication style

The user has been burned by overconfident "ship-ready" claims.
The prior session caught **5+ real bugs** through user pushback +
visual verification (StrictMode regression, R10 cost-key bug,
2 stale e2e selectors, FeedbackModal Esc handler, missing
DocDropOverlay tests). **Be candid about uncertainty.**

When the user asks "Is everything done?" or "Are you sure?":
- **Don't restate confidence.** Audit honestly.
- **Distinguish "tests pass" from "verified."** Tests prove a
  contract; verification proves a behavior.
- **Surface gaps explicitly.** "X verified via Y; Z NOT verified
  because <reason>."
- **Run higher-level tests.** If only Vitest passed, run
  Playwright. If only Playwright headless, run real-Chrome
  visual.
- **Distinguish state-dependent gaps from regressions.** Some
  surfaces (soft-undo button, resolved-collapse) need fixtures
  not in the current DB. Those are gaps, not regressions; flag
  them as such.

When the user gives `auto mode`:
- Execute autonomously on routine work.
- **Halt on the locked stop-and-ask points** even under
  auto-mode. Auto isn't an excuse to take destructive actions.

When you halt:
1. Commit any uncommitted work first.
2. Update `docs/agent/handoff-log.md` with where you halted.
3. Append to `docs/agent/bedrock-spend-2026-05-03.md` if Bedrock
   work happened.
4. Ping with `AskUserQuestion`.

**Never strand uncommitted work across a halt.**

---

## 15. Anti-pattern: things you might be tempted to do but shouldn't

1. **Re-do work already shipped** in the 16 commits past
   `8bb96c0`. The commits below are load-bearing; check the diff
   before assuming a surface is broken:
   ```
   b14a199 visual-verification: full-checklist alignment + FeedbackModal Esc fix
   efbe58d e2e: comprehensive visual-verification spec (17 tests, 17/17 pass)
   95af4b5 docs: handoff log addendum for the verification-pass gaps
   b887b18 test: DocDropOverlay StrictMode tests pin the admitFiles fix
   bca0112 fix: DocDropOverlay StrictMode-double-update + foundation e2e + R10 nested-key tests
   2bd77d3 R10 sweep: live run results + cost-key bug fix + recomputed totals
   df6363f docs: correct test counts in handoff log
   1428555 test: tooltip wrapper smoke tests
   5cb91c0 docs: handoff-log entry for sub-session #11 deferred-work follow-up
   cb408cc test: 15 unit tests for R10 sweep automation helpers
   f86dcfd Sub-session #11 deferred work closed: R10 sweep + cross-browser + Tier 3 polish
   af627b3 Sub-session #11: Tier 2 high-leverage items + close-out
   35a7eba Sub-session #10: Tier 1 advisor friction (#10.1-#10.6)
   8af7104 Sub-session #9: Phase 9 fact-quality recovery (layered iteration)
   735ecae Sub-session #8.5 + close-out: Niesner canary + spend ledger + handoff
   2d61cc0 Sub-session #8.1-#8.4: OCR/vision foundation via Bedrock native PDF
   ```

2. **Push to origin** without explicit user OK. User pushes Mon.

3. **Bulk-modify ProcessingJob rows** from prior sessions
   (locked authorization explicitly forbids).

4. **Disable PII grep / OpenAPI drift / vocab CI gates** to
   "ship faster". The gates are guarding the canon constraints.

5. **Quote real client content** in code, commits, memory, or
   chat. Even paraphrasing a fact ("the household has $X in
   RRSP") is a violation. Use structural counts only.

6. **Skip the foundation e2e re-run** after frontend changes.
   The DocDropOverlay StrictMode regression slipped through
   because foundation wasn't re-run.

7. **Trust subagent "all gates green" reports without verifying.**
   Subagent gates pass against subagent-written fixtures.

8. **Add comments in code that explain WHAT** when well-named
   identifiers already convey it. Comments are for WHY (hidden
   constraints, subtle invariants, workarounds for specific bugs).

9. **Use `aria-label` that diverges materially from visible text.**
   The accessible-name resolution prioritizes aria-label; if the
   text says "Save as draft" but aria-label says "Save the
   current wizard state as a draft", screen-reader users hear
   the long form. Match them or use a tooltip for the long form.

10. **Treat auto-mode as a license to be destructive.** Anything
    that deletes data, modifies shared systems, or forces a
    sandbox-prompt still needs explicit confirmation.

---

## 16. First concrete actions when the next session starts

1. **Run §2 pre-flight** in full. If anything is red, halt + ping.

2. **Read §3 Tier 1 docs** (handoff log last 5 entries +
   sub-sessions plan + production-quality-bar). 10-15 min.

3. **Verify the post-Mon-push state matches expectations** —
   ```bash
   git log --oneline origin/feature/ux-rebuild..HEAD  # should be empty after push
   git tag -l v0.1.0-pilot  # should resolve to a known commit
   ```

4. **Pivot based on pilot-week phase:**

   - **Pre-pilot (before 2026-05-08):** Mon morning runbook §9.
     Demo restore + push. Visual smoke in real Chrome. Verify
     advisor provisioning command works for 5 advisors.

   - **Pilot week 1 (2026-05-08 → 2026-05-15):** Triage cheat
     sheet §10. Daily handoff-log entries. Hot-fix anything Sev-1.

   - **Pilot week 2 (2026-05-15 → 2026-05-22):** Measure pilot
     metrics per `docs/agent/pilot-success-metrics.md`. Decide
     GA-or-extend at end of week 2.

   - **Post-pilot (2026-05-22+):** Pick from §11 backlog based
     on pilot data. Re-edit flow v2 if orphan-history valued;
     Phase 9.4 multi-tool if recall regressed.

5. **For ANY frontend touch:** re-run foundation e2e +
   visual-verification spec. **This is non-negotiable.**

---

## 17. Memory + state pointers (don't write into chat; persist here)

Auto-memory at
`/Users/saranyaraj/.claude/projects/-Users-saranyaraj-Projects-github-repo-mp2-0/memory/MEMORY.md`
indexes the project memories. Most-load-bearing:

- `project_post_r8_demo_locked.md` — earlier checkpoint; superseded
  by the handoff-log entries at HEAD `b14a199`.
- `project_real_pii_not_blocked.md` — pilot data authorization.
- `project_engine_invariants.md` — engine-is-library, AI-numbers
  rule, append-only.
- `feedback_routine_defaults.md` — Opus default; verify infra
  yourself.
- `feedback_collaboration_style.md` — single taxonomy, canon-verbatim
  fidelity, deep research before action.

If you discover a load-bearing constraint that future sessions
need, **write it to memory** + add a one-line entry to
`MEMORY.md`. Don't let it get lost in chat.

---

## 18. The shape of MP2.0 — for grounding when you context-switch

### File-tree map (key paths only)

```
mp2.0/
├── engine/                          # Pure-Python optimizer (canon §9.4.2)
│   ├── optimize.py
│   ├── sleeves.py
│   └── schemas.py                   # Pydantic models; the engine boundary
├── extraction/                      # Bedrock pipeline (canon §11.4)
│   ├── parsers.py                   # is_likely_image_pdf detection
│   ├── llm.py                       # extract_text/visual/native_pdf paths
│   ├── pipeline.py                  # extract_facts_for_document dispatcher
│   ├── prompts/                     # per-doc-type modules + base
│   ├── reconciliation.py            # source-priority hierarchy
│   ├── validation.py                # Phase 9.3 evidence-quote gate
│   └── schemas.py                   # ParsedDocument, FactCandidate, etc.
├── web/                             # Django/DRF
│   ├── api/views.py                 # ReviewWorkspace*View; the request/response surface
│   ├── api/review_state.py          # readiness + commit_reviewed_state
│   ├── api/review_processing.py     # Bedrock worker
│   ├── api/error_codes.py           # PII-safe helpers (use these)
│   └── audit/models.py              # AuditEvent (append-only)
├── frontend/
│   ├── src/chrome/                  # TopBar, ClientPicker, PilotBanner, FeedbackButton
│   ├── src/routes/                  # AccountRoute, GoalRoute, ReviewRoute, CmaRoute
│   ├── src/modals/                  # DocDropOverlay, ReviewScreen, ConflictPanel,
│   │                                 # DocDetailPanel, RealignModal, CompareScreen
│   ├── src/wizard/                  # HouseholdWizard + draft.ts persistence
│   ├── src/components/              # Truncated, ConflictCard, ConfidenceChip, ui/tooltip
│   ├── src/lib/                     # canonical-fields, format, review (TanStack hooks)
│   └── e2e/                         # foundation, visual-verification, cross-browser
├── scripts/
│   ├── reset-v2-dev.sh              # locked #34 pre-authorized
│   ├── demo-prep/upload_and_drain.py
│   └── demo-prep/r10_sweep.py       # automated 7-folder sweep
└── docs/agent/                      # all the load-bearing docs in §3
```

### Pilot data flow (real-PII canon §11.8.3)

```
Croesus PDF/DOCX   →   /api/review-workspaces/<id>/upload/   (multipart, advisor-auth)
                       │
                       ▼
                       MP20_SECURE_DATA_ROOT/<workspace>/<sha256>.<ext>
                       │
                       ▼ (worker picks up)
extraction/parsers     parses to ParsedDocument
extraction/classification → ClassificationResult
extraction/llm.extract_*_with_bedrock_native  →  Bedrock ca-central-1
                       │
                       ▼ (FactCandidate list)
extraction/validation  filter inferred-facts by evidence overlap
extraction/pipeline    cap confidence by classification + 1
                       │
                       ▼
ExtractedFact rows  +  ProcessingJob status flips
                       │
                       ▼ (advisor reviews on /review/<id>/)
ReviewScreen           ConflictPanel + DocDetailPanel + section approvals
                       │
                       ▼
POST /commit/          commit_reviewed_state → Household + Person/Account/Goal/Link
                       │
                       ▼
GeneratePortfolioView  engine.optimize → PortfolioRun + recommendation rows
```

Every arrow above emits an AuditEvent. Every persisted blob
(ExtractedFact, FactOverride, HouseholdSnapshot, PortfolioRun)
is append-only. The advisor commits exactly once per workspace
unless they soft-undo (sub-session #10.6).

---

## 19. If you read only ONE thing

Read `docs/agent/handoff-log.md` last 5 entries. They capture:
- The Mon-pre-pilot state (HEAD `b14a199`).
- The 3 bugs the verification pass surfaced.
- The lesson about subagent-gate fidelity.
- The Mon morning push readiness.

Everything else in this prompt is orientation; the handoff log is
the single source of truth for "what just happened."

---

## 20. Final note

This is the most thoroughly verified MP2.0 release the codebase
has ever shipped. **983 tests passing** across 5 layers (backend
pytest + Vitest + foundation e2e + cross-browser smoke + visual
verification). $0.86 of real-PII Bedrock spend produced 56 docs
reconciled across 7 client folders. Three rounds of "Is everything
done?" each surfaced + closed a real bug.

That said — pilot starts the day MP2.0 first touches a real
advisor's hands. The bugs we don't know about will outnumber the
ones we do. **Honest audit + responsive fixing during pilot week
1 is the success metric, not "we shipped without bugs."**

The user trusts your candor more than your confidence. Earn that
trust by saying "I haven't verified X" when you haven't.

Mon 2026-05-04 + 2026-05-08 are real deadlines. Quality bar > speed
bar. Real-PII discipline > all.

Welcome to MP2.0. Let's launch.

— prior agent, 2026-05-03 22:30Z, HEAD `b14a199`
