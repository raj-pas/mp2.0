from __future__ import annotations

import os

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create or update local advisor and financial analyst logins from env vars."

    def add_arguments(self, parser):  # noqa: ANN001
        parser.add_argument(
            "--skip-if-missing",
            action="store_true",
            help="Exit successfully when local admin env vars are not set.",
        )

    def handle(self, *args, **options):  # noqa: ANN002, ANN003
        User = get_user_model()
        created_any = False
        created_any |= _bootstrap_user(
            command=self,
            user_model=User,
            email_env="MP20_LOCAL_ADMIN_EMAIL",
            password_env="MP20_LOCAL_ADMIN_PASSWORD",
            group_name="advisor",
            label="local advisor admin",
            is_staff=True,
            is_superuser=True,
            skip_if_missing=options["skip_if_missing"],
        )
        created_any |= _bootstrap_user(
            command=self,
            user_model=User,
            email_env="MP20_LOCAL_ANALYST_EMAIL",
            password_env="MP20_LOCAL_ANALYST_PASSWORD",
            group_name="financial_analyst",
            label="local financial analyst",
            is_staff=False,
            is_superuser=False,
            skip_if_missing=options["skip_if_missing"],
        )
        if not created_any:
            self.stdout.write("Local user env not set; skipping bootstrap.")


def _bootstrap_user(
    *,
    command: Command,
    user_model,
    email_env: str,
    password_env: str,
    group_name: str,
    label: str,
    is_staff: bool,
    is_superuser: bool,
    skip_if_missing: bool,
) -> bool:
    email = os.getenv(email_env)
    password = os.getenv(password_env)
    if not email and not password:
        return False
    if not email or not password:
        if skip_if_missing:
            return False
        raise CommandError(f"Set both {email_env} and {password_env} outside git.")

    user, _ = user_model.objects.update_or_create(
        username=email,
        defaults={"email": email, "is_staff": is_staff, "is_superuser": is_superuser},
    )
    user.set_password(password)
    user.save()
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)
    command.stdout.write(command.style.SUCCESS(f"Bootstrapped {label}: {email}"))
    return True
