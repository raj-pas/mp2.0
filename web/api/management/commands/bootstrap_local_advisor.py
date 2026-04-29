from __future__ import annotations

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create or update the local advisor/admin login from env-provided credentials."

    def add_arguments(self, parser):  # noqa: ANN001
        parser.add_argument(
            "--skip-if-missing",
            action="store_true",
            help="Exit successfully when local admin env vars are not set.",
        )

    def handle(self, *args, **options):  # noqa: ANN002, ANN003
        email = os.getenv("MP20_LOCAL_ADMIN_EMAIL")
        password = os.getenv("MP20_LOCAL_ADMIN_PASSWORD")
        if not email or not password:
            if options["skip_if_missing"]:
                self.stdout.write("Local advisor admin env not set; skipping bootstrap.")
                return
            raise CommandError(
                "Set MP20_LOCAL_ADMIN_EMAIL and MP20_LOCAL_ADMIN_PASSWORD outside git."
            )

        User = get_user_model()
        user, _ = User.objects.update_or_create(
            username=email,
            defaults={"email": email, "is_staff": True, "is_superuser": True},
        )
        user.set_password(password)
        user.save()
        self.stdout.write(self.style.SUCCESS(f"Bootstrapped local advisor admin: {email}"))
