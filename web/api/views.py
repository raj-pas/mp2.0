from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from engine import optimize
from engine.frontier import compute_frontier
from extraction.schemas import SYSTEM_FILENAMES
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
from web.api.engine_adapter import (
    committed_construction_snapshot,
    to_engine_cma,
    to_engine_household,
)
from web.api.error_codes import (
    safe_audit_metadata,
    safe_response_payload,
)
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
    portfolio_generation_blocker_for_household,
    readiness_for_state,
    reviewed_state_from_workspace,
    section_blockers,
    validate_review_state_contract,
)
from web.api.serializers import (
    CMASnapshotSerializer,
    HouseholdDetailSerializer,
    HouseholdListSerializer,
    PlanningVersionSerializer,
    PortfolioRunSerializer,
    PortfolioRunSummarySerializer,
)
from web.audit.models import AuditEvent
from web.audit.writer import record_event

DEFAULT_CMA_NAME = "Default CMA"
CMA_AUDIT_ACTIONS = {
    "cma_snapshot_seeded",
    "cma_snapshot_draft_created",
    "cma_snapshot_updated",
    "cma_snapshot_published",
}


class CMAValidationError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "cma_validation_failed",
        diagnostics: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.detail = message  # exposed structurally so callers don't need str(exc) (Phase 2)
        self.code = code
        self.diagnostics = diagnostics or {}


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


class DisclaimerAcknowledgeView(APIView):
    """POST /api/disclaimer/acknowledge/ — Phase 5b.1.

    Records a per-advisor disclaimer acknowledgement on the
    AdvisorProfile + emits an immutable audit event capturing the
    version + advisor + timestamp + ip/UA. Idempotent: re-posting
    the same version updates the timestamp + emits a fresh audit
    row. PII discipline: rationale-style fields aren't accepted;
    only the version + auto-captured request context.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):  # noqa: ANN001
        version = (request.data.get("version") or "").strip()
        if not version:
            return Response(
                {"detail": "version is required.", "code": "version_required"},
                status=400,
            )
        if len(version) > 16:
            return Response(
                {"detail": "version too long.", "code": "version_too_long"},
                status=400,
            )
        profile, _ = models.AdvisorProfile.objects.get_or_create(user=request.user)
        now = timezone.now()
        profile.disclaimer_acknowledged_at = now
        profile.disclaimer_acknowledged_version = version
        profile.save(
            update_fields=[
                "disclaimer_acknowledged_at",
                "disclaimer_acknowledged_version",
            ]
        )
        record_event(
            action="disclaimer_acknowledged",
            entity_type="advisor",
            entity_id=str(request.user.pk),
            actor=_actor(request),
            metadata={
                "version": version,
                "acknowledged_at": now.isoformat(),
                "advisor_id": request.user.pk,
                "ip": _request_ip(request),
                "user_agent": _request_ua(request),
            },
        )
        return Response(
            {"acknowledged_at": now.isoformat(), "version": version}
        )


class TourCompleteView(APIView):
    """POST /api/tour/complete/ — Phase 5b.6.

    Marks the welcome tour as completed for the advisor (server-side
    per-account ack so the tour never re-shows on any device for
    this advisor). Audit event captures advisor + timestamp.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):  # noqa: ANN001
        profile, _ = models.AdvisorProfile.objects.get_or_create(user=request.user)
        if profile.tour_completed_at is None:
            profile.tour_completed_at = timezone.now()
            profile.save(update_fields=["tour_completed_at"])
            record_event(
                action="tour_completed",
                entity_type="advisor",
                entity_id=str(request.user.pk),
                actor=_actor(request),
                metadata={
                    "completed_at": profile.tour_completed_at.isoformat(),
                    "advisor_id": request.user.pk,
                },
            )
        return Response(
            {"completed_at": profile.tour_completed_at.isoformat()}
        )


class FeedbackSubmitView(APIView):
    """POST /api/feedback/ — Phase 5b.1.

    Persists advisor in-app feedback to the Feedback model. No runtime
    Linear API call; ops triages from `GET /api/feedback/report/`
    (analyst-only). Schema mirrors what Linear `save_issue` would
    consume so a future automated-sync migration is a serializer +
    cron task.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):  # noqa: ANN001
        severity = (request.data.get("severity") or "").strip()
        description = (request.data.get("description") or "").strip()
        what_were_you_trying = (request.data.get("what_were_you_trying") or "").strip()
        route = (request.data.get("route") or "").strip()
        session_id = (request.data.get("session_id") or "").strip()
        browser_ua = _request_ua(request)[:512]

        if severity not in {s.value for s in models.Feedback.Severity}:
            return Response(
                {
                    "detail": "Invalid severity.",
                    "code": "severity_invalid",
                    "allowed": [s.value for s in models.Feedback.Severity],
                },
                status=400,
            )
        if len(description) < 20:
            return Response(
                {
                    "detail": "Description must be at least 20 characters.",
                    "code": "description_too_short",
                },
                status=400,
            )
        if len(description) > 5000:
            return Response(
                {"detail": "Description too long.", "code": "description_too_long"},
                status=400,
            )

        feedback = models.Feedback.objects.create(
            advisor=request.user,
            severity=severity,
            description=description,
            what_were_you_trying=what_were_you_trying,
            route=route[:128],
            session_id=session_id[:64],
            browser_user_agent=browser_ua,
        )
        record_event(
            action="feedback_submitted",
            entity_type="feedback",
            entity_id=str(feedback.pk),
            actor=_actor(request),
            metadata={
                "feedback_id": feedback.pk,
                "severity": severity,
                "route": feedback.route,
                "description_len": len(description),
            },
        )
        return Response({"id": feedback.pk, "status": feedback.status}, status=201)


class FeedbackReportView(APIView):
    """GET /api/feedback/report/ — analyst-only triage report (5b.1)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):  # noqa: ANN001
        if role_for_user(request.user) != "financial_analyst":
            return Response(
                {"detail": "Analyst role required.", "code": "analyst_required"},
                status=403,
            )
        queryset = models.Feedback.objects.select_related("advisor").all()

        status_filter = (request.query_params.get("status") or "").strip()
        severity_filter = (request.query_params.get("severity") or "").strip()
        since_filter = (request.query_params.get("since") or "").strip()
        advisor_filter = (request.query_params.get("advisor") or "").strip()

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if severity_filter:
            queryset = queryset.filter(severity=severity_filter)
        if since_filter:
            try:
                since_date = datetime.fromisoformat(since_filter)
                queryset = queryset.filter(created_at__gte=since_date)
            except ValueError:
                return Response(
                    {
                        "detail": "since must be ISO-8601 (YYYY-MM-DD).",
                        "code": "since_invalid",
                    },
                    status=400,
                )
        if advisor_filter:
            queryset = queryset.filter(advisor_id=advisor_filter)

        rows = [
            {
                "id": f.pk,
                "advisor": f.advisor.email or f.advisor.get_username(),
                "severity": f.severity,
                "status": f.status,
                "description": f.description,
                "what_were_you_trying": f.what_were_you_trying,
                "route": f.route,
                "session_id": f.session_id,
                "browser_user_agent": f.browser_user_agent,
                "created_at": f.created_at.isoformat(),
                "ops_notes": f.ops_notes,
                "linear_issue_url": f.linear_issue_url,
            }
            for f in queryset[:1000]
        ]

        record_event(
            action="feedback_report_viewed",
            entity_type="feedback",
            actor=_actor(request),
            metadata={
                "row_count": len(rows),
                "filters": {
                    "status": status_filter,
                    "severity": severity_filter,
                    "since": since_filter,
                    "advisor": advisor_filter,
                },
            },
        )

        if (request.query_params.get("export") or "").lower() == "csv":
            import csv
            import io

            buf = io.StringIO()
            writer = csv.DictWriter(
                buf,
                fieldnames=[
                    "id",
                    "advisor",
                    "severity",
                    "status",
                    "description",
                    "what_were_you_trying",
                    "route",
                    "session_id",
                    "browser_user_agent",
                    "created_at",
                    "ops_notes",
                    "linear_issue_url",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)
            response = Response(
                buf.getvalue(),
                content_type="text/csv",
            )
            response["Content-Disposition"] = "attachment; filename=feedback.csv"
            return response

        return Response({"rows": rows, "count": len(rows)})


class FeedbackUpdateView(APIView):
    """PATCH /api/feedback/<id>/ — analyst-only triage update (5b.1)."""

    permission_classes = [IsAuthenticated]

    def patch(self, request, feedback_id: int):  # noqa: ANN001
        if role_for_user(request.user) != "financial_analyst":
            return Response(
                {"detail": "Analyst role required.", "code": "analyst_required"},
                status=403,
            )
        try:
            feedback = models.Feedback.objects.get(pk=feedback_id)
        except models.Feedback.DoesNotExist:
            return Response(
                {"detail": "Feedback not found.", "code": "feedback_not_found"},
                status=404,
            )

        update_fields: list[str] = []
        if "status" in request.data:
            new_status = request.data["status"]
            if new_status not in {s.value for s in models.Feedback.Status}:
                return Response(
                    {"detail": "Invalid status.", "code": "status_invalid"},
                    status=400,
                )
            feedback.status = new_status
            update_fields.append("status")
        if "ops_notes" in request.data:
            feedback.ops_notes = (request.data.get("ops_notes") or "")[:5000]
            update_fields.append("ops_notes")
        if "linear_issue_url" in request.data:
            feedback.linear_issue_url = (request.data.get("linear_issue_url") or "")[:1024]
            update_fields.append("linear_issue_url")

        if not update_fields:
            return Response(
                {"detail": "Nothing to update.", "code": "no_changes"},
                status=400,
            )
        feedback.save(update_fields=update_fields)

        record_event(
            action="feedback_triaged",
            entity_type="feedback",
            entity_id=str(feedback.pk),
            actor=_actor(request),
            metadata={
                "feedback_id": feedback.pk,
                "fields_updated": update_fields,
                "new_status": feedback.status,
            },
        )
        return Response(
            {
                "id": feedback.pk,
                "status": feedback.status,
                "ops_notes": feedback.ops_notes,
                "linear_issue_url": feedback.linear_issue_url,
            }
        )


def _request_ip(request) -> str:  # noqa: ANN001
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    return (request.META.get("REMOTE_ADDR") or "")[:64]


def _request_ua(request) -> str:  # noqa: ANN001
    return (request.META.get("HTTP_USER_AGENT") or "")[:512]


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
        cma_snapshot = models.CMASnapshot.objects.filter(
            status=models.CMASnapshot.Status.ACTIVE
        ).first()
        if cma_snapshot is None:
            _record_portfolio_event(
                event_type=models.PortfolioRunEvent.EventType.GENERATION_FAILED,
                household=household,
                actor=_actor(request),
                reason_code="no_active_cma",
                metadata={"household_id": household.external_id},
            )
            return Response(
                {
                    "detail": (
                        "No active CMA snapshot exists. Ask a financial analyst to publish one."
                    )
                },
                status=409,
            )
        try:
            _validate_cma_snapshot(cma_snapshot)
        except ValueError as exc:
            _record_portfolio_event(
                event_type=models.PortfolioRunEvent.EventType.GENERATION_FAILED,
                household=household,
                actor=_actor(request),
                reason_code="invalid_cma_universe",
                metadata=safe_audit_metadata(exc, household_id=household.external_id),
            )
            # Phase 2 PII scrub: CMA-universe error message is internally
            # constructed (non-PII) but route through the structured shape
            # for consistency with the grep guard.
            return Response(
                safe_response_payload(exc, hint="invalid_cma_universe"),
                status=409,
            )
        readiness_error = portfolio_generation_blocker_for_household(household)
        if readiness_error:
            _record_portfolio_event(
                event_type=models.PortfolioRunEvent.EventType.GENERATION_FAILED,
                household=household,
                actor=_actor(request),
                reason_code="reviewed_state_not_ready",
                metadata={"household_id": household.external_id, "detail": readiness_error},
            )
            return Response({"detail": readiness_error}, status=400)

        input_snapshot = committed_construction_snapshot(household)
        input_hash = _hash_json(input_snapshot)
        cma_hash = _cma_input_hash(cma_snapshot)
        try:
            reviewed_state_hash, approval_snapshot_hash, provenance_warnings = (
                _portfolio_provenance_hashes(household)
            )
        except ValueError as exc:
            _record_portfolio_event(
                event_type=models.PortfolioRunEvent.EventType.GENERATION_FAILED,
                household=household,
                actor=_actor(request),
                reason_code="missing_real_derived_provenance",
                metadata=safe_audit_metadata(exc, household_id=household.external_id),
            )
            return Response(safe_response_payload(exc), status=400)
        as_of_date = timezone.localdate()
        run_signature = _hash_json(
            {
                "schema_version": "engine_output.link_first.v2",
                "input_hash": input_hash,
                "cma_hash": cma_hash,
                "reviewed_state_hash": reviewed_state_hash,
                "approval_snapshot_hash": approval_snapshot_hash,
                "as_of_date": as_of_date.isoformat(),
            }
        )
        try:
            reusable = _reusable_current_run(household, run_signature)
        except ValueError as exc:
            _record_portfolio_event(
                event_type=models.PortfolioRunEvent.EventType.GENERATION_FAILED,
                household=household,
                actor=_actor(request),
                reason_code="ambiguous_current_lifecycle",
                metadata=safe_audit_metadata(exc, household_id=household.external_id),
            )
            return Response(safe_response_payload(exc), status=409)
        if reusable is not None:
            verification = _portfolio_run_verification(
                reusable,
                input_hash=input_hash,
                output_hash=None,
                cma_hash=cma_hash,
                run_signature=run_signature,
            )
            if verification["ok"]:
                _record_portfolio_event(
                    event_type=models.PortfolioRunEvent.EventType.REUSED,
                    portfolio_run=reusable,
                    household=household,
                    actor=_actor(request),
                    metadata=verification,
                )
                record_event(
                    action="portfolio_run_reused",
                    entity_type="portfolio_run",
                    entity_id=reusable.external_id,
                    actor=_actor(request),
                    metadata={
                        "household_id": household.external_id,
                        "run_signature": run_signature,
                        "input_hash": input_hash,
                        "output_hash": reusable.output_hash,
                    },
                )
                return Response(PortfolioRunSerializer(reusable).data)
            _record_portfolio_event(
                event_type=models.PortfolioRunEvent.EventType.HASH_MISMATCH,
                portfolio_run=reusable,
                household=household,
                actor=_actor(request),
                reason_code="stored_run_hash_mismatch",
                metadata=verification,
            )

        engine_input = to_engine_household(household)
        output = optimize(engine_input, to_engine_cma(cma_snapshot), as_of_date=as_of_date)
        payload = output.model_dump(mode="json")
        payload["run_manifest"] = {
            **payload.get("run_manifest", {}),
            "input_hash": input_hash,
            "cma_hash": cma_hash,
            "reviewed_state_hash": reviewed_state_hash,
            "approval_snapshot_hash": approval_snapshot_hash,
            "run_signature": run_signature,
            "provenance_warnings": provenance_warnings,
        }
        _attach_goal_risk_explainability(
            payload,
            input_snapshot=input_snapshot,
            cma_snapshot=cma_snapshot,
            cma_hash=cma_hash,
        )
        try:
            _validate_v2_manifest(payload["run_manifest"])
        except ValueError as exc:
            _record_portfolio_event(
                event_type=models.PortfolioRunEvent.EventType.GENERATION_FAILED,
                household=household,
                actor=_actor(request),
                reason_code="missing_v2_manifest_inputs",
                metadata=safe_audit_metadata(exc, household_id=household.external_id),
            )
            return Response(safe_response_payload(exc), status=409)
        payload["warnings"] = sorted(set(payload.get("warnings") or []).union(provenance_warnings))
        output_hash = _hash_json(payload)
        regenerated_after_decline = _latest_reusable_run_was_declined(household)
        run = models.PortfolioRun.objects.create(
            household=household,
            cma_snapshot=cma_snapshot,
            generated_by=request.user,
            as_of_date=as_of_date,
            run_signature=run_signature,
            input_snapshot=input_snapshot,
            output=payload,
            input_hash=input_hash,
            output_hash=output_hash,
            cma_hash=cma_hash,
            reviewed_state_hash=reviewed_state_hash,
            approval_snapshot_hash=approval_snapshot_hash,
            engine_version=output.audit_trace.model_version,
            advisor_summary=output.advisor_summary,
            technical_trace=output.technical_trace,
        )
        goals = {goal.external_id: goal for goal in household.goals.all()}
        accounts = {account.external_id: account for account in household.accounts.all()}
        payload_recommendations = {
            item.get("link_id"): item for item in payload.get("link_recommendations", [])
        }
        links = {
            link.external_id: link
            for link in models.GoalAccountLink.objects.filter(
                goal__household=household,
                account__household=household,
            )
        }
        for recommendation in output.link_recommendations:
            link = links.get(recommendation.link_id)
            models.PortfolioRunLinkRecommendation.objects.create(
                portfolio_run=run,
                goal_account_link=link,
                link_external_id=recommendation.link_id,
                goal=goals.get(recommendation.goal_id),
                account=accounts.get(recommendation.account_id),
                goal_external_id=recommendation.goal_id,
                account_external_id=recommendation.account_id,
                allocated_amount=Decimal(str(recommendation.allocated_amount)),
                frontier_percentile=recommendation.frontier_percentile,
                expected_return=Decimal(str(recommendation.expected_return)),
                volatility=Decimal(str(recommendation.volatility)),
                allocations=[
                    allocation.model_dump(mode="json") for allocation in recommendation.allocations
                ],
                current_comparison=recommendation.current_comparison.model_dump(mode="json"),
                explanation=payload_recommendations.get(recommendation.link_id, {}).get(
                    "explanation", recommendation.explanation
                ),
                warnings=recommendation.warnings,
            )
        event_type = (
            models.PortfolioRunEvent.EventType.REGENERATED_AFTER_DECLINE
            if regenerated_after_decline
            else models.PortfolioRunEvent.EventType.GENERATED
        )
        _record_portfolio_event(
            event_type=event_type,
            portfolio_run=run,
            household=household,
            actor=_actor(request),
            metadata={
                "run_signature": run_signature,
                "input_hash": input_hash,
                "output_hash": output_hash,
                "cma_hash": cma_hash,
                "warnings": payload.get("warnings") or [],
            },
        )
        record_event(
            action="portfolio_run_generated",
            entity_type="portfolio_run",
            entity_id=run.external_id,
            actor=_actor(request),
            metadata={
                "model_version": output.audit_trace.model_version,
                "method": output.audit_trace.method,
                "household_id": household.external_id,
                "cma_snapshot_id": cma_snapshot.external_id,
                "input_hash": input_hash,
                "output_hash": output_hash,
                "cma_hash": cma_hash,
                "run_signature": run_signature,
                "schema_version": payload["schema_version"],
                "link_count": len(output.link_recommendations),
            },
        )
        return Response(PortfolioRunSerializer(run).data)


class PortfolioRunListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, household_id: str):  # noqa: ANN001
        if not can_access_real_pii(request.user):
            return Response({"detail": "Role cannot access real-client PII."}, status=403)
        household = get_object_or_404(_household_queryset(request.user), external_id=household_id)
        runs = household.portfolio_runs.order_by("-created_at")
        return Response(PortfolioRunSummarySerializer(runs, many=True).data)


class PortfolioRunDeclineView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, household_id: str, run_id: str):  # noqa: ANN001
        if not can_access_real_pii(request.user):
            return Response({"detail": "Role cannot access real-client PII."}, status=403)
        household = get_object_or_404(_household_queryset(request.user), external_id=household_id)
        run = get_object_or_404(household.portfolio_runs, external_id=run_id)
        reason = str(request.data.get("reason") or "").strip()
        _record_portfolio_event(
            event_type=models.PortfolioRunEvent.EventType.ADVISOR_DECLINED,
            portfolio_run=run,
            household=household,
            actor=_actor(request),
            reason_code="advisor_declined",
            note=reason,
            metadata={"household_id": household.external_id, "run_id": run.external_id},
        )
        record_event(
            action="portfolio_run_declined",
            entity_type="portfolio_run",
            entity_id=run.external_id,
            actor=_actor(request),
            metadata={"household_id": household.external_id, "reason_present": bool(reason)},
        )
        return Response(PortfolioRunSerializer(run).data)


class PortfolioRunAuditExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, household_id: str, run_id: str):  # noqa: ANN001
        if not can_access_real_pii(request.user):
            return Response({"detail": "Role cannot access real-client PII."}, status=403)
        household = get_object_or_404(_household_queryset(request.user), external_id=household_id)
        run = get_object_or_404(household.portfolio_runs, external_id=run_id)
        verification = _portfolio_run_verification(run)
        if not verification["ok"]:
            _record_portfolio_event(
                event_type=models.PortfolioRunEvent.EventType.HASH_MISMATCH,
                portfolio_run=run,
                household=household,
                actor=_actor(request),
                reason_code="audit_export_hash_mismatch",
                metadata=verification,
            )
        _record_portfolio_event(
            event_type=models.PortfolioRunEvent.EventType.AUDIT_EXPORTED,
            portfolio_run=run,
            household=household,
            actor=_actor(request),
            metadata={"verification": verification},
        )
        record_event(
            action="portfolio_run_audit_exported",
            entity_type="portfolio_run",
            entity_id=run.external_id,
            actor=_actor(request),
            metadata={"household_id": household.external_id, "verification_ok": verification["ok"]},
        )
        run.refresh_from_db()
        return Response(_sanitized_portfolio_audit_export(run, verification))


class PlanningVersionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, household_id: str):  # noqa: ANN001
        if not can_access_real_pii(request.user):
            return Response({"detail": "Role cannot access real-client PII."}, status=403)
        household = get_object_or_404(_household_queryset(request.user), external_id=household_id)
        versions = household.planning_versions.order_by("-version")
        return Response(PlanningVersionSerializer(versions, many=True).data)

    def post(self, request, household_id: str):  # noqa: ANN001
        if not can_access_real_pii(request.user):
            return Response({"detail": "Role cannot access real-client PII."}, status=403)
        household = get_object_or_404(_household_queryset(request.user), external_id=household_id)
        latest = household.planning_versions.order_by("-version").first()
        version = (latest.version + 1) if latest else 1
        state = request.data.get("state") or committed_construction_snapshot(household)
        planning_version = models.PlanningVersion.objects.create(
            household=household,
            version=version,
            state=state,
            rationale=str(request.data.get("rationale") or ""),
            created_by=request.user,
        )
        stale_count = _record_current_run_invalidations(
            models.PortfolioRun.objects.filter(household=household),
            event_type=models.PortfolioRunEvent.EventType.INVALIDATED_BY_HOUSEHOLD_CHANGE,
            actor=_actor(request),
            reason_code="planning_version_created",
            metadata={"planning_version": version},
        )
        record_event(
            action="planning_version_created",
            entity_type="planning_version",
            entity_id=f"{household.external_id}:{version}",
            actor=_actor(request),
            metadata={
                "household_id": household.external_id,
                "version": version,
                "state_hash": _hash_json(state),
                "stale_portfolio_run_count": stale_count,
            },
        )
        return Response(PlanningVersionSerializer(planning_version).data, status=201)


class CMASnapshotListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):  # noqa: ANN001
        if role_for_user(request.user) != "financial_analyst":
            return Response(
                {"detail": "Only financial analysts can access CMA snapshots."}, status=403
            )
        snapshots = models.CMASnapshot.objects.prefetch_related(
            "fund_assumptions", "correlations"
        ).all()
        return Response(CMASnapshotSerializer(snapshots, many=True).data)

    def post(self, request):  # noqa: ANN001
        if role_for_user(request.user) != "financial_analyst":
            return Response(
                {"detail": "Only financial analysts can create CMA drafts."}, status=403
            )
        existing_draft = (
            models.CMASnapshot.objects.filter(status=models.CMASnapshot.Status.DRAFT)
            .prefetch_related("fund_assumptions", "correlations")
            .order_by("-version", "-created_at")
            .first()
        )
        if existing_draft is not None:
            return Response(CMASnapshotSerializer(existing_draft).data)

        source_id = request.data.get("copy_from_snapshot_id")
        if source_id:
            source = get_object_or_404(models.CMASnapshot, external_id=source_id)
        else:
            source = models.CMASnapshot.objects.filter(
                status=models.CMASnapshot.Status.ACTIVE
            ).first()
        if source is None:
            return Response({"detail": "No CMA snapshot exists to copy."}, status=400)

        try:
            with transaction.atomic():
                snapshot = _clone_cma_snapshot(source, request.user)
                _apply_cma_patch(snapshot, request.data)
        except ValueError as exc:
            return Response(safe_response_payload(exc), status=400)
        snapshot.refresh_from_db()
        record_event(
            action="cma_snapshot_draft_created",
            entity_type="cma_snapshot",
            entity_id=snapshot.external_id,
            actor=_actor(request),
            metadata={
                "source_snapshot_id": source.external_id,
                "source_version": source.version,
                "version": snapshot.version,
                "snapshot_hash": _hash_json(_cma_audit_payload(snapshot)),
            },
        )
        return Response(CMASnapshotSerializer(snapshot).data, status=201)


class CMASnapshotDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, snapshot_id: str):  # noqa: ANN001
        if role_for_user(request.user) != "financial_analyst":
            return Response(
                {"detail": "Only financial analysts can access CMA snapshots."}, status=403
            )
        snapshot = get_object_or_404(
            models.CMASnapshot.objects.prefetch_related("fund_assumptions", "correlations"),
            external_id=snapshot_id,
        )
        return Response(CMASnapshotSerializer(snapshot).data)

    def patch(self, request, snapshot_id: str):  # noqa: ANN001
        if role_for_user(request.user) != "financial_analyst":
            return Response(
                {"detail": "Only financial analysts can edit CMA snapshots."}, status=403
            )
        snapshot = get_object_or_404(
            models.CMASnapshot.objects.prefetch_related("fund_assumptions", "correlations"),
            external_id=snapshot_id,
        )
        if snapshot.status != models.CMASnapshot.Status.DRAFT:
            return Response({"detail": "Only draft CMA snapshots can be edited."}, status=400)

        try:
            with transaction.atomic():
                before_hash = _hash_json(_cma_audit_payload(snapshot))
                before_payload = _cma_audit_payload(snapshot)
                _apply_cma_patch(snapshot, request.data)
                snapshot.refresh_from_db()
                after_payload = _cma_audit_payload(snapshot)
                after_hash = _hash_json(_cma_audit_payload(snapshot))
                record_event(
                    action="cma_snapshot_updated",
                    entity_type="cma_snapshot",
                    entity_id=snapshot.external_id,
                    actor=_actor(request),
                    metadata={
                        "version": snapshot.version,
                        "before_hash": before_hash,
                        "after_hash": after_hash,
                        "updated_fields": sorted(request.data.keys()),
                        **_cma_diff(before_payload, after_payload),
                    },
                )
        except ValueError as exc:
            return Response(_cma_validation_error_payload(exc), status=400)
        snapshot.refresh_from_db()
        return Response(CMASnapshotSerializer(snapshot).data)


class CMAActiveView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):  # noqa: ANN001
        if role_for_user(request.user) != "financial_analyst":
            return Response(
                {"detail": "Only financial analysts can access active CMA assumptions."},
                status=403,
            )
        snapshot = (
            models.CMASnapshot.objects.filter(status=models.CMASnapshot.Status.ACTIVE)
            .prefetch_related("fund_assumptions", "correlations")
            .first()
        )
        if snapshot is None:
            return Response({"detail": "No active CMA snapshot exists."}, status=404)
        return Response(CMASnapshotSerializer(snapshot).data)


class CMASnapshotPublishView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, snapshot_id: str):  # noqa: ANN001
        if role_for_user(request.user) != "financial_analyst":
            return Response(
                {"detail": "Only financial analysts can publish CMA snapshots."}, status=403
            )
        publish_note = str(request.data.get("publish_note") or "").strip()
        if not publish_note:
            return Response({"detail": "Publish note is required."}, status=400)
        snapshot = get_object_or_404(
            models.CMASnapshot.objects.prefetch_related("fund_assumptions", "correlations"),
            external_id=snapshot_id,
        )
        if snapshot.status != models.CMASnapshot.Status.DRAFT:
            return Response({"detail": "Only draft CMA snapshots can be published."}, status=400)
        try:
            _validate_cma_snapshot(snapshot)
        except ValueError as exc:
            return Response(_cma_validation_error_payload(exc), status=400)

        with transaction.atomic():
            models.CMASnapshot.objects.exclude(pk=snapshot.pk).filter(
                status__in=[
                    models.CMASnapshot.Status.ACTIVE,
                    models.CMASnapshot.Status.DRAFT,
                ]
            ).update(status=models.CMASnapshot.Status.ARCHIVED)
            snapshot.status = models.CMASnapshot.Status.ACTIVE
            snapshot.published_by = request.user
            snapshot.published_at = timezone.now()
            snapshot.save(update_fields=["status", "published_by", "published_at", "updated_at"])
            stale_count = _record_current_run_invalidations(
                models.PortfolioRun.objects.all(),
                event_type=models.PortfolioRunEvent.EventType.INVALIDATED_BY_CMA,
                actor=_actor(request),
                reason_code="cma_snapshot_published",
                metadata={"cma_snapshot_id": snapshot.external_id, "version": snapshot.version},
            )
            record_event(
                action="cma_snapshot_published",
                entity_type="cma_snapshot",
                entity_id=snapshot.external_id,
                actor=_actor(request),
                metadata={
                    "version": snapshot.version,
                    "publish_note": publish_note,
                    "stale_portfolio_run_count": stale_count,
                    "snapshot_hash": _hash_json(_cma_audit_payload(snapshot)),
                },
            )
        return Response(CMASnapshotSerializer(snapshot).data)


class CMAFrontierView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, snapshot_id: str):  # noqa: ANN001
        if role_for_user(request.user) != "financial_analyst":
            return Response(
                {"detail": "Only financial analysts can view the full frontier."}, status=403
            )
        snapshot = get_object_or_404(
            models.CMASnapshot.objects.prefetch_related("fund_assumptions", "correlations"),
            external_id=snapshot_id,
        )
        try:
            payload = _cma_frontier_payload(snapshot)
        except ValueError as exc:
            return Response(_cma_validation_error_payload(exc), status=400)
        return Response(payload)


class CMAAuditView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):  # noqa: ANN001
        if role_for_user(request.user) != "financial_analyst":
            return Response(
                {"detail": "Only financial analysts can access CMA audit events."}, status=403
            )
        events = AuditEvent.objects.filter(action__in=CMA_AUDIT_ACTIONS).order_by("-created_at")[
            :50
        ]
        return Response([_audit_event_payload(event) for event in events])


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
                    metadata=safe_audit_metadata(exc, workspace_id=workspace.external_id),
                )
                return Response(safe_response_payload(exc), status=503)
        files = request.FILES.getlist("files")
        if not files:
            record_event(
                action="review_upload_empty_rejected",
                entity_type="review_workspace",
                entity_id=workspace.external_id,
                actor=_actor(request),
                metadata={"workspace_id": workspace.external_id},
            )
            return Response({"detail": "Upload at least one file."}, status=400)

        uploaded: list[dict] = []
        duplicates: list[dict] = []
        ignored: list[dict] = []
        for uploaded_file in files:
            # Each file is its own try/except so one bad file (oversize,
            # disk error, malformed multipart part) doesn't 500 the whole
            # batch — the user keeps the files that succeeded and gets a
            # per-file reason for the ones that didn't.
            try:
                if Path(uploaded_file.name).name.lower() in SYSTEM_FILENAMES:
                    ignored.append({"filename": uploaded_file.name, "reason": "system_file"})
                    continue
                content = uploaded_file.read()
                if not content:
                    ignored.append({"filename": uploaded_file.name, "reason": "empty_file"})
                    continue
                digest = sha256_bytes(content)
                existing = workspace.documents.filter(sha256=digest).first()
                if existing:
                    duplicates.append({"filename": uploaded_file.name, "document_id": existing.id})
                    continue

                with transaction.atomic():
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
            except Exception as exc:
                # Catch broadly so the rest of the batch still goes
                # through. Surface the failure code to the client and
                # audit it; don't leak full exception strings (paths,
                # stack data) into the user-visible reason.
                ignored.append(
                    {
                        "filename": uploaded_file.name,
                        "reason": "upload_failed",
                        "failure_code": exc.__class__.__name__,
                    }
                )
                record_event(
                    action="review_document_upload_failed",
                    entity_type="review_workspace",
                    entity_id=workspace.external_id,
                    actor=_actor(request),
                    metadata={
                        "workspace_id": workspace.external_id,
                        "filename": uploaded_file.name,
                        "failure_code": exc.__class__.__name__,
                    },
                )

        if uploaded:
            workspace.status = models.ReviewWorkspace.Status.PROCESSING
            workspace.save(update_fields=["status", "updated_at"])
        record_event(
            action="review_documents_uploaded",
            entity_type="review_workspace",
            entity_id=workspace.external_id,
            actor=_actor(request),
            metadata={
                "uploaded_count": len(uploaded),
                "duplicate_count": len(duplicates),
                "ignored_count": len(ignored),
            },
        )
        return Response({"uploaded": uploaded, "duplicates": duplicates, "ignored": ignored})


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


class ReviewDocumentManualEntryView(APIView):
    """Advisor escape hatch when automated extraction can't recover.

    Marks the document as `manual_entry`, leaving the workspace's
    reconcile path to skip it (no fact contributions). The advisor
    will fill the missing fields by hand via the review-screen state
    editor (PATCH /state/). Distinct from FAILED so the audit trail
    captures a deliberate advisor decision rather than an extraction
    error.
    """

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, workspace_id: str, document_id: int):  # noqa: ANN001
        # Phase 3 BUG-1 close-out 2026-05-02: wrap the entire endpoint
        # in `transaction.atomic` and `select_for_update` the document
        # row so concurrent manual-entry calls serialize. Idempotent
        # end-state (both calls land MANUAL_ENTRY) but the audit trail
        # interleave + processing_metadata last-write semantics need
        # the lock to be clean.
        if not can_access_real_pii(request.user):
            return Response({"detail": "Role cannot access real-client PII."}, status=403)
        workspace = _workspace_for_user(workspace_id, request.user)
        document = get_object_or_404(workspace.documents.select_for_update(), pk=document_id)
        # Manual-entry is the escape hatch for non-recoverable extraction
        # failures, not a generic "skip this doc" toggle. Restrict to
        # docs in terminal-or-near-terminal states so an advisor can't
        # accidentally drop a successfully-reconciled doc out of the
        # extraction record (which would lose its facts + audit
        # provenance silently).
        eligible_statuses = {
            models.ReviewDocument.Status.FAILED,
            models.ReviewDocument.Status.UNSUPPORTED,
            models.ReviewDocument.Status.OCR_REQUIRED,
        }
        if document.status not in eligible_statuses:
            return Response(
                {
                    "detail": (
                        "Manual entry is only available for documents that failed "
                        "extraction or require OCR. This document is in state "
                        f"'{document.status}'."
                    ),
                    "code": "manual_entry_not_eligible",
                    "current_status": document.status,
                    "eligible_statuses": sorted(eligible_statuses),
                },
                status=409,
            )
        previous_status = document.status
        previous_failure_code = document.processing_metadata.get("failure_code", "")
        document.status = models.ReviewDocument.Status.MANUAL_ENTRY
        document.failure_reason = ""
        document.processing_metadata = {
            **document.processing_metadata,
            "manual_entry_marked_at": timezone.now().isoformat(),
            "manual_entry_marked_by": (
                request.user.email if getattr(request.user, "email", "") else "system"
            ),
            "manual_entry_previous_status": previous_status,
            "manual_entry_previous_failure_code": previous_failure_code,
        }
        document.save(
            update_fields=[
                "status",
                "failure_reason",
                "processing_metadata",
                "updated_at",
            ]
        )
        # Cancel any in-flight jobs so reconcile doesn't pick the doc
        # back up.
        document.processing_jobs.filter(
            status__in=[
                models.ProcessingJob.Status.QUEUED,
                models.ProcessingJob.Status.PROCESSING,
            ]
        ).update(
            status=models.ProcessingJob.Status.FAILED,
            last_error="Document marked as manual entry by advisor.",
            completed_at=timezone.now(),
        )
        # Re-trigger reconcile so workspace state reflects the doc's
        # exclusion from extraction without waiting for the next job.
        enqueue_reconcile(workspace)
        record_event(
            action="review_document_manual_entry_marked",
            entity_type="review_document",
            entity_id=str(document.id),
            actor=_actor(request),
            metadata={
                "workspace_id": workspace.external_id,
                "previous_status": previous_status,
                "previous_failure_code": previous_failure_code,
            },
        )
        return Response(
            {
                "document_id": document.id,
                "status": document.status,
                "previous_status": previous_status,
                "previous_failure_code": previous_failure_code,
            }
        )


class ReviewWorkspaceFactsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id: str):  # noqa: ANN001
        if not can_access_real_pii(request.user):
            return Response({"detail": "Role cannot access real-client PII."}, status=403)
        workspace = _workspace_for_user(workspace_id, request.user)
        facts = workspace.extracted_facts.select_related("document")
        return Response(ExtractedFactSerializer(facts, many=True).data)


class ReviewFactEvidenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id: str, fact_id: int):  # noqa: ANN001
        if not can_access_real_pii(request.user):
            return Response({"detail": "Role cannot access real-client PII."}, status=403)
        workspace = _workspace_for_user(workspace_id, request.user)
        fact = get_object_or_404(workspace.extracted_facts.select_related("document"), pk=fact_id)
        record_event(
            action="review_evidence_viewed",
            entity_type="review_workspace",
            entity_id=workspace.external_id,
            actor=_actor(request),
            metadata={
                "workspace_id": workspace.external_id,
                "fact_id": fact.id,
                "field": fact.field,
                "document_id": fact.document_id,
                "redacted": True,
            },
        )
        return Response(
            {
                "fact_id": fact.id,
                "field": fact.field,
                "source_page": fact.source_page,
                "source_location": fact.source_location,
                "evidence_quote": fact.evidence_quote,
                "redacted": True,
            }
        )


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
        readiness = readiness_for_state(workspace.reviewed_state).__dict__
        return Response(
            {
                "state": {**workspace.reviewed_state, "readiness": readiness},
                "readiness": readiness,
            }
        )

    def patch(self, request, workspace_id: str):  # noqa: ANN001
        if not can_access_real_pii(request.user):
            return Response({"detail": "Role cannot access real-client PII."}, status=403)
        workspace = _workspace_for_user(workspace_id, request.user)
        patch = request.data.get("state", request.data)
        reason = request.data.get("reason", "").strip()
        if request.data.get("requires_reason") and not reason:
            return Response({"detail": "Reason is required for this review edit."}, status=400)
        invalidated_sections: list[str] = []
        with transaction.atomic():
            locked_workspace = models.ReviewWorkspace.objects.select_for_update().get(
                pk=workspace.pk
            )
            previous_state = locked_workspace.reviewed_state or {}
            state = apply_state_patch(previous_state, patch)
            try:
                validate_review_state_contract(state)
            except ValueError as exc:
                return Response(safe_response_payload(exc), status=400)
            version = create_state_version(locked_workspace, user=request.user, state=state)
            # Approvals are point-in-time. If the new state has fresh
            # blockers in a previously-approved section, the approval
            # is stale — flip it to NEEDS_ATTENTION so the commit gate
            # forces the advisor to re-review. Without this, an advisor
            # could approve `goals`, then PATCH to remove a required
            # field, and still commit (silent gate evasion).
            approvals = locked_workspace.section_approvals.filter(
                status=models.SectionApproval.Status.APPROVED
            )
            for approval in approvals:
                if section_blockers(state, approval.section):
                    approval.status = models.SectionApproval.Status.NEEDS_ATTENTION
                    approval.save(update_fields=["status", "updated_at"])
                    invalidated_sections.append(approval.section)
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
                "invalidated_approvals": invalidated_sections,
            },
        )
        return Response(
            {
                "state": version.state,
                "readiness": version.readiness,
                "invalidated_approvals": invalidated_sections,
            }
        )


class ReviewWorkspaceConflictResolveView(APIView):
    """POST /api/review-workspaces/<wsid>/conflicts/resolve/ — Phase 5a.

    Body: {field, chosen_fact_id, rationale, evidence_ack}.
    Records the advisor's chosen candidate + rationale + evidence
    acknowledgement on the workspace conflict slot. Atomic +
    select_for_update on the workspace; serializes concurrent
    advisor calls. Re-runs section-approval blocker check + flips
    affected approvals to NEEDS_ATTENTION (mirrors
    ReviewWorkspaceStateView.patch behavior). Emits exactly one
    `review_conflict_resolved` audit event per locked decision #37.

    PII discipline (canon §11.8.3): the rationale text is persisted
    on the reviewed_state row (advisor-scoped) but NEVER copied into
    audit-event metadata; metadata records only `rationale_len` so
    the immutable audit row stays free of advisor-typed content
    that could reference real PII.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, workspace_id: str):  # noqa: ANN001
        if not can_access_real_pii(request.user):
            return Response({"detail": "Role cannot access real-client PII."}, status=403)
        workspace = _workspace_for_user(workspace_id, request.user)
        field = (request.data.get("field") or "").strip()
        chosen_fact_id = request.data.get("chosen_fact_id")
        rationale = (request.data.get("rationale") or "").strip()
        evidence_ack = bool(request.data.get("evidence_ack"))

        if not field:
            return Response(
                {"detail": "Conflict field is required.", "code": "field_required"},
                status=400,
            )
        if not isinstance(chosen_fact_id, int):
            return Response(
                {
                    "detail": "chosen_fact_id must be an integer.",
                    "code": "chosen_fact_id_required",
                },
                status=400,
            )
        if len(rationale) < 4:
            return Response(
                {
                    "detail": "Rationale is required (>= 4 characters).",
                    "code": "rationale_required",
                },
                status=400,
            )
        if not evidence_ack:
            return Response(
                {
                    "detail": "Evidence acknowledgement is required.",
                    "code": "evidence_ack_required",
                },
                status=400,
            )

        invalidated_sections: list[str] = []
        with transaction.atomic():
            locked_workspace = models.ReviewWorkspace.objects.select_for_update().get(
                pk=workspace.pk
            )
            previous_state = locked_workspace.reviewed_state or reviewed_state_from_workspace(
                locked_workspace
            )
            conflicts = list(previous_state.get("conflicts") or [])
            target_index: int | None = None
            target_conflict: dict | None = None
            for index, conflict in enumerate(conflicts):
                if conflict.get("field") == field:
                    target_index = index
                    target_conflict = conflict
                    break

            if target_conflict is None or target_index is None:
                return Response(
                    {
                        "detail": "Conflict for the named field was not found.",
                        "code": "conflict_not_found",
                    },
                    status=404,
                )

            if chosen_fact_id not in (target_conflict.get("fact_ids") or []):
                return Response(
                    {
                        "detail": "chosen_fact_id is not a candidate for this conflict.",
                        "code": "chosen_fact_not_in_conflict",
                    },
                    status=400,
                )

            try:
                chosen_fact = locked_workspace.extracted_facts.select_related("document").get(
                    pk=chosen_fact_id
                )
            except models.ExtractedFact.DoesNotExist:
                return Response(
                    {
                        "detail": "Chosen fact does not belong to this workspace.",
                        "code": "chosen_fact_not_in_workspace",
                    },
                    status=400,
                )

            actor_label = (
                getattr(request.user, "email", None)
                or getattr(request.user, "username", None)
                or "unknown"
            )
            resolved_at = timezone.now().isoformat()
            resolved_conflict = {
                **target_conflict,
                "resolved": True,
                "chosen_fact_id": chosen_fact_id,
                "resolution": chosen_fact.value,
                "rationale": rationale,
                "evidence_ack": True,
                "resolved_at": resolved_at,
                "resolved_by": actor_label,
            }
            conflicts[target_index] = resolved_conflict

            new_state = dict(previous_state)
            new_state["conflicts"] = conflicts

            try:
                validate_review_state_contract(new_state)
            except ValueError as exc:
                return Response(safe_response_payload(exc), status=400)

            version = create_state_version(locked_workspace, user=request.user, state=new_state)

            approvals = locked_workspace.section_approvals.filter(
                status=models.SectionApproval.Status.APPROVED
            )
            for approval in approvals:
                if section_blockers(new_state, approval.section):
                    approval.status = models.SectionApproval.Status.NEEDS_ATTENTION
                    approval.save(update_fields=["status", "updated_at"])
                    invalidated_sections.append(approval.section)

        record_event(
            action="review_conflict_resolved",
            entity_type="review_workspace",
            entity_id=workspace.external_id,
            actor=_actor(request),
            metadata={
                "version": version.version,
                "workspace_id": workspace.external_id,
                "field": field,
                "section": target_conflict.get("section"),
                "chosen_fact_id": chosen_fact_id,
                "candidate_count": len(target_conflict.get("fact_ids") or []),
                "rationale_len": len(rationale),
                "invalidated_approvals": invalidated_sections,
            },
        )
        return Response(
            {
                "state": version.state,
                "readiness": version.readiness,
                "invalidated_approvals": invalidated_sections,
            }
        )


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
            # Surface the gate that blocked the commit. The frontend's
            # disabled-state should already keep the user from getting
            # here, but if they do, the toast needs to be specific
            # enough that they can self-serve a fix.
            approvals = {
                approval.section: approval.status for approval in workspace.section_approvals.all()
            }
            missing_approvals = [
                section
                for section in ENGINE_REQUIRED_SECTIONS
                if approvals.get(section) != models.SectionApproval.Status.APPROVED
            ]
            # Phase 2 PII scrub: classify the gate-failure code by
            # string-searching the internally-constructed exception
            # message (commit_reviewed_state raises ValueError with
            # advisor-friendly text, not Bedrock content), but the
            # response body uses the structured `friendly_message` for
            # the `detail` slot so we can't accidentally leak future
            # exception bodies that originate from a real-PII path.
            reason_code = "unknown"
            # PII-safe-classifier: commit_reviewed_state raises with
            # internally-constructed messages (not Bedrock content).
            classifier_text = str(exc)
            if "engine-ready" in classifier_text:
                reason_code = "engine_not_ready"
            elif "construction-ready" in classifier_text:
                reason_code = "construction_not_ready"
            elif "Required review sections" in classifier_text:
                reason_code = "sections_not_approved"
            return Response(
                safe_response_payload(
                    exc,
                    code=reason_code,
                    readiness=workspace.readiness,
                    missing_approvals=missing_approvals,
                    required_sections=list(ENGINE_REQUIRED_SECTIONS),
                ),
                status=400,
            )
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
        "portfolio_runs__cma_snapshot",
        "portfolio_runs__link_recommendation_rows",
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
        # Direct query bypasses any cached OneToOne relationship state on
        # the user instance — APIClient.force_authenticate keeps the same
        # User object across requests, so an instance-level fields_cache
        # could otherwise return stale "DoesNotExist".
        profile = models.AdvisorProfile.objects.filter(user=user).first()
        return {
            "authenticated": True,
            "csrf_token": get_token(request),
            "user": {
                "email": user.email or user.get_username(),
                "name": user.get_full_name() or user.get_username(),
                "role": role_for_user(user),
                "team": user_team_slug(user),
                "engine_enabled": getattr(settings, "MP20_ENGINE_ENABLED", True),
                "disclaimer_acknowledged_at": (
                    profile.disclaimer_acknowledged_at.isoformat()
                    if profile and profile.disclaimer_acknowledged_at
                    else None
                ),
                "disclaimer_acknowledged_version": (
                    profile.disclaimer_acknowledged_version if profile else ""
                ),
                "tour_completed_at": (
                    profile.tour_completed_at.isoformat()
                    if profile and profile.tour_completed_at
                    else None
                ),
            },
        }
    return {"authenticated": False, "csrf_token": get_token(request), "user": None}


def _actor(request) -> str:  # noqa: ANN001
    if getattr(request, "user", None) and request.user.is_authenticated:
        return request.user.get_username()
    return "phase_one_admin"


def _record_portfolio_event(
    *,
    event_type: str,
    portfolio_run: models.PortfolioRun | None = None,
    household: models.Household | None = None,
    actor: str = "system",
    reason_code: str = "",
    note: str = "",
    metadata: dict | None = None,
) -> models.PortfolioRunEvent:
    return models.PortfolioRunEvent.objects.create(
        portfolio_run=portfolio_run,
        household=household or (portfolio_run.household if portfolio_run else None),
        event_type=event_type,
        actor=actor,
        reason_code=reason_code,
        note=note,
        metadata=metadata or {},
    )


def _attach_goal_risk_explainability(
    payload: dict,
    *,
    input_snapshot: dict,
    cma_snapshot: models.CMASnapshot,
    cma_hash: str,
) -> None:
    goals = {goal["id"]: goal for goal in input_snapshot.get("goals", [])}
    accounts = {account["id"]: account for account in input_snapshot.get("accounts", [])}
    household = input_snapshot.get("household", {})
    for recommendation in payload.get("link_recommendations", []):
        goal = goals.get(recommendation.get("goal_id"), {})
        account = accounts.get(recommendation.get("account_id"), {})
        explanation = recommendation.setdefault("explanation", {})
        explanation["goal_risk_audit"] = {
            "scale": "1-5",
            "household_risk_score": household.get("household_risk_score"),
            "goal_risk_score": recommendation.get("goal_risk_score"),
            "frontier_percentile": recommendation.get("frontier_percentile"),
            "goal_inputs": {
                "goal_id": recommendation.get("goal_id"),
                "goal_name": recommendation.get("goal_name") or goal.get("name"),
                "target_date": goal.get("target_date"),
                "horizon_years": recommendation.get("horizon_years"),
                "necessity_score": goal.get("necessity_score"),
            },
            "account_link": {
                "link_id": recommendation.get("link_id"),
                "account_id": recommendation.get("account_id"),
                "account_type": recommendation.get("account_type") or account.get("type"),
                "allocated_amount": recommendation.get("allocated_amount"),
            },
            "cma": {
                "snapshot_id": cma_snapshot.external_id,
                "version": cma_snapshot.version,
                "hash": cma_hash,
            },
            "constraints": [
                "MP2.0 1-5 risk scale",
                "Goal risk maps to an efficient-frontier percentile",
                "Portfolio run uses committed construction data only",
            ],
            "warnings": recommendation.get("warnings", []),
        }


def _portfolio_provenance_hashes(household: models.Household) -> tuple[str, str, list[str]]:
    workspace = household.review_workspaces.order_by("-updated_at", "-created_at").first()
    if workspace is None:
        return "", "", ["synthetic_or_seeded_missing_provenance"]
    if workspace.data_origin == models.ReviewWorkspace.DataOrigin.REAL_DERIVED:
        if (
            workspace.status != models.ReviewWorkspace.Status.COMMITTED
            or not workspace.reviewed_state
        ):
            raise ValueError("Real-derived households require committed reviewed-state provenance.")
    reviewed_state_hash = _hash_json(workspace.reviewed_state or {})
    approval_snapshot_hash = _hash_json(
        {
            "workspace_id": workspace.external_id,
            "status": workspace.status,
            "data_origin": workspace.data_origin,
            "readiness": workspace.readiness or {},
        }
    )
    warnings = []
    if workspace.data_origin == models.ReviewWorkspace.DataOrigin.SYNTHETIC:
        warnings.append("synthetic_missing_real_derived_provenance")
    return reviewed_state_hash, approval_snapshot_hash, warnings


def _portfolio_run_verification(
    run: models.PortfolioRun,
    *,
    input_hash: str | None = None,
    output_hash: str | None = None,
    cma_hash: str | None = None,
    run_signature: str | None = None,
) -> dict:
    actual_input_hash = _hash_json(run.input_snapshot)
    actual_output_hash = _hash_json(run.output)
    actual_cma_hash = _cma_input_hash(run.cma_snapshot)
    expected_input_hash = input_hash or run.input_hash
    expected_output_hash = output_hash or run.output_hash
    expected_cma_hash = cma_hash or run.cma_hash
    expected_run_signature = run_signature or run.run_signature
    checks = {
        "input_hash_matches": actual_input_hash == expected_input_hash == run.input_hash,
        "output_hash_matches": actual_output_hash == expected_output_hash == run.output_hash,
        "cma_hash_matches": actual_cma_hash == expected_cma_hash == run.cma_hash,
        "run_signature_matches": run.run_signature == expected_run_signature,
        "schema_version_matches": (run.output or {}).get("schema_version")
        == "engine_output.link_first.v2",
    }
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "stored_hashes": {
            "input_hash": run.input_hash,
            "output_hash": run.output_hash,
            "cma_hash": run.cma_hash,
            "run_signature": run.run_signature,
        },
        "actual_hashes": {
            "input_hash": actual_input_hash,
            "output_hash": actual_output_hash,
            "cma_hash": actual_cma_hash,
        },
    }


def _reusable_current_run(
    household: models.Household,
    run_signature: str,
) -> models.PortfolioRun | None:
    runs = list(
        models.PortfolioRun.objects.filter(household=household)
        .select_related("household", "cma_snapshot")
        .prefetch_related("events")
        .order_by("-created_at", "-id")
    )
    if not runs:
        return None
    current_run = runs[0]
    duplicate_same_signature = [
        run
        for run in runs[1:]
        if run.run_signature == current_run.run_signature and _run_is_reusable(run)
    ]
    if duplicate_same_signature and _run_is_reusable(current_run):
        raise ValueError("Duplicate or ambiguous current portfolio run lifecycle state.")
    if not _run_is_reusable(current_run):
        return None
    if current_run.run_signature != run_signature:
        return None
    if (current_run.output or {}).get("schema_version") != "engine_output.link_first.v2":
        return None
    return current_run


def _latest_reusable_run_was_declined(household: models.Household) -> bool:
    latest = (
        household.portfolio_runs.order_by("-created_at", "-id").prefetch_related("events").first()
    )
    if latest is None:
        return False
    return models.PortfolioRunEvent.EventType.ADVISOR_DECLINED in _run_event_types(latest)


def _record_current_run_invalidations(
    queryset,
    *,
    event_type: str,
    actor: str,
    reason_code: str,
    metadata: dict,
) -> int:
    current_runs = _current_reusable_runs(queryset)
    count = 0
    for run in current_runs:
        if run.events.filter(event_type=event_type, reason_code=reason_code).exists():
            continue
        _record_portfolio_event(
            event_type=event_type,
            portfolio_run=run,
            household=run.household,
            actor=actor,
            reason_code=reason_code,
            metadata={
                **metadata,
                "run_id": run.external_id,
                "household_id": run.household.external_id,
            },
        )
        count += 1
    return count


def _current_reusable_runs(queryset) -> list[models.PortfolioRun]:  # noqa: ANN001
    current_by_household: dict[int, models.PortfolioRun] = {}
    seen_households: set[int] = set()
    runs = (
        queryset.select_related("household", "cma_snapshot")
        .prefetch_related("events")
        .order_by("household_id", "-created_at", "-id")
    )
    for run in runs:
        if run.household_id in seen_households:
            continue
        seen_households.add(run.household_id)
        if _run_is_reusable(run):
            current_by_household[run.household_id] = run
    return list(current_by_household.values())


def _run_is_reusable(run: models.PortfolioRun) -> bool:
    event_types = _run_event_types(run)
    terminal_events = {
        models.PortfolioRunEvent.EventType.ADVISOR_DECLINED,
        models.PortfolioRunEvent.EventType.INVALIDATED_BY_CMA,
        models.PortfolioRunEvent.EventType.INVALIDATED_BY_HOUSEHOLD_CHANGE,
        models.PortfolioRunEvent.EventType.HASH_MISMATCH,
    }
    return not bool(event_types & terminal_events)


def _run_event_types(run: models.PortfolioRun) -> set[str]:
    return {event.event_type for event in run.events.all()}


def _sanitized_portfolio_audit_export(
    run: models.PortfolioRun,
    verification: dict,
) -> dict:
    output = run.output or {}
    recommendations = []
    for recommendation in output.get("link_recommendations") or []:
        comparison = recommendation.get("current_comparison") or {}
        recommendations.append(
            {
                "link_id": recommendation.get("link_id"),
                "goal_id": recommendation.get("goal_id"),
                "account_id": recommendation.get("account_id"),
                "goal_risk_score": recommendation.get("goal_risk_score"),
                "frontier_percentile": recommendation.get("frontier_percentile"),
                "allocated_amount": recommendation.get("allocated_amount"),
                "warnings": recommendation.get("warnings") or [],
                "current_comparison": {
                    "status": comparison.get("status"),
                    "reason": comparison.get("reason"),
                    "unmapped_holdings": comparison.get("unmapped_holdings") or [],
                },
            }
        )
    return {
        "schema_version": "portfolio_run_audit_export.v2",
        "run_id": run.external_id,
        "household_id": run.household.external_id,
        "status": PortfolioRunSummarySerializer().get_status(run),
        "verification": verification,
        "hashes": {
            "input_hash": run.input_hash,
            "output_hash": run.output_hash,
            "cma_hash": run.cma_hash,
            "reviewed_state_hash": run.reviewed_state_hash,
            "approval_snapshot_hash": run.approval_snapshot_hash,
            "run_signature": run.run_signature,
        },
        "manifest": output.get("run_manifest") or {},
        "diagnostics": {
            "warnings": output.get("warnings") or [],
            "recommendations": recommendations,
        },
        "lifecycle_events": [
            {
                "event_type": event.event_type,
                "actor": event.actor,
                "reason_code": event.reason_code,
                "note": event.note,
                "metadata": event.metadata,
                "created_at": event.created_at,
            }
            for event in run.events.order_by("created_at", "id")
        ],
    }


def _cma_input_hash(snapshot: models.CMASnapshot) -> str:
    return _hash_json(to_engine_cma(snapshot).model_dump(mode="json"))


def _validate_v2_manifest(manifest: dict) -> None:
    required_keys = {
        "schema_version",
        "engine_output_schema",
        "model_version",
        "method",
        "as_of_date",
        "household_id",
        "cma_snapshot_id",
        "cma_version",
        "risk_mapping",
        "optimizer_eligible_fund_ids",
        "whole_portfolio_fund_ids",
        "goal_account_link_ids",
        "input_hash",
        "cma_hash",
        "reviewed_state_hash",
        "approval_snapshot_hash",
        "run_signature",
    }
    missing = sorted(key for key in required_keys if key not in manifest)
    if missing:
        raise ValueError(f"Missing required v2 manifest inputs: {', '.join(missing)}.")
    if manifest.get("engine_output_schema") != "engine_output.link_first.v2":
        raise ValueError("Portfolio run manifest must reference engine_output.link_first.v2.")
    if not manifest.get("optimizer_eligible_fund_ids"):
        raise ValueError("Portfolio run manifest must include optimizer-eligible funds.")
    if not manifest.get("goal_account_link_ids"):
        raise ValueError("Portfolio run manifest must include goal-account link ids.")


@transaction.atomic
def _clone_cma_snapshot(source: models.CMASnapshot, user) -> models.CMASnapshot:  # noqa: ANN001
    last_snapshot = models.CMASnapshot.objects.order_by("-version").first()
    version = (last_snapshot.version + 1) if last_snapshot else 1
    snapshot = models.CMASnapshot.objects.create(
        name=DEFAULT_CMA_NAME,
        version=version,
        status=models.CMASnapshot.Status.DRAFT,
        source=source.source,
        notes="",
        created_by=user,
    )
    for fund in source.fund_assumptions.all():
        models.CMAFundAssumption.objects.create(
            snapshot=snapshot,
            fund_id=fund.fund_id,
            name=fund.name,
            expected_return=fund.expected_return,
            volatility=fund.volatility,
            optimizer_eligible=fund.optimizer_eligible,
            is_whole_portfolio=fund.is_whole_portfolio,
            display_order=fund.display_order,
            aliases=fund.aliases,
            asset_class_weights=fund.asset_class_weights,
            geography_weights=fund.geography_weights,
            tax_drag=fund.tax_drag,
        )
    for correlation in source.correlations.all():
        models.CMACorrelation.objects.create(
            snapshot=snapshot,
            row_fund_id=correlation.row_fund_id,
            col_fund_id=correlation.col_fund_id,
            correlation=correlation.correlation,
        )
    return snapshot


@transaction.atomic
def _apply_cma_patch(snapshot: models.CMASnapshot, data) -> None:  # noqa: ANN001
    changed_fields: list[str] = []
    for field in ("notes",):
        if field in data:
            setattr(snapshot, field, str(data.get(field) or ""))
            changed_fields.append(field)
    if changed_fields:
        snapshot.save(update_fields=[*changed_fields, "updated_at"])

    fund_payloads = data.get("fund_assumptions")
    if fund_payloads is not None:
        if not isinstance(fund_payloads, list):
            raise ValueError("fund_assumptions must be a list.")
        existing = {fund.fund_id: fund for fund in snapshot.fund_assumptions.all()}
        payload_ids = [
            str(fund_payload.get("fund_id") or fund_payload.get("id") or "")
            for fund_payload in fund_payloads
        ]
        if "" in payload_ids or len(payload_ids) != len(set(payload_ids)):
            raise ValueError("fund_assumptions must include unique fund_id values.")
        if set(payload_ids) != set(existing):
            raise ValueError("fund_assumptions must include every existing CMA fund exactly once.")
        for index, fund_payload in enumerate(fund_payloads):
            fund_id = str(fund_payload.get("fund_id") or fund_payload.get("id") or "")
            fund = existing.get(fund_id)
            if fund is None:
                raise ValueError(f"Unknown CMA fund {fund_id}.")
            fund.name = str(fund_payload.get("name") or fund.name or fund_id)
            fund.expected_return = _decimal_payload(
                fund_payload.get("expected_return"),
                fund.expected_return,
                field=f"{fund_id}.expected_return",
            )
            fund.volatility = _decimal_payload(
                fund_payload.get("volatility"),
                fund.volatility,
                field=f"{fund_id}.volatility",
            )
            fund.optimizer_eligible = _bool_payload(
                fund_payload.get("optimizer_eligible", fund.optimizer_eligible)
            )
            fund.is_whole_portfolio = _bool_payload(
                fund_payload.get("is_whole_portfolio", fund.is_whole_portfolio)
            )
            fund.display_order = int(fund_payload.get("display_order", index))
            if isinstance(fund_payload.get("aliases"), list):
                fund.aliases = [str(alias) for alias in fund_payload["aliases"]]
            if isinstance(fund_payload.get("asset_class_weights"), dict):
                fund.asset_class_weights = fund_payload["asset_class_weights"]
            if isinstance(fund_payload.get("geography_weights"), dict):
                fund.geography_weights = fund_payload["geography_weights"]
            if isinstance(fund_payload.get("tax_drag"), dict):
                fund.tax_drag = fund_payload["tax_drag"]
            fund.save()

    correlation_payloads = data.get("correlations")
    if correlation_payloads is not None:
        if not isinstance(correlation_payloads, list):
            raise ValueError("correlations must be a list.")
        _validate_correlation_payloads(snapshot, correlation_payloads)
        snapshot.correlations.all().delete()
        for item in correlation_payloads:
            row_id = str(item.get("row_fund_id") or "")
            col_id = str(item.get("col_fund_id") or "")
            models.CMACorrelation.objects.create(
                snapshot=snapshot,
                row_fund_id=row_id,
                col_fund_id=col_id,
                correlation=_decimal_payload(
                    item.get("correlation"), Decimal("0"), field=f"{row_id}:{col_id}"
                ),
            )
    if hasattr(snapshot, "_prefetched_objects_cache"):
        snapshot._prefetched_objects_cache = {}
    _validate_cma_snapshot(snapshot)


def _decimal_payload(value, fallback: Decimal, *, field: str) -> Decimal:  # noqa: ANN001
    if value is None:
        return fallback
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field} must be numeric.") from exc
    if not result.is_finite():
        raise ValueError(f"{field} must be finite.")
    return result


def _bool_payload(value) -> bool:  # noqa: ANN001
    if isinstance(value, bool):
        return value
    raise ValueError("Boolean CMA fields must be true or false.")


def _validate_correlation_payloads(
    snapshot: models.CMASnapshot, correlation_payloads: list[dict]
) -> None:
    fund_ids = [fund.fund_id for fund in snapshot.fund_assumptions.all()]
    expected_pairs = {(row_id, col_id) for row_id in fund_ids for col_id in fund_ids}
    seen_pairs: set[tuple[str, str]] = set()
    values: dict[tuple[str, str], Decimal] = {}
    for item in correlation_payloads:
        row_id = str(item.get("row_fund_id") or "")
        col_id = str(item.get("col_fund_id") or "")
        pair = (row_id, col_id)
        if pair in seen_pairs:
            raise ValueError(f"Duplicate correlation cell {row_id}:{col_id}.")
        seen_pairs.add(pair)
        if pair not in expected_pairs:
            raise ValueError(f"Unknown correlation cell {row_id}:{col_id}.")
        value = _decimal_payload(item.get("correlation"), Decimal("0"), field=f"{row_id}:{col_id}")
        if value < Decimal("-1") or value > Decimal("1"):
            raise ValueError("Correlations must be between -1 and 1.")
        values[pair] = value
    if seen_pairs != expected_pairs:
        raise ValueError("correlations must include the full square fund matrix.")
    for fund_id in fund_ids:
        if abs(values[(fund_id, fund_id)] - Decimal("1")) > Decimal("0.00001"):
            raise ValueError("Correlation diagonal values must be 1.")
    for row_id in fund_ids:
        for col_id in fund_ids:
            if abs(values[(row_id, col_id)] - values[(col_id, row_id)]) > Decimal("0.00001"):
                raise ValueError("Correlation matrix must be symmetric.")


def _validate_cma_snapshot(snapshot: models.CMASnapshot) -> None:
    funds = list(snapshot.fund_assumptions.all())
    if len(funds) < 2:
        raise ValueError("CMA snapshot must include at least two funds.")
    eligible_funds = [fund for fund in funds if fund.optimizer_eligible]
    if len(eligible_funds) < 2:
        raise ValueError("At least two optimizer-eligible funds are required.")
    for fund in funds:
        if fund.expected_return <= Decimal("-1") or fund.expected_return >= Decimal("1"):
            raise ValueError(f"{fund.name} expected return must be between -100% and 100%.")
        if fund.volatility <= Decimal("0") or fund.volatility >= Decimal("2"):
            raise ValueError(f"{fund.name} volatility must be between 0% and 200%.")
    correlations = _snapshot_correlation_lookup(snapshot)
    fund_ids = [fund.fund_id for fund in funds]
    expected_pairs = {(row_id, col_id) for row_id in fund_ids for col_id in fund_ids}
    if set(correlations) != expected_pairs:
        raise ValueError("CMA correlations must include the full square fund matrix.")
    for fund_id in fund_ids:
        if abs(correlations[(fund_id, fund_id)] - Decimal("1")) > Decimal("0.00001"):
            raise ValueError("Correlation diagonal values must be 1.")
    for row_id in fund_ids:
        for col_id in fund_ids:
            value = correlations[(row_id, col_id)]
            if value < Decimal("-1") or value > Decimal("1"):
                raise ValueError("Correlations must be between -1 and 1.")
            if abs(value - correlations[(col_id, row_id)]) > Decimal("0.00001"):
                raise ValueError("Correlation matrix must be symmetric.")
    matrix = _snapshot_matrix(eligible_funds, correlations)
    try:
        compute_frontier(
            [float(fund.expected_return) for fund in eligible_funds],
            [float(fund.volatility) for fund in eligible_funds],
            matrix,
        )
    except ValueError as exc:
        if "positive definite" in str(exc):
            raise CMAValidationError(
                "correlation matrix must be positive definite",
                code="correlation_matrix_not_positive_definite",
                diagnostics=_positive_definite_diagnostics(snapshot, eligible_funds, correlations),
            ) from exc
        raise


def _snapshot_correlation_lookup(snapshot: models.CMASnapshot) -> dict[tuple[str, str], Decimal]:
    return {
        (item.row_fund_id, item.col_fund_id): item.correlation
        for item in snapshot.correlations.all()
    }


def _snapshot_matrix(
    funds: list[models.CMAFundAssumption],
    correlations: dict[tuple[str, str], Decimal],
) -> list[list[float]]:
    return [
        [float(correlations[(row.fund_id, column.fund_id)]) for column in funds] for row in funds
    ]


def _positive_definite_diagnostics(
    snapshot: models.CMASnapshot,
    eligible_funds: list[models.CMAFundAssumption],
    correlations: dict[tuple[str, str], Decimal],
) -> dict:
    matrix = _snapshot_matrix(eligible_funds, correlations)
    min_cholesky_pivot, failing_index = _cholesky_min_pivot(matrix)
    baseline = (
        models.CMASnapshot.objects.filter(status=models.CMASnapshot.Status.ACTIVE)
        .exclude(pk=snapshot.pk)
        .prefetch_related("fund_assumptions", "correlations")
        .first()
    )
    changed_pairs = []
    if baseline is not None:
        baseline_correlations = _snapshot_correlation_lookup(baseline)
        fund_by_id = {fund.fund_id: fund for fund in eligible_funds}
        for row_index, row in enumerate(eligible_funds):
            for column in eligible_funds[row_index + 1 :]:
                pair = (row.fund_id, column.fund_id)
                baseline_value = baseline_correlations.get(pair)
                if baseline_value is None:
                    continue
                current_value = correlations[pair]
                if abs(current_value - baseline_value) > Decimal("0.00001"):
                    changed_pairs.append(
                        {
                            "row_fund_id": row.fund_id,
                            "row_fund_name": fund_by_id[row.fund_id].name,
                            "col_fund_id": column.fund_id,
                            "col_fund_name": fund_by_id[column.fund_id].name,
                            "current": str(current_value),
                            "suggested": str(baseline_value),
                            "source": "active_snapshot",
                            "source_snapshot_id": baseline.external_id,
                            "source_version": baseline.version,
                        }
                    )
    changed_pairs.sort(
        key=lambda item: abs(Decimal(item["current"]) - Decimal(item["suggested"])),
        reverse=True,
    )
    return {
        "eligible_fund_ids": [fund.fund_id for fund in eligible_funds],
        "min_cholesky_pivot": min_cholesky_pivot,
        "failing_fund_id": eligible_funds[failing_index].fund_id
        if failing_index is not None
        else "",
        "failing_fund_name": eligible_funds[failing_index].name
        if failing_index is not None
        else "",
        "suggested_pairs": changed_pairs[:8],
    }


def _cholesky_min_pivot(matrix: list[list[float]]) -> tuple[float, int | None]:
    size = len(matrix)
    lower = [[0.0 for _ in range(size)] for _ in range(size)]
    min_pivot = float("inf")
    for row in range(size):
        for column in range(row + 1):
            subtotal = sum(lower[row][k] * lower[column][k] for k in range(column))
            if row == column:
                pivot = matrix[row][row] - subtotal
                min_pivot = min(min_pivot, pivot)
                if pivot <= 1e-10:
                    return pivot, row
                lower[row][column] = pivot**0.5
            else:
                lower[row][column] = (matrix[row][column] - subtotal) / lower[column][column]
    return min_pivot, None


def _cma_frontier_payload(snapshot: models.CMASnapshot) -> dict:
    _validate_cma_snapshot(snapshot)
    funds = list(snapshot.fund_assumptions.all())
    eligible_funds = [fund for fund in funds if fund.optimizer_eligible]
    correlations = _snapshot_correlation_lookup(snapshot)
    matrix = _snapshot_matrix(eligible_funds, correlations)
    frontier = compute_frontier(
        [float(fund.expected_return) for fund in eligible_funds],
        [float(fund.volatility) for fund in eligible_funds],
        matrix,
    )
    fund_points = [
        {
            "id": fund.fund_id,
            "name": fund.name,
            "expected_return": float(fund.expected_return),
            "volatility": float(fund.volatility),
            "optimizer_eligible": fund.optimizer_eligible,
            "is_whole_portfolio": fund.is_whole_portfolio,
            "aliases": fund.aliases,
            "asset_class_weights": fund.asset_class_weights,
            "geography_weights": fund.geography_weights,
        }
        for fund in funds
    ]
    efficient_points = [
        {
            "expected_return": point.expected_return,
            "volatility": point.volatility,
            "weights": point.weights,
        }
        for point in frontier.efficient
    ]
    returns = [item["expected_return"] for item in fund_points] + [
        item["expected_return"] for item in efficient_points
    ]
    volatilities = [item["volatility"] for item in fund_points] + [
        item["volatility"] for item in efficient_points
    ]
    return {
        "snapshot_id": snapshot.external_id,
        "funds": fund_points,
        "fund_points": fund_points,
        "efficient": efficient_points,
        "bounds": {
            "expected_return_min": min(returns),
            "expected_return_max": max(returns),
            "volatility_min": min(volatilities),
            "volatility_max": max(volatilities),
        },
        "eligible_fund_count": len(eligible_funds),
        "whole_portfolio_fund_count": sum(fund.is_whole_portfolio for fund in funds),
    }


def _cma_audit_payload(snapshot: models.CMASnapshot) -> dict:
    return {
        "snapshot_id": snapshot.external_id,
        "name": snapshot.name,
        "version": snapshot.version,
        "status": snapshot.status,
        "source": snapshot.source,
        "notes": snapshot.notes,
        "funds": [
            {
                "fund_id": fund.fund_id,
                "expected_return": str(fund.expected_return),
                "volatility": str(fund.volatility),
                "optimizer_eligible": fund.optimizer_eligible,
                "is_whole_portfolio": fund.is_whole_portfolio,
                "display_order": fund.display_order,
                "aliases": fund.aliases,
                "asset_class_weights": fund.asset_class_weights,
                "geography_weights": fund.geography_weights,
            }
            for fund in snapshot.fund_assumptions.all()
        ],
        "correlations": [
            {
                "row_fund_id": cell.row_fund_id,
                "col_fund_id": cell.col_fund_id,
                "correlation": str(cell.correlation),
            }
            for cell in snapshot.correlations.all()
        ],
    }


def _cma_diff(before: dict, after: dict) -> dict:
    field_diffs = {
        field: {"before": before.get(field), "after": after.get(field)}
        for field in ("name", "source", "notes", "status")
        if before.get(field) != after.get(field)
    }
    before_funds = {item["fund_id"]: item for item in before["funds"]}
    after_funds = {item["fund_id"]: item for item in after["funds"]}
    fund_diffs = []
    for fund_id, after_fund in after_funds.items():
        before_fund = before_funds.get(fund_id, {})
        changed = {
            field: {"before": before_fund.get(field), "after": after_fund.get(field)}
            for field in (
                "expected_return",
                "volatility",
                "optimizer_eligible",
                "is_whole_portfolio",
                "display_order",
                "aliases",
                "asset_class_weights",
                "geography_weights",
            )
            if before_fund.get(field) != after_fund.get(field)
        }
        if changed:
            fund_diffs.append({"fund_id": fund_id, "fields": changed})

    before_correlations = {
        (item["row_fund_id"], item["col_fund_id"]): item["correlation"]
        for item in before["correlations"]
    }
    after_correlations = {
        (item["row_fund_id"], item["col_fund_id"]): item["correlation"]
        for item in after["correlations"]
    }
    changed_pairs = []
    for (row_id, col_id), after_value in sorted(after_correlations.items()):
        if row_id >= col_id:
            continue
        before_value = before_correlations.get((row_id, col_id))
        if before_value != after_value:
            changed_pairs.append(
                {
                    "row_fund_id": row_id,
                    "col_fund_id": col_id,
                    "before": before_value,
                    "after": after_value,
                }
            )

    return {
        "field_diffs": field_diffs,
        "fund_diffs": fund_diffs,
        "correlation_pair_diffs": changed_pairs[:25],
        "correlation_pair_diff_count": len(changed_pairs),
    }


def _audit_event_payload(event: AuditEvent) -> dict:
    metadata = event.metadata or {}
    return {
        "id": event.id,
        "actor": event.actor,
        "action": event.action,
        "entity_type": event.entity_type,
        "entity_id": event.entity_id,
        "created_at": event.created_at,
        "metadata": {
            key: metadata.get(key)
            for key in (
                "version",
                "source_version",
                "source_snapshot_id",
                "snapshot_name",
                "snapshot_hash",
                "before_hash",
                "after_hash",
                "updated_fields",
                "field_diffs",
                "fund_diffs",
                "correlation_pair_diffs",
                "correlation_pair_diff_count",
                "publish_note",
                "stale_portfolio_run_count",
                "fund_count",
            )
            if key in metadata
        },
    }


def _cma_validation_error_payload(exc: ValueError) -> dict:
    # CMA validation errors are analyst-facing on non-PII data (market
    # assumptions, not client docs). The internally-constructed
    # `CMAValidationError.detail` is intentionally specific so the
    # analyst can fix the input. Phase 2 routes through
    # `safe_response_payload` for non-CMA-typed exceptions only;
    # CMAValidationError keeps its rich detail for the structured
    # diagnostics payload analysts depend on.
    if isinstance(exc, CMAValidationError):
        return {
            "detail": exc.detail,  # internally-constructed; not a Bedrock surface
            "code": exc.code,
            "diagnostics": exc.diagnostics,
        }
    return safe_response_payload(exc)


def _hash_json(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
