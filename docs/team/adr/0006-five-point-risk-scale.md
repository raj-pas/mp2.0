---
title: ADR-0006 — Five-point risk scale with snap-to-grid percentile mapping
status: Accepted
decision_date: 2026-04-30
deciders: [Saranyaraj Rajendran, Fraser Stark, Lori Norman]
supersedes: []
superseded_by: []
owner: Saranyaraj Rajendran
last_revised: 2026-05-12
update_when: This ADR's supersession-path conditions trigger an update; otherwise revise when the cited canon section, code symbols, or referenced sibling ADRs change.
---

# ADR-0006 — Five-point risk scale with snap-to-grid percentile mapping

**Status:** Accepted
**Decision date:** 2026-04-30 (canon v2.3 reframe; canon §4.2)
**Deciders:** Saranyaraj Rajendran (engineering lead); Fraser Stark
(product lead); Lori Norman (compliance + IS lead, for the
client-facing descriptor names).

## Context

The engine needs a way to express "how risky should this client's
allocation be?" Several plausible representations:

- A continuous risk score (0.0–1.0) computed from a multi-factor
  questionnaire.
- A 1–10 scale (the legacy Steadyhand convention).
- A 1–5 scale snapping to specific frontier percentiles.
- An efficient-frontier percentile directly (5th, 25th, 50th, etc.)
  with named buckets.

Each has trade-offs. Continuous scores produce uninterpretable
recommendations ("your blend is at risk 0.617"). The 1–10 scale was
inconsistent across Steadyhand documents and didn't map cleanly to
frontier math. Raw percentiles don't translate well to advisor or
client conversations.

The 1–5 scale with named descriptors and snap-to-grid percentile
mapping is what canon §4.2 settled on after the offsite. Five points
is enough granularity to distinguish meaningful risk tolerances
without overfitting to questionnaire noise.

## Decision

Risk is represented on a **5-point integer scale (1–5)** at both
household and goal levels. Each score maps to a specific
efficient-frontier percentile (the "snap-to-grid"):

| Score | Descriptor | Optimizer percentile | Confidence floor |
|---|---|---|---|
| 1 | Cautious | 5th | ~95% |
| 2 | Conservative-balanced | 15th | ~85% |
| 3 | Balanced | 25th | ~75% |
| 4 | Balanced-growth | 35th | ~65% |
| 5 | Growth-oriented | 45th | ~55% |

The 5–45 percentile range is **intentionally below the median**.
This prevents 100%-global-equity outcomes even for the most
risk-tolerant clients (the 1st-percentile extreme produced absurd
outcomes in offsite simulation; 50th felt too aggressive). The
5–45 range keeps a margin of conservatism even for "high-risk"
clients.

The blended household-and-goal composite score also rounds to the
nearest 5-point step (snap-to-grid).

**Client-facing copy uses only these five descriptor names.** The
words "low risk," "medium risk," and "high risk" are banned in
advisor-facing surfaces (vocabulary CI guard enforces). The
distinction between "risk tolerance" (a property of the household or
person) and "riskiness" (a property of an allocation) is also
maintained — see canon §2.3.

Legacy 1–10 risk values from earlier Steadyhand documents are migrated
to 1–5 via `(old + 1) // 2` (integer-ceiling equivalent for positive
integers) in
`web/api/migrations/0006_household_risk_five_point.py`. New values
above 5 are rejected at the model + API + engine validation boundaries.

## Consequences

### Positive

- Recommendations are interpretable: "your blend is Balanced
  (sitting at the 25th percentile of the efficient frontier)."
- The 5-point scale maps cleanly to the questionnaire's natural
  discriminations (Q1–Q4 yield T/C/anchor → 1–5 mapping in
  `engine/risk_profile.py`).
- The descriptor names are advisor- and client-friendly.
- The snap-to-grid prevents noise: minor questionnaire variations
  don't ratchet the blend back and forth.
- The 5–45 range keeps even Growth-oriented blends within a
  defensible "Steadyhand culture" envelope.

### Negative

- Discrete scores lose granularity. A household whose true tolerance
  is 3.3 gets rounded to either 3 (Balanced) or 4 (Balanced-growth),
  not somewhere between. The override flow + advisor judgment cover
  this.
- The descriptor names are slightly verbose ("Conservative-balanced,"
  "Balanced-growth"). Frontend uses them throughout; vocabulary CI
  prevents the shorter aliases from creeping in.
- The household × goal composite formula is parameterized but the
  exact weighting is `[OPEN]` (deferred to Fraser + Saranyaraj
  product input). The engine accepts the formula as a configuration.

## Alternatives considered

### Alternative A: Continuous risk score (0.0–1.0)

Rejected. Uninterpretable; produces noise; doesn't map to discrete
frontier percentiles cleanly.

### Alternative B: 1–10 scale (legacy Steadyhand)

Rejected. Inconsistent across legacy documents; doesn't map cleanly
to frontier math; the 1–10 vocabulary was inherited from a different
era. Migration to 1–5 is one-way (`ceil(old / 2)`).

### Alternative C: Named buckets without numeric scores

Rejected. Numeric scores are useful for the household × goal
composite math and for backend persistence (`Goal.goal_risk_score`,
`Household.household_risk_score` are `IntegerField`s with `1 ≤ x ≤
5` validators). Named-only would push the math into string handling.

## Supersession path

If the product team locks the household × goal composite formula and
finds the 5-point scale insufficient (e.g., the composite needs more
granularity to be smooth), supersede this ADR with one specifying
a finer-grained scale + the new descriptor mapping. Sign-off required
from Fraser Stark, Saranyaraj Rajendran, and Lori Norman (for
client-facing copy).

## References

- Canon §4.2 — "Risk modeling — composite, 5-point, three components
  exposed"
- Canon §2.3 — risk tolerance vs riskiness lexical distinction
- Canon §6.3a + §16 — vocabulary discipline (the banned terms list)
- `engine/risk_profile.py` — Q1–Q4 → T/C/anchor → 1–5 mapping
- `engine/optimizer.py` — RISK_TO_PERCENTILE map
- `frontend/src/lib/risk.ts` — `descriptorFor`, `scoreToPercentile`,
  `RISK_DESCRIPTOR_KEYS`
- `web/api/migrations/0006_household_risk_five_point.py` — the 1–10
  → 1–5 migration
- `scripts/check-vocab.sh` — the CI guard that prevents
  low/medium/high re-introduction
- Sibling ADRs:
  - ADR-0005 (link-first engine output) — each link recommendation
    carries a frontier percentile derived from this scale.
  - ADR-0011 (vocabulary discipline) — the CI enforcement of the
    descriptor names.
