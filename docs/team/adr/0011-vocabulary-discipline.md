---
title: ADR-0011 — Vocabulary discipline (banned terms + CI guard)
status: Accepted
decision_date: 2026-04-30
deciders: [Fraser Stark, Lori Norman, Saranyaraj Rajendran]
supersedes: []
superseded_by: []
owner: Saranyaraj Rajendran
last_revised: 2026-05-12
update_when: This ADR's supersession-path conditions trigger an update; otherwise revise when the cited canon section, code symbols, or referenced sibling ADRs change.
---

# ADR-0011 — Vocabulary discipline

**Status:** Accepted
**Decision date:** 2026-04-30 (locked decision #14)
**Deciders:** Fraser Stark (product lead, for advisor- and
client-facing language); Lori Norman (compliance + IS lead, for
regulatory framing); Saranyaraj Rajendran (engineering lead, for CI
enforcement).

## Context

A wealth-management product spans many audiences: clients, advisors,
auditors, regulators, internal Purpose colleagues, press, and the
engineering team. Each may interpret a word differently — and in
specific cases, the same word can mean genuinely incompatible things.
Examples:

- **"Sleeve"** in MP2.0's original design meant "a Purpose-built fund
  designed specifically for this platform." But no purpose-built funds
  are being created — the system uses the existing Purpose fund
  universe. The term is also industry-ambiguous: it can mean an
  in-kind transfer, a sub-portfolio component, or other things
  depending on context.
- **"Reallocation"** (and "transfer," "move money") suggests literal
  money movement. In MP2.0, what looks like moving money between
  accounts is actually changing how money is mapped to goals —
  a logical operation above the regulatory account.
- **"Low risk" / "medium risk" / "high risk"** as risk descriptors
  collide with the regulatory `risk_rating` field (which uses
  low/medium/high with different cutoffs than the 1–5 frontier
  percentile mapping). Conflating the two is genuinely dangerous.
- **`Goal_50`**, raw 0–50 percentile, `schema_version` are
  engine-internal — surfacing them to advisors leaks implementation
  details and confuses the conversation.

Without enforcement, these terms creep into code, copy, commits, and
session notes — and a session that adopted them can be expensive to
roll back.

## Decision

The canon (§6.3a + §16) defines the required vocabulary. Banned
terms and their replacements:

| Banned | Replacement | Where banned |
|---|---|---|
| `sleeve`, `sleeve fund` | `building-block fund` | code + copy + docs |
| `reallocation`, `reallocate` (without hyphen), `transfer`, `move money` | `re-goaling`, `re-allocate` (with hyphen), `re-balance` | code + advisor copy |
| `low risk`, `medium risk`, `high risk` | Cautious / Conservative-balanced / Balanced / Balanced-growth / Growth-oriented | advisor + client copy |
| Bare `Conservative` (without `-balanced`) | `Conservative-balanced` | advisor + client copy |
| `Phase R[0-9]` | Canon Phase A/B/C | client-facing + commit messages |
| `Goal_50`, raw 0–50 percentile | The 1–5 score + descriptor | advisor surfaces |

Enforcement:

- **`scripts/check-vocab.sh`** runs in CI on every push to `main`
  and on every PR. It scans `frontend/src/`,
  `web/api/serializers.py`, `web/api/management/commands/`,
  `web/api/migrations/`, and `engine/fixtures/` for the forbidden
  patterns. Allow-listed contexts: `docs/agent/`, `.test.` files,
  `__tests__/`, files with `# canon-vocab-allow` markers (used
  sparingly for legitimate exceptions like ESLint config strings).
- The CI step is in `.github/workflows/smoke.yml`'s `python` job
  ("Vocabulary CI guard (locked decision #14)").
- New banned patterns can be added to `scripts/check-vocab.sh` as
  the team discovers them. Each addition gets a one-line comment
  citing the canon or session that motivated it.

## Consequences

### Positive

- Cross-functional conversations don't drift. When the PM, advisor,
  auditor, and engineer all use "building-block fund" and "re-goaling,"
  ambiguities surface as questions about the concept, not about the
  vocabulary.
- Compliance posture is clearer. The risk descriptors map deterministically
  to the canon 1–5 scale + frontier percentile, not to a fuzzy
  low/medium/high gradient.
- Engineering-internal terms (`Goal_50`, etc.) don't accidentally
  reach advisor copy.
- The CI guard catches the most common reintroduction vector
  (someone writing "reallocation" out of muscle memory). The grep
  is fast (< 1s) so it runs on every PR.

### Negative

- The descriptor names are slightly verbose ("Conservative-balanced,"
  "Balanced-growth"). Some readers find them less natural than
  low/medium/high. The trade-off is intentional.
- The CI guard occasionally flags legitimate cases (e.g., a code
  comment that quotes a banned term to explain why it's banned).
  Allow-listed via `# canon-vocab-allow` comments.
- Editing legacy text (third-party imports, vendored libraries) can
  surface banned terms; these are allow-listed or kept out of the
  scan paths.

## Alternatives considered

### Alternative A: Style guide only (no CI enforcement)

Rejected. Style guides drift in practice. The CI guard is what makes
the discipline durable across many contributors.

### Alternative B: Lint-rule plugin (per-language linting for the banned terms)

Rejected for now. The grep-based script is simpler, covers code +
serializers + migrations + fixtures in one pass, and is easy to
extend. If the codebase grows large enough that grep becomes too
slow, the lint-rule approach is the natural successor.

### Alternative C: Per-audience copy (engineering-internal vs advisor-facing)

Rejected. The boundary between "internal" and "advisor-facing" is
fuzzy and changes over time. A single rule (banned everywhere
except explicit allow-list) is enforceable.

## Supersession path

If a vocabulary shift is needed (e.g., the product team decides
"re-allocate" with hyphen is too pedantic for advisor copy and we
move to a different phrasing), supersede this ADR with one that
specifies the new banned/allowed lists. Update
`scripts/check-vocab.sh` in the same PR.

Sign-off required from Fraser Stark, Lori Norman, and Saranyaraj
Rajendran.

## References

- Canon §6.3a — "Re-goaling — conceptual, not money-movement"
- Canon §16 — Glossary & vocabulary (the canonical list)
- `scripts/check-vocab.sh` — the CI guard
- `.github/workflows/smoke.yml` — runs the guard
- `docs/team/glossary.md` — expands the canon vocabulary for new
  contributors
- `docs/agent/decisions.md` "locked decision #14" — original lock-in
- Sibling ADRs:
  - ADR-0010 (production-grade-MVP reframe) — the framing that
    motivated retiring "demo-grade" vocabulary
  - ADR-0006 (five-point risk scale) — the descriptor names that
    replace low/medium/high
