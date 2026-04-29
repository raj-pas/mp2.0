from __future__ import annotations

from rest_framework import serializers

from web.api import models


class ReviewDocumentSerializer(serializers.ModelSerializer):
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
            "processing_metadata",
            "created_at",
            "updated_at",
        ]


class ProcessingJobSerializer(serializers.ModelSerializer):
    document_id = serializers.SerializerMethodField()

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
            "created_at",
            "updated_at",
        ]

    def get_document_id(self, obj: models.ProcessingJob) -> int | None:
        return obj.document_id


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
            "created_at",
            "updated_at",
        ]

    def get_owner_email(self, obj: models.ReviewWorkspace) -> str | None:
        return obj.owner.email if obj.owner else None

    def get_linked_household_id(self, obj: models.ReviewWorkspace) -> str | None:
        return obj.linked_household.external_id if obj.linked_household else None


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
