"""Provision pilot advisor accounts from a YAML config (Phase 8.5).

Reproducible, idempotent advisor account creation for the
2026-05-08 limited-beta pilot. The YAML config lives outside the
repo (`MP20_SECURE_DATA_ROOT/pilot-advisors-2026-05-08.yml` per
locked decision); this command reads it + creates / updates User
rows + assigns groups + emits one `advisor_provisioned` audit
event per advisor (locked decision #37).

Idempotent: re-running with the same config doesn't create
duplicates; it updates email + name fields if they changed.
Refuses to run if any advisor's password isn't pre-hashed (we
don't want plain-text passwords flowing through the command).

YAML schema:

    advisors:
      - email: alice@steadyhand.com
        name: Alice Pilot
        team: steadyhand
        password_hash: "argon2$argon2id$v=19$..."  # pre-hashed by ops
      - email: bob@steadyhand.com
        ...
"""

from __future__ import annotations

import os
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import identify_hasher
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from web.api.access import ADVISOR_GROUP
from web.audit.writer import record_event


def _load_yaml_config(path: Path) -> dict:
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError as exc:
        raise CommandError(
            "PyYAML is required for provision_pilot_advisors. Install via `uv add pyyaml`."
        ) from exc
    if not path.is_file():
        raise CommandError(f"Pilot advisor config not found: {path}")
    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict) or "advisors" not in raw:
        raise CommandError("Config must be a dict with an `advisors` list.")
    advisors = raw.get("advisors")
    if not isinstance(advisors, list) or not advisors:
        raise CommandError("`advisors` must be a non-empty list.")
    return raw


_REQUIRED_FIELDS = ("email", "name", "team", "password_hash")


def _validate_advisor_block(block: dict, index: int) -> None:
    missing = [f for f in _REQUIRED_FIELDS if not block.get(f)]
    if missing:
        raise CommandError(
            f"advisors[{index}] missing required fields: {missing}. "
            f"Required: {list(_REQUIRED_FIELDS)}"
        )
    email = str(block["email"])
    if "@" not in email or " " in email:
        raise CommandError(f"advisors[{index}] email {email!r} is malformed.")
    password_hash = str(block["password_hash"])
    try:
        identify_hasher(password_hash)
    except ValueError as exc:
        raise CommandError(
            f"advisors[{index}] password_hash for {email} is not a Django-recognized hash. "
            "Pre-hash via Django's make_password() before adding to YAML."
        ) from exc


class Command(BaseCommand):
    help = (
        "Create or update pilot advisor accounts from a YAML config "
        "(MP20_SECURE_DATA_ROOT/pilot-advisors-2026-05-08.yml). "
        "Idempotent + audit-event-emitting (locked decision #37)."
    )

    def add_arguments(self, parser):  # noqa: ANN001
        parser.add_argument(
            "--config-file",
            required=True,
            help=(
                "Path to the YAML config (typically inside "
                "$MP20_SECURE_DATA_ROOT). Not committed to git."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate the config without writing to the DB.",
        )

    def handle(self, *args, **options):  # noqa: ANN002, ANN003
        config_path = Path(options["config_file"]).expanduser().resolve()
        secure_root = os.environ.get("MP20_SECURE_DATA_ROOT", "")
        if secure_root:
            secure_root_resolved = Path(secure_root).expanduser().resolve()
            if not str(config_path).startswith(str(secure_root_resolved)):
                self.stdout.write(
                    self.style.WARNING(
                        f"Config path is outside MP20_SECURE_DATA_ROOT ({secure_root_resolved}). "
                        "Proceeding, but verify the config isn't committed to git."
                    )
                )

        config = _load_yaml_config(config_path)
        advisors = config["advisors"]
        for i, block in enumerate(advisors):
            if not isinstance(block, dict):
                raise CommandError(f"advisors[{i}] must be a mapping; got {type(block).__name__}.")
            _validate_advisor_block(block, i)

        if options["dry_run"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Dry run OK: {len(advisors)} advisor(s) validated; no DB writes."
                )
            )
            return

        User = get_user_model()
        advisor_group, _ = Group.objects.get_or_create(name=ADVISOR_GROUP)

        created = 0
        updated = 0
        with transaction.atomic():
            for block in advisors:
                email = str(block["email"]).strip().lower()
                name = str(block["name"]).strip()
                team = str(block["team"]).strip()
                password_hash = str(block["password_hash"])

                user, was_created = User.objects.update_or_create(
                    username=email,
                    defaults={
                        "email": email,
                        "first_name": name,
                        "is_active": True,
                        "is_staff": False,
                        "is_superuser": False,
                    },
                )
                # Assign pre-hashed password (skip set_password to avoid
                # accidental re-hash of an already-hashed value).
                if user.password != password_hash:
                    user.password = password_hash
                    user.save(update_fields=["password"])
                user.groups.add(advisor_group)

                record_event(
                    action="advisor_provisioned",
                    entity_type="advisor",
                    entity_id=str(user.pk),
                    actor="provision_pilot_advisors",
                    metadata={
                        "email": email,
                        "name": name,
                        "team": team,
                        "was_created": was_created,
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  {'CREATED' if was_created else 'UPDATED'} {email} ({team})"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Provisioned {created} new + {updated} existing advisor(s) "
                f"from {config_path.name}."
            )
        )
