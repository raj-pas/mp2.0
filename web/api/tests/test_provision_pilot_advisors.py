"""Phase 8.5 provision_pilot_advisors management command tests.

Covers:
  * Creates User + AdvisorProfile + Group from YAML config.
  * Idempotent re-run does not duplicate; emits new audit event per
    re-run (the audit log records every provisioning attempt).
  * Audit event `advisor_provisioned` emitted per advisor with
    correct metadata.
  * Rejects malformed YAML (missing required fields, malformed email,
    plain-text password).
  * Refuses to read config that doesn't exist.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError
from web.api.access import ADVISOR_GROUP
from web.audit.models import AuditEvent


def _yaml_config(advisors: list[dict]) -> str:
    import yaml

    return yaml.safe_dump({"advisors": advisors})


def _write_config(tmp_path: Path, advisors: list[dict]) -> Path:
    cfg = tmp_path / "pilot-advisors.yml"
    cfg.write_text(_yaml_config(advisors))
    return cfg


@pytest.mark.django_db
def test_provision_creates_users_with_groups_and_audit(tmp_path: Path) -> None:
    cfg = _write_config(
        tmp_path,
        [
            {
                "email": "alice@steadyhand.com",
                "name": "Alice Pilot",
                "team": "steadyhand",
                "password_hash": make_password("not-the-real-password"),
            },
            {
                "email": "bob@steadyhand.com",
                "name": "Bob Pilot",
                "team": "steadyhand",
                "password_hash": make_password("another-password"),
            },
        ],
    )

    call_command("provision_pilot_advisors", config_file=str(cfg))

    User = get_user_model()
    alice = User.objects.get(username="alice@steadyhand.com")
    bob = User.objects.get(username="bob@steadyhand.com")
    advisor_group = Group.objects.get(name=ADVISOR_GROUP)
    assert advisor_group in alice.groups.all()
    assert advisor_group in bob.groups.all()
    assert alice.first_name == "Alice Pilot"
    assert alice.email == "alice@steadyhand.com"
    assert alice.is_active is True
    assert alice.is_staff is False
    assert alice.is_superuser is False

    # Each advisor emits one audit event with metadata mirroring the
    # YAML block (email + name + team + was_created).
    events = AuditEvent.objects.filter(action="advisor_provisioned")
    assert events.count() == 2
    metadata_by_email = {e.metadata["email"]: e.metadata for e in events}
    assert metadata_by_email["alice@steadyhand.com"]["was_created"] is True
    assert metadata_by_email["alice@steadyhand.com"]["team"] == "steadyhand"
    assert metadata_by_email["bob@steadyhand.com"]["was_created"] is True


@pytest.mark.django_db
def test_provision_is_idempotent_does_not_duplicate_users(tmp_path: Path) -> None:
    cfg = _write_config(
        tmp_path,
        [
            {
                "email": "carol@steadyhand.com",
                "name": "Carol Pilot",
                "team": "steadyhand",
                "password_hash": make_password("pw"),
            }
        ],
    )

    call_command("provision_pilot_advisors", config_file=str(cfg))
    call_command("provision_pilot_advisors", config_file=str(cfg))  # re-run

    User = get_user_model()
    assert User.objects.filter(username="carol@steadyhand.com").count() == 1

    # Audit log captures BOTH provisioning attempts; the second event
    # has was_created=False so ops can distinguish "first ack" from
    # "re-run" via metadata.
    events = AuditEvent.objects.filter(action="advisor_provisioned")
    assert events.count() == 2
    flags = sorted(e.metadata["was_created"] for e in events)
    assert flags == [False, True]


@pytest.mark.django_db
def test_provision_rejects_malformed_email(tmp_path: Path) -> None:
    cfg = _write_config(
        tmp_path,
        [
            {
                "email": "not-an-email",
                "name": "X",
                "team": "y",
                "password_hash": make_password("pw"),
            }
        ],
    )
    with pytest.raises(CommandError, match="malformed"):
        call_command("provision_pilot_advisors", config_file=str(cfg))


@pytest.mark.django_db
def test_provision_rejects_plain_text_password(tmp_path: Path) -> None:
    """The password_hash field must be a Django-recognized hash, not
    plain text. Catches ops accidentally pasting raw passwords into
    the YAML.
    """
    cfg = _write_config(
        tmp_path,
        [
            {
                "email": "dave@steadyhand.com",
                "name": "Dave",
                "team": "steadyhand",
                "password_hash": "this-is-not-hashed",
            }
        ],
    )
    with pytest.raises(CommandError, match="not a Django-recognized hash"):
        call_command("provision_pilot_advisors", config_file=str(cfg))


@pytest.mark.django_db
def test_provision_rejects_missing_required_fields(tmp_path: Path) -> None:
    cfg = _write_config(
        tmp_path,
        [{"email": "eve@steadyhand.com"}],  # missing name + team + password_hash
    )
    with pytest.raises(CommandError, match="missing required fields"):
        call_command("provision_pilot_advisors", config_file=str(cfg))


@pytest.mark.django_db
def test_provision_rejects_missing_config_file(tmp_path: Path) -> None:
    with pytest.raises(CommandError, match="not found"):
        call_command("provision_pilot_advisors", config_file=str(tmp_path / "nope.yml"))


@pytest.mark.django_db
def test_provision_dry_run_skips_db_writes(tmp_path: Path) -> None:
    cfg = _write_config(
        tmp_path,
        [
            {
                "email": "frank@steadyhand.com",
                "name": "Frank Pilot",
                "team": "steadyhand",
                "password_hash": make_password("pw"),
            }
        ],
    )
    call_command("provision_pilot_advisors", config_file=str(cfg), dry_run=True)

    User = get_user_model()
    assert not User.objects.filter(username="frank@steadyhand.com").exists()
    assert AuditEvent.objects.filter(action="advisor_provisioned").count() == 0
