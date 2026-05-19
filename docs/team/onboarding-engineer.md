---
title: Engineer onboarding — Day 1 + Week 1
owner: Saranyaraj Rajendran
last_revised: 2026-05-12
status: living
update_when: A build/run command changes (uv sync, docker compose,
  gate-suite commands), the synthetic Sandra & Mike Chen fixture
  changes shape, the Phase 0 reading list changes, a subsystem tour
  becomes stale, or a new "how we work" norm gets locked in.
---

# Engineer onboarding

Welcome to MP2.0. This guide takes you from `git clone` to your first
commit, then through a Week-1 tour of each subsystem so you have
hands-on context before being asked to ship a real change.

The voice here is second-person ("you'll set up…") — it's a guide, not
a reference. The reference material lives in
[`architecture-diagrams.md`](architecture-diagrams.md),
[`glossary.md`](glossary.md), and the
[`adr/`](adr/) folder.

## See also

- [`README.md`](README.md) — folder index + conventions + reading order
- [`product-brief.md`](product-brief.md) — why MP2.0 exists (read first)
- [`architecture-diagrams.md`](architecture-diagrams.md) — visual map
- [`real-pii-handling.md`](real-pii-handling.md) — what you can and
  can't do with real client data
- [`troubleshooting.md`](troubleshooting.md) — keep this open while you
  set up
- [`../../CLAUDE.md`](../../CLAUDE.md) — non-negotiable rules + build
  commands
- [`../../MP2.0_Working_Canon.md`](../../MP2.0_Working_Canon.md) — the
  canon

## Before Day 1

Make sure you have:

- Access to the GitHub repo (`github.com:raj-pas/mp2.0`).
- A Purpose email + 1Password access.
- macOS or Linux (Windows works via WSL2 but isn't actively tested).
- The Slack channel `#mp20-pilot` (DM the tech lead for invite).
- Access to the team's Linear project (`MP20`).

Also, **read the product brief first**:
[`product-brief.md`](product-brief.md). It's a single screen and
explains why MP2.0 exists. Without that context, the setup steps below
won't make sense.

## Day 1: get the system running

### Step 1 — Clone and configure environment

```bash
git clone git@github.com:raj-pas/mp2.0.git
cd mp2.0
cp .env.example .env
```

Open `.env` and set `MP20_SECURE_DATA_ROOT` to a **path outside the
repo**. The system rejects repo-local paths at startup. Example:

```
MP20_SECURE_DATA_ROOT=/Users/yourname/mp20-secure-data
```

Then:

```bash
mkdir -p "$HOME/mp20-secure-data"
```

(Or wherever you pointed `MP20_SECURE_DATA_ROOT`.)

**Verify it worked:**

```bash
grep MP20_SECURE_DATA_ROOT .env
# Should print: MP20_SECURE_DATA_ROOT=/Users/yourname/mp20-secure-data
ls -la "$HOME/mp20-secure-data"
# Should list an empty directory
```

If either fails, fix before proceeding.

### Step 2 — Bring up the Docker Compose stack

```bash
docker compose up --build
```

This builds four services: `db` (Postgres 16), `backend` (Django + DRF),
`worker` (process_review_queue), `frontend` (Vite dev server on
:5173). First build takes 3–10 minutes depending on bandwidth.

The backend automatically:

- Runs migrations.
- Seeds the Default CMA snapshot (`seed_default_cma`).
- Loads the synthetic Sandra & Mike Chen persona
  (`load_synthetic_personas`).
- Bootstraps a local advisor + financial-analyst user
  (`bootstrap_local_advisor --skip-if-missing`).

**Verify it worked:**

```bash
# In a separate terminal:
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/session/
# Should print: 200
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5173/
# Should print: 200
```

If you get connection refused, check `docker compose ps` to confirm
all four services are healthy. If the backend is unhealthy, check
`docker compose logs backend` for the failure mode.

### Step 3 — Log in (in real Chrome)

Open `http://localhost:5173` in **real Chrome** (not a Playwright
headless instance). Log in with:

- Email: `advisor@example.com`
- Password: whatever you set in `.env` as `MP20_LOCAL_ADMIN_PASSWORD`
  (the default in `.env.example` is `change-this-local-password`).

You should see a client list with **Sandra & Mike Chen** (the
synthetic baseline persona — Mike Chen born 1964, Sandra Chen born
1968, household risk score 3, $1.308M AUM across four accounts:
Mike RRSP $620K, Sandra RRSP $430K, Sandra-owned TFSA labelled
"joint" $150K, Mike Non-Reg $108K, three goals named "Retirement
income," "Emma education," "Ski cabin option" in the fixture).

**Verify the golden path:**

1. Click into Sandra & Mike Chen.
2. You should see the AUM strip + the squarified treemap + the
   household-level portfolio panel with a RecommendationBanner
   showing a run signature.
3. Click on a goal in the treemap (e.g., Retirement Income).
4. You should see the GoalRoute with the 5-point RiskSlider, the
   AllocationBars, the FanChart projection.
5. Toggle the ModeToggle from "by-account" to "by-goal" in the
   TopBar and verify the treemap re-renders.

If any of this fails, see [`troubleshooting.md`](troubleshooting.md).

### Step 4 — Run the gate suite

In a separate terminal (with the Docker stack still running):

```bash
# Backend gates
uv sync --all-groups
uv run ruff check .
uv run ruff format --check .
scripts/test-python-postgres.sh
```

**Verify:** all four commands exit 0. The `pytest` run takes ~2–4
minutes and should report something close to **1,198 tests passing**
(as of `v0.1.3-pilot-quality-closure`; the exact number drifts as
new tests are added — what matters is zero failures).

```bash
# Frontend gates
cd frontend
npm install
npm run typecheck
npm run lint
npm run build
```

**Verify:** all four commands exit 0. The build should produce
`frontend/dist/assets/*.js` with total gzipped size ≤ 290 kB (the
bundle gate). Current baseline: ~278.94 kB.

```bash
# Playwright synthetic e2e
PLAYWRIGHT_BASE_URL=http://localhost:5173 npm run e2e:synthetic
```

**Verify:** 13 foundation tests pass. (The full Playwright matrix
includes visual-verification, regression-coverage, pilot-features-axe,
and cross-browser specs; you can run them individually.)

If any gate fails, **don't push past it.** Fix locally or ask in
Slack. See the "Red flags" section below.

### Step 5 — Phase 0: read the canon and the docs/agent/ infrastructure

Before any code change, the project has a mandatory reading-order
discipline. Spend 30–45 minutes:

1. [`../agent/session-state.md`](../agent/session-state.md) — current
   phase, branch, HEAD, gate-suite status. Tells you where the
   project is right now.
2. [`../agent/open-questions.md`](../agent/open-questions.md) — what's
   still open. Affects what you should and shouldn't change.
3. [`../../CLAUDE.md`](../../CLAUDE.md) — the 16 non-negotiable
   architecture rules.
4. [`../../MP2.0_Working_Canon.md`](../../MP2.0_Working_Canon.md) —
   skim the table of contents; deep-read Parts 1 (mission), 4
   (investment theory), 9 (engineering architecture), 11 (extraction).
5. [`../agent/handoff-log.md`](../agent/handoff-log.md) — read the
   most recent 5–10 entries (the tail). This is the chronological
   record of every recent session.

This is "Phase 0" in the project's session protocol. Don't skip it.
Many of the bugs the team has paid to learn are encoded in those
documents.

## Day 2–5: subsystem tour

The goal of Week 1 is to **touch each subsystem** so you have hands-on
context before being asked to ship a real change. Don't try to
understand everything — just navigate each layer once, read the key
files, and ask questions in Slack.

### Tour 1: Engine (`engine/`)

The pure-Python optimizer library. Per ADR-0001, the engine has
**zero** inbound imports from web/extraction/integrations/Django/DRF.

- Read [`engine/__init__.py`](../../engine/__init__.py) — the public
  re-exports.
- Read [`engine/optimizer.py`](../../engine/optimizer.py) — the
  `optimize()` entry point.
- Read [`engine/projections.py`](../../engine/projections.py) — the
  lognormal projection math + external-holdings penalty.
- Read [`engine/tests/test_engine_purity.py`](../../engine/tests/test_engine_purity.py)
  — the AST-enforced boundary guard. If you ever try to import Django
  from engine code, this is what fails.
- Run just the engine tests: `uv run pytest engine/tests/ -q`.

**Try this:** add a print to `engine/optimizer.py:optimize()`, run
`uv run pytest engine/tests/test_engine.py`, see your print appear,
remove it. You've now touched the engine.

### Tour 2: Web (`web/api/`)

The Django/DRF application. ~5,000 lines in `views.py`, ~1,000 lines
in `models.py`, ~1,800 lines in `review_state.py`.

- Read [`web/api/models.py`](../../web/api/models.py) — every Django
  model with its key fields.
- Read [`web/api/views.py`](../../web/api/views.py) — DRF views; pay
  attention to the 5 typed exceptions near the top
  (`EngineKillSwitchBlocked`, etc.) and the helper trio
  (`_trigger_portfolio_generation`, `_trigger_and_audit`,
  `_trigger_and_audit_for_workspace`).
- Read [`web/api/engine_adapter.py`](../../web/api/engine_adapter.py)
  — the **boundary** between Django models and engine schemas.
- Read [`web/api/review_state.py`](../../web/api/review_state.py) —
  pay attention to `commit_reviewed_state` and
  `_merge_household_state` (around line 1505 — the only place
  lowercase account types get normalized).
- Read [`web/audit/models.py`](../../web/audit/models.py) + the
  `record_event` writer at [`web/audit/writer.py`](../../web/audit/writer.py)
  — the append-only audit subsystem.

**Try this:** in a Django shell (`docker compose exec backend uv run
python web/manage.py shell`), query
`AuditEvent.objects.filter(action__startswith='portfolio_').order_by('-created_at')[:5]`
and read the metadata. Then try to `delete()` one — it'll raise. That's
the model guard (ADR-0002) + the DB trigger (ADR-0013) working.

### Tour 3: Extraction (`extraction/`)

The Layer 1–5 ingestion pipeline.

- Read [`extraction/__init__.py`](../../extraction/__init__.py) + the
  individual layer files (`layer1_ingestion.py`, `layer2_text.py`,
  `layer3_facts.py`, `layer4_reconcile.py`, `layer5_review.py`).
- Read [`extraction/llm.py`](../../extraction/llm.py) — the Bedrock
  client + the typed exceptions (`BedrockNonJsonError`,
  `BedrockTokenLimitError`, etc.).
- Read [`extraction/entity_alignment.py`](../../extraction/entity_alignment.py)
  — the three-tier matcher (ADR-0007). The Tier-2 band logic is
  recent (2026-05-05); read the `MergeCandidate` dataclass.
- Read [`extraction/prompts/`](../../extraction/prompts/) — per-doc-type
  prompt builders. The shared no-fabrication discipline (canon §9.4.5)
  lives in `base.py`.

**Try this:** upload a small synthetic doc to a fresh workspace via
the `/review` UI. Watch the worker process it in the logs
(`docker compose logs -f worker`). See the extracted facts surface
in the workspace UI.

### Tour 4: Frontend (`frontend/`)

React 18 + Vite + TypeScript strict. The v36 design system.

- Read [`frontend/src/App.tsx`](../../frontend/src/App.tsx) — the
  router + ErrorBoundary tree.
- Read [`frontend/src/routes/`](../../frontend/src/routes/) — the four
  primary routes (Household, Account, Goal, Wizard).
- Read [`frontend/src/goal/`](../../frontend/src/goal/) — the
  engine→UI display surfaces (RecommendationBanner, AdvisorSummaryPanel,
  OptimizerOutputWidget, MovesPanel, SourcePill).
- Read [`frontend/src/lib/household.ts`](../../frontend/src/lib/household.ts)
  — the four engine-output navigation helpers (`findGoalRollup`,
  `findHouseholdRollup`, `findGoalLinkRecommendations`,
  `findLinkRecommendationRow`).
- Read [`frontend/src/modals/ConflictPanel.tsx`](../../frontend/src/modals/ConflictPanel.tsx)
  and [`frontend/src/modals/ReviewScreen.tsx`](../../frontend/src/modals/ReviewScreen.tsx)
  — the review workspace UI.

**Try this:** edit a copy string in `frontend/src/i18n/en.json`
(e.g., add a typo to a label), reload `http://localhost:5173`,
verify the change. Run `npm run typecheck && npm run lint &&
npm run build`. Revert.

### Tour 5: Tests across all subsystems

- Read [`engine/tests/test_engine_purity.py`](../../engine/tests/test_engine_purity.py)
  — the AST boundary guard.
- Read [`web/api/tests/test_audit_metadata_invariants.py`](../../web/api/tests/test_audit_metadata_invariants.py)
  — the Hypothesis property test for audit-event invariants.
- Read [`web/api/tests/test_goal_risk_override_engine_flow.py`](../../web/api/tests/test_goal_risk_override_engine_flow.py)
  — the regression-coverage pin for the override→engine contract.
- Read [`frontend/src/__tests__/__fixtures__/household.ts`](../../frontend/src/__tests__/__fixtures__/household.ts)
  — the byte-for-byte mockHousehold (locked decision #55).
- Read [`frontend/e2e/foundation.spec.ts`](../../frontend/e2e/foundation.spec.ts)
  — the core synthetic flow Playwright spec.

**Try this:** run a single backend test in isolation. Pick one from
[`web/api/tests/`](../../web/api/tests/) and run
`uv run pytest <path>::<test_name> -v`.

## How we work

These are the team's working norms — codified here because they
matter and because new contributors don't pick them up by osmosis.

### Canon discipline and the Phase 0 reading protocol

Before any code change — especially under deadline pressure — read
the canon section + handoff-log entries + open-questions row relevant
to your change. The full Phase 0 reading order is in the
`mp2-protocol` Claude Code skill, but for human contributors it's:

1. `docs/agent/session-state.md` — where the project is right now.
2. `docs/agent/open-questions.md` — what's open in the area you're
   touching.
3. The relevant canon section.
4. The two or three most-recent `docs/agent/handoff-log.md` entries.

Why this exists: the team has paid (many times) for sessions that
skipped it. A "small fix" that ignores a locked decision can
unintentionally re-introduce a fixed bug class. Phase 0 takes
~15 minutes; skipping it has cost days.

### Real-browser smoke (never skip)

The Playwright headless test suite caught **nothing** of the FileList
ref race or the StrictMode-double-update bug. The user's actual Chrome
caught both. After any frontend change:

1. Open `http://localhost:5173` in real Chrome (not headless).
2. Walk the golden path + edge cases you touched.
3. Watch the console for errors.

If you can't run a real browser, say so explicitly rather than
claiming the change "works." See ADR-0009 references + master dossier
§9.5 for the documented "honest meta-call" lesson.

### Clarifying questions over wrong execution

Especially under deadline pressure. The team has paid more for wrong
execution than for clarifying questions. Examples of good questions
to ask:

- "Should this change supersede ADR-NNNN, or is it consistent with
  it?"
- "The canon §X.Y says Y; my change implements Z. Is there a
  rationale I'm missing?"
- "I'm about to commit. Should the new test catch a regression class
  we've seen before, or is this a new failure mode?"

Examples of questions you don't need to ask (the answer is always
yes):

- "Should I add a regression test?" — yes.
- "Should I run the gate suite before pushing?" — yes.
- "Should I read the canon section first?" — yes.

### Evidence before assertions

When you say a change is done, the team wants to see the evidence:
the gate suite output, the real-browser smoke, the audit-event
queries showing the new behavior. "Tests pass" without showing the
output is incomplete.

The "honest meta-call" pattern (documented in `docs/agent/handoff-log.md`
around 2026-05-03's sub-session #11 deferred-work follow-up):
subagent gates pass against the fixtures the subagent itself wrote.
They don't catch regressions in existing higher-level tests or shape
drifts in production payloads. Re-run the FULL gate suite + real
browser after any change.

### Append, don't overwrite

The handoff log is append-only. Session-state is mutable but updated,
not overwritten. The canon evolves with explicit version bumps. The
audit trail (ADR-0002 + ADR-0013) is unmodifiable.

When in doubt about whether to delete or annotate: annotate.

### Vocabulary

See [`glossary.md`](glossary.md). The vocabulary CI guard
(`scripts/check-vocab.sh`) enforces the canon-aligned terms.
Banned: sleeve, reallocation, transfer, low/medium/high risk, bare
Conservative, Phase R[0-9] in client-facing copy.

## Red flags — when to ask for help

Stop and ask in `#mp20-pilot` (or DM the tech lead) if:

- A gate that was passing yesterday is now failing and you didn't
  intentionally change the relevant code.
- A test failure references real-PII content (don't share the
  failure output in Slack; report the test name + ask for a private
  DM).
- You see real client data anywhere it shouldn't be (in logs, in
  commits, in chat). Treat as Sev-1; see
  [`real-pii-handling.md`](real-pii-handling.md).
- You're about to do something the canon says not to do, with a
  rationale that feels reasonable. The canon's "don't"s are paid for
  in lessons; ask before overriding.
- You're about to push to `main` for the first time. Pushing is
  always explicit (the canon says "do not push unless explicitly
  asked"). Confirm scope with the tech lead.
- A migration looks like it'll be irreversible or will affect
  audit data. The audit immutability layer (ADR-0013) is
  load-bearing; any migration that touches it needs review.
- You're confused. The team prefers you ask than guess.

## First "real" task

In Week 2, pick up a real ticket from Linear (`MP20` project). Pair
with the tech lead on the first one — most likely it'll be a small
copy fix or a bug fix surfaced from pilot feedback. The pairing
session covers:

- How to branch off `feature/ux-rebuild` (the current working branch).
- How to write the regression test before the fix.
- How to run the gate suite + real-browser smoke.
- How to write a commit message + handoff-log entry.
- How to open a PR.

After 2–3 paired tickets, you should be independently productive.

## IDE / editor recommendations

VS Code is the team's primary editor. Recommended extensions:

- **Python** (Microsoft) — Python language support.
- **Ruff** (Astral) — fast linting; integrates with `pyproject.toml`.
- **ESLint** — frontend linting.
- **Tailwind CSS IntelliSense** — tab-completion for utility classes.
- **Mermaid Preview** — render the diagrams in
  `architecture-diagrams.md` inline.
- **markdownlint** — flag markdown violations as you write.

A starter `.vscode/settings.json` snippet for ruff format-on-save:

```json
{
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": "explicit"
    }
  }
}
```

Other editors (JetBrains IDEs, Neovim, Emacs) work fine; the team
just doesn't actively test against them.

## Where to find what

| If you're confused about… | Read |
|---|---|
| Why MP2.0 exists | [`product-brief.md`](product-brief.md) + canon Part 1 |
| The architecture | [`architecture-diagrams.md`](architecture-diagrams.md) + the 13 ADRs in [`adr/`](adr/) |
| Domain vocabulary | [`glossary.md`](glossary.md) |
| Real-PII handling | [`real-pii-handling.md`](real-pii-handling.md) |
| What command failed | [`troubleshooting.md`](troubleshooting.md) |
| The non-negotiable rules | [`../../CLAUDE.md`](../../CLAUDE.md) |
| The deepest architecture decisions | canon Part 9 + relevant ADRs |
| What shipped in which tag | [`../../CHANGELOG.md`](../../CHANGELOG.md) |
| The current sprint state | [`../agent/session-state.md`](../agent/session-state.md) |
| The most recent session's work | tail of [`../agent/handoff-log.md`](../agent/handoff-log.md) |
| The active multi-phase plan | `~/.claude/plans/` (most recent file) |

Welcome aboard. The first week feels like drinking from a fire hose;
the second week starts to make sense.
