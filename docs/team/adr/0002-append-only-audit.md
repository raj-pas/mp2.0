---
title: ADR-0002 — Append-only audit model (model guards)
status: Accepted
decision_date: 2026-04-30
deciders: [Saranyaraj Rajendran, Lori Norman]
supersedes: []
superseded_by: []
owner: Saranyaraj Rajendran
last_revised: 2026-05-12
update_when: This ADR's supersession-path conditions trigger an update; otherwise revise when the cited canon section, code symbols, or referenced sibling ADRs change.
---

# ADR-0002 — Append-only audit model (model guards)

**Status:** Accepted
**Decision date:** 2026-04-30 (locked decision #37 in earlier session)
**Deciders:** Saranyaraj Rajendran (engineering lead); Lori Norman
(compliance reviewer).

## Context

MP2.0 produces a stream of advisor actions that may need to be
reconstructed forensically: portfolio generations, household commits,
fact overrides, section approvals, conflict resolutions, kill-switch
flips, CMA publishes. Each is a regulatory event in a wealth-management
context — a regulator asking "what did the advisor see when they
approved this section?" must get an answer reconstructable from
immutable rows.

Two failure modes are catastrophic:

1. A future code path that "fixes up" audit rows after the fact
   (well-intentioned correction, but invalidates the immutability
   guarantee).
2. A defensive `.update()` or `.delete()` in test code or a management
   command that quietly removes evidence.

Both are real risks in a multi-contributor codebase where audit
emission is woven through many code paths.

## Decision

The `AuditEvent` Django model (in `web/audit/models.py`) overrides
`save()` and `delete()` to **raise** on any update or delete attempt
at the model layer.

Specifically:

- `save()` raises unconditionally if the instance already has a
  primary key (any update attempt fails, even if fields are
  unchanged). The guard checks `self.pk and
  AuditEvent.objects.filter(pk=self.pk).exists()`.
- `delete()` raises unconditionally.

The same pattern is applied to other audit-relevant append-only models:
`PortfolioRun`, `PortfolioRunEvent`, `HouseholdSnapshot`,
`GoalRiskOverride`, `FactOverride`.

A complementary DB-trigger layer (ADR-0013) backs this up at the
storage layer so the protection holds even if the model guard is
bypassed (e.g., via raw SQL or a misconfigured ORM call).

## Consequences

### Positive

- Audit history survives every code path. A misconfigured
  `.objects.filter(...).delete()` raises immediately; a confused
  contributor's "let me just fix this row" raises immediately.
- The compliance posture is defensible: "the system architecturally
  cannot modify audit rows." Auditors can verify by reading the model
  guards + the DB triggers.
- The trigger DDL is restored by migrations after the canonical dev
  reset (`scripts/reset-v2-dev.sh --yes`), so the append-only
  invariant is in force again on the fresh DB. **Note:** the `--yes`
  reset runs `docker compose down -v` which destroys the Postgres
  volume, so historical audit *rows* are lost across the reset; only
  the trigger contract is preserved by re-running migrations.
- New contributors who try to "clean up" old audit data hit the guard
  immediately and learn the invariant.

### Negative

- Genuine cleanup of test data requires bypassing the guard via a
  data migration with explicit rationale. The friction is intentional.
- Append-only growth means the audit table grows monotonically. At
  pilot scale (3–5 advisors), this is not a concern. At GA scale,
  archival to an analytics warehouse + Postgres partitioning may
  become necessary — but that's a Phase B+ problem.
- Some tests intentionally need to set up "stale audit state." Those
  tests use direct SQL (bypassing the ORM) with explicit comments,
  not via the model's `.save()`.

## Alternatives considered

### Alternative A: No audit guard; rely on code review

Rejected. Code review is not a reliable boundary for a class of bugs
that look like "harmless cleanup." A regulator's question would be:
"how do you guarantee no row has been modified?" Code-review-only is
not a defensible answer.

### Alternative B: Soft-delete (set a `deleted_at` column) instead of
hard guard

Rejected. Soft-delete still allows the row to be modified after the
"deletion"; future queries that don't filter `deleted_at = NULL`
return the (modified) row. The complexity outweighs the simplicity
of a hard guard.

### Alternative C: DB-trigger only (no model guard)

Rejected. Model-guard-only catches errors at code-review time (where
the guard is visible in the model file). DB-trigger-only requires
running a query that fails before the bug is caught. Both layers are
desirable: model guard catches it early in dev; DB trigger catches it
if the model is bypassed. ADR-0013 covers the DB-trigger half.

## Supersession path

If a regulatory change later requires *redaction* of audit fields
(e.g., right-to-be-forgotten regimes), supersede this ADR with one
specifying a redaction process that preserves the append-only
invariant for non-redacted fields. Sign-off required from Lori Norman
(compliance) and Saranyaraj Rajendran.

Note: redaction is different from deletion. A redaction sets
specific fields to a tombstone value but doesn't remove the row.
The append-only contract can be preserved if redaction is itself
an append (a new audit event recording the redaction).

## References

- Canon §9.2 — auth phasing + audit production foundation
- `web/audit/models.py` — the `AuditEvent` model with `save()`
  guards
- `web/audit/writer.py` — `record_event` writer
- `web/api/error_codes.py` — `safe_audit_metadata` (strips exception
  details and PII patterns before audit storage)
- `docs/agent/handoff-log.md` 2026-04-30 — original locked decision
  #37
- Sibling ADRs:
  - ADR-0013 (immutable audit via DB triggers) — the DB-layer
    backstop to this model-layer guard.
  - ADR-0004 (real-PII defense-in-depth) — audit immutability is one
    layer of the defense-in-depth regime.
