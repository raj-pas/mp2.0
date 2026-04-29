from __future__ import annotations

import hashlib
import json

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import ImproperlyConfigured
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from engine import STEADYHAND_PURE_SLEEVES, optimize
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from web.api import models
from web.api.access import (
    can_access_real_pii,
    linkable_households,
    role_for_user,
    team_households,
    team_workspaces,
    user_team_slug,
)
from web.api.engine_adapter import to_engine_household
from web.api.review_processing import enqueue_reconcile
from web.api.review_security import (
    assert_real_upload_backend_ready,
    relative_secure_path,
    sha256_bytes,
    write_uploaded_file,
)
from web.api.review_serializers import (
    ExtractedFactSerializer,
    ReviewWorkspaceListSerializer,
    ReviewWorkspaceSerializer,
)
from web.api.review_state import (
    ENGINE_REQUIRED_SECTIONS,
    apply_state_patch,
    commit_reviewed_state,
    create_state_version,
    match_candidates,
    reviewed_state_from_workspace,
    section_blockers,
)
from web.api.serializers import HouseholdDetailSerializer, HouseholdListSerializer
from web.audit.writer import record_event


@method_decorator(csrf_exempt, name="dispatch")
class LocalLoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):  # noqa: ANN001
        email = request.data.get("email", "")
        password = request.data.get("password", "")
        user = authenticate(request, username=email, password=password)
        if user is None:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_400_BAD_REQUEST)
        login(request, user)
        get_token(request)
        record_event(action="local_login", entity_type="session", actor=user.get_username())
        return Response(_session_payload(request))


class LocalLogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):  # noqa: ANN001
        actor = _actor(request)
        logout(request)
        record_event(action="local_logout", entity_type="session", actor=actor)
        return Response({"ok": True})


@method_decorator(ensure_csrf_cookie, name="dispatch")
class SessionView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):  # noqa: ANN001
        record_event(
            action="session_viewed",
            entity_type="session",
            actor=_actor(request),
            metadata={"phase": "phase_1"},
        )
        return Response(_session_payload(request))


class ClientListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):  # noqa: ANN001
        if not can_access_real_pii(request.user):
            return Response({"detail": "Role cannot access real-client PII."}, status=403)
        households = _households_visible_to_user(request.user).prefetch_related("goals", "accounts")
        record_event(action="client_list_viewed", entity_type="household", actor=_actor(request))
        return Response(HouseholdListSerializer(households, many=True).data)


class ClientDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, household_id: str):  # noqa: ANN001
        if not can_access_real_pii(request.user):
            return Response({"detail": "Role cannot access real-client PII."}, status=403)
        household = get_object_or_404(_household_queryset(request.user), external_id=household_id)
        record_event(
            action="client_detail_viewed",
            entity_type="household",
            entity_id=household.external_id,
            actor=_actor(request),
        )
        return Response(HouseholdDetailSerializer(household).data)


class GeneratePortfolioView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, household_id: str):  # noqa: ANN001
        if not can_access_real_pii(request.user):
            return Response({"detail": "Role cannot access real-client PII."}, status=403)
        if not getattr(settings, "MP20_ENGINE_ENABLED", True):
            record_event(
                action="engine_kill_switch_blocked",
                entity_type="household",
                entity_id=household_id,
                actor=_actor(request),
                metadata={"workspace_id": "", "reason": "MP20_ENGINE_ENABLED=false"},
            )
            return Response({"detail": "Portfolio generation is disabled."}, status=403)
        household = get_object_or_404(_household_queryset(request.user), external_id=household_id)
        engine_input = to_engine_household(household)
        output = optimize(engine_input, STEADYHAND_PURE_SLEEVES)
        payload = output.model_dump(mode="json")

        household.last_engine_output = payload
        household.save(update_fields=["last_engine_output", "updated_at"])
        record_event(
            action="engine_run",
            entity_type="household",
            entity_id=household.external_id,
            actor=_actor(request),
            metadata={
                "model_version": output.audit_trace.model_version,
                "method": output.audit_trace.method,
                "goal_count": len(output.goal_blends),
            },
        )
        return Response(payload)


class ReviewWorkspaceListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):  # noqa: ANN001
        if not can_access_real_pii(request.user):
            return Response({"detail": "Role cannot access real-client PII."}, status=403)
        workspaces = team_workspaces(request.user).prefetch_related("documents")
        return Response(ReviewWorkspaceListSerializer(workspaces, many=True).data)

    def post(self, request):  # noqa: ANN001
        if not can_access_real_pii(request.user):
            return Response({"detail": "Role cannot access real-client PII."}, status=403)
        label = request.data.get("label", "").strip()
        if not label:
            return Response({"detail": "Workspace label is required."}, status=400)
        data_origin = (
            request.data.get("data_origin") or models.ReviewWorkspace.DataOrigin.REAL_DERIVED
        )
        if data_origin not in models.ReviewWorkspace.DataOrigin.values:
            return Response({"detail": "Unsupported data_origin."}, status=400)
        workspace = models.ReviewWorkspace.objects.create(
            label=label,
            owner=request.user,
            data_origin=data_origin,
        )
        record_event(
            action="review_workspace_created",
            entity_type="review_workspace",
            entity_id=workspace.external_id,
            actor=_actor(request),
            metadata={"data_origin": workspace.data_origin},
        )
        return Response(
            ReviewWorkspaceSerializer(_review_workspace_queryset().get(pk=workspace.pk)).data
        )


class ReviewWorkspaceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id: str):  # noqa: ANN001
        if not can_access_real_pii(request.user):
            return Response({"detail": "Role cannot access real-client PII."}, status=403)
        workspace = _workspace_for_user(workspace_id, request.user)
        return Response(ReviewWorkspaceSerializer(workspace).data)


class ReviewWorkspaceUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, workspace_id: str):  # noqa: ANN001
        if not can_access_real_pii(request.user):
            return Response({"detail": "Role cannot access real-client PII."}, status=403)
        workspace = _workspace_for_user(workspace_id, request.user)
        if workspace.data_origin == models.ReviewWorkspace.DataOrigin.REAL_DERIVED:
            try:
                assert_real_upload_backend_ready()
            except ImproperlyConfigured as exc:
                record_event(
                    action="real_upload_blocked",
                    entity_type="review_workspace",
                    entity_id=workspace.external_id,
                    actor=_actor(request),
                    metadata={"reason": str(exc), "workspace_id": workspace.external_id},
                )
                return Response({"detail": str(exc)}, status=503)
        files = request.FILES.getlist("files")
        if not files:
            return Response({"detail": "Upload at least one file."}, status=400)

        uploaded: list[dict] = []
        duplicates: list[dict] = []
        for uploaded_file in files:
            content = uploaded_file.read()
            digest = sha256_bytes(content)
            existing = workspace.documents.filter(sha256=digest).first()
            if existing:
                duplicates.append({"filename": uploaded_file.name, "document_id": existing.id})
                continue

            target = write_uploaded_file(
                workspace_external_id=workspace.external_id,
                filename=uploaded_file.name,
                content=content,
            )
            document = models.ReviewDocument.objects.create(
                workspace=workspace,
                original_filename=uploaded_file.name,
                content_type=uploaded_file.content_type or "",
                extension=target.suffix.lower().lstrip("."),
                file_size=uploaded_file.size,
                sha256=digest,
                storage_path=relative_secure_path(target),
                processing_metadata={
                    "extraction_version": "extraction.v2",
                    "review_schema_version": "reviewed_client_state.v1",
                    "artifact_version": "secure_upload_artifact.v1",
                },
            )
            models.ProcessingJob.objects.create(workspace=workspace, document=document)
            uploaded.append({"filename": uploaded_file.name, "document_id": document.id})

        workspace.status = models.ReviewWorkspace.Status.PROCESSING
        workspace.save(update_fields=["status", "updated_at"])
        record_event(
            action="review_documents_uploaded",
            entity_type="review_workspace",
            entity_id=workspace.external_id,
            actor=_actor(request),
            metadata={"uploaded_count": len(uploaded), "duplicate_count": len(duplicates)},
        )
        return Response({"uploaded": uploaded, "duplicates": duplicates})


class ReviewDocumentRetryView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, workspace_id: str, document_id: int):  # noqa: ANN001
        if not can_access_real_pii(request.user):
            return Response({"detail": "Role cannot access real-client PII."}, status=403)
        workspace = _workspace_for_user(workspace_id, request.user)
        document = get_object_or_404(workspace.documents, pk=document_id)
        pending = document.processing_jobs.filter(
            status__in=[
                models.ProcessingJob.Status.QUEUED,
                models.ProcessingJob.Status.PROCESSING,
            ]
        ).first()
        if pending:
            return Response({"job_id": pending.id, "status": pending.status})

        document.status = models.ReviewDocument.Status.UPLOADED
        document.failure_reason = ""
        document.save(update_fields=["status", "failure_reason", "updated_at"])
        job = models.ProcessingJob.objects.create(workspace=workspace, document=document)
        workspace.status = models.ReviewWorkspace.Status.PROCESSING
        workspace.save(update_fields=["status", "updated_at"])
        record_event(
            action="review_document_retry_queued",
            entity_type="review_document",
            entity_id=str(document.id),
            actor=_actor(request),
            metadata={"workspace_id": workspace.external_id, "document_status": document.status},
        )
        return Response({"job_id": job.id, "status": job.status})


class ReviewWorkspaceFactsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id: str):  # noqa: ANN001
        if not can_access_real_pii(request.user):
            return Response({"detail": "Role cannot access real-client PII."}, status=403)
        workspace = _workspace_for_user(workspace_id, request.user)
        facts = workspace.extracted_facts.select_related("document")
        return Response(ExtractedFactSerializer(facts, many=True).data)


class ReviewWorkspaceStateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id: str):  # noqa: ANN001
        if not can_access_real_pii(request.user):
            return Response({"detail": "Role cannot access real-client PII."}, status=403)
        workspace = _workspace_for_user(workspace_id, request.user)
        if not workspace.reviewed_state:
            workspace.reviewed_state = reviewed_state_from_workspace(workspace)
            workspace.readiness = workspace.reviewed_state["readiness"]
            workspace.save(update_fields=["reviewed_state", "readiness", "updated_at"])
        return Response({"state": workspace.reviewed_state, "readiness": workspace.readiness})

    def patch(self, request, workspace_id: str):  # noqa: ANN001
        if not can_access_real_pii(request.user):
            return Response({"detail": "Role cannot access real-client PII."}, status=403)
        workspace = _workspace_for_user(workspace_id, request.user)
        patch = request.data.get("state", request.data)
        reason = request.data.get("reason", "").strip()
        if request.data.get("requires_reason") and not reason:
            return Response({"detail": "Reason is required for this review edit."}, status=400)
        previous_state = workspace.reviewed_state or {}
        state = apply_state_patch(previous_state, patch)
        version = create_state_version(workspace, user=request.user, state=state)
        record_event(
            action="review_state_edited",
            entity_type="review_workspace",
            entity_id=workspace.external_id,
            actor=_actor(request),
            metadata={
                "version": version.version,
                "workspace_id": workspace.external_id,
                "changed_paths": sorted(patch.keys()),
                "old_state_hash": _hash_json(previous_state),
                "new_state_hash": _hash_json(state),
                "reason_present": bool(reason),
                "source_fact_ids": request.data.get("source_fact_ids", []),
            },
        )
        return Response({"state": workspace.reviewed_state, "readiness": workspace.readiness})


class ReviewWorkspaceSectionApprovalView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, workspace_id: str):  # noqa: ANN001
        if not can_access_real_pii(request.user):
            return Response({"detail": "Role cannot access real-client PII."}, status=403)
        workspace = _workspace_for_user(workspace_id, request.user)
        section = request.data.get("section", "")
        status_value = request.data.get("status", models.SectionApproval.Status.APPROVED)
        if not section:
            return Response({"detail": "section is required."}, status=400)
        if section not in ENGINE_REQUIRED_SECTIONS:
            return Response({"detail": "Unsupported review section."}, status=400)
        if status_value not in models.SectionApproval.Status.values:
            return Response({"detail": "Unsupported approval status."}, status=400)
        state = workspace.reviewed_state or reviewed_state_from_workspace(workspace)
        blockers = section_blockers(state, section)
        if status_value == models.SectionApproval.Status.APPROVED and blockers:
            return Response(
                {
                    "detail": (
                        "Plain approval is blocked while required data, conflicts, "
                        "or unknowns remain."
                    ),
                    "blockers": blockers,
                },
                status=400,
            )
        notes = request.data.get("notes", "")
        if (
            status_value
            in {
                models.SectionApproval.Status.APPROVED_WITH_UNKNOWNS,
                models.SectionApproval.Status.NOT_READY,
            }
            and not notes.strip()
        ):
            return Response({"detail": "Approval notes are required for this status."}, status=400)
        approval, _ = models.SectionApproval.objects.update_or_create(
            workspace=workspace,
            section=section,
            defaults={
                "status": status_value,
                "notes": notes,
                "data": {**request.data.get("data", {}), "blockers": blockers},
                "approved_by": request.user,
                "approved_at": timezone.now(),
            },
        )
        record_event(
            action="review_section_approved",
            entity_type="review_workspace",
            entity_id=workspace.external_id,
            actor=_actor(request),
            metadata={
                "workspace_id": workspace.external_id,
                "section": approval.section,
                "status": approval.status,
                "blocker_count": len(blockers),
                "notes_present": bool(notes.strip()),
            },
        )
        return Response(
            ReviewWorkspaceSerializer(_review_workspace_queryset().get(pk=workspace.pk)).data
        )


class ReviewWorkspaceMatchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id: str):  # noqa: ANN001
        if not can_access_real_pii(request.user):
            return Response({"detail": "Role cannot access real-client PII."}, status=403)
        workspace = _workspace_for_user(workspace_id, request.user)
        candidates = match_candidates(workspace)
        workspace.match_candidates = candidates
        workspace.save(update_fields=["match_candidates", "updated_at"])
        return Response({"candidates": candidates})


class ReviewWorkspaceCommitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, workspace_id: str):  # noqa: ANN001
        if not can_access_real_pii(request.user):
            return Response({"detail": "Role cannot access real-client PII."}, status=403)
        workspace = _workspace_for_user(workspace_id, request.user)
        household = None
        if household_id := request.data.get("household_id"):
            household = get_object_or_404(
                _households_owned_by_user(request.user), external_id=household_id
            )
        try:
            committed = commit_reviewed_state(workspace, user=request.user, household=household)
        except ValueError as exc:
            return Response({"detail": str(exc), "readiness": workspace.readiness}, status=400)
        return Response(
            {
                "household_id": committed.external_id,
                "workspace": ReviewWorkspaceSerializer(
                    _review_workspace_queryset().get(pk=workspace.pk)
                ).data,
            }
        )


class ReviewWorkspaceManualReconcileView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, workspace_id: str):  # noqa: ANN001
        if not can_access_real_pii(request.user):
            return Response({"detail": "Role cannot access real-client PII."}, status=403)
        workspace = _workspace_for_user(workspace_id, request.user)
        job = enqueue_reconcile(workspace)
        record_event(
            action="review_manual_reconcile_queued",
            entity_type="review_workspace",
            entity_id=workspace.external_id,
            actor=_actor(request),
            metadata={"workspace_id": workspace.external_id, "job_id": job.id},
        )
        return Response({"job_id": job.id, "status": job.status})


def _households_visible_to_user(user):
    return team_households(user)


def _households_owned_by_user(user):
    return linkable_households(user)


def _household_queryset(user):
    return _households_visible_to_user(user).prefetch_related(
        "members",
        "goals__account_allocations__account",
        "accounts__holdings",
        "accounts__owner_person",
    )


def _review_workspace_queryset():
    return models.ReviewWorkspace.objects.select_related(
        "owner", "linked_household"
    ).prefetch_related(
        "documents",
        "processing_jobs__document",
        "section_approvals",
    )


def _workspace_for_user(workspace_id: str, user):
    return get_object_or_404(
        _review_workspace_queryset().filter(pk__in=team_workspaces(user).values("pk")),
        external_id=workspace_id,
    )


def _session_payload(request) -> dict:  # noqa: ANN001
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        return {
            "authenticated": True,
            "csrf_token": get_token(request),
            "user": {
                "email": user.email or user.get_username(),
                "name": user.get_full_name() or user.get_username(),
                "role": role_for_user(user),
                "team": user_team_slug(user),
                "engine_enabled": getattr(settings, "MP20_ENGINE_ENABLED", True),
            },
        }
    return {"authenticated": False, "csrf_token": get_token(request), "user": None}


def _actor(request) -> str:  # noqa: ANN001
    if getattr(request, "user", None) and request.user.is_authenticated:
        return request.user.get_username()
    return "phase_one_admin"


def _hash_json(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
