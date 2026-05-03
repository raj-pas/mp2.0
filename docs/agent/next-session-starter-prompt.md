# Next-Session Starter Prompt — Sub-sessions #8 → #11 (Pilot-quality close-out)

**Use this verbatim.** Copy from BEGIN to END into the next session;
the agent has no memory of the prior session.

---

BEGIN

You are continuing the **MP2.0 beta-pilot hardening** — a multi-sub-
session engineering effort to ship production-grade software for
Steadyhand's 3-5 advisor limited-beta pilot.

**Hard deadlines:**
- Demo to CEO + CPO: Mon 2026-05-04
- Limited-beta pilot release: Mon 2026-05-08

**Branch:** `feature/ux-rebuild` (cut from `main` for v36 UI/UX rewrite)
**Tag at last sub-session boundary:** `v0.1.0-pilot` at `d2abfa1`
**HEAD at session start:** `59fed18` (sub-session #8 plan + tracking foundation)

The user is **Saranyaraj Rajendran** (technical lead at Purpose Inc.),
collaborating with Fraser/Lori/Amitha/Raj. Real-PII pilot data lives
at `/Users/saranyaraj/Documents/MP2.0_Clients/` (7 folders:
Gumprich, Herman, McPhalen, Niesner, Schlotfeldt, Seltzer, Weryha).

Auto mode is active. Execute autonomously. Minimize interruptions.
Halt + `AskUserQuestion` only on the locked stop-points (§7 below).

---

## 0. Pre-flight verification (do this BEFORE anything else)

```bash
cd /Users/saranyaraj/Projects/github-repo/mp2.0

# Branch + HEAD
git status --short --branch          # expect: feature/ux-rebuild, clean
git log --oneline -5                 # newest at top
# Expected: 59fed18 docs: sub-sessions #8-#11 roadmap + project tracking foundation
#           9d03013 docs: cumulative handoff for sub-sessions #3-#7
#           3d16134 Phase 7 e2e validation: live-stack passes + 1 a11y bug fixed
#           4864759 Phase 6.9 + monitoring: perf budget gate + JSON logging + request-id
#           d90cd6f Phase 6 deep tests + 2 pilot-grade bug fixes (subagent-parallel)

git tag -l "v0.1.0*"                 # expect: v0.1.0-pilot

# Backend gate suite
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 \
  uv run python -m pytest engine/tests/ extraction/tests/ web/api/tests/ web/audit/tests/ \
  --tb=no -p no:warnings --benchmark-disable
# expect: 786 passed, 6 skipped (perf-bench under --benchmark-disable)

uv run ruff check . && uv run ruff format --check .
bash scripts/check-pii-leaks.sh      # expect: PII grep guard: OK
bash scripts/check-vocab.sh          # expect: vocab CI: OK
bash scripts/check-openapi-codegen.sh  # expect: OpenAPI codegen gate: OK
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 \
  uv run python web/manage.py makemigrations --check --dry-run

# Frontend gates
cd frontend && npm run typecheck && npm run lint && npm run build && npm run test:unit
# expect: typecheck/lint/build clean; 40 Vitest passing
cd ..

# Live stack
docker compose ps                    # expect: backend + db running, both up
curl -s -o /dev/null -w "backend: %{http_code}\nfrontend: " http://localhost:8000/api/session/
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5173/
# expect: 200 / 200

# Env
echo "MP20_SECURE_DATA_ROOT=$MP20_SECURE_DATA_ROOT"
ls /Users/saranyaraj/Documents/MP2.0_Clients/ | head -8
# expect: secure root set; 7 client folders present
```

If ANY check is red BEFORE you change anything, halt and ping the
user — environment is wrong.

---

## 1. Read in this order (load-bearing)

These docs are the source of truth. If anything in this prompt
conflicts with them, **the docs win**.

1. **`docs/agent/sub-sessions-8-11-plan.md`** — single roadmap doc
   for the four sub-sessions you're executing. Status timeline per
   item. **Read this first.** Contains exit criteria + stop conditions
   + locked stop-and-ask points.
2. **`docs/agent/bedrock-spend-2026-05-03.md`** — append-only spend
   ledger. Track every Bedrock canary run here.
3. **`docs/agent/post-pilot-improvements.md`** — append-only backlog
   for deferred items.
4. **`docs/agent/handoff-log.md`** — read the last 3 entries (newest
   first: `2026-05-03 (sub-sessions #3 → #7)`,
   `2026-05-03 (sub-session #2)`, `2026-05-03 (sub-session #1,
   hardening pass)`). Captures session-by-session deltas + diagnoses.
5. **`docs/agent/production-quality-bar.md`** — load-bearing quality
   bar; per-surface UX-polish checklist + comprehensive test-coverage
   map. Every Tier-3 polish item is anchored here.
6. **`docs/agent/ux-spec.md`** + **`docs/agent/design-system.md`** —
   durable UX canon. Read before any new advisor-facing surface work.
7. **`docs/agent/phase9-fact-quality-iteration.md`** — design for
   sub-session #9 fact-quality recovery (5 alternatives canvassed,
   layered approach recommended).
8. **`docs/agent/r10-sweep-results-2026-05-02.md`** — pre-Phase-9
   baseline (12 docs, −41% recall regression context).
9. **`docs/agent/phase7-validation-results-2026-05-03.md`** — Phase 7
   automated e2e results + procedures the user is supposed to run.
10. **`docs/agent/pilot-rollback.md`** + **`docs/agent/pilot-success-metrics.md`**
    — Sev-1 rollback procedure + pilot KPIs.
11. **`~/.claude/plans/you-are-continuing-a-playful-hammock.md`** —
    master plan with 50+ user-locked decisions. Skim §11
    Constraints/Tripwires + §6 Anti-Patterns.
12. **`MP2.0_Working_Canon.md`** — product/strategy/regulatory/
    architecture canon. Reference §6.3a + §16 (vocabulary), §9.4.2
    (engine purity), §9.4.5 (AI-numbers rule), §11.4 (source-priority
    hierarchy), §11.8.3 (real-PII discipline).

Auto-memory at
`~/.claude/projects/-Users-saranyaraj-Projects-github-repo-mp2-0/memory/MEMORY.md`
auto-loads the most-load-bearing memories on session start.

---

## 2. Where you are in the journey

### Done (sub-sessions #1 → #7) — 13 commits past `1c4e0aa`

| Sub-session | Phases | HEAD | Tests added |
|---|---|---|---|
| #1 | 5b.3 + 5b.8 + hardening (orphan workspace) | `1c4e0aa` | +1 backend |
| #2 | 5b.4/5/7/10/11/12/13 + UX polish | `85d64b2` | +19 backend |
| #3 | 5c UX docs + Phase 6 scaffolding (Vitest + RTL + jest-dom) | `d85c0bc` | +8 Vitest |
| #4 | Phase 6 deep tests (subagent-parallel × 4) + 2 bugs closed | `d90cd6f` | +329 backend +32 Vitest |
| #5 | Phase 6.9 perf gate + JSON logging + request-id | `4864759` | +10 backend |
| #6 | Phase 7 e2e validation (live stack) + 1 a11y bug closed | `3d16134` | (live-stack validation) |
| #7 | Cumulative handoff + close-out docs | `9d03013` | — |

**Bugs closed during the journey** (don't re-introduce):
- REDACT-2: AMEX 4-6-5 PII leak (sub-session #4)
- Tour TOCTOU race (sub-session #4)
- Color-contrast WCAG 2.1 AA fail (sub-session #6)
- JSON logger Docker import failure (sub-session #6)
- Orphan-workspace race on 401 (sub-session #1 hardening)

### Pre-authorized + sequenced (sub-sessions #8 → #11)

User explicitly approved 2026-05-03 ("do all of Tier 1, 2, 3 right
now"; OCR via Claude PDF/vision support; Bedrock spend **no hard
cap** — soft escalation $200/sub-session, $500 cumulative; "automate
everything" including R10 7-folder sweep via Playwright).

| Sub-session | Scope | Estimate |
|---|---|---|
| **#8 (in progress)** | OCR/vision foundation | 2 days, ~$5-15 canary |
| #9 | Phase 9 fact-quality recovery | 1.5 days, ~$15-30 |
| #10 | Tier 1 advisor friction (incl. ASK on undo) | 2 days |
| #11 | Tier 2+3 + automated R10 sweep + close-out | 3 days, subagent-parallel |

Total estimate: **8-10 days, $30-80 Bedrock**.

### Sub-session #8 status (at session boundary)

`HEAD 59fed18` — project tracking docs shipped (the three above
in §1 reading list 1-3). Detection-helper implementation NOT yet
started. Next concrete action is §3 below.

---

## 3. Sub-session #8 — Resume here

**Goal:** OCR/vision ingestion foundation — Croesus CRM image-PDFs
extract facts via Bedrock vision instead of returning empty (current
text-only path returns 0 facts on scanned docs → advisor manually
adds 30+ facts/doc via 5b.10/11).

**Architecture (verified 2026-05-03 via Anthropic docs):**
- Bedrock `InvokeModel` API supports native PDF document blocks
  (NOT Converse — Converse falls back to text-only without citations
  enabled)
- `AnthropicBedrock` SDK uses `InvokeModel` by default
- ca-central-1 fully supports PDF + vision for Sonnet 4.6 + Opus 4.7
- Real-PII data residency preserved
- ~7K tokens for a 3-page PDF in visual mode (vs ~1K text-only)
- ~$0.10/Croesus-doc estimated; ~$7 for full 7-folder R10 sweep

**Existing scaffold to extend:**
- `extraction/llm.py:204` — `extract_visual_facts_with_bedrock` uses
  per-page rasterization (keep as fallback for non-PDF images)
- `extraction/parsers.py:_parse_pdf` (line 31-49) — already returns
  `kind="ocr_required"` for zero-text PDFs (signal for routing)
- `extraction/pipeline.py:extract_facts_for_document` (line 79-105) —
  already dispatches text vs vision (extend with native-PDF branch)

**Files to touch:**
1. `extraction/parsers.py` — add `is_likely_image_pdf(parsed)` helper
   (also catches low-density text — `<50 chars/page`)
2. `extraction/llm.py` — add
   `extract_pdf_facts_with_bedrock_native(path, ...)` that sends PDF
   as `{"type": "document", "source": {"type": "base64", "media_type":
   "application/pdf", "data": <b64>}}`
3. `extraction/pipeline.py` — dispatch: PDF + image-likely → native
   path; non-PDF image → existing image-blocks path; else → text path
4. Cost-tracking: every Bedrock call writes `bedrock_input_tokens`,
   `bedrock_output_tokens`, `bedrock_cost_estimate`,
   `extraction_path` to `processing_metadata`. Append per-call to
   `docs/agent/bedrock-spend-2026-05-03.md`.

**Tests** (`extraction/tests/test_vision_pdf_path.py`):
- Synthetic image-PDF fixture (rendered text → PDF → no extractable text)
- Mock Bedrock vision response → assert facts via vision path
- Real Niesner image-PDF integration test (gated on real-PII flag)
- Detection-helper unit tests (text-rich vs sparse vs zero)
- Cost-tracking metadata assertions

**Real-PII canary** (sub-session #8.5):
- Pick 1-2 Niesner image-PDFs from
  `/Users/saranyaraj/Documents/MP2.0_Clients/Niesner/` that previously
  failed text extraction
- Run through new vision path
- Capture: facts extracted (structural counts only), token usage, cost
- Append to spend ledger
- Real-PII discipline: structural counts only — no values, no quotes

**Stop conditions for #8:**
- Detection false-positive rate >10% → tune threshold
- Per-doc vision cost >$0.50 → halt + ask
- Real-PII Niesner canary regresses fact count vs prior text path → diagnose

**Exit criteria** (verify before moving to #9):
- [ ] Native PDF path implemented + dispatched
- [ ] Detection helper bounded false-positive
- [ ] 5+ unit tests passing; integration test against synthetic image-PDF
- [ ] Audit metadata includes per-call token + cost estimate
- [ ] Spend ledger updated with sub-session #8 canary
- [ ] Real-PII Niesner canary: ≥1 doc that previously failed now extracts facts
- [ ] Full backend gate suite green
- [ ] Per-phase ping ~400 words

---

## 4. Sub-sessions #9, #10, #11 — upcoming

After #8 exits cleanly:

### Sub-session #9 — Phase 9 fact-quality recovery (~1.5 days)

Layered approach per `docs/agent/phase9-fact-quality-iteration.md`:
- **9.1** Permissive base prompt (relax strict no-fabrication copy
  in `extraction/prompts/base.py:NO_FABRICATION_BLOCK`)
- **9.2** Per-type strict guards (KYC must extract DOB; statement
  must extract balances; meeting note may infer aspirational facts
  with confidence cap)
- **9.3** Inferred-with-evidence-quote validation (every inferred
  fact MUST cite verbatim quote; missing quote → drop)
- **9.4** Re-canary against Seltzer + Weryha; capture pre/post recall
  in `docs/agent/r10-sweep-results-2026-05-03.md`

**Stop conditions:**
- Recall recovery <20pp → escalate
- Hallucinated section paths return → tighten prompts
- Defaulted facts >0 → canon §9.4.5 violation, halt

### Sub-session #10 — Tier 1 advisor friction (~2 days)

6 items:
1. Inline edit polish (date/number/dropdown inputs schema-driven)
   — `frontend/src/modals/DocDetailPanel.tsx` `FactEditForm`
2. Field-path autocomplete (full canonical-field listing) —
   `frontend/src/modals/DocDetailPanel.tsx` `AddFactSection`
3. Progress indicator with ETA per doc — `frontend/src/modals/ReviewScreen.tsx`
   `ProcessingPanel`
4. Holistic commit-preview (replace StatePeekPanel JSON)
5. Demo-state restore validated end-to-end (run
   `scripts/reset-v2-dev.sh --yes` + Sandra/Mike + Seltzer/Weryha
   pre-upload + capture wall-clock + structural counts)
6. **Undo on commit — STOP-AND-ASK first** (see §7)

### Sub-session #11 — Tier 2 + Tier 3 + automated R10 sweep + close-out (~3 days)

**Tier 2:**
- **R10 7-folder sweep automation** (Playwright-driven; user
  authorized 2026-05-03). Per-folder: upload all docs via live UI →
  watch reconcile → capture structural counts (reconciled / failed /
  conflict / fact totals) → save to
  `docs/agent/r10-sweep-results-2026-05-03.md`. **Do NOT auto-commit
  households** (preserve demo state).
- Missing-field guidance per section blocker
- Audit timeline visible to advisor (`useAuditTimeline()` hook)
- Conflict-rule heuristics (saved-rule support)
- Size-cap revisited (vision path handles larger PDFs)
- Test-mode visual cue (`data_origin: synthetic` badge)
- Cross-browser smoke (Safari + Firefox spec via Playwright)

**Tier 3 polish** (subagent-parallel for ~6 agents):
Per `docs/agent/production-quality-bar.md` §1.10 [gap] items:
empty states, error recovery, color-blind palette, number/date
formatting audit, long-text truncation, hover delay, wizard
step-progress, save-as-draft, Realign "what's about to change"
preview, drop-zone visual feedback, conflict card progression,
resolved-cards collapse.

**Final close-out:**
- Cumulative ping covering #8-#11
- Tag verification (`v0.1.0-pilot` at `d2abfa1`; user may bump to
  `v0.1.1-pilot` before Mon push)
- Monday push staged but NOT executed (user pushes Mon morning)
- Update CLAUDE.md "Useful Project Memory" with new docs

---

## 5. Critical context (locked decisions)

### From the user 2026-05-03 (most recent)

- **No Bedrock spend cap.** Soft escalation at $200/sub-session,
  $500 cumulative — but no hard cap. Track per-call in spend ledger.
- **Automate R10 sweep.** Don't ask the user to run it manually;
  Playwright drives the upload via the live UI.
- **OCR is Tier-1.** Croesus exports image-PDFs; current pipeline
  returns 0 facts → advisor friction is unacceptable.
- **Bedrock InvokeModel API only** for vision (NOT Converse).
  AnthropicBedrock SDK uses InvokeModel by default. Real-PII stays
  in ca-central-1.
- **Don't deprioritize anything.** Honor every item in Tier 1, 2, 3
  + production-quality-bar §1.10. Both depth + breadth.
- **Project tracking discipline matters.** Per-phase ping (~400 words);
  plan + spend ledger + post-pilot doc updated continuously;
  mid-sub-session checkpoints.

### From earlier locked decisions

- **Branch + push:** stay on `feature/ux-rebuild`; one logical
  commit per phase exit-criteria-met. **No push during the session;**
  user pushes Monday 2026-05-04 morning.
- **Reporting cadence:** verbose ~400-word per-phase exit ping with
  HEAD, diff highlights, audit-finding closures, tests added, full
  gate-suite results, Bedrock $ delta vs estimate, failures
  encountered + resolutions, reasoning, open items, next phase.
- **Branch + commits format:** HEREDOC commit messages per
  CLAUDE.md.
- **Real-PII discipline (canon §11.8.3):** never quote real client
  content in code, commits, memory, chat, or any logs that escape
  `MP20_SECURE_DATA_ROOT`. Use structural counts only.
- **AI-numbers rule (canon §9.4.5):** LLM never invents financial
  numbers, names, dates, or any field. `derivation_method =
  "defaulted"` is forbidden.
- **Source-priority hierarchy (canon §11.4):** SoR > structured >
  note-derived. Cross-class silent. Same-class surfaces as conflict
  cards. Advisor override (FactOverride) is highest priority.
- **Engine-is-library boundary (canon §9.4.2):** `engine/` never
  imports framework code.
- **PII grep guard:** `str(exc)` NEVER in DB columns / API response
  bodies / audit metadata. Use `web/api/error_codes.py:safe_response_payload`
  + `safe_audit_metadata` instead.
- **Audit-event regression (locked #37):** every state-changing
  endpoint emits exactly one audit event. Append-only via DB
  triggers (canon §11.8).
- **Concurrent-edit safety (locked #30):** workspace
  `select_for_update()` before reading/writing dependent rows.
- **Append-only models:** `HouseholdSnapshot`, `FactOverride`,
  `PortfolioRunEvent`. `save()` raises on existing pk.

---

## 6. Per-phase gate suite (FULL — run at every phase exit)

```bash
cd /Users/saranyaraj/Projects/github-repo/mp2.0

# Backend
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 \
  uv run python -m pytest engine/tests/ extraction/tests/ web/api/tests/ web/audit/tests/ \
  --tb=no -p no:warnings --benchmark-disable
uv run ruff check . && uv run ruff format --check .
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 \
  uv run python web/manage.py makemigrations --check --dry-run

# Frontend
cd frontend && npm run typecheck && npm run lint && npm run build && npm run test:unit
cd ..

# Project guards
bash scripts/check-vocab.sh
bash scripts/check-pii-leaks.sh
bash scripts/check-openapi-codegen.sh
```

**Perf gate (separate run, when adding/changing endpoints):**
```bash
DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 \
  uv run python -m pytest web/api/tests/test_perf_budgets.py \
  --benchmark-only --benchmark-min-rounds=20
# expect: 6/6 within budget (P50 < 250ms, P99 < 1000ms — locked #18)
```

If new endpoint with drf-spectacular schema, regenerate via
`cd frontend && npm run codegen` then commit `api-types.ts`.

---

## 7. Stop-and-ask points (locked)

| Sub-session | When | Question |
|---|---|---|
| #10 | Before undo implementation | Undo-on-commit semantics: **soft-undo** (new `review_workspace_uncommitted` audit event + nullify `linked_household_id`; Household stays orphaned in DB; subsequent re-commit creates a NEW household) **OR re-edit flow** (PATCH workspace endpoint takes a household + creates a workspace seeded from its current state). Both honor canon §11.8 append-only audit. A is simpler; B is more production-grade. Default for pilot: A. |
| #11 | After R10 sweep results | If a folder regresses against pre-Phase-4 baseline, gate pilot launch on Phase 9 close-out OR ship with documented gap? |

Anything else surfaces via `AskUserQuestion` only if:
- Fix grows beyond ~150 lines OR
- Bedrock spend approaches $200/sub-session OR
- Real-PII anomaly surfaces (PII leak detected, audit-emission
  count mismatch, etc.)

The user is highly reachable (minute-grade response on stop-condition
asks) — when in doubt, ask.

---

## 8. Anti-patterns (DO NOT)

1. **Re-do work already shipped** (the 13 commits past `1c4e0aa`).
2. **Re-introduce free-form JSON parsing** in extraction (Phase 4
   tool-use migration removed it; don't bring it back).
3. **Allow `derivation_method="defaulted"`** (canon §9.4.5; Phase 7
   sweep eliminated 2 such facts; keep at 0).
4. **Generate hallucinated section paths**
   (`identification.*`, `next_steps.*`, etc.). Tool-use schema
   prevents this; don't loosen the schema.
5. **Bulk-modify ProcessingJob rows** from prior sessions (locked
   authorization explicitly forbids).
6. **Disable PII grep / OpenAPI drift / vocab CI gates** to "ship
   faster".
7. **`str(exc)` in DB columns / API response bodies / audit metadata**
   `detail` fields. Use `web/api/error_codes.py:safe_response_payload`
   + `safe_audit_metadata` instead.
8. **Push to `origin`** without explicit user OK. User pushes Mon.
9. **Skip per-phase commits + pings** to "save time". Verbose
   discipline is what made the prior 13 commits reviewable.
10. **Add comments in code explaining what well-named identifiers
    already convey** (per CLAUDE.md style).
11. **Auto-commit households during R10 sweep** — preserves demo
    state for Mon. Capture structural counts + leave workspaces in
    review_ready state.
12. **Use Bedrock Converse API** for vision PDFs — falls back to
    text-only without citations. InvokeModel only.
13. **Quote real client content in code, commits, memory, or chat.**
    Structural counts only (canon §11.8.3).

---

## 9. Patterns shipped — use them, don't reinvent

- **PII helpers** `web/api/error_codes.py`: `failure_code_for_exc`,
  `safe_exception_summary`, `safe_response_payload(exc, **extra)`,
  `safe_audit_metadata(exc, **extra)`, `friendly_message_for_code`.
- **Atomicity:** `@transaction.atomic` + `.select_for_update()` on
  workspace is canonical for new state-changing endpoints. See
  `ReviewWorkspaceConflictResolveView.post` (Phase 5a) +
  `ReviewWorkspaceFactOverrideView.post` (Phase 5b.10) for templates.
- **Audit-event regression:** mirror `record_event(action="...",
  entity_type="review_workspace", entity_id=..., actor=_actor(request),
  metadata={...})` per locked #37. Emit AFTER atomic block commits to
  avoid orphan rows on rollback.
- **Append-only:** `FactOverride`, `HouseholdSnapshot`,
  `PortfolioRunEvent`. `save()` raises on existing pk.
- **Frontend wire-shape evolution:** extend
  `frontend/src/lib/review.ts` types alongside backend serializer
  changes; regenerate `api-types.ts` via `npm run codegen`; commit
  both. The drift gate verifies.
- **Mutation hook patterns:** see
  `docs/agent/design-system.md` "Mutation Hook Patterns" — defensive
  null check; `qc.invalidateQueries` per query key.
- **Modal / slide-out focus management:** see `docs/agent/design-system.md`
  "Focus Management Patterns" — useEffect + ref (NOT autoFocus attr;
  jsx-a11y/no-autofocus).
- **PDF detection signal:** `extraction/parsers.py:_parse_pdf` already
  returns `kind="ocr_required"` for zero-text PDFs. Extend with
  `is_likely_image_pdf()` for low-density text (`<50 chars/page`).
- **Subagent-parallel discipline:** for Phase 6 deep tests we
  dispatched 4 agents concurrently; each got ~700-1500 line scope
  + clear stop-conditions. For Tier 3 polish in #11, do same with
  ~6 agents.

---

## 10. Communication style

User has been burned by overconfident "ship-ready" claims (the
FileList race lesson; the Phase 4 canary regression caught only by
real-PII validation; the Phase 7 a11y bug caught only by axe-core).
Be candid about uncertainty. Demand verifiable evidence per change.

When user pushes back ("are we really done?"), audit honestly. The
2026-05-03 audit (covered in `docs/agent/handoff-log.md`) showed
real gaps that prompted sub-sessions #8-#11. Don't be afraid to
surface gaps.

When you halt, do it cleanly:
1. Commit any uncommitted work
2. Update `docs/agent/sub-sessions-8-11-plan.md` status timeline
3. Append to `docs/agent/handoff-log.md`
4. Append to `docs/agent/bedrock-spend-2026-05-03.md` if Bedrock
   work happened
5. Ping with `AskUserQuestion`

Don't strand uncommitted work across a halt.

---

## 11. Real-PII discipline (LOAD-BEARING)

Canon §11.8.3 + dossier §10:
- **Never** quote real client content in code, commits, memory,
  chat, or any logs that escape `MP20_SECURE_DATA_ROOT`.
- Bedrock `ca-central-1` only for `data_origin: real_derived`.
  Anthropic direct for synthetic.
- Use **structural counts** ("N facts across M sources") — never
  values.
- The R10 sweep automation (sub-session #11) MUST capture only
  structural counts — no fact values, no evidence quotes, no
  workspace labels with client names.
- Sub-session #8 + #9 Bedrock canaries against Niesner / Seltzer /
  Weryha: real-PII data flows through Bedrock. Audit metadata
  captures token counts + extraction_path + structural fact counts
  ONLY. Spend ledger entries are structural.

If you discover any `str(exc)` / raw client text leaking into a DB
column / API response / audit metadata: STOP, fix, regression test,
gate suite green before continuing.

---

## 12. First concrete action

After running §0 pre-flight verification:

1. **Read** the four most-load-bearing docs (in order):
   - `docs/agent/sub-sessions-8-11-plan.md`
   - `docs/agent/handoff-log.md` (last 3 entries)
   - `docs/agent/production-quality-bar.md`
   - `docs/agent/phase9-fact-quality-iteration.md` (Phase 9 design
     for sub-session #9)

2. **Verify** the current state matches §2 (HEAD `59fed18`,
   sub-sessions #1-#7 done, #8 in progress at "tracking docs done,
   detection helper not started").

3. **Resume sub-session #8.1** (detection helper):
   - Read `extraction/parsers.py` lines 31-49 (existing `_parse_pdf`)
   - Read `extraction/llm.py` lines 204-241 (existing
     `extract_visual_facts_with_bedrock`)
   - Read `extraction/pipeline.py` lines 79-105 (current dispatch)
   - Implement `is_likely_image_pdf(parsed: ParsedDocument) -> bool`
     in `extraction/parsers.py` per the design in
     `docs/agent/sub-sessions-8-11-plan.md` §Sub-session #8 → Detection.

4. **Move through #8.2 → #8.5** sequentially. Per-phase commit + ping.

5. **Stop conditions:** if Bedrock canary cost-per-doc >$0.50 OR
   detection false-positive rate >10% OR real-PII Niesner regresses
   vs prior text path → halt + ping.

If anything in §0 is red OR §1's docs reveal scope creep beyond the
per-phase Stop-condition thresholds, halt + `AskUserQuestion` before
coding.

---

## 13. Success criteria for the entire session

At the end of sub-session #11:
- HEAD ahead of `59fed18` with 25-50 commits across #8-#11
- 786 → ~1100 backend pytest passing (estimate +300 new)
- 40 → ~80 frontend Vitest passing (estimate +40 new)
- 18 → ~25 Playwright e2e passing (estimate +5-10 new for cross-
  browser + R10 sweep specs)
- All gate suites green at each sub-session boundary
- Bedrock cumulative spend tracked + under $500 (or escalation
  doc'd)
- R10 7-folder sweep complete with structural results in
  `docs/agent/r10-sweep-results-2026-05-03.md`
- Phase 9 fact-quality recovery achieves ≥20pp recall recovery vs
  HEAD `9d03013` baseline
- All Tier 1, Tier 2, Tier 3 [gap] items closed
- Cross-browser smoke green (Safari + Firefox)
- Demo state restored for Mon 2026-05-04 (script + script
  end-to-end validated)
- User-locked ASKs answered (undo semantics; R10 regression handling)
- Final cumulative ping covering #8-#11

The user pushes Monday 2026-05-04 morning. The pilot launches Mon
2026-05-08. Get ready.

END

---

## Notes for the writer (NOT for the next session)

These notes are for you (the human reviewing this prompt before
copy-pasting), not for the next agent.

- This prompt is ~600 lines vs the prior ~482. The extra fidelity
  is justified by the OCR/vision architectural addition + the
  4-sub-session roadmap + the project tracking discipline + the
  pre-authorized scope.
- Stop-and-ask points are locked + cited at §7 + at sub-session
  start. The next agent should NOT re-litigate these.
- The §1 reading list is in DEPENDENCY order. The plan doc is the
  single roadmap; everything else feeds into specific sub-session
  tasks.
- §11 (Real-PII discipline) is intentionally redundant with
  earlier sections. The canon §11.8.3 violation risk is high
  enough that bordering on too-cautious is the right call.
- Per-sub-session commit + ping discipline is what made the prior
  13 commits reviewable. Maintain it.
- If the next agent's context allows it, continue all 4 sub-sessions.
  If context limit approaches, halt at sub-session boundary cleanly
  + write a fresh starter prompt for the remainder.
- Prior versions of this prompt are visible in git history; this
  one is for sub-session #8 onwards only.
