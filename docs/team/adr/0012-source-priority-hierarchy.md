---
title: ADR-0012 — Source-priority hierarchy
status: Accepted
decision_date: 2026-04-30
deciders: [Saranyaraj Rajendran, Lori Norman]
supersedes: []
superseded_by: []
owner: Saranyaraj Rajendran
last_revised: 2026-05-12
update_when: This ADR's supersession-path conditions trigger an update; otherwise revise when the cited canon section, code symbols, or referenced sibling ADRs change.
---

# ADR-0012 — Source-priority hierarchy

**Status:** Accepted
**Decision date:** 2026-04-30 (canon §11.4)
**Deciders:** Saranyaraj Rajendran (engineering lead); Lori Norman
(compliance + IS lead).

## Context

Real client documents disagree with each other. A KYC form from
2024-Q1 lists a date of birth; a meeting note from 2025-Q3 mentions
the spouse's date of birth in passing. Each is a fact about the same
person, but they may contain different values (or the same value
written differently).

The extraction pipeline produces multiple `ExtractedFact` rows for the
same field. Layer 4 reconciliation must decide what the canonical
value is.

Two failure modes are bad:

1. **Surface every disagreement as a conflict.** Floods the advisor
   with conflicts that aren't real disagreements (a note casually
   mentioning a date that's already established in KYC).
2. **Pick the most-recent-wins silently.** Lose audit trail of the
   resolution; misclassify a low-confidence note as authoritative.

The canon's framing (Canon §11.4) provides a structured hierarchy
that resolves most disagreements silently while still surfacing the
ones that need advisor adjudication.

## Decision

The source-priority hierarchy is:

```
Advisor override (FactOverride)
  ↓
System of Record (KYC, custodial statement)
  ↓
Structured planning doc (Conquest/Adviice/Planworth export, intake form)
  ↓
Note-derived fact (meeting_note, generic_financial)
```

Resolution rules:

- **Cross-class disagreement** (different source classes disagree;
  e.g., KYC says DOB=X, note says DOB=Y) resolves **silently** to
  the higher-priority source. The advisor doesn't see a conflict.
- **Same-class disagreement** (same source class disagrees with
  itself; e.g., two meeting notes from different dates list different
  DOBs) surfaces as a **conflict card** in the ConflictPanel for
  advisor adjudication with rationale + evidence_ack.
- **Advisor override** (`FactOverride` rows) trumps everything below
  it. The override is append-only; the latest row for a given
  `(workspace, field)` wins.
- **`derivation_method`** further qualifies the fact: `extracted`
  (LLM read it from the doc), `inferred` (LLM inferred from context),
  `defaulted` (banned — code-smell per canon §9.4.5).

Implementation:

- `extraction/reconciliation.py` carries `conflicts_for_facts` and
  `current_facts_by_field`.
- `web/api/review_state.py` consumes these to build the conflict UI
  contract.
- The cross-class silent resolution is what makes the advisor's
  conflict load tractable. Pre-canon-§11.4, every disagreement
  surfaced; the load was untenable on real-PII workspaces.

## Consequences

### Positive

- The advisor's conflict load is bounded to *real* disagreements, not
  artifacts of cross-class mention.
- The hierarchy is auditable: every silently-resolved disagreement
  is reconstructable from the underlying ExtractedFact rows + their
  document types.
- Advisor override is the top of the hierarchy, which matches the
  canon §9.4.5 discipline ("advisor explicitly decides").
- The structure handles the most common pattern (KYC is authoritative;
  notes are supplementary) without per-field tuning.

### Negative

- The "cross-class silent resolution" can hide genuine errors. If a
  note correctly captures an updated DOB but the KYC is stale, the
  silent resolution keeps the wrong KYC value. The advisor can
  notice and apply a `FactOverride`, but the system doesn't surface
  the discrepancy automatically. Phase B+ work could add an "audit"
  view showing all silent resolutions per workspace.
- The hierarchy doesn't carry confidence. A high-confidence note
  (e.g., "the client's DOB is 1968-07-04, confirmed during call")
  doesn't outweigh a low-confidence KYC. Confidence is a separate
  qualifier (`derivation_method`); combining the two would complicate
  the rule.
- Same-class disagreement always surfaces, even when one source is
  clearly stale. The advisor still has to click through. The
  ConflictPanel's bulk-resolve UI mitigates.

## Alternatives considered

### Alternative A: Most-recent-wins across all sources

Rejected. Loses the auditability of "KYC is system-of-record."
Misclassifies a casual note mention as overriding a structured form.

### Alternative B: Confidence-weighted scoring across all sources

Rejected. Confidence is hard to calibrate across document types; the
LLM's confidence on a KYC form vs a meeting note isn't directly
comparable. The hierarchy provides a cleaner default.

### Alternative C: Surface every disagreement as a conflict, no silent resolution

Rejected. Advisor load is untenable on real-PII workspaces. The
real-PII verification that surfaced the Tier-2 matcher need (ADR-0007)
also showed the conflict load was the bottleneck without
cross-class silent resolution.

## Supersession path

If pilot feedback shows the silent cross-class resolution misclassifies
too often (e.g., advisors report finding stale-KYC values that the
system didn't flag), supersede with either:

- An "audit view" surface showing silently-resolved disagreements,
  toggleable by the advisor.
- A confidence-weighted layer on top of the hierarchy that surfaces
  high-confidence note overrides as conflicts.

Sign-off required from Lori Norman + Saranyaraj Rajendran. Pilot
week 4 retrospective is the natural trigger.

## References

- Canon §11.4 — "Layer 4 — Field reconciliation"
- Canon §9.4.5 — "AI doesn't invent financial numbers"
- `extraction/reconciliation.py` — `conflicts_for_facts`,
  `current_facts_by_field`
- `web/api/review_state.py` — conflict UI contract
- `web/api/models.py` — `FactOverride` (append-only)
- `frontend/src/modals/ConflictPanel.tsx` — the advisor surface for
  same-class disagreements
- Sibling ADRs:
  - ADR-0007 (three-tier entity matcher) — the entity-level resolution
    that runs alongside this field-level resolution
  - ADR-0011 (vocabulary discipline) — `derivation_method =
    "defaulted"` is banned
