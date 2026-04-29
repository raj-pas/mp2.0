from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand

from web.api import models
from web.api.review_security import secure_data_root
from web.audit.writer import record_event

CURRENT_ARTIFACT_VERSION = "secure_upload_artifact.v1"


class Command(BaseCommand):
    help = "Report or delete secure local review artifacts whose artifact version is outdated."

    def add_arguments(self, parser):  # noqa: ANN001
        parser.add_argument("--delete", action="store_true", help="Delete eligible files.")
        parser.add_argument(
            "--retain-reason",
            default="",
            help="Record an explicit reason to retain files instead of deleting them.",
        )

    def handle(self, *args, **options):  # noqa: ANN002, ANN003
        root = secure_data_root()
        delete = options["delete"]
        retain_reason = options["retain_reason"].strip()
        candidates: list[models.ReviewDocument] = []
        retained = 0
        deleted = 0

        for document in models.ReviewDocument.objects.select_related("workspace"):
            artifact_version = document.processing_metadata.get("artifact_version", "")
            if artifact_version == CURRENT_ARTIFACT_VERSION:
                continue
            candidates.append(document)
            path = (root / document.storage_path).resolve() if document.storage_path else None
            if retain_reason:
                retained += 1
                continue
            if delete and path and _inside_root(path, root) and path.exists():
                path.unlink()
                deleted += 1

        action = (
            "review_artifact_retention_recorded"
            if retain_reason
            else "review_artifact_disposal_delete"
            if delete
            else "review_artifact_disposal_report"
        )
        record_event(
            action=action,
            entity_type="review_artifacts",
            metadata={
                "candidate_count": len(candidates),
                "deleted_count": deleted,
                "retained_count": retained,
                "retain_reason_present": bool(retain_reason),
                "artifact_version": CURRENT_ARTIFACT_VERSION,
            },
        )
        self.stdout.write(f"{len(candidates)} candidates; {deleted} deleted; {retained} retained.")


def _inside_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
