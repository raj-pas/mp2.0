---
title: Architecture Decision Records
owner: Saranyaraj Rajendran
last_revised: 2026-05-12
status: living
update_when: A new ADR is added (update the index), an ADR's status
  changes (Proposed → Accepted, Accepted → Superseded), the ADR format
  or supersession workflow itself changes, or the "why this folder
  exists" rationale needs revisiting.
---

# Architecture Decision Records (ADRs)

This folder captures the most important architectural decisions in MP2.0.
Each ADR is a small, self-contained document that explains:

- **What** decision was made,
- **Why** it was made (context + alternatives),
- **What follows** from it (positive and negative consequences),
- **Who** decided and **when**, and
- **How** to supersede it if the decision turns out to be wrong.

The format is a hybrid of [MADR](https://adr.github.io/madr/) and
[Michael Nygard's original ADR template](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).

## See also

- [`CONTRIBUTING.md`](CONTRIBUTING.md) — how to author the next ADR
- [`../README.md`](../README.md) — folder index + conventions
- [`../architecture-diagrams.md`](../architecture-diagrams.md) — visual
  map of the decisions captured here
- Master dossier at `~/.claude/plans/i-want-you-to-sorted-meadow.md`
  — Part 15 "Anti-patterns" + Part 17 "Recommended next artifacts"
  references this folder

## ADR index

Ordered by importance (the architectural rules most likely to be
violated if a contributor doesn't know about them are first).

| # | Title | Status | Source |
|---|---|---|---|
| [0001](0001-engine-as-library.md) | Engine as a library (no framework imports) | Accepted | Canon §9.4.2 |
| [0002](0002-append-only-audit.md) | Append-only audit model (model guards) | Accepted | Locked decision #37 |
| [0003](0003-bedrock-ca-central-1.md) | Bedrock ca-central-1 for real-PII extraction | Accepted | Canon §11.8.3 |
| [0004](0004-real-pii-defense-in-depth.md) | Real-PII defense-in-depth regime | Accepted | Canon §11.8.3 |
| [0005](0005-link-first-engine-output.md) | Link-first engine output (`GoalAccountLink` as optimization unit) | Accepted | Canon Part 12 |
| [0006](0006-five-point-risk-scale.md) | Five-point risk scale with snap-to-grid percentile mapping | Accepted | Canon §4.2 |
| [0007](0007-three-tier-entity-matcher.md) | Three-tier entity matcher (auto-merge / advisor / new-canonical) | Accepted | Round 18 #1 |
| [0008](0008-postgres-only.md) | Postgres-only persistence (fail-loud on missing/non-Postgres URL) | Accepted | Locked decision |
| [0009](0009-sync-auto-trigger.md) | Synchronous auto-trigger inside mutation transactions | Accepted | Locked decision #74 |
| [0010](0010-production-grade-mvp-reframe.md) | Production-grade-MVP reframe (retire "demo-grade") | Accepted | Canon §1.6 |
| [0011](0011-vocabulary-discipline.md) | Vocabulary discipline (banned terms + CI guard) | Accepted | Canon §6.3a + §16 |
| [0012](0012-source-priority-hierarchy.md) | Source-priority hierarchy | Accepted | Canon §11.4 |
| [0013](0013-immutable-audit-via-db-triggers.md) | Immutable audit via DB triggers (defense beyond model guards) | Accepted | Canon §9.2 |

## How to read an ADR

Each ADR follows this section order:

1. **Front-matter** — title, status, decision date, deciders,
   supersedes / superseded_by.
2. **Context** — what problem this decision solves; what was known at
   the time; why the obvious alternatives weren't chosen.
3. **Decision** — the specific architectural choice in plain language.
4. **Consequences** — positive (what becomes easier) and negative
   (what becomes harder or constrained) implications.
5. **Alternatives considered** — at least two other options that were
   weighed.
6. **Supersession path** — how to override this ADR if it turns out
   to be wrong.
7. **References** — links to canon sections, code, and prior session
   handoff entries.

## Status values

- **Proposed** — drafted but not yet ratified. Should rarely be
  committed to `main` in this state.
- **Accepted** — currently in force. The team agrees this is how the
  system works.
- **Superseded** — replaced by another ADR. Keep the file (don't
  delete); update front-matter `superseded_by` and add a banner
  at the top pointing to the replacement.
- **Deprecated** — no longer in force, but no replacement yet.
  Indicates a gap that needs filling.

Every ADR in this folder is currently `Accepted` because they document
decisions already locked in canon or prior session handoff. New ADRs
proposed in the future may start as `Proposed`.

## Supersession workflow

When a decision needs to change:

1. Author a new ADR with the next available number. Status = `Proposed`.
2. In the new ADR's "Context" section, explain what changed and why
   the prior decision no longer holds.
3. Reference the prior ADR in the new ADR's `supersedes` front-matter.
4. Get sign-off from the original Deciders (or their current
   role-equivalents).
5. Once accepted, mark the new ADR `Accepted` and the old ADR
   `Superseded`. Add a banner at the top of the old ADR pointing to
   the new one.
6. Update the index in this README.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full authoring
workflow.

## Why this folder exists

Before this folder, the locked architectural decisions in MP2.0 were
spread across:

- The canon (`MP2.0_Working_Canon.md`) — authoritative for product /
  strategy / regulatory intent, but architecture is mixed with other
  topics.
- The handoff log (`docs/agent/handoff-log.md`) — append-only session
  notes; decisions get buried in context.
- The decisions distillation (`docs/agent/decisions.md`) — one-line
  summaries without the "why."
- Project memory (`~/.claude/projects/.../memory/`) — Claude-session
  context; not human-readable for new hires.
- Plan files (`~/.claude/plans/*.md`) — multi-phase action plans;
  decisions get woven in but not easily extractable.

ADRs consolidate the most load-bearing architectural decisions into
one-page-each documents that:

- A new engineer can read on Day 1 without prior context.
- An auditor can use to reconstruct the engineering rationale.
- A future contributor can supersede when the decision needs to change,
  with a clear paper trail.

ADRs do **not** replace the canon, the handoff log, or the decisions
distillation. They are a *reading-friendly slice* of those sources
focused on architecture.
