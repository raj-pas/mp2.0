# Next-Session Kickoff Prompt — Post-R7 Extraction Hardening

This is the exact prompt to paste into a fresh Claude Code session that
continues from HEAD `c07acc8` on `feature/ux-rebuild`. It establishes
the mission, reading order, working phases, and constraints for the
3-day demo + 1-week release window.

> **Tip:** start a fresh session in the repo root
> `/Users/saranyaraj/Projects/github-repo/mp2.0`. Confirm `git log
> --oneline -3` shows `c07acc8 docs(R7): handoff dossier...` at HEAD,
> then paste everything below the line.

---

```
You are continuing a multi-session engineering effort on the MP2.0
codebase (planning-first model portfolio platform with Steadyhand).
The previous session left a complete handoff dossier and an action
plan; your job is to execute the plan with high precision against a
hard deadline.

## Mission

Make the doc-drop → review-screen → commit → portfolio-generation
pipeline production-grade for a limited-pilot demo and release.

Hard deadlines (from the user, locked 2026-05-01):
- Demo to CEO + Chief Product Officer on 2026-05-04 (3 days)
- Release on 2026-05-08 (1 week)

The pipeline must work for real client folders (PDFs + DOCX + xlsx)
end-to-end without manual intervention or surprises during the demo.
Auth/RBAC and audit-immutability validation are explicitly deferred
to post-pilot per the user.

## Phase 0 — Load Context Before Anything Else (~15 min)

Do not write code, do not run destructive commands, do not even
formulate a plan until you have read these files in order. Each one
explains what to read next and why.

1. `docs/agent/post-r7-handoff-2026-05-01.md` — master state-of-
   the-world dossier. 18 sections. Read end-to-end. This is the
   single source of truth for current state, fixed bugs, open
   bugs, gotchas, code pointers, gates, real-PII discipline.
2. `~/.claude/plans/post-r7-extraction-hardening.md` — action plan
   with 7 phases (A–G), concrete sub-tasks, decision trees,
   validation checklists, anti-patterns. Tuned to the 3-day demo
   window.
3. `~/.claude/plans/i-want-you-to-rosy-mccarthy.md` — v36 master
   rewrite plan with 39 locked decisions across phases R0–R10.
   Skim; come back to specific decisions as needed.
4. `MP2.0_Working_Canon.md` (canon v2.8) at repo root — authoritative
   product/strategy/architecture. Skim §11 (extraction), §9.4
   (architecture invariants), §11.8.3 (real-PII discipline).
5. Auto-loaded memory: `MEMORY.md` index already points at
   `project_post_r7_demo_state.md` — verify you've absorbed it.

After reading, run:
- `git status --short --branch` (confirm `feature/ux-rebuild`)
- `git log --oneline -5` (confirm HEAD `c07acc8`)
- The full gate suite from dossier §8.

If gates aren't green at HEAD before you change anything, your
environment is wrong — fix that first. Do not proceed with the
plan against a broken baseline.

Before moving to Phase 1, output a brief status post (under 100
words) to the user confirming:
- You've read the dossier and plan
- The HEAD commit you're at
- The gate-suite results
- Any environment issue that needs fixing first

## Phase 1 — Research / Investigate

Per the action plan Phase A (`~/.claude/plans/post-r7-extraction-
hardening.md`), the first task is to characterize the actual
Bedrock failure modes for the 2 known-bad Niesner documents.

Do NOT fix blind. The "Bedrock did not return valid JSON" message
is a generic catch-all. The actual response from Bedrock for the
failing docs is what tells you whether to:
- Tweak the prompt (cheap)
- Switch to Bedrock structured-output mode (medium effort)
- Bypass Bedrock for tabular content with rule-based extraction
  (medium-high effort)
- Chunk-and-merge for large PDFs (medium-high effort)

Steps (per Phase A.1–A.4 of the action plan):

1. Add a Bedrock-response debug hook in `extraction/llm.py`
   gated on `MP20_DEBUG_BEDROCK_RESPONSES=1`. Writes raw text to
   `MP20_SECURE_DATA_ROOT/_debug/<workspace>/<doc-id>-<ts>.txt`.
   Never to stdout, repo, or chat. Real-PII discipline: never
   commit this code in its on-by-default state — feature-flag it
   off before commit, OR revert before commit.

2. Re-run the 2 failing Niesner docs by:
   - Logging in via curl (procedure in dossier §7)
   - POST to `/api/review-workspaces/<wsid>/documents/<doc-id>/retry/`
   - Run `process_review_queue --once` with the debug env flag set
   - Workspace ID: `d689fe68-c335-44ae-bbb3-104974b7e764`
   - Failed doc IDs: query the DB via `web/manage.py shell`

3. Read the captured debug logs IN A DJANGO SHELL — never paste
   contents into chat. Characterize each response with the
   structural signal table from action plan Phase A.3:
   - Starts with markdown table?
   - Starts with prose preamble?
   - Ends mid-string / mid-array (truncation)?
   - Total chars vs typical Bedrock response budget?

4. Pick interventions per the action plan Phase A.4 decision matrix.
   Document the decision in a table: doc class → failure mode → chosen
   intervention (Option A / B / C) → rationale → expected effect.

Do NOT skip step 4. The per-doc-class decision is what unblocks
Phase 2.

## Phase 2 — Plan + Iterate With User

You have findings from Phase 1. Now sync with the user before
spending hours on the wrong intervention.

Use the `AskUserQuestion` tool to ask all the essential and neededed questions from every single dimension in a single batch:

1. xlsx fix preference: prompt tweak (A) / pre-normalize (B) /
   rule-based bypass (C). Recommend the option that aligns with
   your Phase 1 evidence and explain why in the description.
2. Large-PDF fix preference: smaller input window (A) / chunk-and-
   merge (B) / structured output mode (C). Same recommendation
   pattern.
3. Conflict-resolution UI scope for the demo: minimum-viable
   (single accept/reject per conflict) vs full-mockup parity
   (rationale capture + evidence tooltips).
4. Demo content folder: which client folder to use during the
   live demo. Recommend Seltzer or Weryha (smallest, fastest
   Bedrock turnaround); Niesner has known bugs your fix targets.

After the user answers, propose a sequenced timeline (in the chat,
not as a separate doc) covering Phases A–F of the action plan
mapped to clock time across the 3-day window. Get user OK on the
sequence before starting Phase 3.

If the user redirects scope, follow them. They explicitly prefer
clarifying questions over wrong execution in this 3-day window.

## Phase 3 — Implement

Now you can write code. Execute Phases B → C → D → E from the
action plan in order, with these constraints:

### Per-fix discipline (DO NOT SKIP)

For every code change:

1. Use `TodoWrite` to track sub-tasks. Mark progress in real time.
2. Make the change as small as possible to satisfy the goal.
3. Add a regression test BEFORE marking the fix complete:
   - Backend: pytest in `web/api/tests/test_review_ingestion.py`
   - Frontend: Playwright in `frontend/e2e/foundation.spec.ts`
   - The test must fail without your fix and pass with it.
4. Run the relevant gate(s) after the change:
   - For backend: `uv run ruff check . && uv run ruff format
     --check . && pytest`
   - For frontend: `npm run typecheck && npm run lint && npm run
     build`
5. If a fix grows beyond ~150 lines OR touches more than 3 files,
   stop and check in with the user. The 3-day window favors
   bounded interventions.

### Implementation order

Per the action plan:

- Phase B (failure-code taxonomy): typed `BedrockExtractionError`
  subclasses, mapped to structured `failure_code` strings on
  `processing_metadata`. Replace the generic `ValueError` raises.
  Add tests `test_bedrock_non_json_sets_failure_code`,
  `test_bedrock_token_limit_sets_failure_code`.

- Phase C (xlsx fix): the option you picked in Phase 2. If rule-
  based, add a small header → fact-field mapping; never fabricate
  values; mark `derivation_method="rule_xlsx_v1"` for audit
  honesty. Add tests.

- Phase D (large-PDF fix): the option you picked in Phase 2.
  Start with the cheapest first — if smaller input window
  resolves the 6.2MB PDF, skip chunk-and-merge entirely. Add
  tests.

- Phase E (manual-entry escape hatch): new endpoint
  `/api/review-workspaces/<wsid>/documents/<id>/manual-entry/`,
  frontend hook + button, i18n keys for failure_code copy. Add
  tests.

### Real-PII discipline (LOAD-BEARING — see dossier §10)

- Never quote real client content in code, commits, memory,
  chat, or debug logs that escape `MP20_SECURE_DATA_ROOT`.
- Never `cp` real client files into the repo.
- Real-derived extraction stays on Bedrock ca-central-1 only.
- When characterizing extraction output, use structural counts:
  "field X has Y candidates from Z sources" — never the values.
- Bulk DB modifications (workspaces, jobs you didn't create)
  require explicit user authorization. Locked decision #34
  pre-authorizes only `scripts/reset-v2-dev.sh --yes`.

### Canon invariants (DO NOT VIOLATE — dossier §11)

- §9.4.5: AI extracts and styles, never invents financial numbers.
  If extraction can't recover a field, surface the gap to the
  advisor — do not fabricate.
- §9.4.2: `engine/` does not import Django, DRF, `web/`,
  `extraction/`, or `integrations/`.
- §11.4: source-priority hierarchy; cross-class silent resolution
  is correct (don't surface as conflict).
- §6.3a: vocabulary — building-block fund (not "sleeve" in UX);
  re-goaling, never reallocation; canon-aligned risk descriptors.

## Phase 4 — Thorough Testing

After Phases B–E ship, validate end-to-end before declaring done.

### 4.1 Synthetic full pipeline

Re-run the synthetic curl chain from dossier §3 / handoff-log
2026-05-01. Confirm:
- Workspace create → upload → worker → reconcile → state PATCH →
  6 approvals → commit → portfolio gen all 200.
- No new failure_codes introduced.

### 4.2 Niesner real-PII regression

Create a fresh real_derived workspace, upload all Niesner files
(see dossier §6 for procedure), run worker. Target: 12/12
reconciled. If 11/12 or worse, escalate the residual failure to
Phase 1 (re-investigate that specific doc).

Do not commit Niesner workspace data to the repo or paste
contents to chat. Use the same structural-counts discipline as
the previous session.

### 4.3 Smaller-folder validation

Run end-to-end against a small folder (Seltzer or Weryha — 5
files, 504K each). Demo will use this folder; validate it
beforehand. Target: full pipeline (upload → worker → review →
commit → portfolio) without manual intervention.

### 4.4 Regression test suite

Add or update tests so that any return of the bug class is caught
in CI:

- `test_xlsx_extraction_*` per Phase C (mock or actual xlsx)
- `test_large_pdf_*` per Phase D (synthesized large-text scenario)
- `test_manual_entry_marks_document_and_audits` per Phase E
- Frontend: foundation spec asserts `failure_code` copy renders
  with retry + manual-entry CTA for a failed doc

### 4.5 Full gate suite (dossier §8)

Run every gate. All must be green:
- ruff check + format
- pytest (≥ 319 passing + your new tests)
- makemigrations check
- typecheck + lint + build
- vocab CI
- Playwright e2e against the live host-mode stack

### 4.6 Real-browser manual smoke

Open `localhost:5173` in actual Chrome (not headless), log in,
go to `/review`, drag-and-drop the Seltzer folder, watch the
flow:
- Files attach (counter shows correct count)
- Click Start (mutation fires, toast appears)
- Workspace appears in queue
- Click into workspace
- Watch processing complete (status flips per doc)
- Failed docs (if any) show actionable copy + retry/manual-entry
- Approve sections, commit
- Land on the new household; portfolio generation works

This is the test the previous session missed. Playwright headless
caught nothing wrong; the user's actual browser caught everything.
Do not skip this step.

## Phase 5 — Demo Prep + Handoff Update

### 5.1 Update artifacts

- `docs/agent/post-r7-handoff-2026-05-01.md` §3 ("Where We Are At
  Exactly") — update HEAD + DB state.
- `docs/agent/session-state.md` — update the phase line.
- `docs/agent/handoff-log.md` — append a new dated entry covering
  what you did, what you found, what you fixed, what's still open.
- `~/.claude/projects/.../memory/project_post_r7_demo_state.md`
  — update if state changed materially.
- `~/.claude/plans/post-r7-extraction-hardening.md` — mark phases
  complete; note any deviations from the plan.

### 5.2 Commit

Single logical commit per the project convention. Use HEREDOC
formatting (see CLAUDE.md). Reference the phase number. Do NOT
push to remote unless the user explicitly authorizes — the branch
is currently 4 commits ahead of origin.

Suggested commit message structure:

  fix(R7): extraction-quality hardening — xlsx + large-PDF +
  failure-code taxonomy + manual-entry hatch

  [Brief summary of what changed and why]

  - [Sub-bullet per fix with file refs]

  Niesner real-PII run now reaches N/12 reconciled (was 10/12).
  Synthetic full pipeline still green. New regression tests:
  test_X, test_Y, test_Z.

  Gates: 319+N pytest, ruff, typecheck/lint/build, vocab CI,
  Playwright e2e.

### 5.3 Demo readiness checklist

Before declaring demo-ready, confirm:

- [ ] Real-browser smoke (4.6) passes against the demo folder
- [ ] No console errors on the happy path (font OTS errors are
      acceptable — known cosmetic debt)
- [ ] All failure_codes have advisor copy in `en.json`
- [ ] Manual-entry button reachable for any failed doc
- [ ] Conflict-resolution UI exists if user escalated P0 #2
      into this session (otherwise note as P0 #2 backlog)
- [ ] Worker idle (queue drained) so demo uploads land at front
- [ ] DB has clean Sandra/Mike + the demo folder workspace,
      nothing else (run `scripts/reset-v2-dev.sh --yes` if
      authorized to wipe + reseed)

### 5.4 Final user check-in

Post a status update in chat covering:
- What was fixed (with HEAD commit)
- Niesner reconciled count (target 12/12)
- Demo-folder validation result
- Any remaining P0 items that didn't fit the window
- Recommendation for the demo flow (which folder, which clicks)

Ask the user one closing question via `AskUserQuestion`:

  Are we go for demo on 2026-05-04, or do you want one more
  round on a specific failure mode before then?

## When to Stop and Ask

Use `AskUserQuestion` when:
- Phase 1 evidence points to a Bedrock prompt-level rewrite
  (vs per-doc-type fix)
- A fix would touch `engine/` schemas in a way that affects
  `engine_output.link_first.v2` schema version
- Real-PII discipline is ambiguous (e.g., should this debug
  log live in the secure root?)
- A fix grows beyond ~150 lines OR touches more than 3 files
- The R10 sweep across all 7 folders surfaces a NEW failure
  pattern not covered by Phases C/D
- You're considering pushing to remote (`feature/ux-rebuild`)

Don't ask:
- "Should I add a regression test?" — yes, always
- "Should I run the gates before committing?" — yes, always
- "Should I read the dossier?" — yes, you should already have
- "Which option of the 3 in the action plan should I pick?" —
  pick the smallest one that ships, document the choice, move on

## Anti-Patterns (DO NOT REPEAT)

From dossier §14 — bugs we just spent a day finding:

1. React 18 deferred state setter + live event reference + sync
   mutation = race condition. Snapshot live refs synchronously
   before mutating their source.
2. Frontend hardcoded enums diverging from backend `TextChoices`
   — drive frontend types off the wire shape until openapi-
   typescript codegen lands (P0 #5).
3. Hardcoded section-list on the frontend — read
   `workspace.required_sections` from the serializer.
4. Generic `failure_code = exc.__class__.__name__` — replace with
   typed exceptions and structured codes (Phase B).
5. 10/10 Playwright pass = ship-ready confidence — it's not. Add
   explicit intermediate-state assertions, run real-browser smoke.
6. "Bedrock did not return valid JSON" as the only error — replace
   with `BedrockNonJsonError`, `BedrockTokenLimitError`, etc.
7. Adding default values to make a doc reconcile — violates canon
   §9.4.5. Surface the gap, never fabricate.
8. Pushing without authorization.

## Success Looks Like

At end of session:
- HEAD ahead of `c07acc8` with one logical commit per phase (or a
  single squashed commit if all phases land cleanly).
- 319+N pytest passing, all gates green.
- Niesner real-PII run: 12/12 reconciled OR known residual failure
  routed to manual-entry with clear advisor copy.
- Real-browser smoke against the demo folder passes.
- Handoff dossier + memory updated. Next session can pick up
  cleanly.
- User has explicitly OK'd "go for demo" or specified one more
  iteration.

## Tone + Working Style

The user has been burned by overconfident "ship-ready" claims.
Be candid about uncertainty. Do not overclaim test coverage.
Demand verifiable evidence per change. When asked "is this ready?",
answer with the specific evidence (gate results, regression test
ids, real-browser smoke confirmation), not opinions.

You have full authorization to:
- Read any file in the repo
- Run gates, pytest, Playwright
- Edit any file under the repo (with the canon constraints
  above)
- Run the worker, restart Vite/backend if needed (with caution
  per process-killing permission rules)
- Commit to `feature/ux-rebuild` after gates green

You do NOT have authorization to (without explicit confirmation):
- Push to `origin`
- Bulk-modify ProcessingJobs from prior sessions (only the full
  reset script is pre-authorized)
- Process real-PII folders other than what the user names in
  Phase 2 (recommend smaller folders for cost + latency)
- Spend over $10 on Bedrock without warning the user first

Begin with Phase 0. Do not skip ahead.
```

---

## How to use this prompt

1. Open a fresh Claude Code session in the repo root.
2. Verify HEAD: `git log --oneline -3` should show `c07acc8 docs(R7): handoff dossier...`.
3. Copy everything between the triple-backtick fences above and paste as the first user message.
4. The session will read context, run gates, and check in with you before any code change.

## Customization knobs

If you want to tighten or relax the next session's behavior, edit the **content inside the fenced block** before pasting. Common adjustments:

- **Move auth/audit back into scope:** delete the "explicitly deferred" line in the Mission section and add P0 items to Phase 3.
- **Restrict Bedrock spend further:** change the "$10" in the authorization list to a tighter cap.
- **Authorize `git push`:** add it to the authorization list and remove from the blocked list.
- **Pick a different demo folder up-front:** add the folder name to Phase 2's recommendation so the session doesn't ask.
- **Skip Phase 1 investigation** and go straight to a fix you've already chosen: replace Phase 1 with "the user has decided: xlsx → Option C, large-PDF → Option A; proceed directly to Phase 3."
