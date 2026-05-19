---
title: How to author an ADR
owner: Saranyaraj Rajendran
last_revised: 2026-05-12
status: living
update_when: The ADR template adds or removes a required field, the
  authoring workflow changes (sign-off process, branch convention,
  PR-tag convention), or "when to write/supersede an ADR" guidance
  changes.
---

# How to author the next ADR

## See also

- [`README.md`](README.md) — what an ADR is, how to read one, the index
- [`../README.md`](../README.md) — folder conventions

## Template

Copy this template into a new file at
`docs/team/adr/NNNN-short-kebab-title.md` (use the next available
number; pad to four digits).

```markdown
---
title: ADR-NNNN — Short title
status: Proposed   # Proposed | Accepted | Superseded | Deprecated
decision_date: YYYY-MM-DD
deciders: [Mission-Aligned Team member names; role-only for others]
supersedes: []     # list of ADR numbers this replaces
superseded_by: []  # list of ADR numbers that replace this (filled in when superseded)
owner: Saranyaraj Rajendran
last_revised: YYYY-MM-DD
---

# ADR-NNNN — Short title

**Status:** Proposed
**Decision date:** YYYY-MM-DD
**Deciders:** Mission-Aligned Team (Fraser Stark, Nafal Butt,
Lori Norman, Saranyaraj Rajendran); plus role-only for others
(e.g., Engineering Director liaison, compliance reviewer).

## Context

(2–4 paragraphs.)

What problem does this decision address? What was known at the time?
What constraints applied? Why is this decision being made *now* rather
than earlier or later?

If this ADR ties to a specific incident, real-PII finding, or canon
section, cite it here. Cross-link to handoff-log entries when
relevant.

## Decision

(1–2 paragraphs.)

The specific architectural choice, in plain language. Avoid jargon
unless the term is defined in [`../glossary.md`](../glossary.md).

If a code snippet is the clearest explanation of the decision (e.g.,
the AST purity check, the audit trigger SQL), include it here — but
only when the snippet is the actual enforcement mechanism, not when
it's incidental.

## Consequences

### Positive

- (Bullet list.) What becomes easier? What guarantees does the team
  now have? What anti-patterns does this prevent?

### Negative

- (Bullet list.) What becomes harder or more constrained? What
  trade-offs did we accept? What might surprise a new contributor?

## Alternatives considered

At least two other options that were weighed:

### Alternative A: (one-sentence summary)

Why it was rejected. If it was a close call, say so.

### Alternative B: (one-sentence summary)

Why it was rejected.

## Supersession path

If this ADR turns out to be wrong, here's how to replace it:

1. Author a new ADR with the next available number.
2. In the new ADR's "Context," explain what changed and why this
   decision no longer holds.
3. The new ADR's `supersedes` front-matter lists this ADR's number.
4. Sign-off required from: (specific deciders or role-equivalents).
5. Once accepted, this ADR's status flips to `Superseded` and a
   banner appears at the top pointing to the replacement.

## References

- Canon `§X.Y` — section reference and verbatim quote of the key
  sentence(s) that motivated this decision.
- Linear ticket `MP20-NNN` (if known) — the originating tracker entry.
- `docs/agent/handoff-log.md` 2026-MM-DD entry — the session where this
  decision was first executed.
- Code references (file:concept, not file:line — line numbers drift):
  - `engine/optimizer.py` — primary touchpoint
  - `web/api/views.py` — secondary touchpoint
- Sibling ADRs:
  - ADR-NNNN — related decision (one-sentence linkage)
```

## Conventions for the body

- **Voice:** passive impersonal ("the engine is kept a library").
  This is the architectural-fact tone. Don't say "we decided" or
  "you should." Just state the architectural reality.
- **Length:** target 100–250 lines per ADR (front-matter + body).
  Longer is fine if a code snippet is necessary for clarity.
- **Cross-link** to other ADRs liberally, especially when decisions
  interact.
- **Cite the canon** with `§X.Y` notation. If the canon doesn't have
  an applicable section, this ADR may itself need to be promoted into
  the canon.
- **Reference handoff-log dates** rather than commit SHAs where
  possible (commits get squashed; dates remain meaningful).
- **No file:line references** in the body of the ADR; use
  file:concept ("`web/api/views.py` — the typed exception declarations").
  Line numbers drift fast in this codebase.
- **Never quote real-PII.** Use synthetic or descriptor references
  ("a real-PII couple workspace") if illustrating with examples.

## Authoring workflow

1. **Open a draft branch** (`adr/NNNN-short-title`).
2. **Copy the template** to `docs/team/adr/NNNN-short-kebab-title.md`.
3. **Fill in Context first**, then Decision, then Alternatives.
   Consequences come last (they fall out of the decision + alternatives).
4. **Cross-link** to existing ADRs, the canon, and the glossary as you
   write.
5. **Run the gates locally:**

   ```bash
   bash scripts/check-vocab.sh
   bash scripts/check-pii-leaks.sh
   npx markdownlint-cli2 'docs/team/adr/NNNN-*.md'
   ```

6. **Open a PR** tagged with `docs: adr-NNNN` and the title.
7. **Get sign-off** from the Mission-Aligned Team members listed in
   `deciders`. Other Purpose colleagues sign off if their role
   appears in `deciders`.
8. **Merge when accepted.** Status flips from `Proposed` to `Accepted`
   in the same commit as the merge.
9. **Update the index** at [`README.md`](README.md) — add a row to the
   ADR index table.
10. **Append a one-line entry** to `docs/agent/handoff-log.md` under
    today's date, noting the new ADR.

## When to write an ADR

Write an ADR when:

- A non-obvious architectural choice is being made.
- A choice constrains future flexibility (e.g., choosing Postgres
  over MySQL constrains the storage layer for years).
- A choice trades off something the team will want back (e.g., choosing
  sync auto-trigger over async background queue trades responsiveness
  for connection-pool pressure).
- A choice has compliance / regulatory implications (e.g., audit
  immutability via DB triggers).
- A future contributor would otherwise ask "why is it like this?" and
  not find a satisfying answer.

Don't write an ADR for:

- Routine refactors that don't change architecture.
- Local code style choices (those go in linter configs).
- One-off bug fixes (those go in the handoff log).
- Decisions the canon already documents in full (just reference the
  canon).

## When to supersede an ADR

Supersede when:

- The decision turns out to be wrong in light of new evidence
  (production incident, pilot feedback, regulatory change).
- The constraint that motivated the decision no longer holds
  (e.g., Phase B brings real auth roles; some Phase A decisions
  about RBAC may need revision).
- A better architectural choice emerges (e.g., a new Bedrock region
  becomes preferred over ca-central-1 — though this would also need
  compliance review).

Don't supersede:

- For minor refinements (edit the ADR in place; bump `last_revised`).
- For clarifications that don't change the decision (edit in place).
- Without sign-off from the original Deciders or current
  role-equivalents.

## Numbering

ADR numbers are sequential and **permanent**. Once assigned, a number
is not reused even if the ADR is superseded.

The current next number is **0014** (we ship 0001–0013 in 2026-05-12).
