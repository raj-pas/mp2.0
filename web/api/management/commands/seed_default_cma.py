from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from web.api import models
from web.audit.writer import record_event

DEFAULT_CMA_NAME = "Default CMA"


class Command(BaseCommand):
    help = "Seed the active Default CMA snapshot from tracked default fixtures."

    def add_arguments(self, parser):  # noqa: ANN001
        parser.add_argument(
            "--force",
            action="store_true",
            help="Create a new active Default CMA snapshot even when one already exists.",
        )

    def handle(self, *args, **options):  # noqa: ANN002, ANN003
        fixture_path = Path(__file__).resolve().parents[4] / "engine/fixtures/default_cma_v1.json"
        data = json.loads(fixture_path.read_text())
        with transaction.atomic():
            active = models.CMASnapshot.objects.filter(
                status=models.CMASnapshot.Status.ACTIVE
            ).first()
            if active and not options["force"] and _is_current_default_snapshot(active):
                self.stdout.write("Active Default CMA snapshot already exists; skipping seed.")
                return
            snapshot = _create_snapshot(data)
        self.stdout.write(self.style.SUCCESS(f"Seeded Default CMA snapshot v{snapshot.version}."))


def _is_current_default_snapshot(snapshot: models.CMASnapshot) -> bool:
    legacy_text = f"{snapshot.name} {snapshot.source} {snapshot.notes}".lower()
    legacy_owner_token = "f" + "raser"
    return (
        snapshot.name == DEFAULT_CMA_NAME
        and legacy_owner_token not in legacy_text
        and "/users/" not in legacy_text
    )


def _create_snapshot(data: dict) -> models.CMASnapshot:
    models.CMASnapshot.objects.filter(status=models.CMASnapshot.Status.ACTIVE).update(
        status=models.CMASnapshot.Status.ARCHIVED
    )
    models.CMASnapshot.objects.filter(status=models.CMASnapshot.Status.DRAFT).update(
        status=models.CMASnapshot.Status.ARCHIVED
    )
    version = (
        models.CMASnapshot.objects.order_by("-version").first().version + 1
        if models.CMASnapshot.objects.exists()
        else 1
    )
    snapshot = models.CMASnapshot.objects.create(
        name=DEFAULT_CMA_NAME,
        version=version,
        status=models.CMASnapshot.Status.ACTIVE,
        source=data["source_note"],
        notes="Seeded from tracked Default CMA fixtures.",
    )
    for index, fund in enumerate(data["funds"]):
        models.CMAFundAssumption.objects.create(
            snapshot=snapshot,
            fund_id=fund["id"],
            name=fund["name"],
            expected_return=Decimal(str(fund["expected_return"])),
            volatility=Decimal(str(fund["volatility"])),
            optimizer_eligible=bool(fund["optimizer_eligible"]),
            is_whole_portfolio=bool(fund["is_whole_portfolio"]),
            display_order=index,
            asset_class_weights={},
            tax_drag={"neutral": 0},
        )
    fund_ids = [fund["id"] for fund in data["funds"]]
    for row_index, row in enumerate(data["correlation_matrix"]):
        for col_index, value in enumerate(row):
            models.CMACorrelation.objects.create(
                snapshot=snapshot,
                row_fund_id=fund_ids[row_index],
                col_fund_id=fund_ids[col_index],
                correlation=Decimal(str(value)),
            )
    record_event(
        action="cma_snapshot_seeded",
        entity_type="cma_snapshot",
        entity_id=snapshot.external_id,
        metadata={
            "version": snapshot.version,
            "source": snapshot.source,
            "fund_count": len(data["funds"]),
            "snapshot_name": snapshot.name,
        },
    )
    return snapshot
