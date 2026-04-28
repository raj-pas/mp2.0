from __future__ import annotations

from django.shortcuts import get_object_or_404
from engine import STEADYHAND_PURE_SLEEVES, optimize
from rest_framework.response import Response
from rest_framework.views import APIView

from web.api import models
from web.api.engine_adapter import to_engine_household
from web.api.serializers import HouseholdDetailSerializer, HouseholdListSerializer
from web.audit.writer import record_event


class SessionView(APIView):
    authentication_classes = []

    def get(self, request):  # noqa: ANN001
        record_event(
            action="session_viewed",
            entity_type="session",
            actor=_actor(request),
            metadata={"phase": "phase_1"},
        )
        return Response(
            {
                "user": {
                    "email": "admin@mp20.local",
                    "name": "MP2.0 Local Admin",
                    "role": "phase_one_admin",
                }
            }
        )


class ClientListView(APIView):
    def get(self, request):  # noqa: ANN001
        households = models.Household.objects.prefetch_related("goals", "accounts")
        record_event(action="client_list_viewed", entity_type="household", actor=_actor(request))
        return Response(HouseholdListSerializer(households, many=True).data)


class ClientDetailView(APIView):
    def get(self, request, household_id: str):  # noqa: ANN001
        household = get_object_or_404(_household_queryset(), external_id=household_id)
        record_event(
            action="client_detail_viewed",
            entity_type="household",
            entity_id=household.external_id,
            actor=_actor(request),
        )
        return Response(HouseholdDetailSerializer(household).data)


class GeneratePortfolioView(APIView):
    def post(self, request, household_id: str):  # noqa: ANN001
        household = get_object_or_404(_household_queryset(), external_id=household_id)
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


def _household_queryset():
    return models.Household.objects.prefetch_related(
        "members",
        "goals__account_allocations__account",
        "accounts__holdings",
        "accounts__owner_person",
    )


def _actor(request) -> str:  # noqa: ANN001
    if getattr(request, "user", None) and request.user.is_authenticated:
        return request.user.get_username()
    return "phase_one_admin"
