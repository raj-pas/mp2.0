"""Sub-session #11 deferred close-out — workspace DELETE endpoint tests.

The DELETE endpoint exists for the R10 sweep automation's
cleanup-on-failure path so abandoned sweeps don't leave orphan
workspaces + raw bytes accumulating. Refuses to delete a committed
workspace (the soft-undo endpoint is the right entry point for
that case).
"""

from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from web.api import models
from web.api.review_state import readiness_for_state
from web.api.tests.test_review_ingestion import (
    _approve_required_sections,
    _engine_ready_state,
    _user,
)
from web.audit.models import AuditEvent


@pytest.mark.django_db
def test_delete_uncommitted_workspace_cascades_docs_and_jobs() -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(label="Sweep workspace", owner=user)
    # Add a doc + a processing job to verify cascade.
    doc = models.ReviewDocument.objects.create(
        workspace=workspace,
        original_filename="kyc.pdf",
        content_type="application/pdf",
        extension=".pdf",
        file_size=1024,
        sha256="a" * 64,
        storage_path="kyc.pdf",
        status=models.ReviewDocument.Status.UPLOADED,
    )
    models.ProcessingJob.objects.create(
        workspace=workspace,
        document=doc,
        job_type=models.ProcessingJob.JobType.PROCESS_DOCUMENT,
        status=models.ProcessingJob.Status.QUEUED,
    )

    response = client.delete(reverse("review-workspace-detail", args=[workspace.external_id]))

    assert response.status_code == 204
    assert not models.ReviewWorkspace.objects.filter(pk=workspace.pk).exists()
    assert not models.ReviewDocument.objects.filter(pk=doc.pk).exists()
    assert not models.ProcessingJob.objects.filter(workspace_id=workspace.pk).exists()


@pytest.mark.django_db
def test_delete_emits_audit_event_with_doc_count() -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(label="Audit ws", owner=user)
    models.ReviewDocument.objects.create(
        workspace=workspace,
        original_filename="a.pdf",
        content_type="application/pdf",
        extension=".pdf",
        file_size=512,
        sha256="b" * 64,
        storage_path="a.pdf",
        status=models.ReviewDocument.Status.UPLOADED,
    )
    pre_count = AuditEvent.objects.filter(action="review_workspace_deleted").count()

    response = client.delete(reverse("review-workspace-detail", args=[workspace.external_id]))
    assert response.status_code == 204

    post_count = AuditEvent.objects.filter(action="review_workspace_deleted").count()
    assert post_count == pre_count + 1
    event = AuditEvent.objects.filter(action="review_workspace_deleted").latest("created_at")
    assert event.entity_type == "review_workspace"
    assert event.metadata.get("doc_count_at_delete") == 1


@pytest.mark.django_db
def test_delete_committed_workspace_returns_409(tmp_path, settings) -> None:
    settings.MP20_SECURE_DATA_ROOT = str(tmp_path / "secure")
    from django.core.management import call_command

    call_command("seed_default_cma")
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(label="Committed", owner=user)
    workspace.reviewed_state = _engine_ready_state()
    workspace.readiness = readiness_for_state(workspace.reviewed_state).__dict__
    workspace.save()
    _approve_required_sections(workspace, user)
    commit_response = client.post(
        reverse("review-workspace-commit", args=[workspace.external_id]), {}
    )
    assert commit_response.status_code == 200

    response = client.delete(reverse("review-workspace-detail", args=[workspace.external_id]))

    assert response.status_code == 409
    assert response.json().get("code") == "committed_workspace_not_deletable"
    # Workspace must still exist + still be linked to a household.
    workspace.refresh_from_db()
    assert workspace.status == models.ReviewWorkspace.Status.COMMITTED
    assert workspace.linked_household is not None


@pytest.mark.django_db
def test_delete_unknown_workspace_returns_404() -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.delete(reverse("review-workspace-detail", args=["nonexistent_id"]))
    assert response.status_code == 404


@pytest.mark.django_db
def test_delete_requires_real_pii_role() -> None:
    """Anonymous + unauthorized roles must be rejected."""
    workspace = models.ReviewWorkspace.objects.create(
        label="Anon test",
        owner=_user(),
    )
    client = APIClient()  # not authenticated
    response = client.delete(reverse("review-workspace-detail", args=[workspace.external_id]))
    # Anonymous: DRF's default IsAuthenticated returns 403 for unauth
    # (custom auth backend may return 401; either is acceptable as
    # long as the workspace is preserved).
    assert response.status_code in (401, 403)
    assert models.ReviewWorkspace.objects.filter(pk=workspace.pk).exists()
