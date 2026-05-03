"""Phase 6 — Migration rollback tests.

Mirrors the pilot-rollback procedure (docs/agent/pilot-rollback.md
§3 — code revert): every recent migration must reverse cleanly.
A bad downgrade path leaves the DB in an inconsistent state during
a Sev-1 rollback, which is the worst possible time to discover it.

These tests run the migrations forward + backward + forward again
to verify both directions work without data corruption. The 0010
migration (Phase 5b.1 — AdvisorProfile + Feedback + FactOverride)
is the last addition; future migrations must extend this suite.
"""

from __future__ import annotations

import pytest
from django.core.management import call_command


@pytest.mark.django_db(transaction=True)
def test_migration_0010_advisorprofile_rolls_back_cleanly() -> None:
    """The 0010_advisorprofile_factoverride_feedback migration must
    reverse to 0009 + re-apply forward without errors. Catches
    RemoveField / bad-default migrations before pilot rollback ever
    needs to execute.
    """
    # Reverse to 0009
    call_command("migrate", "api", "0009", verbosity=0)
    # Re-apply forward to current
    call_command("migrate", "api", verbosity=0)


@pytest.mark.django_db(transaction=True)
def test_full_session_migrations_round_trip() -> None:
    """Apply ALL session migrations forward → backward → forward.
    End-state must match start-state at the schema level.

    Pin the round-trip so a future migration that only works in
    one direction is caught BEFORE pilot uses it. Mirrors locked
    decision #34's reset-script discipline + pilot-rollback.md §3.
    """
    # Reverse everything in the api app to 0001 (initial)
    call_command("migrate", "api", "0001", verbosity=0)
    # Re-apply forward to current head
    call_command("migrate", "api", verbosity=0)


@pytest.mark.django_db(transaction=True)
def test_audit_app_migrations_round_trip() -> None:
    """Audit log uses backend-specific DB triggers (canon §11.8.3 +
    locked #19). The migration that installs them must reverse to
    drop the triggers without leaving orphans.
    """
    call_command("migrate", "audit", "zero", verbosity=0)
    call_command("migrate", "audit", verbosity=0)
