from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from web.api import models
from web.audit.writer import record_event


class Command(BaseCommand):
    help = "Seed the active Fraser CMA snapshot from extracted reference fixtures."

    def add_arguments(self, parser):  # noqa: ANN001
        parser.add_argument(
            "--force",
            action="store_true",
            help="Create a new active Fraser CMA snapshot even when one already exists.",
        )

    def handle(self, *args, **options):  # noqa: ANN002, ANN003
        fixture_path = Path(__file__).resolve().parents[4] / "engine/fixtures/fraser_v1.json"
        data = json.loads(fixture_path.read_text())
        with transaction.atomic():
            if (
                not options["force"]
                and models.CMASnapshot.objects.filter(
                    status=models.CMASnapshot.Status.ACTIVE
                ).exists()
            ):
                self.stdout.write("Active CMA snapshot already exists; skipping Fraser seed.")
                return
            snapshot = _create_snapshot(data)
        self.stdout.write(self.style.SUCCESS(f"Seeded Fraser CMA snapshot v{snapshot.version}."))


def _create_snapshot(data: dict) -> models.CMASnapshot:
    models.CMASnapshot.objects.filter(status=models.CMASnapshot.Status.ACTIVE).update(
        status=models.CMASnapshot.Status.ARCHIVED
    )
    version = (
        models.CMASnapshot.objects.order_by("-version").first().version + 1
        if models.CMASnapshot.objects.exists()
        else 1
    )
    snapshot = models.CMASnapshot.objects.create(
        name="Fraser CMA",
        version=version,
        status=models.CMASnapshot.Status.ACTIVE,
        source=data["source_note"],
        notes=f"Seeded from {data['source_artifact']}",
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
        },
    )
    return snapshot
