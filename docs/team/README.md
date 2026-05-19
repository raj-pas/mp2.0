---
title: Team-facing documentation index
owner: Saranyaraj Rajendran
last_revised: 2026-05-12
status: living
update_when: A new artifact is added to docs/team/, an artifact is
  removed or renamed, the reading-order-by-role priorities change, or
  the markdown/voice/cross-link conventions change.
---

# Team-facing documentation

This folder holds **team-facing reference documentation** for MP2.0 —
the materials new engineers, the new product manager, and leadership
should be able to read on day one without needing a guided walkthrough.

It sits alongside two other doc folders in the repo:

- [`../agent/`](../agent/) — operational and handoff infrastructure
  (session state, handoff log, runbooks, pilot procedures, UX spec,
  design system, decision log). Aimed at engineers actively shipping
  changes and at Claude Code sessions that need to load context.
- [`../validation/`](../validation/) — internal optimizer validation
  evidence (committed baselines for the optimizer, human-review
  checklist). Aimed at Fraser, Nafal, and the financial analyst.

`docs/team/` differs from those two: it's the **stable, self-contained
reading material** for someone who has never seen the codebase before.
It does not move every session; expect a quarterly review cadence rather
than weekly churn.

The authoritative product/strategy/architecture canon remains
[`MP2.0_Working_Canon.md`](../../MP2.0_Working_Canon.md) at the repo
root. Everything in this folder is a *map of* the canon, not a
*replacement for* it.

## Start here

If you're new, follow the reading order for your role.

### New engineer (mixed seniority, full-stack expected)

| # | Read | Time |
|---|---|---|
| 1 | [`product-brief.md`](product-brief.md) — what we're building and why | ~3 min |
| 2 | [`architecture-diagrams.md`](architecture-diagrams.md) — the four layers + critical data flows | ~15 min |
| 3 | [`onboarding-engineer.md`](onboarding-engineer.md) — Day 1 setup + Week 1 tour + how we work | ~25 min |
| 4 | [`adr/README.md`](adr/README.md) — what ADRs are + how to read them | ~5 min |
| 5 | All 13 ADRs in [`adr/`](adr/) (0001 → 0013, importance order) | ~60-90 min |
| 6 | [`ai-doc-ingestion-deep-dive.md`](ai-doc-ingestion-deep-dive.md) — every mechanic of Layer 1-5 + commit boundary + auto-trigger | ~45-60 min |
| 7 | [`real-pii-handling.md`](real-pii-handling.md) — production-grade PII discipline | ~15 min |
| 8 | [`glossary.md`](glossary.md) — domain terms (skim; refer back as needed) | ~10 min |
| 9 | [`../../MP2.0_Working_Canon.md`](../../MP2.0_Working_Canon.md) — the canon (read Parts 1, 4, 9, 11) | ~45 min |
| 10 | [`../../CLAUDE.md`](../../CLAUDE.md) — non-negotiable rules + build commands | ~10 min |
| 11 | [`troubleshooting.md`](troubleshooting.md) — keep open for when commands fail | ~bookmark |

Estimated time-to-productive: **first PR within Week 2**.

### New product manager (new to wealth-management)

| # | Read | Time |
|---|---|---|
| 1 | [`product-brief.md`](product-brief.md) — the bet, four goals, business case, pilot state | ~3 min |
| 2 | [`glossary.md`](glossary.md) — domain vocabulary (full read; load-bearing) | ~25 min |
| 3 | [`architecture-diagrams.md`](architecture-diagrams.md) — the 6-stage journey, four-layer architecture, review pipeline | ~15 min |
| 4 | [`ai-doc-ingestion-deep-dive.md`](ai-doc-ingestion-deep-dive.md) — Parts 1, 2, 6, 11 (skip the code-level deep parts) | ~25 min |
| 5 | [`../../MP2.0_Working_Canon.md`](../../MP2.0_Working_Canon.md) — canon Parts 1, 2, 3, 4, 8, 13 | ~60 min |
| 6 | [`../agent/pilot-success-metrics.md`](../agent/pilot-success-metrics.md) — the 8 quantitative bars + cadence | ~10 min |
| 7 | [`../agent/ux-spec.md`](../agent/ux-spec.md) — UX dimensions taxonomy + decision log | ~20 min |
| 8 | [`real-pii-handling.md`](real-pii-handling.md) — what compliance posture looks like | ~15 min |

Estimated time-to-productive: **first weekly status report within Week 1**.

### Leadership (Som / Fraser / Lori / Amitha)

| # | Read | Time |
|---|---|---|
| 1 | [`product-brief.md`](product-brief.md) — the bet, four goals, pilot state, metrics | ~3 min |
| 2 | [`../agent/pilot-readiness-2026-05-04.md`](../agent/pilot-readiness-2026-05-04.md) — pilot-state snapshot with live metric queries | ~5 min |
| 3 | [`../agent/pilot-success-metrics.md`](../agent/pilot-success-metrics.md) — what we measure + when to off-ramp | ~5 min |
| 4 | [`../../CHANGELOG.md`](../../CHANGELOG.md) — what has shipped (each tag) | ~10 min |

## What's in this folder

| File | Purpose | Audience |
|---|---|---|
| [`README.md`](README.md) | This file — index + conventions + reading order by role | All |
| [`product-brief.md`](product-brief.md) | Som-CEO consumable; the bet, four goals, business case, pilot state, metrics | All (especially leadership + new PM) |
| [`architecture-diagrams.md`](architecture-diagrams.md) | 6 Mermaid diagrams + ASCII fallback: 4-layer architecture, upload→commit→portfolio-gen, 3-tier matcher, deployment, review-workspace state machine, auto-trigger lifecycle | Engineers + PM |
| [`glossary.md`](glossary.md) | ~80–100 domain terms with plain-language definitions and canon cross-references | All (load-bearing for the PM) |
| [`adr/README.md`](adr/README.md) | What an ADR is + the format we use + supersession workflow | Engineers |
| [`adr/CONTRIBUTING.md`](adr/CONTRIBUTING.md) | How to author the next ADR | Engineers |
| [`adr/0001-engine-as-library.md`](adr/0001-engine-as-library.md) through [`0013-immutable-audit-via-db-triggers.md`](adr/0013-immutable-audit-via-db-triggers.md) | 13 architecture decisions in importance order | Engineers |
| [`onboarding-engineer.md`](onboarding-engineer.md) | Day 1 setup + Week 1 subsystem tour + how-we-work norms + red flags | New engineer hires |
| [`ai-doc-ingestion-deep-dive.md`](ai-doc-ingestion-deep-dive.md) | Every mechanic of the AI document ingestion + engine-ready data creation pipeline: Layer 1-5, commit boundary, sync auto-trigger, audit, state machines, real-PII discipline, error modes, performance characteristics, extension points | Engineers (definitive reference); technical PM |
| [`real-pii-handling.md`](real-pii-handling.md) | Canon §11.8.3 defense-in-depth in plain language + access workflow + day-to-day operating discipline + the "never" list + incident procedure | Engineers + compliance reviewers |
| [`troubleshooting.md`](troubleshooting.md) | Common Day-1 errors and their fixes | Engineers |

## Conventions

These conventions apply to every file in `docs/team/`. They're locked
here so future contributors can extend the folder consistently.

### Markdown style

- **Line length:** hard-wrap prose at 80 columns. Code blocks and
  tables run full-width. Matches the canon and `docs/agent/handoff-log.md`
  in-tree convention.
- **Headings:** sentence-case (`## Mission, business case, and strategic
  position`), not Title-Case. Matches the master dossier and canon.
- **Linter:** `.markdownlint.json` at the repo root pins the rules
  (MD013 line-length 80, MD025 single h1, MD041 first-line h1, MD033
  inline HTML allowed, MD036 disabled). Run
  `npx markdownlint-cli2 'docs/team/**/*.md'` to check.
- **Dates:** ISO 8601 (`YYYY-MM-DD`) throughout.

### Front-matter

Every file starts with:

```yaml
---
title: <human-readable title>
owner: Saranyaraj Rajendran
last_revised: 2026-MM-DD
status: living | frozen | superseded
---
```

For ADRs, the front-matter also carries `decision_date`, `deciders`,
`supersedes`, and `superseded_by`.

### Cross-linking

Every file has a `See also` section near the top or bottom linking to
sibling files in `docs/team/` and to the relevant operational docs in
`docs/agent/`. Citations to the canon use `§X.Y` notation (e.g.,
`Canon §9.4.2`).

The **master dossier** at
`~/.claude/plans/i-want-you-to-sorted-meadow.md` is the index document
this folder maps to. Files in `docs/team/` cross-link to it as
"the master onboarding map."

### Voice and tone

Voice is **mixed by genre**:

| Artifact | Voice |
|---|---|
| `product-brief.md` | First-person plural ("we are building…") — thesis tone |
| ADRs | Passive impersonal ("the engine is kept a library") — architectural-fact tone |
| `onboarding-engineer.md` | Second-person ("you'll set up…") — guide tone |
| `architecture-diagrams.md` | Passive descriptive |
| `real-pii-handling.md` | Imperative ("never paste real client values into Slack") |
| `glossary.md` | Definitional |

### Naming discipline

- **Real client surnames** (the surname keys that exist in
  `MP20_SECURE_DATA_ROOT`) are **never** carried into these files.
  Use descriptors ("the 28-merge-candidate real-PII workspace") or
  codenames ("client_a"). Synthetic Sandra & Mike Chen are named.
- **Mission-Aligned Team** members (Fraser Stark, Nafal Butt,
  Lori Norman, Saranyaraj Rajendran) are named in full to match canon
  §1.1.
- **Other Purpose colleagues** are referenced by role
  ("Engineering Director liaison," "extraction prompt owner,"
  "reporting team lead") to remain resilient to org changes.

### Vocabulary

Vocabulary CI enforces the canon-aligned terms in `scripts/check-vocab.sh`:

- Use **building-block fund** (not "sleeve") and **whole-portfolio fund**.
- Use **re-goaling** / **re-allocate** / **re-balance**
  (not "transfer," "move money," "reallocation").
- Use the five canon risk descriptors (**Cautious**,
  **Conservative-balanced**, **Balanced**, **Balanced-growth**,
  **Growth-oriented**), not low/medium/high.
- Avoid `Phase R[0-9]` in client-facing copy; engineering round labels
  are internal.

See [`glossary.md`](glossary.md) for full term inventory.

## How to add a new doc

1. Decide where it belongs: team-facing reference (`docs/team/`),
   operational (`docs/agent/`), or canonical (`MP2.0_Working_Canon.md`).
2. Follow the conventions above (front-matter, voice, vocabulary).
3. Add it to the "What's in this folder" table above with a one-line
   purpose + audience.
4. Update the role-based reading order if the artifact belongs in one.
5. Add a `See also` cross-link from at least one existing artifact.
6. Run `npx markdownlint-cli2 'docs/team/**/*.md'`.
7. Run `bash scripts/check-vocab.sh` and `bash scripts/check-pii-leaks.sh`.
8. Open a PR; tag Saranyaraj for review.

## Maintenance cadence

- **Quarterly review** (suggested): re-read every file, refresh
  `last_revised` dates, retire stale claims.
- **Trigger-based updates:** when a canon section changes, when an ADR
  is superseded, when a build command changes, when a new role joins
  the team.
- The owner field tells you who to ping when a doc looks stale.

## See also

- [`../../README.md`](../../README.md) — repo-root README (runnable
  scaffold introduction)
- [`../../CLAUDE.md`](../../CLAUDE.md) — Claude Code session protocol
  and non-negotiable rules
- [`../../MP2.0_Working_Canon.md`](../../MP2.0_Working_Canon.md) — the
  canon
- [`../agent/`](../agent/) — operational and handoff infrastructure
- [`../validation/`](../validation/) — optimizer validation evidence
