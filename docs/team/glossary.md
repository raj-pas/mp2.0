---
title: Glossary
owner: Saranyaraj Rajendran
last_revised: 2026-05-12
status: living
update_when: A new domain term enters the team's vocabulary, a term is
  retired or replaced (e.g., the canon supersedes a definition), a
  canon section reference for an existing term changes, or a new ADR
  introduces a term that should be discoverable here.
---

# Glossary

Plain-language definitions of the domain terms MP2.0 uses. Aimed at new
engineers and at a product manager who is new to wealth-management.

Terms are grouped by theme rather than alphabetized — related terms
sit next to each other so the reader can build a mental model
progressively. A flat alphabetic index sits at the bottom for lookup.

## See also

- [`README.md`](README.md) — folder index + conventions
- [`product-brief.md`](product-brief.md) — uses these terms in context
- [`architecture-diagrams.md`](architecture-diagrams.md) — visual map
  of the system the glossary describes
- [`../../MP2.0_Working_Canon.md`](../../MP2.0_Working_Canon.md) §16
  — the canon's vocabulary section, which this glossary expands

## Product and strategy

**MP2.0** — the project name for Purpose Investments' planning-first
model portfolio platform. The "2.0" signals a deliberate departure
from portfolio-first (1.0) thinking.

**Planning-first wealth.** The strategic bet behind MP2.0: that the
advisor value of the next decade comes from integrated planning, not
from picking model portfolios. Portfolio construction commoditizes; the
plan becomes the product.

**The four locked project goals.** (1) Re-imagine planning-first wealth.
(2) Connect the experience ("One Purpose"). (3) Accelerate fund sales.
(4) Access new distribution channels. See Canon §1.3 for the canonical
form.

**One Purpose.** Internal initiative for a single integrated journey
across Steadyhand, Harness, Link, and the Partnership Program. MP2.0
is the goal-based lens that layers on top of those platforms (Canon
§1.7).

**Steadyhand.** Purpose subsidiary, MFDA-registered. ~3,500–4,000
clients. Small Investment Specialist (IS) team. The launch context
for the MP2.0 MVP — three to five Steadyhand IS members are the
initial pilot cohort.

**Pilot.** A controlled deployment of MP2.0 to a small advisor cohort
with real client data. Distinguished from "demo" (synthetic data) and
"GA" (general availability). The current pilot launched 2026-05-08.

**Production-grade MVP.** MP2.0's bar definition: production-grade
software with a deliberately small user set. "MVP" describes scope,
not engineering quality. Real PII flows through the system from day
one; controls are production-grade or the system doesn't ship.
See Canon §1.6.

**Phase A / B / C.** The rollout sequence. Phase A: offsite scaffold
and foundation. Phase B: pilot hardening and Investment Specialist
(IS) validation. Phase C: controlled pilot expansion with 3–5
Steadyhand advisors using real client data. Each phase is
production-grade for its scope.

**Mission-Aligned Team.** Fraser Stark (project lead), Nafal Butt,
Lori Norman, Saranyaraj Rajendran (engineering lead). Listed in canon
§1.1.

**Longevity Pension Fund (LPF).** A Purpose product mentioned as the
catalyst for MP2.0 — strong product, weak sales because it doesn't
fit a traditional risk-bucket portfolio. Needs a planning-aware
allocation engine, which is MP2.0.

## Conceptual model

**Household.** The top-level entity. One or two people; never more.
Three or more people becomes "dependents as goals," not a multi-person
household. Central object the engine optimizes for.

**Person.** A member of a household. Carries everything regulatory +
planning needs: name, DOB, marital status, citizenship, residency,
employment, pensions, longevity assumption, trusted contact, POA, will,
beneficiaries.

**Account.** A regulatory container where money is held. Types include
RRSP, TFSA, RESP, RDSP, FHSA, Non-Registered, LIRA, RRIF, Corporate.
Each account carries regulatory constraints (objective, time horizon,
risk rating).

**Goal.** Something the household actually cares about. Carries target
amount, target date, necessity score (need/want/wish), current funded
amount, contribution plan, and a goal risk score (1–5).

**`GoalAccountLink`.** The many-to-many link between goals and
accounts, carrying either an allocated dollar amount or an allocated
percentage. **This is the engine's optimization unit** — not the goal
alone. See Canon §4.3a and ADR-0005.

**Holding.** The actual fund-by-fund position rows under an account.
What the optimizer rebalances toward.

**Fund.** The vocabulary term we use for the constituent units of a
portfolio. Replaces the retired industry term "sleeve."

**Building-block fund.** The 8–12 funds that compose the v36 universe
(Cash, Income, Equity, Global Equity, Canadian Small-Cap, Global
Small-Cap, etc.). Each is a real, papered fund with a Purpose PM
attached. Optimizer-eligible. The "paints" in Fraser's paint-mixing
analogy.

**Whole-portfolio fund.** A pre-mixed multi-asset fund (Founders,
Builders, PACF). Optimizer-eligible and may mix with building-block
funds; labeled distinctly in explanations.

**External holding.** A position held outside Purpose (e.g., a brokerage
account at another firm, an employer pension, a property). Tracked in
the `ExternalHolding` model. Informs projections (drift penalty:
μ × 0.85, σ × 1.15) and eventually risk-tolerance dampening (deferred
to Phase B).

**Macro Insight Layer.** The CIO/strategist function. Updates the
*internals* of building-block funds (duration, sector tilts, currency
hedging) on a monthly cadence. Independent from the client-blend update
cycle, which fires on plan changes.

**Living Financial Plan.** The household's continuously-updated model.
Not a document — an event-driven model that updates on life changes,
advisor observations, and material market moves. The source of truth
for the portfolio blend.

**The 6-stage customer journey.** Stage 1 Onboarding → Stage 2 Living
Financial Plan → Stage 3 Portfolio Construction → Stage 4 Automated
Execution (Phase 2+) → Stage 5 Outcomes Reporting → Stage 6 Continuous
Loop. The MVP covers Stages 1 → 2 → 3 → 5. Stage 4 is mocked.

## Investment theory and engine mechanics

**Efficient frontier.** Modern Portfolio Theory applied at the
building-block-fund level. The set of portfolios that maximize expected
return for each level of volatility. A curve in (volatility, return)
space.

**Pareto filter.** A post-frontier filter that drops dominated points
(any portfolio with lower return AND higher volatility than another).
Lives in `engine/frontier.py`. Added in R4 after a Hypothesis property
test surfaced a falsifying example.

**5-point risk scale.** Risk on the canonical 1–5 scale, mapped to
optimizer percentiles 5/15/25/35/45. The 5–45 range (intentionally
below the median) prevents 100%-global-equity outcomes even for the
most risk-tolerant clients.

**Risk descriptors** (the only risk vocabulary allowed in advisor-facing
copy):

| Score | Descriptor | Optimizer percentile |
|---|---|---|
| 1 | Cautious | 5th |
| 2 | Conservative-balanced | 15th |
| 3 | Balanced | 25th |
| 4 | Balanced-growth | 35th |
| 5 | Growth-oriented | 45th |

Low / medium / high risk vocabulary is **banned** in client-facing
surfaces — see Canon §6.3a and `scripts/check-vocab.sh`.

**Snap-to-grid.** The blended risk score rounds to the nearest 5-point
step. No interpolation between descriptors.

**Risk tolerance.** A property of the *person or household*. The "are
you a Cautious or a Growth-oriented investor?" question.

**Riskiness.** A property of the *position or portfolio*. The "is this
goal-account allocation Cautious or Growth-oriented?" question. The
lexical distinction matters (Canon §2.3).

**Household × goal composite.** The combined risk score used to set
the optimization percentile for a specific goal-account link. The
specific weighting formula is open (deferred to product input from
Lori and Saranyaraj); code parameterizes it.

**External-holdings dampener.** Canon §4.6a deferral: external holdings
should *dampen* household risk tolerance (more external exposure →
lower household score). Formula not yet team-confirmed. The projection
drift penalty (μ × 0.85, σ × 1.15) is implemented in
`engine/projections.py`; the dampener itself is deferred to Phase B.

**The "AI never invents financial numbers" rule.** Canon §9.4.5,
load-bearing. The LLM can extract and style; it never invents numbers,
names, dates, or any data field. If a value isn't in the document, the
system surfaces the gap to the advisor — it does not default, guess,
or interpolate.

**`derivation_method = "defaulted"`.** A code-smell. The post-pilot
Phase 9 plan explicitly forbids re-introducing it after a 2026-05-03
sweep eliminated the last two cases.

## Source-priority and reconciliation

**Source-priority hierarchy** (Canon §11.4). When facts disagree
across documents, the system resolves silently to:
System of Record (KYC, custodial statement) > structured planning doc
> note-derived fact. Advisor override (via `FactOverride`) trumps
everything below it.

**Cross-class disagreement.** Different source classes disagree
(e.g., KYC says X, note says Y). Resolves silently to the higher-
priority source. The advisor doesn't see a conflict.

**Same-class disagreement.** Same source class disagrees with itself
(e.g., two notes disagree about a goal). Surfaces as a **conflict
card** for advisor adjudication with rationale + evidence_ack.

**Canonical entity.** After Layer 4 reconciliation, the deduplicated
representation of a person / account / goal across all the docs in a
workspace. Stored with a stable `canonical_index` on each
`ExtractedFact`.

**`canonical_index`.** The integer index of a canonical entity within a
workspace. Stored on each `ExtractedFact`. Stable across reconcile
cycles when the matcher's contributing-doc count + lexical tiebreak is
deterministic.

**Tier-1 / Tier-2 / Tier-3 matcher.** The three-tier entity alignment
classification:

- **Tier-1 (auto-merge):** high-confidence identity match. People:
  name + DOB or name + last_name + last-4-of-account_number.
  Auto-merges silently.
- **Tier-2 (advisor adjudicates):** medium-confidence with no
  contradicting fields. Surfaces as a `MergeCandidate` for advisor
  decision (merge / keep_separate / defer). Shipped 2026-05-05.
- **Tier-3 (new canonical):** below all bands, or any contradicting
  identity field. Creates a new canonical.

**`MergeCandidate`.** A Tier-2 candidate. Persisted to
`reviewed_state['merge_candidates']`. Surfaces in the ConflictPanel's
"Possible duplicates" group (Phase B2, in flight).

**`FactOverride`.** Advisor manual correction or addition to extracted
facts. Append-only. `is_added` flag distinguishes "corrected an
extracted value" from "added a new fact."

**Reconciliation.** Layer 4 of the extraction pipeline. Entity
alignment + conflict detection + source-priority resolution.

**`_merge_household_state`.** The Layer-5 commit boundary in
`web/api/review_state.py` (around line 1505). The **only** place
lowercase / snake_case extracted account types get normalized to
canonical values ("rrsp" → "RRSP", "non_registered" → "Non-Registered").

## Architecture and code structure

**The four layers.** Engine / web / extraction / frontend. Each has
strict boundary rules. See [`architecture-diagrams.md`](architecture-diagrams.md)
diagram 1.

**Engine purity.** The engine package has *zero inbound dependencies*
from web, extraction, integrations, Django, or DRF. AST-enforced by
`engine/tests/test_engine_purity.py`. See ADR-0001.

**Engine adapter.** `web/api/engine_adapter.py` — the only place where
Django model instances become `engine.schemas` Pydantic models. The
seam between the persistence layer and the engine library.

**`engine_ready`.** Reviewed facts are sufficient for the engine to
optimize. A boolean gate in the readiness checks.

**`construction_ready`.** Committed household data can pass portfolio
generation rules. A boolean gate that must hold (along with
`engine_ready` and all required section approvals) for a commit to
succeed.

**`ENGINE_REQUIRED_SECTIONS`.** The six sections the advisor must
approve before a workspace can commit: household, people, accounts,
goals, goal_account_mapping, risk. Defined in `web/api/review_state.py`;
read from the workspace payload on the frontend (never hardcoded).

**Real-PII discipline.** Canon §11.8.3, defense-in-depth. Real client
data is authenticated-ingress-only, stored under `MP20_SECURE_DATA_ROOT`
outside the repo, routed through Bedrock ca-central-1 fail-closed,
hashed for sensitive identifiers, redacted in evidence quotes,
immutably audited, RBAC-gated. See [`real-pii-handling.md`](real-pii-handling.md)
and ADR-0004.

**`MP20_SECURE_DATA_ROOT`.** Required environment variable pointing to
a filesystem path **outside** the repo where real client raw files
live. Repo-local paths are rejected at startup.

**`MP20_ENGINE_ENABLED`.** The kill-switch env var. `MP20_ENGINE_ENABLED=0`
returns 503 from portfolio generation endpoints + emits
`portfolio_generation_skipped_post_<source>` audit events. Existing
PortfolioRun rows + committed households remain visible.

**Append-only model.** A Django model whose `save()` raises on update
and whose `delete()` raises always. Plus, in some cases, Postgres
triggers block UPDATE/DELETE at the storage layer. Used for
`AuditEvent`, `PortfolioRun`, `PortfolioRunEvent`, `HouseholdSnapshot`,
`GoalRiskOverride`, `FactOverride`.

**`PortfolioRun`.** The append-only row recording an engine output.
Carries the input snapshot, output, all the hashes
(input/output/CMA/reviewed_state/approval), engine_version, advisor
summary, technical trace, and a `run_signature`. Source of truth for
generated recommendations.

**`PortfolioRunEvent`.** Append-only lifecycle event attached to a
`PortfolioRun`. Types: generated, reused, regenerated_after_decline,
invalidated_by_cma, invalidated_by_household_change, advisor_declined,
audit_exported, generation_failed, hash_mismatch.

**`AuditEvent`.** The immutable audit row. Lives in `web/audit/models.py`
(separate Django app from `web/api/`). `save()` raises on update;
Postgres triggers block UPDATE and DELETE.

**`HouseholdSnapshot`.** Append-only audit trail of portfolio-altering
events (realignment, cash_in, cash_out, re_link, override, re_goal,
restore). Captures the full state-before for forensic replay.

**`record_event`.** The audit writer in `web/audit/writer.py`. Metadata
is sanitized via `safe_audit_metadata` (from `web/api/error_codes.py`)
to strip exception details and PII patterns.

**`safe_audit_metadata`, `safe_response_payload`,
`safe_exception_summary`, `failure_code_for_exc`.** Helpers in
`web/api/error_codes.py` that enforce real-PII discipline. Never put
`str(exc)` into DB columns / response bodies / audit metadata — use
these instead.

**`failure_code`.** A stable, structurally-PII-safe code derived from
the exception class name (not the message). Drives advisor-facing copy
via `friendly_message_for_code`.

## Worker, CMA, and runtime

**Worker.** A separate Docker service running
`web/api/management/commands/process_review_queue.py`. Indefinitely
claims `ProcessingJob` rows with Postgres row-locking and processes
them.

**`ProcessingJob`.** A Postgres-backed queue row. Job_type:
`process_document` (extract one file) or `reconcile_workspace`
(re-align all facts in a workspace).

**`WorkerHeartbeat`.** Worker liveness. Updates periodically; if it
goes stale, the frontend's WorkerHealthBanner warns advisors.

**CMA — Capital Market Assumptions.** Per-fund expected return,
volatility, correlation matrix, asset-class / geography weights,
eligibility flags. Versioned globally; analyst-edited via the CMA
Workbench; advisor-read-only.

**`CMASnapshot`.** The versioned CMA row. Has status (draft / active /
archived). The unique-active-CMA constraint ensures exactly one active
snapshot.

**CMA Workbench.** The financial-analyst-only UI for drafting, editing,
publishing, and auditing CMA snapshots. Includes the efficient frontier
visualization. Advisors generate and view runs but cannot edit CMA.

**Bedrock.** AWS managed LLM service. Required to live in ca-central-1
for real-PII routing per canon §11.8.3.

**Fail-closed.** When ca-central-1 is unreachable, the document is
marked `failed`. No fallback to us-east-1, no fallback to local
extraction. The advisor uses the manual-entry escape hatch.

**Manual-entry escape hatch.** When extraction fails on a doc, the
advisor can use `ReviewDocumentManualEntryView` to type facts in
directly. Marks the doc `manual_entry`.

## Pipeline layers

**Layer 1 — Ingestion.** Authenticated browser upload → secure-root
storage → SHA-256 dedup → `ProcessingJob(process_document)` enqueue.

**Layer 2 — Parsing.** Local libraries (pdfplumber, python-docx,
openpyxl, csv) extract text. OCR fallback (pytesseract) when text
extraction yields nothing. Capped by `MP20_OCR_MAX_PAGES`.

**Layer 3 — LLM extraction.** Bedrock ca-central-1 (real-derived) or
Anthropic-direct (synthetic). Tool-use API with per-doc-type JSON
Schema. Typed exceptions: `BedrockExtractionError` (base),
`BedrockNonJsonError`, `BedrockTokenLimitError`,
`BedrockSchemaMismatchError`.

**Layer 4 — Reconciliation.** Entity alignment (Tier-1 + Tier-2 +
Tier-3) + conflict detection + source-priority resolution. Lives in
`extraction/entity_alignment.py` and `extraction/reconciliation.py`.

**Layer 5 — Review.** Advisor sees the reconciled state, resolves
conflicts, resolves Tier-2 merge candidates, applies `FactOverride`,
approves sections, commits. Commit boundary normalizes account types
and creates/upserts the `Household`.

## Frontend and design system

**v36 rewrite.** The 2026-04 UI rewrite spanning rounds R0 through
R10 on the `feature/ux-rebuild` branch. Replaced earlier UI surfaces
with a strict-TS, design-token-driven, Radix-primitive React 18 app.

**Three-tab pivot.** The advisor console's primary navigation:
Household / Account / Goal. Click-to-drill from treemap into account,
from account into goal.

**Treemap.** The d3-hierarchy squarified treemap on the HouseholdRoute.
Renders the household's AUM as nested rectangles, mode-toggleable by
account or by goal.

**RecommendationBanner.** The goal-route component that surfaces the
engine's PortfolioRun result. Five visual states: current run / stale /
declined / failure / cold-start / integrity-alert.

**SourcePill.** The shared indicator: "Engine recommendation" (accent)
vs "Calibration preview" (muted) vs "Calibration drag" (during slider
drag before save).

**StaleRunOverlay.** The advisor-actionable overlay for invalidated /
superseded / declined runs with a Regenerate CTA.

**IntegrityAlertOverlay.** The engineering-only overlay for
`hash_mismatch` events. No Regenerate button — root cause requires
engineering attention.

**`canonizeFundId`.** The frontend normalizer in `frontend/src/lib/funds.ts`
that maps every fund-id variant (`SH-Sav`, `sh_savings`, `income_fund`,
etc.) to the canon form. Workaround for the four coexisting fund-id
naming conventions.

**PilotBanner.** The disclaimer banner advisors see, acknowledging the
pilot-mode bar. Disclaimer acknowledgement lives on
`AdvisorProfile.disclaimer_acknowledged_at` and
`disclaimer_acknowledged_version`.

**WelcomeTour.** The 3-step coachmark for first-login. Server-side ack
via `AdvisorProfile.tour_completed_at`.

**ConflictPanel.** The review-screen surface for same-class fact
disagreements (and, in Phase B2, the new MergeCandidateGroup for
Tier-2 entity merges).

**ResolveAllMissingWizard.** The bulk-resolution wizard for missing
required fields. Lazy-loaded; surfaces a "Resolve all N missing
fields →" CTA when `missing.length >= 4`.

## Operational

**Sev-1 / Sev-2 / Sev-3.** Incident severity. Sev-1 = real-PII leak,
engine fabrication, advisor blocked from any commit, or data
corruption. Sev-2 = systematic failure for >25% of advisors or a
class-level extraction bug. Sev-3 = cosmetic or non-blocking friction.

**Kill-switch.** Setting `MP20_ENGINE_ENABLED=0` and restarting both
the backend and worker containers. Pauses new portfolio generation
without affecting existing data. The fastest Sev-1 mitigation.

**GA — General Availability.** The post-pilot release stage. Requires
Sev-1 = 0, NPS ≥ 8, ≥ 50% of pilot advisors used the system for ≥ 3
onboardings, perf budget intact, R10 sweep re-passing weekly, manual-
entry rate < 15%, all for two consecutive weeks.

**R10 sweep.** A scripted multi-folder real-PII extraction run across
all 7 client folders, measuring reconciliation rate + Bedrock cost +
fact counts. Lives in `scripts/demo-prep/r10_sweep.py`.

**`scripts/reset-v2-dev.sh --yes`.** The canonical destructive reset
of the local dev DB. Wipes the `web_api_*` tables but preserves the
audit log (audit triggers survive the reset). Re-seeds Sandra & Mike
Chen synthetic + bootstraps the local advisor.

**Sandra & Mike Chen.** The fully-synthetic baseline persona. Defined
in `personas/sandra_mike_chen/client_state.json`. Mike (1964) + Sandra
(1968), $1.308M AUM across four accounts (Mike RRSP, Sandra RRSP, joint
TFSA, Mike Non-Reg), three goals (Retirement Income, Emma Education,
Ski Cabin). The demo state.

**Default CMA.** The seeded baseline capital market assumptions used
when a fresh dev environment boots. Loaded via
`web/api/management/commands/seed_default_cma.py`.

## Persistent context and tooling

**The canon.** `MP2.0_Working_Canon.md` at the repo root.
Currently v2.8 (2,202 lines). The single authoritative source for
product / strategy / regulatory / architecture decisions. Decision
tags throughout: `[LOCKED]`, `[DEFAULT]`, `[OPEN]`.

**`docs/agent/`.** Operational and handoff infrastructure. Contains
session-state, handoff-log (append-only), decisions, open-questions,
ux-spec, design-system, ops-runbook, pilot-rollback, pilot-success-
metrics, and many more. Not for casual reading; for the engineer
actively shipping or for Claude Code sessions.

**`docs/team/`.** This folder. Team-facing reference documentation.

**`docs/validation/`.** Optimizer validation evidence + human-review
checklist.

**`CLAUDE.md`.** The Claude Code session entrypoint at the repo root.
Non-negotiable rules + start-of-session ritual + build commands.

**Master dossier.** The 1,500+ line MP2.0 onboarding dossier at
`~/.claude/plans/i-want-you-to-sorted-meadow.md`. The map of everything
in `docs/team/` and the canon. Authored 2026-05-12.

**Phase 0.** The mandatory pre-work reading order before any code
change: project memory → START HERE → session-state → active dossier
→ active plan → canon → open-questions → CLAUDE.md. Enforced by the
`mp2-protocol` skill.

## Vocabulary (banned and replacements)

**"sleeve" / "sleeve fund"** → **building-block fund**.

**"reallocation" / "transfer" / "move money"** → **re-goaling** (when
changing goal-account mapping) / **re-allocate** (with hyphen, when
changing blend within a link) / **re-balance** (when bringing held
holdings back to target).

**"low risk" / "medium risk" / "high risk"** → the five canon
descriptors (Cautious / Conservative-balanced / Balanced /
Balanced-growth / Growth-oriented).

**"Conservative"** (bare) → ambiguous; never use without `-balanced`.

**"Phase R0 / R1 / …"** in client-facing copy → these are engineering
round labels; use canon Phase A / B / C for product-facing copy.

**`Goal_50`, raw 0–50 percentile, `schema_version`** → engine-internal;
never surface to advisor.

The vocabulary CI guard at `scripts/check-vocab.sh` enforces these
rules across `frontend/src/`, `web/api/serializers.py`,
`web/api/management/commands/`, migrations, and engine fixtures.

## Alphabetical index

- 5-point risk scale → Investment theory
- Account → Conceptual model
- AI never invents financial numbers rule → Investment theory
- Append-only model → Architecture and code structure
- AuditEvent → Architecture and code structure
- Bedrock → Worker, CMA, and runtime
- Building-block fund → Conceptual model
- canonical_index → Source-priority and reconciliation
- canonical entity → Source-priority and reconciliation
- canonizeFundId → Frontend and design system
- CMA → Worker, CMA, and runtime
- CMA Workbench → Worker, CMA, and runtime
- ConflictPanel → Frontend and design system
- construction_ready → Architecture and code structure
- Cross-class disagreement → Source-priority and reconciliation
- Default CMA → Operational
- derivation_method = "defaulted" → Investment theory
- docs/agent/, docs/team/, docs/validation/ → Persistent context
- Efficient frontier → Investment theory
- Engine adapter → Architecture and code structure
- Engine purity → Architecture and code structure
- ENGINE_REQUIRED_SECTIONS → Architecture and code structure
- engine_ready → Architecture and code structure
- External holding → Conceptual model
- External-holdings dampener → Investment theory
- FactOverride → Source-priority and reconciliation
- Fail-closed → Worker, CMA, and runtime
- failure_code → Architecture and code structure
- Four layers → Architecture and code structure
- GA → Operational
- Goal → Conceptual model
- GoalAccountLink → Conceptual model
- Holding → Conceptual model
- Household → Conceptual model
- HouseholdSnapshot → Architecture and code structure
- IntegrityAlertOverlay → Frontend and design system
- Kill-switch → Operational
- Layer 1–5 → Pipeline layers
- Living Financial Plan → Conceptual model
- LPF → Product and strategy
- Macro Insight Layer → Conceptual model
- Manual-entry escape hatch → Worker, CMA, and runtime
- MergeCandidate → Source-priority and reconciliation
- Mission-Aligned Team → Product and strategy
- MP2.0 → Product and strategy
- MP20_ENGINE_ENABLED → Architecture and code structure
- MP20_SECURE_DATA_ROOT → Architecture and code structure
- One Purpose → Product and strategy
- Pareto filter → Investment theory
- Person → Conceptual model
- Phase A / B / C → Product and strategy
- Phase 0 → Persistent context
- Pilot → Product and strategy
- PilotBanner → Frontend and design system
- Planning-first wealth → Product and strategy
- PortfolioRun → Architecture and code structure
- PortfolioRunEvent → Architecture and code structure
- ProcessingJob → Worker, CMA, and runtime
- Production-grade MVP → Product and strategy
- R10 sweep → Operational
- Real-PII discipline → Architecture and code structure
- Reconciliation → Source-priority and reconciliation
- record_event → Architecture and code structure
- RecommendationBanner → Frontend and design system
- ResolveAllMissingWizard → Frontend and design system
- reset-v2-dev.sh → Operational
- Risk descriptors → Investment theory
- Risk tolerance vs riskiness → Investment theory
- Same-class disagreement → Source-priority and reconciliation
- Sandra & Mike Chen → Operational
- Sev-1 / Sev-2 / Sev-3 → Operational
- Snap-to-grid → Investment theory
- Source-priority hierarchy → Source-priority and reconciliation
- SourcePill → Frontend and design system
- StaleRunOverlay → Frontend and design system
- Steadyhand → Product and strategy
- Tier-1 / Tier-2 / Tier-3 matcher → Source-priority and reconciliation
- Treemap → Frontend and design system
- v36 rewrite → Frontend and design system
- WelcomeTour → Frontend and design system
- Whole-portfolio fund → Conceptual model
- Worker → Worker, CMA, and runtime
- WorkerHeartbeat → Worker, CMA, and runtime
- _merge_household_state → Source-priority and reconciliation
