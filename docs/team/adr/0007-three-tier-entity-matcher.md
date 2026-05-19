---
title: ADR-0007 — Three-tier entity matcher (auto-merge / advisor / new-canonical)
status: Accepted
decision_date: 2026-05-05
deciders: [Saranyaraj Rajendran, Fraser Stark]
supersedes: []
superseded_by: []
owner: Saranyaraj Rajendran
last_revised: 2026-05-12
update_when: This ADR's supersession-path conditions trigger an update; otherwise revise when the cited canon section, code symbols, or referenced sibling ADRs change.
---

# ADR-0007 — Three-tier entity matcher

**Status:** Accepted
**Decision date:** 2026-05-05 (Round 18 #1 LOCKED; commit `7274485`)
**Deciders:** Saranyaraj Rajendran (engineering lead); Fraser Stark
(project lead).

## Context

Layer 4 of the extraction pipeline (canon §11.4) takes facts produced
by Layer 3's LLM extraction and groups them by canonical entity (a
specific person, account, or goal). The matcher decides "is this fact
about the same Mike Chen as that other fact?"

Round 13 #2 LOCKED tightened the auto-merge threshold to require two
identity fields (e.g., name + DOB, or name + last_name + last-4 of
account_number). This eliminated the father+son same-surname
false-merge that had surfaced earlier.

After v0.1.3-pilot-quality-closure shipped (2026-05-05), end-of-session
real-PII verification on a real client couple workspace surfaced a
high-severity defect: the matcher produced **11 person canonicals,
30 account canonicals, and 18 goal canonicals** for what the canon
says is a couple (~2 / ~5–7 / ~3–4 expected).

Root cause: real LLM extraction obeys canon §9.4.5 ("only emit what's
in the doc"). Real client documents have sparse identity fields
(6/17 DOBs, 8/29 account numbers in the workspace examined).
Synthetic Hypothesis property tests pass because their strategies
generate facts with all identity fields populated. Real data has a
fundamentally different missingness distribution.

The obvious fix — loosen the auto-merge threshold to allow single-field
matches — would re-introduce the father+son false-merge. **Wrong fix.**

The right fix is a **third state**: medium-confidence merge candidates
that surface to the advisor for explicit adjudication. This preserves
the canon §9.4.5 discipline ("AI never invents; advisor explicitly
decides") while resolving real-PII over-fragmentation.

## Decision

Entity alignment operates in three tiers:

**Tier 1 — Auto-merge (UNCHANGED from Round 13 #2 LOCKED).**

- People: `name + DOB → 100` OR `name + last_name + last-4 of
  account_number → ≥115`.
- Accounts: `account_number_hash` exact match OR `type + institution
  + single-candidate` → ≥80.
- Goals: `normalize_key(name)` → ≥80.

Tier-1 matches are merged silently.

**Tier 2 — Merge candidate (NEW; advisor adjudicates).**

Emitted when the score lands in a medium band AND no contradicting
identity field exists on either canonical.

- People band: 60–99 (e.g., single-field name match with no
  contradicting DOB or last_name).
- Accounts band: 50–79 (e.g., type + institution match with no
  contradicting account_number_hash).
- Goals band: 50–79 (e.g., target + horizon close with no
  contradicting name).

The "contradicting field" rule: if canonical A has `DOB = X` and
canonical B has `DOB = Y` where `X ≠ Y`, they're NOT a Tier-2 candidate
— they're clearly different people. Same for `last_name`,
`account_number_hash`, `institution`.

Tier-2 candidates persist to `reviewed_state['merge_candidates']` and
surface in the frontend ConflictPanel under a "Possible duplicates (N)"
group (Phase B2, in flight at time of writing).

**Tier 3 — New canonical (existing fall-through).**

Below all bands OR at least one contradicting identity field present.
A new canonical entity is created.

**Merge action data semantics (Round 18 #16).** When the advisor
clicks "Merge" on a Tier-2 candidate:

1. Compute target = the canonical with more contributing documents
   (tie-break: lower canonical_index).
2. Re-index all `ExtractedFact` rows where `canonical_index == B` to
   `canonical_index = A` via a single SQL update.
3. Remove canonical-B from `EntityAlignment.canonical_entities`.
   canonical_index slots are NOT renumbered (preserves audit
   references).
4. Re-derive `reviewed_state[prefix]` array from facts.
5. Persist the decision to
   `reviewed_state['merge_decisions']` as
   `{"people:0:2": "merge"}`.
6. Emit AuditEvent `entity_merge_candidate_resolved` with structural
   metadata (counts + UUIDs only; never raw names).

**Re-reconcile preserves decision history (Round 18 #17).** On a fresh
reconcile run, prior `keep_separate` decisions stay hidden; prior
`merge` decisions get re-executed automatically; prior `defer`
decisions re-surface for re-adjudication.

## Consequences

### Positive

- Real-PII over-fragmentation now has a resolution path that respects
  canon §9.4.5. The advisor (not the system) decides when sparse
  identity fields warrant a merge.
- The father+son guard remains: contradicting DOB or last_name keeps
  them separate.
- Decisions are durable across reconcile cycles via
  `reviewed_state['merge_decisions']`. Re-reconciling doesn't ask the
  advisor to re-adjudicate the same pair.
- Audit trail captures the adjudication: each `merge_candidate_resolved`
  event records which canonical-pair, which decision, and the
  contributing-doc counts.
- Bulk "keep separate" is supported (no bulk merge — every merge
  requires an explicit advisor click per canon §9.4.5).

### Negative

- The advisor will see a new surface (the MergeCandidateGroup in the
  ConflictPanel) once the Phase B2 UI ships and must learn to
  adjudicate. **As of 2026-05-12 the backend endpoints
  (`MergeCandidateResolveView`, `MergeCandidateBulkKeepSeparateView`)
  and the persistence layer (`reviewed_state['merge_candidates']`) are
  live, but the frontend MergeCandidateGroup component is still in
  the Phase B2 backlog.** Workspaces created today store
  `merge_candidates` data but show no UI for resolution. Onboarding
  doc covers the contract in the Week 1 tour.
- The matcher emits more candidates than synthetic tests anticipate.
  Some workspaces (a real client couple) may surface 20+ candidates
  on first reconcile. The bulk "Mark all separate" action mitigates
  but doesn't eliminate the friction.
- The Phase B2 UI (MergeCandidateGroup) shipped after the backend
  endpoints. Workspaces created between backend ship (2026-05-05) and
  Phase B2 UI ship store `merge_candidates` in `reviewed_state` but
  show no UI. This is a temporary gap.

## Alternatives considered

### Alternative A: Loosen the Tier-1 threshold (single-field name
match becomes auto-merge)

Rejected. Re-introduces father+son false-merges. Wrong fix.

### Alternative B: Auto-merge with a confidence indicator (merge
silently but flag low-confidence merges)

Rejected. Violates canon §9.4.5 — the system would be making an
invent-y decision and asking the advisor to undo it. The right model
is opt-in advisor adjudication.

### Alternative C: Single Tier-2 score (e.g., a single 50–99 band
across all entity types)

Rejected. Different entity types have different identity-field
distributions. Accounts have account_number_hash; goals don't.
Per-type bands are more precise.

## Supersession path

If pilot feedback shows Tier-2 friction is sustained (e.g., advisors
report ≥20 candidates per workspace consistently), supersede with
either:

- An ML-driven matcher that uses contextual signals beyond field
  matches (date proximity, document context).
- A first-pass advisor preset that auto-applies "keep separate" to
  pairs below a configurable confidence threshold.

Sign-off required from Fraser Stark (product) + Saranyaraj Rajendran.
Pilot week 4 retrospective is the natural trigger.

## References

- Canon §11.4 — source-priority hierarchy + same-class vs cross-class
  disagreement
- Canon §9.4.5 — "AI never invents financial numbers"
- `extraction/entity_alignment.py` — three-tier matcher implementation
  (Tier-1 thresholds; Tier-2 bands; `MergeCandidate` dataclass)
- `web/api/views.py` — `MergeCandidateResolveView` +
  `MergeCandidateBulkKeepSeparateView`
- `web/api/review_state.py` — `reviewed_state['merge_candidates']` +
  `reviewed_state['merge_decisions']` persistence
- `docs/agent/handoff-log.md` 2026-05-05 — P1.1 fix landing entry
- `~/.claude/plans/you-are-continuing-a-playful-hammock.md` — Round 18
  full 37-lock-in plan
- Sibling ADRs:
  - ADR-0012 (source-priority hierarchy) — the field-level resolution
    that runs alongside entity alignment.
  - ADR-0002 (append-only audit) — the audit emission for merge
    decisions.
