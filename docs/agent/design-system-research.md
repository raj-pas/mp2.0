# Design-System + UX Research — MP2.0 (Durable, Cross-Session)

**Created:** 2026-05-05 (Phase P0, plan v20 §A1.21).
**Last updated:** 2026-05-05 (initial draft; back-fills sister-shipped
A3-A4 patterns at HEAD `979a692`, tag `v0.1.3-engine-display-polish`).
**Authoritative companions:**
- `docs/agent/ux-spec.md` — UX dimensions taxonomy (A-M) + canonical
  flows + decision log.
- `docs/agent/design-system.md` — design tokens + component inventory
  + ErrorBoundary + focus-management patterns.
- `docs/agent/decisions.md` — locked implementation decisions distilled
  from canon (~512 lines + sister A7 migrations).
- `docs/agent/post-pilot-improvements.md` — Tier 1/2/3 deferred items.
- `MP2.0_Working_Canon.md` — product/strategy/regulatory/architecture
  intent. §6.3a (re-goaling vocab), §9.4.2 (engine boundary), §9.4.5
  (AI-numbers rule), §11.4 (source-priority hierarchy), §11.8.3
  (defense-in-depth privacy regime), Part 16 (vocabulary glossary).

This document is the bridge between abstract UX principles and concrete
implementation. It cites real reference systems, names the patterns
adopted (and not adopted) from each, and maps every adopted pattern to
the file:line where MP2.0 applies it. New advisor-facing surface work
**must** read this document before designing or implementing.

---

## §1 — Purpose & Cross-Session Contract

### Why this document exists

Earlier in MP2.0, sessions shipped surfaces that locally made sense but
globally diverged — sessions re-derived patterns from training data
(or no reference at all), and the resulting UI drifted in colour
usage, density, error semantics, and copy register. The cumulative
effect was incoherence: each route felt like a different tool by a
different team.

This document fixes that drift. It pins the team's adopted reference
systems, names the patterns lifted from each, maps each pattern to
the MP2.0 file/line where it lives, and lists counter-patterns
explicitly considered and rejected. Future sessions read this
document, locate the closest analogous pattern, and either reuse it
(preferred) or extend it with a new entry.

### Lifecycle (full contract in §7)

- **Read-when:** before new advisor-facing surface work, changing
  component patterns, or introducing advisor copy.
- **Update-when:** at session boundaries — append to §6 with
  phase-commit-hash; sister sessions append in parallel.
- **Prune-when:** patterns applied 3+ times migrate to `ux-spec.md`
  (conceptual) or `design-system.md` (reusable component); the §3 row
  becomes a one-line stub. Captures novel applications, not
  steady-state.
- **Lori-review-when:** post-pilot week 2 for vocab + canon compliance.

### Scope guards

Captures **patterns**, not screenshots or visual specs. Visual
pattern-library (paste-in screenshots beside each cited inspiration)
is deferred to post-pilot Tier 2 (plan §P0.6). Does NOT capture:
token values (`design-system.md`), canonical copy (`i18n/en.json`),
accessibility commitments (`design-system.md` + `ux-spec.md` §I), or
routing structure (v36 plan + code).

### Real-PII discipline

Follows canon §11.8.3. No client content in any form — not as
illustrations, quoted evidence, or hypothetical examples. Examples
use synthetic Sandra/Mike Chen persona or schematic placeholder
text. Counts are structural ("4 accounts, 2 goals"), never real
values.

---

## §2 — Cited Reference Systems

Every external system the team has consulted, with a one-line learning
per system and a "when to apply" note. Each entry gates an entry in
§3 (patterns adopted) — if cited here, it has at least one concrete
adopted pattern in §3 with file:line reference.

Cited systems split into four buckets: financial-product UIs
(competitive context), CRM/relationship UIs (multi-entity nav),
legal-tech and research-bench UIs (high-density reviewer surfaces),
and productivity tools (keyboard-first density baseline).

### 2.1 — Linear (issue tracker)

**Learning:** muted-by-default surfaces with action-on-hover and tight
density baseline; visual hierarchy is structural (size, indentation,
weight) not chromatic.
**When to apply:** any list-of-things surface (review-workspace list,
recommendations list, conflict cards). Linear's `text-muted` baseline
with selective `text-ink` for the focused row is the inspiration for
MP2.0's `font-mono text-[11px] uppercase tracking-widest text-muted`
metadata baseline. Command-bar-over-panel discipline (Cmd-K for
navigation) inspires GroupBy toggle + ClientPicker collapsing into
TopBar rather than persistent left rail.
**Partial:** keyboard-first command-bar is deferred (advisor mental
model is mouse-first day one; keyboard polish-layer only).

### 2.2 — Stripe Dashboard

**Learning:** multi-entity navigation as flat type-tagged listing
scales further than nested trees; "all your customers / subscriptions
/ invoices" flat view sets the precedent.
**When to apply:** `frontend/src/chrome/ClientPicker.tsx` (Radix
Popover with search and paginated list) inherits "search-first,
scroll-second, entity-type chip on each row." Empty-state vocabulary
("No customers yet — create your first") informs MP2.0's empty-state
copy register: action-oriented, never apologetic.
**Partial:** Stripe density is too tight for advisor surfaces (not
10k-row tables). MP2.0 relaxes to medium density for household list,
tight only for doc review sub-table.

### 2.3 — Stripe Connect

**Learning:** "completion banner with field-level fix-in-place" for
KYC/onboarding gates: persistent banner lists missing fields as
structured items (not a single string), clicking each opens inline
editor for that exact field. Banner state is backend-derived
structured (typed blocker objects, not frontend-parsed string).
**When to apply:** `frontend/src/goal/RecommendationBanner.tsx`
mirrors completion-banner pattern (5-state banner with structured
backend payload). Future Phase P11 structured-blockers work (plan
§A1.27, deferred) extends to portfolio-generation blockers on the
household-detail page.
**Why primary:** the alternative (frontend string-parsing of error
sentence) creates i18n breakage and silent regression risk.

### 2.4 — Wealthfront (advisor / investor view)

**Learning:** allocation visualization as single authoritative view
(treemap or stacked bar) plus today-vs-target toggle is more legible
than two side-by-side charts. "Advisor reasoning" copy below
allocation chart is structured (not free prose), bounded — 2-3
sentences per recommendation.
**When to apply:** `frontend/src/charts/Treemap.tsx` adopts
single-authoritative-view-plus-toggle (one treemap, click to drill,
no parallel current/proposed at household level — side-by-side lives
in CompareScreen, modal scoped to realignment review). Bounded
"advisor reasoning" inspires `AdvisorSummaryPanel.tsx`
engine-narrative rendering (2-3 sentence summary per goal-account
link from `engine_output.link_recommendations[].advisor_summary`).
**Partial:** goal-required-at-account-creation discipline IS adopted
(P14 deferred); hide-the-numbers defaults are NOT (advisor surfaces
show numbers always).

### 2.5 — Betterment (advisor / consumer view)

**Learning:** goal-account allocation card pattern: each goal-account
link rendered as self-contained card with allocation amount,
auto-categorization with override, projection. Multi-link goals
stack cards under one collapsing header.
**When to apply:** `frontend/src/goal/AdvisorSummaryPanel.tsx`
renders multi-link goals as stacked sections with first link
expanded, subsequent below hairline divider (locked #78 —
default-collapsed Radix Accordion was the design but execution
landed as flat stacked sections; ergonomics equivalent at ≤4 links).
**Carefully:** Betterment's auto-categorization is the OPPOSITE of
canon §9.4.5 AI-numbers rule. CARD PATTERN adopted; AUTO-CATEGORIZE
HEURISTIC explicitly rejected (§4 counter-patterns).

### 2.6 — Vanguard advisor portal

**Learning:** multi-household navigation with switch-without-losing-
context — advisor switches active household and current view
(treemap, accounts, goals) re-renders in place, preserving the tab.
**When to apply:** `frontend/src/chrome/ClientPicker.tsx` plus
`useRememberedClientId` localStorage helper preserve active client
across navigation (last-client memory is pilot requirement, not
nice-to-have, because advisors triage 5-10 clients/hour). Switching
client preserves tab (HouseholdRoute / AccountRoute / GoalRoute).
**Partial:** recent-households 4-slot rail is deferred to post-pilot
Tier 3 (server-side recent-clients tracking + cache invalidation
non-trivial).

### 2.7 — Schwab Intelligent Portfolios (advisor view)

**Learning:** risk-band as 5-band horizontal track with single marker
is more legible to advisors than numeric score with tooltip; the
marker on the track is what the advisor reads, the numeric score is
engineering-internal.
**When to apply:** `frontend/src/charts/RiskBandTrack.tsx` direct
adoption: 5 bands (Cautious / Conservative-balanced / Balanced /
Balanced-growth / Growth-oriented per canon §16.1), marker placed at
the descriptor mapped from risk score (1-5 scale, mapped to
optimizer percentiles 5/15/25/35/45). Advisor never sees raw 0-50
internal score (engine-internal per §9.4.2 boundary).
**Why fully adopted:** band metaphor pre-empts "your number is X.7"
trap that pushes advisors toward false-precision questions.

### 2.8 — Morningstar Direct (research workbench)

**Learning:** workbench layouts with saved views and multi-pane
density work for ANALYST surfaces, NOT advisor surfaces.
**When to apply:** `frontend/src/routes/CmaRoute.tsx`
(financial-analyst-only CMA Workbench) adopts multi-pane research
density: edit panel + frontier chart + draft state + audit history
visible together. Advisor surfaces (HouseholdRoute / AccountRoute /
GoalRoute) DO NOT inherit — they keep one authoritative view per
route with slide-outs for deep dives.
**Why split:** advisors triage 5-10 clients/hour and lack
context-switching budget for multi-pane density. Analysts deep-work
for hours on one CMA snapshot.

### 2.9 — Salesforce Financial Services Cloud

**Learning:** household relationship modeling with roll-up and
one-click resolution: household card shows multi-person membership
and asset roll-up; any data integrity issue (missing relationship,
unaffiliated account) renders as fix-in-place modal triggered by
single click on issue chip.
**When to apply:** `frontend/src/routes/HouseholdPortfolioPanel.tsx`
inherits household-level rollup card pattern (expected return +
volatility + top funds, all from engine `household_rollup`).
Fix-in-place inspires future Phase P11 structured-blockers
(BlockerBanner with clickable rows opening inline editor for that
field — deferred). Current cold-start path on
HouseholdPortfolioPanel surfaces readiness blockers as list with
Generate CTA disabled while blockers exist.
**Why central:** "fix in place, never lose context" is the antidote
to MP2.0's worst current pattern (soft-undo cascade that destroys
household identity when advisor wants to fix one field).

### 2.10 — HubSpot CRM

**Learning:** duplicate detection with merge-with-rationale capture:
when system suspects duplicate, shows candidates side by side, asks
user to choose one (or create new explicitly), captures merge reason
as free text → audit log.
**When to apply:** `web/api/review_state.py` reconciliation paths
adopt "advisor explicitly chooses one, rationale captured" model
(`ConflictPanel` with `rationale_required` + `evidence_ack_required`
per locked #37 + sister-shipped). Future post-pilot upgrade is the
source-priority-hierarchy ladder UI (visual stack: SoR > structured >
note-derived per canon §11.4); current implementation surfaces
priority via ConfidenceChip color + text.
**Partial:** auto-merge under high confidence NOT adopted (canon
§9.4.5 — advisor explicit). MP2.0 bar: "advisor chooses, system
records" even at 95% confidence.

### 2.11 — Relativity (legal-tech doc review)

**Learning:** evidence-card + assertion-grid pattern at 50k-doc
density: each fact has quote-with-source-doc citation in card;
assertion grid (which fact appears in which doc) is pivotable;
reviewer can mark fact "redacted" without losing citation.
Discipline: every assertion points back to quoted source, no
inferences without citation.
**When to apply:** `frontend/src/modals/DocDetailPanel.tsx`
slide-out per-doc detail panel inherits evidence-card pattern: each
extracted fact shows redacted quote, source doc ID, confidence chip,
override affordance. Post-pilot upgrade is assertion-grid pivot
(rows = facts, columns = docs, cells = extracted value); not
pilot-week-1.
**Selective:** Relativity reviewer density is way above advisor
threshold; EVIDENCE DISCIPLINE adopted everywhere; GRID PIVOT is
research-bench-density (analyst-only future surface).

### 2.12 — Logikcull (legal-tech doc review)

**Learning:** redacted-evidence-quote rendering with provenance: quote
shows enough context to be meaningful but masks directly-identifying
tokens (account number, SIN, phone) with structured redaction
markers; provenance includes doc name, page, extraction run ID.
**When to apply:** `extraction/redaction.py` (`redact_evidence_quote`
helper) implements redaction; UI in `ConflictPanel.CandidateRow`
displays redacted quote with provenance. Canon §11.8.3 #4
(minimally-redacted evidence quotes) is the exact policy.
**Constrained:** redaction is backend-side, not frontend (frontend
cannot un-redact).

### 2.13 — Figma

**Learning:** left-rail nav + right-rail context with panel-collapse
persistence; either rail can collapse with state remembered across
sessions.
**When to apply:** MP2.0 adopts softer version. TopBar holds global
nav (no left rail; advisor surfaces too narrow). Slide-outs from
right edge serve contextual deep-dive role (`DocDetailPanel` per
ux-spec.md component taxonomy). Panel-collapse persistence in scope
for future post-pilot polish.
**Why softer:** Figma left-rail assumes desktop-first analyst-density
usage; advisor day-to-day is split-attention work where collapsed
nav rail wastes pixel budget.

### 2.14 — Notion

**Learning:** database views (table / board / list / gallery) over
same data with view persistence per database; inline cell-edit so
the table itself is editor, not separate edit modal.
**When to apply:** `frontend/src/modals/DocDetailPanel.tsx` inline
fact edit (`FactEditForm`, locked Phase 5b.10) adopts inline-cell-
edit: clicking a fact's value in slide-out opens editor in place,
no modal stack. Future post-pilot upgrade is multi-view pivot for
assertion grid (table = current, board = group-by-conflict-status,
gallery = doc-thumbnails).
**Why central:** modal-on-modal stacks explicitly avoided (§4);
inline edit is the alternative that preserves context.

### 2.15 — Apple Numbers / Google Sheets

**Learning:** inline edit affordances and cell-level validation:
the cell IS the editor; validation errors render inline beside or
below the cell with clear "fix this to continue" affordance.
**When to apply:** `frontend/src/wizard/Step3Goals.tsx` and
allocation-bar inline editors adopt cell-level-validation: each %
input has its own inline message; form-level error summary
cross-references each field. Reinforces Lattice §2.22 field-level +
summary pattern.
**Partial:** spreadsheet flexibility (cell formulas, multi-row
paste) not in pilot scope; EDIT-IN-PLACE shape is.

### 2.16 — Plaid Link

**Learning:** financial-document onboarding with source disambiguation
and categorization required: at upload time, user explicitly tags
each document type (statement / KYC / meeting note); system never
silently infers because inference cost when wrong is large.
**When to apply:** `frontend/src/modals/DocDropOverlay.tsx` adopts
explicit-categorization: dropped docs tagged by type via dropdown;
auto-detection is best-effort with override always available. Canon
§9.4.5 (AI-numbers, generalized to AI-categorization) backs this.
**Why fully adopted:** silent doc-type inference is the
LLM-hallucination vector that bypasses source-priority hierarchy;
explicit tagging keeps reconciliation deterministic.

### 2.17 — YNAB (You Need A Budget)

**Learning:** every dollar must be assigned; persistent "Ready to
Assign" hot-pink CTA at top of screen is the single most effective
UI pattern in personal finance for forcing allocation discipline.
**When to apply:** future Phase P12 UnallocatedBanner + Treemap
virtual `_unallocated` tile (deferred — see plan §A1.16 G12-G14)
inherits "Ready to Assign" CTA pattern. Advisor sees persistent
banner showing total unallocated balance until zero. Click banner →
AssignAccountModal (deferred P13). Vocabulary discipline matters:
MP2.0 uses "unallocated" (canon-aligned), NOT YNAB's "ready to
assign" (consumer-register).
**Why central:** canon §6 data model treats goal-account links as
optimization unit; unassigned balance is structural blocker to
portfolio generation. YNAB's persistent affordance is the visual
pattern that makes the structural blocker visible.

### 2.18 — Quicken

**Learning:** uncategorized transactions render prominently with
one-click categorize CTA; uncategorized state never hidden behind
filter or summary number.
**When to apply:** Treemap virtual `_unallocated` tile (deferred
P12) inherits "uncategorized prominent": unallocated portion of a
Purpose account renders as tile with dashed border + striped pattern
(visually distinct from allocated tiles), not collapsed into summary
tooltip. Dashed + striped = colour-redundant cue per WCAG 2.1 AA.
**Carefully:** Quicken's "Total Net Worth" hero IS NOT adopted (§4
counter-patterns); "uncategorized prominent" rule IS.

### 2.19 — Mint (consumer net-worth tracker)

**Learning:** Mint's unified net-worth hero number masks
account-class differentials that matter for regulated wealth
management. Lesson: never roll up across classes with distinct
regulatory or tax treatment.
**When to apply:** MP2.0's HouseholdRoute AUM strip splits AUM into
Steadyhand (regulated) vs External (advisory-only) per canon Part
6.1 householding. Roll-up never collapses to single "Total Net
Worth" on household tab — that erases regulatory split that drives
compliance ratings.
**Shapes counter-pattern:** §4.1 — "Total Net Worth hero" explicitly
forbidden in MP2.0 advisor copy.

### 2.20 — Apple Wallet

**Learning:** every transaction has a category; uncategorized state
briefly visible and immediately actionable. Category chip on each
row IS the edit affordance.
**When to apply:** `frontend/src/components/ConfidenceChip.tsx`
(Phase 5b.9) and `frontend/src/goal/SourcePill.tsx` (sister-shipped
A2) adopt chip-as-affordance: chip displays state AND opens editor
on click (or, for SourcePill, opens source explanation tooltip).
Apple Wallet "no orphan transactions" mirrors MP2.0 "no orphan facts
in reviewed_state."
**Selective:** swipe-to-categorize gesture is mobile-first, not
adopted; chip-edit shape is.

### 2.21 — Toggl Goals

**Learning:** every project must map to a goal at creation; orphan
projects not allowed; goal mapping is required field, not
discoverable affordance.
**When to apply:** `frontend/src/wizard/Step3Goals.tsx`
account-centric superRefine validation (deferred P14) adopts must-
map-at-creation for accounts: every account in wizard must allocate
100% to one or more goals, validated at cell level (Apple Numbers /
Google Sheets §2.15) AND form level (Lattice §2.22).
**Why central:** orphan accounts are the smoking-gun bug behind
G12-G14 cluster (plan §A1.16): wizard accepts household where 99%
unallocated because wizard validation is goal-centric while backend
gate is account-centric. Toggl's must-map discipline pre-empts this
class of bug at the form level.

### 2.22 — Lattice / Culture Amp (HR review tools)

**Learning:** required fields blocked at form level with field-level
errors AND summary at top — both cues. Summary lists each missing
field as clickable link that scrolls to and focuses the field.
**When to apply:** `frontend/src/wizard/HouseholdWizard.tsx` Step 5
Review (and deferred P14 hardening) inherits field-level-plus-
summary: per-step trigger() validation catches errors at the cell;
Step 5 review surfaces summary list of all blockers across all steps
with links to each. Reinforces §2.15 (cell-level) and §2.21
(must-map-at-creation).
**Why central:** wizard is highest-friction surface in MP2.0;
advisor abandonment at wizard step 4 is measured pilot risk.
Lattice's pattern compresses friction by putting fix CTA next to
error AND at top.

### 2.23 — Linear (issue tracking, second cite — keyboard model)

**Learning:** keyboard-first navigation with mouse as secondary;
muted defaults so focused row stands out; spotlight commands for
navigation (Cmd-K).
**When to apply:** keyboard navigation model (focus management in
slide-outs, modals, wizard step navigation) follows Linear: every
interactive element has focus-visible ring; modals trap focus;
slide-outs return focus to trigger on close. Spotlight commands NOT
adopted in pilot; deferred to post-pilot Tier 3.
**Partial:** advisor day-one mental model is mouse-first;
keyboard-first is power-user posture earned through pilot adoption.

---

## §3 — Patterns Adopted in MP2.0 (file:line map)

The load-bearing table: source system named, MP2.0 phase named,
file:line cited. Sister-shipped patterns are back-filled per plan
§P0.5 with reverse-cited inspirations.

### 3.1 — Sister-shipped patterns (back-filled at HEAD `979a692`, tag `v0.1.3-engine-display-polish`)

Shipped in engine→UI display sub-sessions (2026-04-30 → 2026-05-04)
by parallel sister session. Cited inspirations reverse-mapped here
so this document captures the FULL MP2.0 pattern set.

| Pattern (source) | MP2.0 phase | File:line application |
|---|---|---|
| Completion-banner with structured backend payload (Stripe Connect §2.3) + muted-by-default surfaces (Linear §2.1) | A3.5 + A4 stale/integrity | `frontend/src/goal/RecommendationBanner.tsx:53-190` (5 states: current / cold-start / failure / stale / integrity-issue) |
| Risk-band-track marker visualization (Schwab §2.7) | R3 (pre-pair) | `frontend/src/charts/RiskBandTrack.tsx` (5 bands per canon §16.1) |
| Single-authoritative-view treemap (Wealthfront §2.4) + uncategorized prominent (Quicken §2.18; deferred for unallocated tile) | R3 (pre-pair) | `frontend/src/charts/Treemap.tsx` (squarified d3-hierarchy treemap with click-to-drill) |
| Goal-account allocation card (Betterment §2.5) + advisor reasoning bounded copy (Wealthfront §2.4) | A3.5 | `frontend/src/goal/AdvisorSummaryPanel.tsx:23-61` (multi-link rendering with hairline divider; sources `engine_output.link_recommendations[].advisor_summary`) |
| Household-level rollup card with fix-in-place affordance (Salesforce FSC §2.9) + completion banner failure mirror (Stripe Connect §2.3) | A4 | `frontend/src/routes/HouseholdPortfolioPanel.tsx:30-263` (current / cold-start with readiness-blockers list / failure inline / stale / integrity-issue) |
| Chip-as-affordance for state+edit (Apple Wallet §2.20) | A2 | `frontend/src/goal/SourcePill.tsx:29-64` (3 source variants: engine / calibration / calibration_drag with run-signature display) |
| Stale-state alertdialog with focus trap + auto-focus on action (Lattice §2.22 form-level discipline; Salesforce FSC §2.9 fix-in-place posture) | A4 | `frontend/src/goal/StaleRunOverlay.tsx:42-117` (3 stale statuses: invalidated / superseded / declined) |
| Engineering-only alert with no advisor action (Stripe Dashboard §2.2 system-state separation) | A4 | `frontend/src/goal/IntegrityAlertOverlay.tsx:27-59` (hash_mismatch — no Regenerate; renders run signature for engineer triage) |
| Inline cell edit in slide-out (Notion §2.14 + Apple Numbers §2.15) | Phase 5b.10 | `frontend/src/modals/DocDetailPanel.tsx` FactEditForm |
| Add-missing-fact affordance per row (Plaid §2.16 explicit-categorization generalized) | Phase 5b.11 | `frontend/src/modals/DocDetailPanel.tsx` AddFactSection |
| Bulk action bar with shared rationale capture (HubSpot §2.10 merge-with-rationale generalized) | Phase 5b.12 | `frontend/src/modals/ConflictPanel.tsx` BulkResolveBar |
| Defer-and-resurface-when-evidence-grows (Relativity §2.11 assertion discipline) | Phase 5b.13 | `frontend/src/modals/ConflictPanel.tsx` defer flow + `_conflicts` rebuild |
| Welcome tour 3-step coachmark with server-side ack (Stripe Dashboard §2.2 onboarding pattern) | Phase 5b.6 | `frontend/src/chrome/WelcomeTour.tsx` + `tour_completed_at` field |
| Worker health banner persistent system-state (Linear §2.1 muted-by-default + Stripe Dashboard §2.2 system status) | Phase 5b.2 | `frontend/src/chrome/WorkerHealthBanner.tsx` |
| Pilot disclaimer ribbon with version-pinned ack (Lattice §2.22 form-level discipline applied at app shell) | Phase 5b.1 | `frontend/src/chrome/PilotBanner.tsx` + `DISCLAIMER_VERSION` |
| Free-text feedback channel persistent in chrome (Linear §2.1 command-bar adjacency) | Phase 5b.1 | `frontend/src/chrome/FeedbackButton.tsx` + Feedback model |
| Slide-out from right edge with focus management (Figma §2.13 right-rail context) | Phase 5b.5 | `frontend/src/modals/DocDetailPanel.tsx` (auto-focus close button on open; Esc binding) |
| Last-client memory across navigation (Vanguard §2.6 switch-without-losing-context) | R2 (pre-pair) | `frontend/src/lib/clients.ts` `useRememberedClientId` localStorage |
| Pagination with Load-more on long rosters (Stripe Dashboard §2.2 flat listing density) | Phase 5b.7 | `frontend/src/chrome/ClientPicker.tsx` PAGE_SIZE=20 |
| Toast dedup under rapid mutation (Linear §2.1 muted-by-default extends to notifications) | UX-polish | `frontend/src/lib/toast.ts` 1.5s memory window |
| Multi-pane research-bench density for analyst-only surface (Morningstar §2.8) | R6+ | `frontend/src/routes/CmaRoute.tsx` (CMA Workbench: edit + frontier + draft state + audit) |

### 3.2 — Patterns adopted by current pair (Phase P0 + sister A6+A7)

Table seeded at P0 dispatch; later pairs append rows with phase
commit hash.

| Pattern (source) | MP2.0 phase | File:line application | Phase commit |
|---|---|---|---|
| (P0 itself; this document) | P0 | `docs/agent/design-system-research.md` | (this commit) |

### 3.3 — Patterns scheduled for adoption (deferred phases)

Forward-citations; when phase commits, row migrates to §3.2 with
actual commit hash and verified file:line.

| Pattern (source) | MP2.0 phase | Anticipated file:line | Notes |
|---|---|---|---|
| Field-level fix-in-place with structured backend blockers (Stripe Connect §2.3 + Salesforce FSC §2.9) | P11 | `web/api/review_state.py:329-401` PortfolioGenerationBlocker structured objects + `frontend/src/routes/HouseholdRoute.tsx` BlockerBanner | Sister has shipped readiness_blockers list rendering at HouseholdPortfolioPanel.tsx:115-126; P11 extends to clickable structured rows |
| Every-dollar-assigned persistent CTA (YNAB §2.17) + uncategorized prominent (Quicken §2.18) | P12 | `frontend/src/routes/HouseholdRoute.tsx` UnallocatedBanner + `frontend/src/charts/Treemap.tsx` `_unallocated` virtual tile | dashed border + striped pattern; canon-vocab "unallocated" not "ready to assign" |
| Goal-required-at-account-creation (Wealthfront §2.4 + Toggl §2.21 must-map-at-creation) | P14 | `frontend/src/wizard/schema.ts` superRefine + `frontend/src/wizard/Step3Goals.tsx` per-account % | Field-level + summary per Lattice §2.22 |
| One-click resolve via dedicated modal (Salesforce FSC §2.9) | P13 | `frontend/src/modals/AssignAccountModal.tsx` (new) | Same backend endpoint as RealignModal; semantically distinct (assign vs reassign) |
| Cross-doc entity alignment with score-based matching (HubSpot §2.10 duplicate-detection ladder) | P1.1 | `extraction/entity_alignment.py` (new) | Backend-only; no UI surface change |
| Schema-aligned wizard validation (Lattice §2.22 + Apple Numbers §2.15) | P5 | `frontend/src/wizard/schema.ts` unified backend-mirroring zod | OpenAPI codegen drift gate prevents future drift |
| Inline cell edit in DocDropOverlay quick-fix (Notion §2.14) | P3.1 | `frontend/src/modals/DocDropOverlay.tsx` quick-fix | Stale copy fix |
| Tab-state propagation in ContextPanel (Figma §2.13 right-rail context) | P3.2 | `frontend/src/components/ContextPanel.tsx` Tabs.Root controlled value | G4 fix |

---

## §4 — Counter-Patterns Avoided (with reasoning)

Source system (or pattern family), failure mode, canon section
backing MP2.0's rejection. Explicit guards; future sessions tempted
to adopt must read this section first.

### 4.1 — Total Net Worth hero number

**Source:** Quicken (§2.18 — adopted for "uncategorized prominent")
and Mint (§2.19 — counter-cited). Retail consumer net-worth UIs roll
up checking, savings, retirement, taxable, real estate, and crypto
into one above-the-fold number.
**Why avoided:** the roll-up collapses the regulated split between
Steadyhand-managed (CIRO/MFDA-regulated, fee-disclosure-bound,
suitability-rated) AUM and external advisory-only assets. An advisor
making a regulated recommendation needs the split visible at all
times; collapsing it makes the regulated portion invisible at the
most important moment.
**Canon backing:** Part 6.1 (householding) treats Steadyhand vs
External as structural distinction, not presentation choice. Canon
§16.1 mandates demo-friendly terminology that does NOT include a
unified net-worth-hero.
**Alternative:** HouseholdRoute AUM strip shows Steadyhand AUM and
External AUM as parallel bands with descriptors; treemap drills only
into Steadyhand-managed holdings; external holdings appear as
household-risk dampener (canon Part 4.6a), never as treemap tiles.

### 4.2 — Auto-resolve via heuristic (silent inference)

**Source:** Betterment (§2.5 auto-categorization), HubSpot (§2.10
auto-merge under high confidence), broad fintech "we made a guess,
click here to confirm or correct" pattern.
**Why avoided:** advisor surfaces are not consumer-grade; silent
inference at high confidence is the LLM-hallucination vector that
bypasses source-priority hierarchy and creates "recommendation came
out wrong because system silently mis-categorized one input three
steps upstream" — the failure mode canon §9.4.5 explicitly forbids.
**Canon backing:** §9.4.5 (determinism / AI-creativity balance) —
"Output never includes numbers that didn't come from the engine. AI
styles the deterministic output; AI does not produce financial
figures." Generalized: AI does not silently categorize, merge, or
infer in advisor-impacting paths.
**Alternative:** every conflict gets a card; advisor explicitly
chooses; rationale captured (HubSpot §2.10 merge-with-rationale).
Auto-merge under high confidence replaced by best-default-preselected
with one-click confirm — choice still explicit.

### 4.3 — All-in-one super-form intake

**Source:** legacy enterprise CRM intake forms, some KYC vendors,
"submit a giant form to get started" pattern.
**Why avoided:** super-forms have catastrophic abandonment curves;
partial-progress recovery is hard; field-level errors collide with
form-level errors.
**Canon backing:** ux-spec.md F.1 (multi-step wizard SHIPPED
PILOT-tier). Canon Part 11.5.1 (engine-ready gating with required
sections) treats intake as section-decomposable.
**Alternative:** `HouseholdWizard.tsx` 5-step wizard with per-step
trigger() validation, sessionStorage + localStorage draft recovery
(Phase 5b.8), Step 5 review summary (Lattice §2.22).

### 4.4 — Hidden-by-default advanced fields (disclosures)

**Source:** consumer fintech onboarding (deliberate friction
reduction); some compliance UIs.
**Why avoided for advisor surfaces:** advisors are power users with
explicit information needs; hiding advanced fields behind disclosure
toggles increases cognitive load (advisor hunts for the field) and
creates "I didn't see it" risk for compliance fields.
**Canon backing:** Part 7 (regulatory & compliance constraints) —
KYC fields, suitability ratings, risk-tolerance components are all
advisor-visible by default. Canon §16.1 ("Three-component risk
exposure") explicitly mandates three components surface in the UI
"rather than hidden behind a single 'your risk score is X.'"
**Alternative:** dense layout with all advisor-relevant fields
visible; slide-out pattern (DocDetailPanel) is for deep-dive
contextual data, not for hiding required fields.

### 4.5 — Inferred-progress completion bars without field counts

**Source:** consumer onboarding "75% complete" progress bars; some
HR onboarding tools.
**Why avoided:** "75% complete" is meaningless without field-level
breakdown; advisors cannot act on percentage. Worse, a heuristic
percentage incentivizes hand-waving ("bar is 90%, you're almost
done" when actually 5 required fields are missing).
**Canon backing:** ux-spec.md C.7 (visual hierarchy: required vs
nice-to-have) and readiness-blockers contract in
`web/api/review_state.py` `readiness_for_state` — returns structured
list of typed blockers, not percentage.
**Alternative:** literal readiness blockers (e.g. "Date of birth
required for [synthetic person]", "Goal target amount required for
[goal name]") rendered as list, each linkable to the field via
fix-in-place (P11 deferred). Cold-start state on
HouseholdPortfolioPanel.tsx:115-126 already renders this list.

### 4.6 — Modal-on-modal stacks

**Source:** some legacy admin UIs; deeply-nested wizards with edit
modals on top of step modals.
**Why avoided:** stacks break focus management (tab order escapes
inner modal), accessibility (screen readers lose dialog hierarchy),
and cognitive ergonomics (advisor forgets which level of nesting).
**Canon backing:** ux-spec.md component taxonomy — "Block the user
only when the action MUST complete or be cancelled (Modal). For
deep-dive without blocking, use Slide-out." Implicitly: never stack
two blockings.
**Alternative:** one modal at a time. For deep-dive without blocking,
slide-out (DocDetailPanel) supersedes secondary modal; for inline
edit, inline-form (Notion §2.14) supersedes child modal.

### 4.7 — Color-only conveyance

**Source:** widespread anti-pattern across consumer fintech; some
internal admin UIs.
**Why avoided:** WCAG 2.1 AA requires color + secondary cue (text
label, icon, pattern). MP2.0 colorblind-palette audit deferred to
post-pilot (ux-spec.md I.4) but color+text+icon trio is pilot scope.
**Canon backing:** ux-spec.md I.1 (WCAG 2.1 AA semantic HTML) + I.7
(prefers-reduced-motion). Both backed by canon Part 7 accessibility.
**Alternative:** every status chip carries text label AND color AND
lucide-icon; ConfidenceChip is canonical example
(`frontend/src/components/ConfidenceChip.tsx` Phase 5b.9 — color +
text label per locked decision).

### 4.8 — Toast-only error reporting for blocking errors

**Source:** consumer fintech "your transaction failed" toasts that
disappear before the user can read them.
**Why avoided:** blocking errors must persist until the user has a
chance to act. Toasts are transient (≤5s); blocking errors render
inline AND emit toast as reinforcement, never toast-only.
**Canon backing:** ux-spec.md Component Taxonomy — "Toast for
transient confirmations. For persistent state changes, use a Banner."
Sister pattern at RecommendationBanner.tsx:65-71 + locked #9 (toast
as reinforcement, not primary) implements this discipline.
**Alternative:** blocking errors get inline rendering (banner OR
inline section header) AND toast on first occurrence; subsequent
renders of same error don't re-toast (lastSurfacedRef dedup at
RecommendationBanner.tsx:63-71). Non-blocking errors (e.g. single
field validation) toast with clear next-step CTA in toast body.

---

## §5 — Decision Log (why each pattern chosen over alternatives)

This section captures the "we considered both, here's why we picked
one" reasoning. Future sessions tempted to revisit a decision read
this section first.

### 5.1 — Dual inline + wizard Add CTA (P3.3, deferred) over single pattern

**Considered:** single Add CTA (inline-only OR wizard-only).
**Chosen:** dual — inline `Plus` for quick-add when N ≤ 3, wizard
step for bulk-add when N ≥ 4.
**Why:** YNAB bulk-wizard (§2.17) fits batch-mode; Notion inline-edit
(§2.14) fits fix-mode. One pattern at both thresholds creates
friction at the other end.

### 5.2 — New AssignAccountModal (P13, deferred) over RealignModal extension

**Considered:** extending RealignModal with a mode prop for both
unallocated-assignment and reassignment.
**Chosen:** new AssignAccountModal sharing the same backend endpoint
with distinct copy and mental model.
**Why:** Salesforce FSC (§2.9) keeps reassign vs assign semantically
distinct. Conflating in one modal forces a mode-toggle that adds
cognitive load. Backend endpoint reuse keeps implementation lean.

### 5.3 — Backend structured blockers (P11, deferred) over frontend string-parsing

**Considered:** parsing `engine_ready=False` error sentence
client-side to extract field references.
**Chosen:** backend returns structured list of typed
PortfolioGenerationBlocker objects; frontend renders typed list with
per-blocker fix CTA.
**Why:** Stripe Connect (§2.3) keeps source-of-truth backend-side.
Frontend string-parsing breaks under i18n (different word order),
under prompt revisions (silent regex breakage), and creates silent
regression risk for new blocker types.

### 5.4 — Account-centric superRefine (P14, deferred) over runtime gate-only

**Considered:** rely solely on backend `engine_ready` gate at commit;
let wizard accept any input.
**Chosen:** Lattice-pattern (§2.22) field-level + form-level zod
validation BEFORE backend submission.
**Why:** the backend gate is authoritative, but catching the error
at the wizard step (where the field is) is ~10x faster ergonomically
than at commit (where advisor navigates back). Dual-validation
optimizes for advisor experience without sacrificing backend
correctness. P5 schema-unify (deferred) eliminates drift via
generated zod from OpenAPI.

### 5.5 — Inline render of failure inside route-level ErrorBoundary (sister-shipped) over global error toast

**Considered:** route-level error toast with rest of route showing
previous state.
**Chosen:** inline render of failure state inside route-level
ErrorBoundary plus Sonner toast on first surface (lastSurfacedRef
dedup at RecommendationBanner.tsx:63-71).
**Why:** §4.8 (toast-only blocking error forbidden). Previous
recommendation is misleading once new generation failed. Inline
render keeps advisor on route, surfaces Retry CTA at the spot the
recommendation would have been.

### 5.6 — Three sleeve-source pill variants over two

**Considered:** two variants — engine vs calibration.
**Chosen:** three variants with calibration_drag distinct during
slider drag.
**Why:** calibration_drag is operationally distinct (what-if preview,
not persistent baseline). Conflating risks advisor thinking dragged
value is saved. Apple Wallet chip-as-affordance discipline (§2.20)
generalized: every state-change has a visible chip variant.

### 5.7 — Hash-mismatch as engineering-only overlay (no Regenerate CTA)

**Considered:** hash_mismatch surfaces with Regenerate CTA same as
invalidated/superseded/declined.
**Chosen:** separate IntegrityAlertOverlay with NO advisor action;
engineering investigates via ops-runbook §2.
**Why:** hash_mismatch is a backend integrity violation (stored
signature ≠ recomputed signature from same inputs). Regenerating
doesn't help — same inputs fail same way. Salesforce FSC fix-in-place
(§2.9) is for advisor-recoverable issues; this isn't one. Backend
auto-emits `portfolio_run_integrity_alert` AuditEvent (Phase A1
commit `95dfd01`).

### 5.8 — Slide-out from right edge for DocDetailPanel over modal

**Considered:** modal for per-doc detail view.
**Chosen:** slide-out from right edge with semi-transparent backdrop.
**Why:** per-doc detail is a deep-dive without blocking; parent
ReviewScreen context (other docs, conflict counts, readiness)
remains visible. Figma right-rail context (§2.13) softened —
right-rail-on-demand. Avoids modal-on-modal stack risk (§4.6).

### 5.9 — Bulk conflict resolve emits one audit event per conflict

**Considered:** one audit event with `bulk: True` and array of
conflict IDs.
**Chosen:** one audit event per conflict, each with `bulk: True` +
`bulk_count: N`.
**Why:** audit traceability — each conflict's resolution must be
independently inspectable for compliance review. HubSpot
merge-with-rationale (§2.10) extends to bulk: bulk doesn't bypass
rationale, shares rationale across the set.

### 5.10 — Vocab discipline as CI gate over linter rule

**Considered:** ESLint rule with custom vocabulary plugin.
**Chosen:** standalone `scripts/check-vocab.sh` Perl-regex grep
script gated in CI.
**Why:** the vocab list is small (4 forbidden patterns currently);
a 100-line bash script is more inspectable than an ESLint plugin
and reaches backend Python (serializers + commands + migrations)
that ESLint cannot. `docs/agent/` allowlisted so this document can
reference forbidden words.

---

## §6 — Implementation Refs (auto-updated; append per-phase)

"What shipped where" log. Each entry: phase ID, commit hash,
file:line, pattern reference (§3 row).

### 6.1 — Pre-pair baseline

§3.1 (sister-shipped at HEAD `979a692`) IS the pre-pair inventory.

### 6.2 — Pair 1 entries (P0 + sister A6+A7 close-out)

| Phase | Commit | File:line | Pattern (§3 row) | Notes |
|---|---|---|---|---|
| P0 | (this commit) | `docs/agent/design-system-research.md:*` | (this document; meta-entry) | Cross-references CLAUDE.md, MEMORY.md, ux-spec.md, design-system.md, post-pilot-improvements.md |

### 6.3 — Pair 2+ entries (deferred)

To be appended as later pairs ship. Plan §A1.16 sequence: Pair 2 =
P11 + P14; Pair 3 = P5 + P3.1+P3.2; subsequent = P1.1, P12, P13.
Each phase commit references this document by relative path AND
cites the §3 row realized. Verification at A7 PII review per plan
§A1.40.

---

## §7 — Lifecycle + Cross-Session Contract

This section is the explicit contract that future sessions read on
startup (CLAUDE.md auto-loads this file's existence).

### 7.1 — Read-when (mandatory)

Future sessions MUST read this document before designing or
implementing any new advisor-facing surface (route, modal,
slide-out, banner, card, chip, overlay), changing component
patterns (card vs banner vs modal vs slide-out vs toast vs
coachmark), introducing advisor-facing copy (every i18n key is a
copy decision), or adding a new external system to §2.

Future sessions SHOULD read this document before designing
analyst-facing surfaces (Morningstar-class research-bench density
§2.8 is the relevant split) or adding a new error-handling path
(§4.8 + §5.5 both back the inline-render-with-toast-reinforcement
discipline).

### 7.2 — Update-when

SHOULD update when: a new pattern is adopted from a system not
yet cited (§2 + §3 + consider §4); an existing pattern lands in
a new file (§3.3 → §3.2 transition with commit hash); an
anti-pattern is rejected (§4 with reasoning + canon backing); a
decision is revisited (append §5 entry with date).

MUST update when: a pattern migrates from §3.3 to §3.2 with phase
commit hash; an adopted pattern is reversed (rare; requires its
own §5 entry); Lori review surfaces canon-vocab violation.

### 7.3 — Prune-when (post-pilot, Lori-reviewed)

A pattern applied 3+ times across surfaces becomes canonical and
migrates to `ux-spec.md` (conceptual patterns) or
`design-system.md` (reusable components). After migration, the §3
row here becomes a one-line stub pointing to the canonical home.
This keeps the research document narrow — captures novel
applications, not steady-state.

Pruning happens post-pilot week 2 with Lori review: vocab
compliance audit, 3+ pattern migration, 0-application pattern
demotion to §4.

### 7.4 — Cross-session collision handling

Sister sessions running in parallel may both append. Protocol:
each session appends to its own §3.2 or §3.3 row; at pair-commit
boundary, the owning session merges; same pattern from same source
for different surfaces → both kept (pattern general, file:line
specific); disagreement on §4 → open-questions.md entry; user
decides at next session-state review.

### 7.5 — Versioning

Git history IS the version history. Each commit references the
phase ID + commit hash that motivated the change. The `Last
updated:` line at the top reflects the most recent meaningful
update.

### 7.6 — Connection to canon

The canon (`MP2.0_Working_Canon.md`) is authoritative for
product/strategy/regulatory/architecture intent; this document is
the design-system + UX research artifact downstream of canon.
When canon changes: §6.3a vocab → §4 re-validation; §9.4.5
AI-numbers → §3 + §4 re-validation; §11.4 source-priority → §2.10
+ §3.1 reconciliation re-validation; §11.8.3 defense-in-depth →
§1 real-PII discipline re-validation. Canon takes precedence on
contradiction; this document is updated to reflect canon position.

---

## Appendix A — Quick lookup index

For sessions in a hurry: cite-by-pattern shortcut.

| If you're building... | Read first |
|---|---|
| A persistent state banner | §2.3, §3.1 (RecommendationBanner.tsx), §5.5, §4.8 |
| A multi-entity nav | §2.2, §2.6, §3.1 (ClientPicker.tsx) |
| A risk-band visualization | §2.7, §3.1 (RiskBandTrack.tsx); canon §16.1 |
| An allocation chart | §2.4, §2.18, §3.1 (Treemap.tsx); §4.1 |
| A goal-account card | §2.5, §3.1 (AdvisorSummaryPanel.tsx); §4.2 |
| A conflict resolution surface | §2.10, §3.1 (ConflictPanel.tsx); §4.2 |
| A doc review surface | §2.11, §2.12, §3.1 (DocDetailPanel.tsx) |
| A slide-out deep-dive | §2.13, §3.1 (DocDetailPanel.tsx); §5.8 |
| An inline cell editor | §2.14, §2.15, §3.1 |
| A wizard with required fields | §2.21, §2.22, §3.3 (P14), §5.4 |
| An every-dollar-assigned CTA | §2.17, §2.18, §3.3 (P12) |
| A doc upload with category disambiguation | §2.16, §3.1 (DocDropOverlay.tsx) |
| An analyst-only research workbench | §2.8, §3.1 (CmaRoute.tsx) |
| A status chip with state+edit affordance | §2.20, §3.1 (ConfidenceChip.tsx, SourcePill.tsx) |
| An engineering-only alert (no advisor action) | §3.1 (IntegrityAlertOverlay.tsx), §5.7 |

---

## Appendix B — Counter-pattern at-a-glance

When tempted to adopt a pattern that "feels right but," check this
list:

1. **Total Net Worth hero** — never; canon Part 6.1 + §4.1.
2. **Auto-resolve heuristic** — never; canon §9.4.5 + §4.2.
3. **All-in-one super-form** — never; canon Part 11.5.1 + §4.3.
4. **Hidden advanced fields** — never on advisor surfaces; §4.4.
5. **Inferred-progress %** — never; readiness blockers structured + §4.5.
6. **Modal-on-modal** — never; slide-out or inline-form alternative + §4.6.
7. **Color-only conveyance** — never; WCAG 2.1 AA color+text+icon trio + §4.7.
8. **Toast-only blocking error** — never; inline-render + toast-reinforcement + §4.8.

---

## Appendix C — Vocabulary discipline cross-cite

Per canon §6.3a + §16 (vocab CI enforced):

- Risk descriptors: Cautious / Conservative-balanced / Balanced /
  Balanced-growth / Growth-oriented (NEVER low/medium/high in
  client-visible copy).
- Fund vocabulary: building-block fund (NOT sleeve in user-visible
  surfaces; the code identifier `Sleeve` Pydantic class is allowed
  per Part 16); whole-portfolio fund.
- Re-goaling vocabulary: re-goaling, re-allocate, re-balance
  (NEVER "transfer", "move money", "reallocation" without hyphen
  in goal-realignment context).
- Engineer-internal: Goal_50 is engine-internal; never surfaces in
  advisor copy.
- Engineering-only-status: hash_mismatch is the engineering term;
  advisor copy says "integrity issue, see ops-runbook" and routes
  to engineering.

---
