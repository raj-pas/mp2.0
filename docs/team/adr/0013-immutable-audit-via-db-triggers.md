---
title: ADR-0013 — Immutable audit via DB triggers (defense beyond model guards)
status: Accepted
decision_date: 2026-04-30
deciders: [Saranyaraj Rajendran, Lori Norman]
supersedes: []
superseded_by: []
owner: Saranyaraj Rajendran
last_revised: 2026-05-12
update_when: This ADR's supersession-path conditions trigger an update; otherwise revise when the cited canon section, code symbols, or referenced sibling ADRs change.
---

# ADR-0013 — Immutable audit via DB triggers

**Status:** Accepted
**Decision date:** 2026-04-30
**Deciders:** Saranyaraj Rajendran (engineering lead); Lori Norman
(compliance + IS lead).

## Context

ADR-0002 establishes that `AuditEvent` (and other audit-relevant
append-only models like `PortfolioRun`, `PortfolioRunEvent`,
`HouseholdSnapshot`, `GoalRiskOverride`, `FactOverride`) override
`save()` and `delete()` at the Django model layer to raise on any
modify attempt.

The model-layer guard catches most paths:

- `MyModel.objects.create(...)` — fine.
- `instance.save()` — fine on initial create; raises on update.
- `instance.delete()` — raises.
- `MyModel.objects.filter(...).update(...)` — bypasses model `save()`
  but Django's `.update()` doesn't fire `save()` either way.
- `MyModel.objects.filter(...).delete()` — bypasses model `delete()`.

The two bypass cases (`.update()` and `.filter().delete()`) are real
ways the model-layer guard can be circumvented. There's also raw SQL
via `connection.cursor()`, which bypasses the ORM entirely.

For a regulatory event log, "the model layer raises" is not the
defensible posture. The defensible posture is "the storage layer
rejects modifications regardless of how they're attempted."

## Decision

A Postgres **trigger** on each audit-relevant table blocks `UPDATE`
and `DELETE` at the storage layer. The trigger raises an error that
propagates up through the ORM regardless of the access path
(`.save()`, `.update()`, `.delete()`, raw SQL).

The trigger is created via a Django data migration:

- `web/audit/migrations/0002_audit_immutability.py` — the trigger
  for `audit_auditevent`.

The other append-only models in the family (`PortfolioRun`,
`PortfolioRunEvent`, `HouseholdSnapshot`, `GoalRiskOverride`,
`FactOverride`) currently rely on the model-layer `save()` /
`delete()` guard (ADR-0002) only. Extending the DB-trigger backstop
to those tables is a Phase B+ hardening item; flagged for
post-pilot review.

A trigger looks roughly like:

```sql
CREATE OR REPLACE FUNCTION audit_immutability_guard()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit rows are append-only; UPDATE/DELETE forbidden';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_event_immutability
BEFORE UPDATE OR DELETE ON audit_auditevent
FOR EACH ROW EXECUTE FUNCTION audit_immutability_guard();
```

The trigger contract is restored after the canonical dev reset
(`scripts/reset-v2-dev.sh --yes`) because the migration creating it
re-runs on the fresh DB. **Note:** the `--yes` reset runs
`docker compose down -v`, which destroys the Postgres volume, so
historical audit rows are not retained across the reset; only the
trigger DDL is. If you need to preserve audit history across a dev
reset, use a non-volume-destroying approach (e.g., manual
`TRUNCATE` of non-audit tables instead of `docker compose down -v`).

## Consequences

### Positive

- Every code path that reaches the audit table — ORM, raw SQL, future
  data-pipeline jobs, ad-hoc psql sessions — is blocked from
  modification. The protection holds even if a contributor bypasses
  the model layer entirely.
- The reset script clears non-audit data without touching the audit
  triggers. The audit log persists across dev resets, which is the
  correct behavior for a regulatory event log.
- Compliance posture is defensible: "the storage layer rejects audit
  modifications" is a structural assertion an auditor can verify by
  inspecting the trigger definitions.

### Negative

- Genuine cleanup of test data requires bypassing the trigger via a
  data migration that explicitly drops + recreates it. The friction
  is intentional (any cleanup is auditable via the migration history).
- Some test setups need to create stale audit state. Tests use direct
  SQL with `DROP TRIGGER` + `INSERT` + `CREATE TRIGGER` in a test
  fixture (with explicit comments + isolation from non-audit tests).
  These tests are rare.
- Database-level errors are slightly less informative than ORM errors.
  The Django `IntegrityError` wrapping the Postgres error message
  surfaces the gist ("audit rows are append-only; UPDATE/DELETE
  forbidden") but the full diagnostic is in the Postgres log.

## Alternatives considered

### Alternative A: Model-layer guard only (ADR-0002 alone)

Rejected. The `.update()` / `.filter().delete()` / raw SQL bypass
paths are real. Compliance posture requires storage-layer
enforcement.

### Alternative B: DB trigger only (no model-layer guard)

Rejected. The model-layer guard catches the bug at code-review time
(the guard is visible in `web/audit/models.py`). The DB trigger is
the runtime backstop. Both layers are desirable: model guard catches
it early in dev; trigger catches it if the model is bypassed.

### Alternative C: Append-only via a column-level `IMMUTABLE` constraint on each field

Rejected. Postgres doesn't have a per-row immutability primitive at
the constraint level. The trigger approach is the standard pattern.

## Supersession path

If a regulatory change later requires *redaction* of audit fields
(e.g., right-to-be-forgotten regimes), supersede this ADR with one
that specifies a redaction process. Redaction is different from
deletion — a redaction sets specific fields to a tombstone value but
doesn't remove the row, and the redaction itself is auditable as a
new append.

The trigger would need to be relaxed to permit specific column
UPDATEs in specific cases. Sign-off required from Lori Norman
(compliance), Saranyaraj Rajendran, and the Engineering Director
liaison.

Note: this is also tightly coupled to ADR-0008 (Postgres-only).
If a supersession to a different storage backend lands, the
trigger-based immutability needs to be reimplemented in the new
backend (or moved entirely to the application layer with stronger
discipline).

## References

- Canon §9.2 — auth phasing + audit foundation
- `web/audit/migrations/` — trigger-creation migrations
- `web/audit/models.py` — model-layer guard (ADR-0002)
- `scripts/reset-v2-dev.sh` — clears non-audit tables; preserves
  audit triggers
- `docs/agent/handoff-log.md` 2026-04-30 — original locked decision
  #37 + trigger landing
- Sibling ADRs:
  - ADR-0002 (append-only audit model) — the model-layer half of the
    enforcement
  - ADR-0008 (Postgres-only) — the storage backend assumption that
    enables the trigger pattern
  - ADR-0004 (real-PII defense-in-depth) — audit immutability is one
    layer of the regime
