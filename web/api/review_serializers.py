from __future__ import annotations

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers

from web.api import models
from web.audit.models import AuditEvent


class ReviewDocumentSerializer(serializers.ModelSerializer):
    failure_code = serializers.SerializerMethodField()
    failure_stage = serializers.SerializerMethodField()
    retry_eligible = serializers.SerializerMethodField()
    ocr_overflow = serializers.SerializerMethodField()

    class Meta:
        model = models.ReviewDocument
        fields = [
            "id",
            "original_filename",
            "content_type",
            "extension",
            "file_size",
            "sha256",
            "document_type",
            "status",
            "failure_reason",
            "failure_code",
            "failure_stage",
            "retry_eligible",
            "ocr_overflow",
            "processing_metadata",
            "created_at",
            "updated_at",
        ]

    def get_failure_code(self, obj: models.ReviewDocument) -> str:
        return str(obj.processing_metadata.get("failure_code", ""))

    def get_failure_stage(self, obj: models.ReviewDocument) -> str:
        return str(obj.processing_metadata.get("failure_stage", ""))

    def get_retry_eligible(self, obj: models.ReviewDocument) -> bool:
        return obj.status in {
            models.ReviewDocument.Status.FAILED,
            models.ReviewDocument.Status.UNSUPPORTED,
        }

    def get_ocr_overflow(self, obj: models.ReviewDocument) -> dict:
        return obj.processing_metadata.get("ocr_overflow", {})


class ProcessingJobSerializer(serializers.ModelSerializer):
    document_id = serializers.SerializerMethodField()
    is_stale = serializers.SerializerMethodField()
    retry_eligible = serializers.SerializerMethodField()

    class Meta:
        model = models.ProcessingJob
        fields = [
            "id",
            "document_id",
            "job_type",
            "status",
            "attempts",
            "max_attempts",
            "last_error",
            "metadata",
            "locked_at",
            "started_at",
            "completed_at",
            "is_stale",
            "retry_eligible",
            "created_at",
            "updated_at",
        ]

    def get_document_id(self, obj: models.ProcessingJob) -> int | None:
        return obj.document_id

    def get_is_stale(self, obj: models.ProcessingJob) -> bool:
        if obj.status != models.ProcessingJob.Status.PROCESSING:
            return False
        stale_after = timezone.now() - timezone.timedelta(
            seconds=getattr(settings, "MP20_WORKER_STALE_SECONDS", 60)
        )
        return obj.updated_at < stale_after

    def get_retry_eligible(self, obj: models.ProcessingJob) -> bool:
        return obj.status == models.ProcessingJob.Status.FAILED and obj.attempts < obj.max_attempts


class ExtractedFactSerializer(serializers.ModelSerializer):
    document_id = serializers.IntegerField(source="document.id")
    document_name = serializers.CharField(source="document.original_filename")
    document_type = serializers.CharField(source="document.document_type")

    class Meta:
        model = models.ExtractedFact
        fields = [
            "id",
            "document_id",
            "document_name",
            "document_type",
            "field",
            "value",
            "asserted_at",
            "confidence",
            "derivation_method",
            "source_page",
            "source_location",
            "evidence_quote",
            "extraction_run_id",
            "is_current",
            "created_at",
        ]


class SectionApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SectionApproval
        fields = [
            "id",
            "section",
            "status",
            "notes",
            "data",
            "approved_at",
            "updated_at",
        ]


class ReviewWorkspaceSerializer(serializers.ModelSerializer):
    owner_email = serializers.SerializerMethodField()
    linked_household_id = serializers.SerializerMethodField()
    documents = ReviewDocumentSerializer(many=True, read_only=True)
    processing_jobs = ProcessingJobSerializer(many=True, read_only=True)
    section_approvals = SectionApprovalSerializer(many=True, read_only=True)
    worker_health = serializers.SerializerMethodField()
    timeline = serializers.SerializerMethodField()

    class Meta:
        model = models.ReviewWorkspace
        fields = [
            "id",
            "external_id",
            "label",
            "owner_email",
            "status",
            "data_origin",
            "linked_household_id",
            "reviewed_state",
            "readiness",
            "match_candidates",
            "documents",
            "processing_jobs",
            "section_approvals",
            "worker_health",
            "timeline",
            "created_at",
            "updated_at",
        ]

    def get_owner_email(self, obj: models.ReviewWorkspace) -> str | None:
        return obj.owner.email if obj.owner else None

    def get_linked_household_id(self, obj: models.ReviewWorkspace) -> str | None:
        return obj.linked_household.external_id if obj.linked_household else None

    def get_worker_health(self, obj: models.ReviewWorkspace) -> dict:
        heartbeat = models.WorkerHeartbeat.objects.first()
        active_jobs = [
            job
            for job in obj.processing_jobs.all()
            if job.status
            in {models.ProcessingJob.Status.QUEUED, models.ProcessingJob.Status.PROCESSING}
        ]
        if heartbeat is None:
            status = "offline" if active_jobs else "idle"
            return {"status": status, "last_seen_at": None, "active_job_count": len(active_jobs)}
        stale_after = timezone.now() - timezone.timedelta(
            seconds=getattr(settings, "MP20_WORKER_STALE_SECONDS", 60)
        )
        status = "stale" if heartbeat.last_seen_at < stale_after else "online"
        return {
            "status": status,
            "name": heartbeat.name,
            "last_seen_at": heartbeat.last_seen_at,
            "active_job_count": len(active_jobs),
        }

    def get_timeline(self, obj: models.ReviewWorkspace) -> list[dict]:
        events = AuditEvent.objects.filter(
            entity_type__in=["review_workspace", "review_document", "processing_job"],
        ).filter(Q(entity_id=obj.external_id) | Q(metadata__workspace_id=obj.external_id))[:50]
        return [
            {
                "id": event.id,
                "action": event.action,
                "entity_type": event.entity_type,
                "entity_id": event.entity_id if event.entity_type == "review_workspace" else "",
                "metadata": _sanitized_metadata(event.metadata),
                "created_at": event.created_at,
            }
            for event in events
        ]


class ReviewWorkspaceListSerializer(serializers.ModelSerializer):
    document_count = serializers.SerializerMethodField()

    class Meta:
        model = models.ReviewWorkspace
        fields = [
            "id",
            "external_id",
            "label",
            "status",
            "data_origin",
            "readiness",
            "document_count",
            "created_at",
            "updated_at",
        ]

    def get_document_count(self, obj: models.ReviewWorkspace) -> int:
        return obj.documents.count()


SENSITIVE_METADATA_KEYS = {
    "old_value",
    "new_value",
    "raw_value",
    "evidence_quote",
    "before",
    "after",
}


def _sanitized_metadata(metadata: dict) -> dict:
    safe: dict = {}
    for key, value in (metadata or {}).items():
        if key in SENSITIVE_METADATA_KEYS:
            safe[key] = "[redacted]"
        elif isinstance(value, dict):
            safe[key] = _sanitized_metadata(value)
        elif isinstance(value, list):
            safe[key] = [
                _sanitized_metadata(item) if isinstance(item, dict) else item for item in value
            ]
        else:
            safe[key] = value
    return safe
