# Next-Session Starter Prompt — copy/paste at session start

Below is the prompt to use for the next sub-session. Copy from
`---BEGIN PROMPT---` through `---END PROMPT---` into the new
session.

---BEGIN PROMPT---

You are continuing the MP2.0 beta-pilot hardening — a multi-week,
multi-session engineering effort that is now mid-flight. This
sub-session picks up at HEAD `d2abfa1` with **Phase 8
release-essentials shipped and tagged `v0.1.0-pilot`**. The next
work is the Phase 5b polish remainder, Phase 5c (UX spec docs),
Phase 6 (deep test coverage), and Phase 6.9 (perf budget gate).

Auto mode is active: make reasonable assumptions, proceed on
low-risk work, minimize interruptions, halt + `AskUserQuestion`
on stop conditions, ping per-phase verbose ~400 words. The user's
quality bar is **"production-grade for the limited-beta release"**
— no cutting corners, no half-finished implementations, no
dead-code shims; every commit ships with the full gate suite green
and the per-phase ping documents trade-offs explicitly.

## 0. Pre-flight verification (do this BEFORE anything else)

```bash
cd /Users/saranyaraj/Projects/github-repo/mp2.0
git status --short --branch    # expect: feature/ux-rebuild, clean
git log --oneline -12
# Expected chain (newest first):
#   d2abfa1 Phase 8: pilot-rollback + success-metrics + provision command + CHANGELOG
#   4303c37 docs: update session-state HEAD reference to 0069330
#   0069330 docs: Phase 7 R10 sweep results + Phase 9 fact-quality iteration plan
#   6b0ea9b Phase 4 hardening: confidence-floor cap + multi_schema_sweep dispatcher
#   8c9cdaa docs: handoff log + session-state for Phase 4-5b partial wave
#   e952c61 Phase 5b.2/5b.7/5b.9/5b.14: worker health banner + polling backoff + ConfidenceChip + axe-core + pilot smoke spec
#   288c3e7 Phase 5b.1+5b.6: pilot banner + feedback infra + welcome tour
#   2b28220 Phase 5a: Conflict-resolution endpoint + ConflictPanel UI
#   413fd02 Phase 4.5: OpenAPI-typescript codegen + drift CI gate
#   7a2e252 Phase 4: Bedrock tool-use migration + per-doc-type prompts
#   448b281 docs: handoff Phase 0-3 done; halt for fresh session on Phases 4-8
#   0277675 Phase 3: close BUG-1 manual-entry atomicity + REC-1 reconcile-enqueue ordering

git tag -l "v0.1.0*"           # expect: v0.1.0-pilot

DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 \
  uv run python -m pytest engine/tests/ web/api/tests/ web/audit/tests/ -q
# expect: 429 passed

uv run ruff check . && uv run ruff format --check .   # expect: clean
bash scripts/check-pii-leaks.sh                       # expect: "PII grep guard: OK"
bash scripts/check-vocab.sh                           # expect: "vocab CI: OK"
bash scripts/check-openapi-codegen.sh                 # expect: "OpenAPI codegen gate: OK"
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 \
  uv run python web/manage.py makemigrations --check --dry-run    # expect: "No changes detected"

cd frontend && npm run typecheck && npm run lint && npm run build  # expect: clean
```

If ANY check is red before you change anything, stop and ping the
user — the environment is wrong.

## 1. Read in this order before acting

The plan + handoff are the source of truth. If anything in this
prompt conflicts with them, **the plan + handoff win**.

1. `~/.claude/plans/you-are-continuing-a-playful-hammock.md` —
   the master plan. 50+ user-locked decisions. Phase 5b sub-phases
   are documented in detail under "Phase 5b — UX Hardening for
   Limited-Beta Pilot".
2. **`docs/agent/production-quality-bar.md` — LOAD-BEARING.**
   Per-surface UX polish checklist + UX inspiration sources (Linear,
   Notion, Stripe, GitHub, Asana) + comprehensive end-to-end test
   coverage map (unit + hook + integration + property-based +
   concurrency stress + edge cases + migration rollback + PII
   adversarial fuzzing + auth/RBAC matrix + DB invariants + perf
   budgets + real-browser smoke + axe-core full-route +
   cross-browser + visual regression + demo dress rehearsal) +
   production infrastructure (logging, monitoring, audit retention,
   PII data classification, secrets rotation, disaster recovery) +
   sub-session #2 + #6 + #7 detailed scope. **Every sub-session
   from #2 onward gates on items from this doc.**
3. `docs/agent/handoff-log.md` — read the last 3 entries (in
   reverse chronological order: `2026-05-03`,
   `2026-05-02 (later, Phase 7 R10 sweep)`, `2026-05-02 (later,
   Phase 5 wave)`). They capture exact session-by-session deltas +
   diagnoses + Bedrock cost.
4. `docs/agent/session-state.md` — current state line + phase line.
5. `docs/agent/r10-sweep-results-2026-05-02.md` — per-doc
   structural diff that surfaced the −41% recall trade-off; read
   for context on the canon §9.4.5 quality wins + the Phase 9
   recovery plan.
6. `docs/agent/phase9-fact-quality-iteration.md` — post-pilot
   fact-quality iteration plan (10 alternatives canvassed). Don't
   execute Phase 9 in this sub-session; it's post-pilot scope.
7. `docs/agent/pilot-rollback.md` + `docs/agent/pilot-success-metrics.md`
   — Phase 8 outputs; reference these when adjusting downstream
   behavior or coordinating with ops.

Skim only — these docs are dense. The Phase 5b sub-phase mappings
(below) tell you which doc-section is relevant for each commit.

## 2. Context-management strategy (LOAD-BEARING)

This is a deliberate multi-sub-session effort. Each sub-session
ends with a commit + per-phase ping + suggested `/compact` before
the next sub-session. **The plan order (revised 2026-05-03)
to put Phase 7 back as a first-class validation gate + add UX
polish + auth/RBAC matrix + PII adversarial fuzzing + cross-browser
+ axe-core full route coverage + demo dress rehearsal:**

| Sub-session | Phase scope | Est commits | Est lines |
|---|---|---|---|
| **#1 (this one — START HERE)** | 5b.3 + 5b.8 | 2-3 | 200-400 |
| #2 | 5b.4 + 5b.5 + 5b.7-pag + 5b.10/11 + 5b.12/13 **+ UX-polish pass** (loading skeletons, empty states, error recovery, focus mgmt, kbd nav, prefers-reduced-motion, number/date formatting audit, toast dedup, hover delay) per `production-quality-bar.md` §1.10 + §6 | 5-7 | 1700-2600 |
| #3 | 5c (UX spec + design system docs) + Phase 6 scaffolding (factory_boy + Vitest + RTL + jest-dom) | 2-3 | 800-1200 |
| #4 | Phase 6 deep tests (subagent-parallel) — Hypothesis + concurrency stress + edge cases + migration rollback **+ auth/RBAC matrix (`test_auth_rbac_matrix.py`) + PII adversarial fuzzing (`test_pii_adversarial.py`) + audit-invariant property suite + per-component Vitest unit tests + DB-invariant expansion** per `production-quality-bar.md` §3.1–§3.10 | 5-7 | 2000-3000 |
| #5 | Phase 6.9 perf budget gate + JSON logging + monitoring hooks per `production-quality-bar.md` §4.1–§4.2 | 2-3 | 500-900 |
| **#6 (NEW)** | **Phase 7 — full end-to-end validation.** Real-browser smoke + cross-browser spot-check (Safari + Firefox) + 7-folder R10 sweep (re-upload missing folders OR documented partial) + Niesner DEMO DRESS REHEARSAL + axe-core every route + PII adversarial fuzzing live + visual regression spot checks + demo state restore. Per `production-quality-bar.md` §3.12–§3.16 + §7.1–§7.7 | 3-5 | 600-1200 |
| **#7 (NEW)** | Final gates + push readiness check + cumulative ping + tag verification + Monday push staged. Per `production-quality-bar.md` §8 | 1-2 | 200-400 |

**This sub-session executes #1 only.** Stop after Phase 5b.3 +
5b.8 commit + per-phase ping. Suggest `/compact` to the user before
they kick off #2.

**Subagent-parallel discipline (use heavily for #4):**
- For Phase 6 Hypothesis suites (3 separate property-test files),
  dispatch 3 `general-purpose` agents concurrently in a single
  message. Each agent writes one suite + runs it locally.
- For per-route Vitest scaffolding, dispatch 1 agent.
- For migration rollback tests, dispatch 1 agent.
- The main thread orchestrates + reviews + commits — do NOT do
  the test-writing yourself when subagent-parallel is feasible.

**Other context-light tools to lean on:**
- `Explore` agent for any "where does X live" lookup that would
  otherwise burn 3+ grep+read cycles.
- `Bash` with `run_in_background: true` for any wait > 10s
  (worker drains, builds, R10 retries). NEVER block your main
  thread on a sleep.
- `Monitor` for stream-events from a long-running process.

## 3. Locked decisions (won't be obvious from code alone)

These were established across 12 user-interview rounds + the live
session work. Some are documented in code comments; others only
in the plan / handoff. Honor them without re-litigating.

### 3.1 UI patterns

- **DocDetailPanel = slide-out from the right edge** (NOT modal,
  NOT inline expansion). Sets the design-system pattern
  "contextual deep-dive without losing parent context." Codify in
  `docs/agent/design-system.md` (Phase 5c).
- **PilotBanner ack** = server-side audit-tracked via
  `AdvisorProfile.disclaimer_acknowledged_at` +
  `disclaimer_acknowledged_version`. Bumping the
  `DISCLAIMER_VERSION` code constant in `frontend/src/lib/auth.ts`
  forces re-ack on next login. Audit log captures every version
  per advisor (queryable via
  `AuditEvent.objects.filter(action="disclaimer_acknowledged",
  metadata__advisor_id=X)`).
- **WelcomeTour ack** = server-side per-account via
  `AdvisorProfile.tour_completed_at`. Both "Done" and "Skip" mark
  acknowledged so the tour never re-shows on any device for that
  advisor. Idempotent endpoint: only first transition emits the
  audit event.
- **FeedbackButton** = backend persists only (no runtime Linear
  API call). `Feedback` model schema mirrors what Linear's
  `save_issue` MCP would consume so a future automated-sync
  migration is a serializer + cron task, not a schema rewrite.
  Auto-included context: route + session_id + browser_user_agent.
  NEVER auto-include workspace_id / household_id / fact values
  (advisor narrates in their own words).
- **ConfidenceChip = color + text + ARIA label** (NOT color-only;
  WCAG 2.1 AA). Reuses existing `accent`/`muted`/`danger` tokens.
  Already wired into `ConflictPanel.CandidateRow`.
- **ConflictPanel = full mockup parity** (already shipped in
  Phase 5a; per-conflict cards + multi-source candidates +
  redacted evidence + rationale + evidence-ack). Bulk + defer UI
  layers on top in 5b.12/13.

### 3.2 Data + state patterns

- **`FactOverride` model is APPEND-ONLY** (mirrors
  `HouseholdSnapshot` pattern). Each advisor edit creates a NEW
  row; never UPDATE existing rows. `save()` raises on existing
  pk (DB-enforced). Latest-row-wins per `(workspace, field_path)`
  via `MAX(created_at)`. Audit event `review_fact_overridden`
  per row. The model + migration are SHIPPED at HEAD `288c3e7`;
  the endpoint + UI integration is Phase 5b.10/11 work.
- **Inline fact edit (5b.10) + add-missing-fact (5b.11) reuse one
  mechanism** — same `FactOverride` model. `is_added=False` ==
  override; `is_added=True` == advisor-added (no underlying
  extracted fact). The runtime detects via querying for an existing
  `ExtractedFact` on the same field path.
- **Bulk conflict resolve (5b.12)** — the endpoint accepts
  `{conflict_ids: [...], chosen_fact_id, rationale, evidence_ack}`.
  Atomic — partial failure rolls back. EACH conflict still gets
  one `review_conflict_resolved` audit event (not one per bulk
  request).
- **Defer conflict (5b.13)** — `reconcile_workspace` checks each
  deferred conflict's `field_path` against latest extracted facts;
  new evidence triggers auto-undefer with a `re_surfaced_at`
  timestamp + audit event `review_conflict_resurfaced`. Section
  approval blockers logic in `web/api/review_state.py:section_blockers`
  treats deferred conflicts as advisory (do NOT block section
  approval) but surfaces them in a separate "deferred" UI list.

### 3.3 Extraction patterns

- **multi_schema_sweep classification routes to `generic.build_prompt`**
  regardless of `document_type`. Per-type bodies are too narrow
  when the classifier saw signals from multiple doc types.
  Implemented at HEAD `6b0ea9b`.
- **Confidence floor cap** = `min(classification_rank + 1, 3)`.
  HIGH classification → no cap; MEDIUM → no cap; LOW → HIGH
  floors to MEDIUM but doesn't collapse medium to low. Implemented
  at HEAD `6b0ea9b`. PROMPT-5 spirit ("low classification can't
  produce HIGH facts") preserved without flattening signal.
- **Phase 9 fact-quality iteration is post-pilot scope** — do NOT
  attempt to improve recall in this session's work. The plan +
  handoff explicitly defer fact-quality iteration; the −41%
  recall trade-off is accepted by the user.

### 3.4 Operational

- **Branch:** `feature/ux-rebuild`. Per-phase commits. **No push**
  during the session — user pushes Monday morning
  `2026-05-04` (the demo date) per locked direction.
- **Bedrock spend:** authorized to $100. ~$3 spent in prior
  sessions (12 real-PII doc retries via Phase 7 R10 sweep). Phase
  6 deep tests use mocked Bedrock; no additional spend. Phase 9
  (post-pilot) has its own per-iteration $50 budget.
- **Cost tracking** is intentionally NOT instrumented (user scope
  decision 2026-05-02). Watch AWS console manually if needed.
- **Reporting cadence:** verbose ~400-word per-phase exit ping
  with: HEAD commit + diff highlights, audit-finding closure refs,
  tests added, full gate-suite results, reasoning, open items,
  next phase. Format already established in prior session pings
  (handoff-log examples).
- **User availability:** highly reachable, minute-grade response
  on stop-condition `AskUserQuestion`. Highly autonomous on
  routine work.

## 4. Per-phase gate suite (FULL — run at every phase exit)

```bash
# Backend
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 \
  uv run python -m pytest engine/tests/ web/api/tests/ web/audit/tests/ -q
uv run ruff check .
uv run ruff format --check .
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 \
  uv run python web/manage.py makemigrations --check --dry-run

# Frontend
cd frontend && npm run typecheck && npm run lint && npm run build && cd ..

# Project-level guards
bash scripts/check-vocab.sh
bash scripts/check-pii-leaks.sh
bash scripts/check-openapi-codegen.sh
```

If your phase added a new endpoint with drf-spectacular schema
support, the OpenAPI drift gate will catch it; regenerate via
`cd frontend && npm run codegen` then commit the regenerated
`api-types.ts`.

## 5. Stop conditions (halt + AskUserQuestion when these fire)

1. Any prior gate is red BEFORE you change anything.
2. A fix grows beyond ~150 lines / ~3 files (Phase 5b sub-phases
   have higher thresholds — Phase 5b.5 ≤ ~400 lines, 5b.10/11 ≤
   ~600 lines).
3. Phase output doesn't meet exit criteria after 2 iterations.
4. Bedrock spend approaches $100 (won't happen in this
   sub-session; flagged for #4 + #5 if any live testing
   surfaces).
5. You discover a regression vs prior state (handoff-log
   2026-05-02 sweep results = the baseline; Phase 5b.3 + 5b.8
   are pure UI additions and should not regress fact extraction).
6. You're considering pushing to `origin`.
7. The user-locked decision in §3 conflicts with what the code
   says. The handoff is right; the code is wrong; flag it and
   ask before changing.

## 6. Anti-patterns (DO NOT)

1. Re-do work already shipped (the 11 commits past `448b281`).
2. Re-introduce free-form JSON parsing in extraction.
3. Allow `derivation_method="defaulted"` (canon §9.4.5 prohibits
   default-to-make-it-fit; Phase 7 sweep eliminated 2 such facts —
   keep them at 0).
4. Generate hallucinated section paths
   (`identification.*`, `next_steps.*`, etc.). Tool-use schema
   prevents this; don't loosen the schema.
5. Bulk-modify `ProcessingJob` rows from prior sessions
   (locked authorization explicitly forbids).
6. Disable PII grep / OpenAPI drift / vocab CI gates to "ship
   faster."
7. `str(exc)` in DB columns / API response bodies / audit metadata
   `detail` fields. Phase 2 closed this; the PII grep guard
   prevents regression. Use `web/api/error_codes.py:safe_response_payload`
   + `safe_audit_metadata` instead.
8. Push to `origin` without explicit user OK. User pushes Monday.
9. Skip per-phase commits + pings to "save time." The verbose
   discipline is what made the prior 11 commits reviewable.
10. Add comments in code explaining what well-named identifiers
    already convey (per CLAUDE.md style).

## 7. Patterns shipped — use them, don't reinvent

- **PII helpers** `web/api/error_codes.py`: `failure_code_for_exc`,
  `safe_exception_summary`, `safe_response_payload(exc, **extra)`,
  `safe_audit_metadata(exc, **extra)`, `friendly_message_for_code`.
- **Atomicity**: `@transaction.atomic` + `.select_for_update()`
  on workspace is canonical for new state-changing endpoints.
  See `ReviewWorkspaceConflictResolveView.post` (Phase 5a) for
  the template.
- **Audit-event regression**: every state-changing endpoint emits
  exactly one audit event per locked decision #37. Mirror the
  Phase 5a `record_event(action="review_conflict_resolved",
  entity_type="review_workspace", entity_id=..., actor=_actor(request),
  metadata={...})` shape.
- **Append-only**: `FactOverride` (already shipped) +
  `HouseholdSnapshot` (pre-existing). Both override `save()` to
  raise on existing pk. Mirror the pattern when adding new
  append-only models.
- **Frontend wire-shape evolution**: extend
  `frontend/src/lib/review.ts` types alongside backend serializer
  changes; regenerate `api-types.ts` via `npm run codegen`; commit
  both. The drift gate verifies.
- **Test scaffolding**: backend tests in `web/api/tests/test_*.py`
  using `pytest-django` `@pytest.mark.django_db` + `APIClient` +
  `client.force_authenticate(user=user)`. Mirror existing tests
  (e.g., `test_phase5a_conflict_resolve.py` for endpoint testing
  patterns).

## 8. Sub-session #1 plan (this session)

Execute these in order. Each phase = one commit + one ping.

### 8.1 Phase 5b.3 — Inline retry + manual-entry CTAs per failed doc row

**Today** failed-doc actions live in a separate area of
`ReviewScreen.tsx`. Plan: embed retry + manual-entry buttons
inline within each failed doc row in the `ProcessingPanel`
sub-component.

**Files:**
- `frontend/src/modals/ReviewScreen.tsx` — refactor
  `ProcessingPanel` to render per-row actions when
  `doc.status === "failed"`. Add a "Failure reason" tooltip with
  the `review.failure_code.<code>` i18n copy (already in en.json
  from Phase 3).
- `frontend/src/i18n/en.json` — extend
  `review.processing.*` if new keys needed.
- `frontend/e2e/foundation.spec.ts` (optional) — assert inline
  buttons render per failed doc row.

**Estimated scope:** ~80-150 lines, 2-3 files.

**Stop condition:** if the existing layout's separate-action area
is depended on by `e2e/manual-entry-flow.spec.ts`, halt + ask
whether to update the spec or keep the legacy area.

### 8.2 Phase 5b.8 — Session-interruption recovery

If session expires mid-upload, files in-flight are lost. Detect
401 from upload endpoint; preserve `files` array + `label` in
sessionStorage; on re-login, check sessionStorage for pending
upload; if present, redirect to `/review` with restored files
and toast: "Re-signed in — resume upload."

**Files:**
- `frontend/src/modals/DocDropOverlay.tsx` (or wherever the
  upload mutation lives) — wrap upload in 401-detection that
  saves to sessionStorage on auth-failure.
- `frontend/src/routes/LoginRoute.tsx` — on successful re-login,
  read sessionStorage; if pending upload exists, navigate to
  `/review` with restored state.
- `frontend/src/lib/api.ts` (or `api-error.ts`) — extend the
  401 handling pathway if needed.
- `frontend/src/i18n/en.json` — new key
  `chrome.session.resume_upload_toast`.
- `frontend/e2e/foundation.spec.ts` — simulate 401 + re-login +
  assert files restored.

**Estimated scope:** ~150-250 lines, 4-5 files.

**Stop condition:** if `lib/api.ts`'s 401 handler already redirects
to login (likely; check first), the sessionStorage hook needs to
intercept BEFORE the redirect. If the existing flow doesn't expose
that hook, halt + ask.

### 8.3 Sub-session exit

Per-phase ping (verbose ~400 words) covering each Phase 5b sub-
phase. Then suggest `/compact` to the user.

## 9. After this sub-session

The next sub-session (#2) continues the polish remainder:
5b.4 + 5b.5 + 5b.7-pagination + 5b.10/11 + 5b.12/13 **+ the
UX-polish pass per `production-quality-bar.md` §1.10 + §6**.
The `docs/agent/handoff-log.md` entries this session generates
will be the bring-up context for #2.

The deferred sub-sessions (per the table in §2):

- **#3:** Phase 5c UX spec + design-system docs (parallelize:
  one subagent writes design-system.md while you write
  ux-spec.md). Phase 6 scaffolding: factory_boy fixtures + Vitest
  + RTL + jest-dom setup.
- **#4:** Phase 6 deep tests — **subagent-parallel** (3 agents
  writing 3 Hypothesis property suites concurrently). Plus
  concurrency stress + edge cases + migration rollback **+
  auth/RBAC matrix + PII adversarial fuzzing + audit-invariant
  properties + per-component Vitest unit tests + DB-invariant
  expansion** per `production-quality-bar.md` §3.
- **#5:** Phase 6.9 perf budget gate (pytest-benchmark; P50<250ms
  / P99<1000ms) **+ JSON logging + monitoring hooks** per
  `production-quality-bar.md` §4.1–§4.2.
- **#6 (Phase 7 — full e2e validation):** real-browser smoke +
  cross-browser (Safari + Firefox spot-check) + 7-folder R10
  sweep (re-upload missing folders if available, OR documented
  partial) + Niesner DEMO DRESS REHEARSAL + axe-core every route
  + every modal + every slide-out + PII adversarial fuzzing live
  + optional visual regression + demo state restore for Monday.
  Per `production-quality-bar.md` §3.12–§3.16 + §7.1–§7.7.
- **#7 (Monday push prep):** cumulative ping summarizing entire
  pilot release; final CI gate verification; tag intact;
  push staged but NOT executed (user pushes Monday morning). Per
  `production-quality-bar.md` §8.

## 10. Communication style

User has been burned by overconfident "ship-ready" claims (the
FileList race lesson; the Phase 4 canary regression caught only by
real-PII validation). Be candid about uncertainty. Demand
verifiable evidence per change. Verbose per-phase pings with
`file_path:line_number` specifics where applicable. The user
will redirect if you drift; treat redirects as normal input.

When you need to halt, do it cleanly: write the handoff entry,
update `session-state.md`, commit if there's uncommitted work,
THEN ping with `AskUserQuestion`. Don't strand uncommitted work
across a halt.

## 11. Real-PII discipline (LOAD-BEARING — canon §11.8.3 + dossier §10)

- **Never** quote real client content in code, commits, memory,
  chat, or any logs that escape `MP20_SECURE_DATA_ROOT`.
- Bedrock `ca-central-1` only for `data_origin: real_derived`.
  Anthropic direct for synthetic.
- Use **structural counts** ("N facts across M sources") — never
  values.
- Phase 5b.3 + 5b.8 are pure UI changes; no extraction work in
  this sub-session, so real-PII discipline is mostly latent. But
  if you write tests that touch real workspaces, follow the
  redaction patterns in `web/api/review_redaction.py`.

## 12. First concrete action

After running §0 pre-flight verification:

1. Read the handoff-log last entry (Phase 7 R10 sweep + Phase 9
   design) and the entry before that (Phase 5b partial wave) for
   context.
2. Read `frontend/src/modals/ReviewScreen.tsx` `ProcessingPanel`
   sub-component to understand the current per-doc rendering.
3. Read `frontend/src/i18n/en.json` `review.processing.*` and
   `review.failure_code.*` namespaces for available copy.
4. Begin Phase 5b.3 implementation per §8.1.

If anything in §0 is red OR §1's docs reveal scope creep beyond
the per-phase Stop-condition thresholds, halt + `AskUserQuestion`
before coding.

---END PROMPT---

---

## Notes for the human (Saranyaraj)

This prompt is intentionally:
- **Comprehensive** — front-loads locked decisions that won't be
  obvious from code alone (UI patterns, server-side ack patterns,
  append-only mechanisms, multi_schema_sweep dispatcher,
  confidence floor refinement). The cost of including these is
  ~80 lines; the benefit is the next session doesn't burn 1000+
  context tokens re-discovering them.
- **Bring-up-deterministic** — §0 commands give exact expected
  output. If the env is wrong, the session halts before any code
  change.
- **Indexed** — table of contents (numbered §s); the next
  session can jump directly to §3 (locked decisions) or §8 (action
  plan) without reading sequentially.
- **Subagent-aware** — §2 + §9 explicitly call out where to
  parallelize via subagents (especially Phase 6 Hypothesis
  suites in #4).
- **Stop-condition-explicit** — §5 + the per-phase stop
  conditions in §8.1/8.2 prevent silent scope creep.
- **Style-coherent** — matches the verbose-ping discipline of
  the prior session pings; the next agent inherits the
  communication style without learning it from drift.

Use as-is for the next sub-session. Update only if you decide to
re-order the sub-sessions or add a constraint we surfaced after
this draft was written.
