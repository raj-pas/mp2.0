from __future__ import annotations

from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.utils import timezone
from extraction.llm import bedrock_config_from_env, json_payload_from_model_text
from extraction.parsers import ParserDependencyError, parse_document_path
from extraction.pipeline import classify_from_parsed, extract_facts_for_document
from extraction.schemas import SUPPORTED_EXTENSIONS, ParsedDocument

from web.api import models
from web.api.review_redaction import (
    pii_detection_summary,
    redact_evidence_quote,
    sanitize_fact_value,
)
from web.api.review_security import secure_data_root
from web.api.review_state import create_state_version, reviewed_state_from_workspace
from web.audit.writer import record_event


def record_worker_heartbeat(
    *,
    name: str | None = None,
    current_job: models.ProcessingJob | None = None,
    metadata: dict[str, Any] | None = None,
) -> models.WorkerHeartbeat:
    heartbeat, _ = models.WorkerHeartbeat.objects.update_or_create(
        name=name or settings.MP20_WORKER_NAME,
        defaults={
            "last_seen_at": timezone.now(),
            "current_job": current_job,
            "metadata": metadata or {},
        },
    )
    return heartbeat


def claim_next_job() -> models.ProcessingJob | None:
    with transaction.atomic():
        job = (
            models.ProcessingJob.objects.select_for_update(skip_locked=True)
            .filter(status=models.ProcessingJob.Status.QUEUED)
            .order_by("created_at")
            .first()
        )
        if job is None:
            return None
        job.status = models.ProcessingJob.Status.PROCESSING
        job.attempts += 1
        job.locked_at = timezone.now()
        job.started_at = job.started_at or timezone.now()
        job.metadata = {**job.metadata, "stage": "claimed"}
        job.save(
            update_fields=[
                "status",
                "attempts",
                "locked_at",
                "started_at",
                "metadata",
                "updated_at",
            ]
        )
        return job


def process_job(job: models.ProcessingJob) -> None:
    record_worker_heartbeat(current_job=job, metadata={"stage": "processing"})
    try:
        job.metadata = {**job.metadata, "stage": job.job_type}
        job.save(update_fields=["metadata", "updated_at"])
        if job.job_type == models.ProcessingJob.JobType.PROCESS_DOCUMENT:
            if job.document is None:
                raise ValueError("process_document job requires a document")
            process_document(job.document)
        elif job.job_type == models.ProcessingJob.JobType.RECONCILE_WORKSPACE:
            reconcile_workspace(job.workspace)
        else:
            raise ValueError(f"Unsupported job type: {job.job_type}")
    except Exception as exc:
        _fail_or_retry(job, exc)
        return

    job.status = models.ProcessingJob.Status.COMPLETED
    job.completed_at = timezone.now()
    job.last_error = ""
    job.metadata = {**job.metadata, "stage": "completed"}
    job.save(update_fields=["status", "completed_at", "last_error", "metadata", "updated_at"])
    record_worker_heartbeat(current_job=None, metadata={"stage": "idle"})


def process_document(document: models.ReviewDocument) -> None:
    secure_data_root()
    extension = Path(document.original_filename).suffix.lower()
    document.extension = extension.lstrip(".")

    if extension not in SUPPORTED_EXTENSIONS:
        document.status = models.ReviewDocument.Status.UNSUPPORTED
        document.failure_reason = f"Unsupported file type: {extension or '[none]'}"
        document.save(update_fields=["status", "failure_reason", "updated_at"])
        record_event(
            action="review_document_unsupported",
            entity_type="review_document",
            entity_id=str(document.id),
            metadata={"extension": extension},
        )
        return

    parsed = parse_document(document)
    classification = classify_from_parsed(document.original_filename, extension, parsed)
    document.document_type = classification.document_type
    document.status = models.ReviewDocument.Status.CLASSIFIED
    document.processing_metadata = {
        **document.processing_metadata,
        "classifier": classification.as_metadata(),
        "classifier_version": "adaptive_classifier.v1",
    }
    document.save(
        update_fields=["extension", "document_type", "status", "processing_metadata", "updated_at"]
    )
    document.status = (
        models.ReviewDocument.Status.OCR_REQUIRED
        if parsed.method == "ocr_required"
        else models.ReviewDocument.Status.TEXT_EXTRACTED
    )
    document.processing_metadata = {
        **document.processing_metadata,
        "parse_method": parsed.method,
        "parse_metadata": parsed.metadata,
        "pii_detection_summary": pii_detection_summary(parsed.text),
        "parser_version": "parser.v1",
    }
    document.save(update_fields=["status", "processing_metadata", "updated_at"])

    facts, extraction_metadata = extract_facts(document, parsed.text)
    if extraction_metadata.get("ocr_overflow"):
        document.processing_metadata = {
            **document.processing_metadata,
            "ocr_overflow": extraction_metadata["ocr_overflow"],
        }
    document.processing_metadata = {
        **document.processing_metadata,
        "extraction": extraction_metadata,
    }
    fact_rows = []
    for candidate in facts:
        fact = candidate.as_dict() if hasattr(candidate, "as_dict") else dict(candidate)
        fact_rows.append(
            models.ExtractedFact(
                workspace=document.workspace,
                document=document,
                field=fact["field"],
                value=sanitize_fact_value(fact["field"], fact["value"]),
                asserted_at=fact.get("asserted_at") or None,
                confidence=fact.get("confidence", "medium"),
                derivation_method=fact.get("derivation_method", "extracted"),
                source_page=fact.get("source_page"),
                source_location=fact.get("source_location", ""),
                evidence_quote=redact_evidence_quote(fact.get("evidence_quote", "")),
                extraction_run_id=fact["extraction_run_id"],
            )
        )

    with transaction.atomic():
        models.ExtractedFact.objects.filter(document=document).delete()
        models.ExtractedFact.objects.bulk_create(fact_rows)

    document.status = models.ReviewDocument.Status.FACTS_EXTRACTED
    document.save(update_fields=["status", "processing_metadata", "updated_at"])
    enqueue_reconcile(document.workspace)
    record_event(
        action="review_document_processed",
        entity_type="review_document",
        entity_id=str(document.id),
        metadata={
            "document_type": document.document_type,
            "fact_count": len(facts),
            "classifier_confidence": classification.confidence,
            "classifier_route": classification.route,
        },
    )


def reconcile_workspace(workspace: models.ReviewWorkspace) -> dict[str, Any]:
    state = reviewed_state_from_workspace(workspace)
    workspace.reviewed_state = state
    workspace.readiness = state["readiness"]
    workspace.status = (
        models.ReviewWorkspace.Status.ENGINE_READY
        if state["readiness"]["engine_ready"]
        else models.ReviewWorkspace.Status.REVIEW_READY
    )
    workspace.match_candidates = []
    workspace.save(
        update_fields=["reviewed_state", "readiness", "status", "match_candidates", "updated_at"]
    )
    create_state_version(workspace, user=None, state=state)
    workspace.documents.filter(status=models.ReviewDocument.Status.FACTS_EXTRACTED).update(
        status=models.ReviewDocument.Status.RECONCILED
    )
    record_event(
        action="review_workspace_reconciled",
        entity_type="review_workspace",
        entity_id=workspace.external_id,
        metadata={
            "workspace_id": workspace.external_id,
            "engine_ready": state["readiness"]["engine_ready"],
            "missing_count": len(state["readiness"].get("missing", [])),
        },
    )
    return state


def enqueue_reconcile(workspace: models.ReviewWorkspace) -> models.ProcessingJob:
    pending = models.ProcessingJob.objects.filter(
        workspace=workspace,
        job_type=models.ProcessingJob.JobType.RECONCILE_WORKSPACE,
        status__in=[models.ProcessingJob.Status.QUEUED, models.ProcessingJob.Status.PROCESSING],
    ).first()
    if pending:
        return pending
    return models.ProcessingJob.objects.create(
        workspace=workspace,
        job_type=models.ProcessingJob.JobType.RECONCILE_WORKSPACE,
        metadata={"stage": "queued_reconcile"},
    )


def classify_document(filename: str, extension: str) -> str:
    parsed = ParsedDocument("", "metadata_only", {})
    return classify_from_parsed(filename, extension, parsed).document_type


def parse_document(document: models.ReviewDocument) -> ParsedDocument:
    path = secure_data_root() / document.storage_path
    try:
        return parse_document_path(path)
    except ParserDependencyError as exc:
        raise ImproperlyConfigured(str(exc)) from exc


def extract_facts(document: models.ReviewDocument, text: str):
    path = secure_data_root() / document.storage_path
    parsed = ParsedDocument(
        text=text,
        method=str(document.processing_metadata.get("parse_method", "plain")),
        metadata=document.processing_metadata.get("parse_metadata", {}),
    )
    classification = classify_from_parsed(
        document.original_filename,
        f".{document.extension}" if document.extension else Path(document.original_filename).suffix,
        parsed,
    )
    if document.workspace.data_origin == models.ReviewWorkspace.DataOrigin.REAL_DERIVED:
        ensure_bedrock_configured()
        config = bedrock_config_from_env(getattr(settings, "AWS_REGION", "ca-central-1"))
    else:
        config = None
    return extract_facts_for_document(
        path=path,
        filename=document.original_filename,
        data_origin=document.workspace.data_origin,
        parsed=parsed,
        classification=classification,
        text_max_chars=getattr(settings, "MP20_TEXT_EXTRACTION_MAX_CHARS", 24000),
        ocr_max_pages=getattr(settings, "MP20_OCR_MAX_PAGES", 12),
        bedrock_config=config,
    )


def ensure_bedrock_configured() -> None:
    try:
        bedrock_config_from_env(getattr(settings, "AWS_REGION", "ca-central-1"))
    except RuntimeError as exc:
        raise ImproperlyConfigured(str(exc)) from exc


def _json_payload_from_model_text(content: str) -> dict[str, Any]:
    return json_payload_from_model_text(content)


def _fail_or_retry(job: models.ProcessingJob, exc: Exception) -> None:
    job.last_error = str(exc)
    job.metadata = {
        **job.metadata,
        "stage": job.metadata.get("stage", job.job_type),
        "failure_code": exc.__class__.__name__,
    }
    if job.attempts < job.max_attempts:
        job.status = models.ProcessingJob.Status.QUEUED
    else:
        job.status = models.ProcessingJob.Status.FAILED
        job.completed_at = timezone.now()
        if job.document:
            job.document.status = models.ReviewDocument.Status.FAILED
            job.document.failure_reason = str(exc)
            job.document.processing_metadata = {
                **job.document.processing_metadata,
                "failure_code": exc.__class__.__name__,
                "failure_stage": job.metadata.get("stage", job.job_type),
            }
            job.document.save(
                update_fields=[
                    "status",
                    "failure_reason",
                    "processing_metadata",
                    "updated_at",
                ]
            )
    job.save(update_fields=["status", "last_error", "completed_at", "metadata", "updated_at"])
    record_event(
        action="review_processing_failed",
        entity_type="processing_job",
        entity_id=str(job.id),
        metadata={
            "workspace_id": job.workspace.external_id,
            "attempts": job.attempts,
            "max_attempts": job.max_attempts,
            "will_retry": job.status == models.ProcessingJob.Status.QUEUED,
            "failure_code": exc.__class__.__name__,
        },
    )
    record_worker_heartbeat(current_job=None, metadata={"stage": "idle_after_failure"})
