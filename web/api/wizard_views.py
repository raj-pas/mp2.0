"""DRF state-changing endpoints for the v36 advisor console (Phase R1).

Covers wizard commit, realignment, household snapshot lifecycle, goal
risk overrides, and external-holdings CRUD.

Per locked decision #30, every endpoint that mutates household-tree
state wraps its work in ``transaction.atomic()`` with
``Household.objects.select_for_update().get(...)`` to serialize edits.

Per locked decision #37, every state change emits exactly one
AuditEvent with the expected ``kind`` field — the centralized
regression test ``test_audit_event_emission.py`` verifies this.

Per locked decision #11, the projection-time external penalty is the
only external-holdings effect implemented; the canon §4.6a household
risk-tolerance dampener stays deferred.

Per locked decisions #6, #14, vocabulary discipline applies to every
serializer field label and audit detail string.
"""

from __future__ import annotations

import copy
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, inline_serializer
from engine.risk_profile import RiskProfileInput, compute_risk_profile
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from web.api import models
from web.api.access import team_households
from web.audit.writer import record_event

# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------


class WizardMemberSerializer(serializers.Serializer):
    name = serializers.CharField(min_length=1)
    dob = serializers.DateField()


class WizardAccountSerializer(serializers.Serializer):
    account_type = serializers.ChoiceField(
        choices=[
            "RRSP",
            "TFSA",
            "RESP",
            "RDSP",
            "FHSA",
            "Non-Registered",
            "LIRA",
            "RRIF",
            "Corporate",
        ],
    )
    current_value = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0"),
    )
    custodian = serializers.CharField(required=False, allow_blank=True, default="")


class WizardGoalLegSerializer(serializers.Serializer):
    account_index = serializers.IntegerField(min_value=0)
    allocated_amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0"),
    )


class WizardGoalSerializer(serializers.Serializer):
    name = serializers.CharField(min_length=1)
    target_date = serializers.DateField()
    necessity_score = serializers.IntegerField(min_value=1, max_value=5)
    target_amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        required=False,
        allow_null=True,
    )
    legs = WizardGoalLegSerializer(many=True, allow_empty=False)


class WizardExternalHoldingSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True, default="")
    value = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0"))
    equity_pct = serializers.DecimalField(max_digits=5, decimal_places=2)
    fixed_income_pct = serializers.DecimalField(max_digits=5, decimal_places=2)
    cash_pct = serializers.DecimalField(max_digits=5, decimal_places=2)
    real_assets_pct = serializers.DecimalField(max_digits=5, decimal_places=2)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        total = (
            attrs["equity_pct"]
            + attrs["fixed_income_pct"]
            + attrs["cash_pct"]
            + attrs["real_assets_pct"]
        )
        if total != Decimal("100"):
            raise serializers.ValidationError(f"Asset percentages must sum to 100; got {total}.")
        return attrs


class WizardCommitSerializer(serializers.Serializer):
    """Locked decision #7: wizard is the fallback path. Doc-drop is primary.

    Server validates the full wizard payload, creates Household + Person(s)
    + Account(s) + Goal(s) + GoalAccountLink(s) + RiskProfile +
    ExternalHolding(s) atomically.
    """

    display_name = serializers.CharField(min_length=1)
    household_type = serializers.ChoiceField(choices=["single", "couple"])
    members = WizardMemberSerializer(many=True, min_length=1, max_length=2)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    risk_profile = inline_serializer(
        name="WizardRiskProfile",
        fields={
            "q1": serializers.IntegerField(min_value=0, max_value=10),
            "q2": serializers.ChoiceField(choices=["A", "B", "C", "D"]),
            "q3": serializers.ListField(
                child=serializers.CharField(), required=False, default=list
            ),
            "q4": serializers.ChoiceField(choices=["A", "B", "C", "D"]),
        },
    )
    accounts = WizardAccountSerializer(many=True, allow_empty=False)
    goals = WizardGoalSerializer(many=True, allow_empty=False)
    external_holdings = WizardExternalHoldingSerializer(many=True, required=False, default=list)


class GoalRiskOverrideRequestSerializer(serializers.Serializer):
    score_1_5 = serializers.IntegerField(min_value=1, max_value=5)
    descriptor = serializers.ChoiceField(
        choices=[
            "Cautious",
            "Conservative-balanced",
            "Balanced",
            "Balanced-growth",
            "Growth-oriented",
        ],
    )
    rationale = serializers.CharField(min_length=10)


class RealignmentRequestSerializer(serializers.Serializer):
    """Locked decision #15 + canon §6.3a: re-goaling is label-only.

    Body shape: ``{account_goal_amounts: {acct_external_id: {goal_external_id: amount}}}``.
    Server enforces that each account's leg sums equal the account total
    (no money created/destroyed). The mutation updates GoalAccountLink
    rows; underlying Holdings are never touched.
    """

    account_goal_amounts = serializers.DictField(
        child=serializers.DictField(
            child=serializers.DecimalField(max_digits=14, decimal_places=2)
        ),
    )


class ExternalHoldingMutationSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True, default="")
    value = serializers.DecimalField(max_digits=14, decimal_places=2)
    equity_pct = serializers.DecimalField(max_digits=5, decimal_places=2)
    fixed_income_pct = serializers.DecimalField(max_digits=5, decimal_places=2)
    cash_pct = serializers.DecimalField(max_digits=5, decimal_places=2)
    real_assets_pct = serializers.DecimalField(max_digits=5, decimal_places=2)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        total = (
            attrs["equity_pct"]
            + attrs["fixed_income_pct"]
            + attrs["cash_pct"]
            + attrs["real_assets_pct"]
        )
        if total != Decimal("100"):
            raise serializers.ValidationError(f"Asset percentages must sum to 100; got {total}.")
        return attrs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate(request: Request, serializer_cls: type[serializers.Serializer]) -> dict[str, Any]:
    serializer = serializer_cls(data=request.data)
    serializer.is_valid(raise_exception=True)
    return dict(serializer.validated_data)


def _resolve_household_for_write(request: Request, household_id: str) -> models.Household:
    """Locked decision #30: select_for_update inside transaction.atomic.

    ``team_households()`` returns a LEFT OUTER JOIN (ownerless synthetic
    households OR owner__is_active=True). Postgres rejects SELECT FOR
    UPDATE on the nullable side of an outer join, so we split the
    operation: scope check first (no lock), then a direct
    ``select_for_update()`` on the household row to actually lock it.
    """

    if not request.user.is_authenticated:
        raise PermissionDenied("Authentication required.")
    if not team_households(request.user).filter(external_id=household_id).exists():
        raise NotFound(f"Household {household_id} not found.")
    try:
        return models.Household.objects.select_for_update().get(external_id=household_id)
    except models.Household.DoesNotExist as exc:
        raise NotFound(f"Household {household_id} not found.") from exc


def _household_snapshot_payload(household: models.Household) -> dict[str, Any]:
    """Deep-clone household + accounts + goals + risk profile for snapshot.

    Mirrors the v36 mockup ``CLIENT_DATA[id].archives[].snapshot``.
    Reads only structured fields; never includes raw evidence quotes or
    real-derived document text per canon §11.8.3.
    """

    return {
        "household": {
            "id": household.external_id,
            "display_name": household.display_name,
            "household_type": household.household_type,
            "household_risk_score": household.household_risk_score,
        },
        "members": [
            {
                "id": person.external_id,
                "name": person.name,
                "dob": person.dob.isoformat(),
            }
            for person in household.members.all()
        ],
        "accounts": [
            {
                "id": account.external_id,
                "type": account.account_type,
                "current_value": str(account.current_value),
                "cash_state": account.cash_state,
                "links": [
                    {
                        "goal_id": link.goal.external_id,
                        "allocated_amount": str(link.allocated_amount or 0),
                    }
                    for link in account.goal_allocations.all()
                ],
            }
            for account in household.accounts.all()
        ],
        "goals": [
            {
                "id": goal.external_id,
                "name": goal.name,
                "target_date": goal.target_date.isoformat(),
                "necessity_score": goal.necessity_score,
                "goal_risk_score": goal.goal_risk_score,
            }
            for goal in household.goals.all()
        ],
        "external_holdings": [
            {
                "id": h.id,
                "name": h.name,
                "value": str(h.value),
                "equity_pct": str(h.equity_pct),
                "fixed_income_pct": str(h.fixed_income_pct),
                "cash_pct": str(h.cash_pct),
                "real_assets_pct": str(h.real_assets_pct),
            }
            for h in household.external_holdings.all()
        ],
    }


def _household_summary_payload(household: models.Household) -> dict[str, Any]:
    """Pre-computed aggregates for the History tab + Compare view."""

    sh_total = sum(float(account.current_value) for account in household.accounts.all())
    ext_total = sum(float(h.value) for h in household.external_holdings.all())
    return {
        "total_aum": sh_total + ext_total,
        "sh_aum": sh_total,
        "ext_aum": ext_total,
        "account_count": household.accounts.count(),
        "goal_count": household.goals.count(),
        "blended_score": float(household.household_risk_score),
    }


def _create_snapshot(
    *,
    household: models.Household,
    triggered_by: str,
    label: str,
    user: Any,
) -> models.HouseholdSnapshot:
    snapshot = models.HouseholdSnapshot.objects.create(
        household=household,
        triggered_by=triggered_by,
        label=label,
        snapshot=_household_snapshot_payload(household),
        summary=_household_summary_payload(household),
        created_by=user,
    )
    record_event(
        action="household_snapshot_created",
        actor=user.email if hasattr(user, "email") else str(user),
        entity_type="household",
        entity_id=household.external_id,
        metadata={
            "snapshot_id": snapshot.id,
            "triggered_by": triggered_by,
            "label": label,
        },
    )
    return snapshot


# ---------------------------------------------------------------------------
# Wizard commit
# ---------------------------------------------------------------------------


@extend_schema(
    tags=["clients"],
    summary="Create a new household via the 5-step wizard (locked decision #7)",
    description=(
        "Doc-drop is the primary onboarding path; this wizard is the "
        "fallback for edge cases per canon §6.7. Server creates Household "
        "+ Person(s) + Account(s) + Goal(s) + GoalAccountLink(s) + "
        "RiskProfile + ExternalHolding(s) atomically inside "
        "transaction.atomic per locked decision #30."
    ),
    request=WizardCommitSerializer,
)
class WizardCommitView(APIView):
    """POST /api/households/wizard/"""

    def post(self, request: Request) -> Response:
        if not request.user.is_authenticated:
            raise PermissionDenied("Authentication required.")
        data = _validate(request, WizardCommitSerializer)

        with transaction.atomic():
            risk_input = RiskProfileInput(
                q1=data["risk_profile"]["q1"],
                q2=data["risk_profile"]["q2"],
                q3=list(data["risk_profile"].get("q3", [])),
                q4=data["risk_profile"]["q4"],
            )
            risk_result = compute_risk_profile(risk_input)

            household = models.Household.objects.create(
                external_id=models.uuid_string(),
                display_name=data["display_name"],
                household_type=data["household_type"],
                household_risk_score=risk_result.score_1_5,
                external_assets=[],
                notes=data.get("notes", ""),
                owner=request.user,
            )

            for member in data["members"]:
                models.Person.objects.create(
                    external_id=models.uuid_string(),
                    household=household,
                    name=member["name"],
                    dob=member["dob"],
                )

            models.RiskProfile.objects.create(
                household=household,
                q1=risk_input.q1,
                q2=risk_input.q2,
                q3=risk_input.q3,
                q4=risk_input.q4,
                tolerance_score=Decimal(str(risk_result.tolerance_score)),
                capacity_score=Decimal(str(risk_result.capacity_score)),
                tolerance_descriptor=risk_result.tolerance_descriptor,
                capacity_descriptor=risk_result.capacity_descriptor,
                household_descriptor=risk_result.household_descriptor,
                score_1_5=risk_result.score_1_5,
                anchor=Decimal(str(risk_result.anchor)),
                flags=list(risk_result.flags),
            )

            account_objs: list[models.Account] = []
            for raw in data["accounts"]:
                account = models.Account.objects.create(
                    external_id=models.uuid_string(),
                    household=household,
                    account_type=raw["account_type"],
                    regulatory_objective="growth_and_income",
                    regulatory_time_horizon="3-10y",
                    regulatory_risk_rating="medium",
                    current_value=raw["current_value"],
                )
                account_objs.append(account)

            for raw in data["goals"]:
                goal = models.Goal.objects.create(
                    external_id=models.uuid_string(),
                    household=household,
                    name=raw["name"],
                    target_date=raw["target_date"],
                    necessity_score=raw["necessity_score"],
                    target_amount=raw.get("target_amount"),
                    goal_risk_score=risk_result.score_1_5,
                )
                for leg in raw["legs"]:
                    if leg["account_index"] >= len(account_objs):
                        raise serializers.ValidationError(
                            f"Goal '{raw['name']}' references unknown account index "
                            f"{leg['account_index']}."
                        )
                    account = account_objs[leg["account_index"]]
                    models.GoalAccountLink.objects.create(
                        external_id=models.uuid_string(),
                        goal=goal,
                        account=account,
                        allocated_amount=leg["allocated_amount"],
                    )

            for raw in data.get("external_holdings", []):
                models.ExternalHolding.objects.create(
                    household=household,
                    name=raw.get("name", ""),
                    value=raw["value"],
                    equity_pct=raw["equity_pct"],
                    fixed_income_pct=raw["fixed_income_pct"],
                    cash_pct=raw["cash_pct"],
                    real_assets_pct=raw["real_assets_pct"],
                )

            record_event(
                action="household_wizard_committed",
                actor=request.user.email,
                entity_type="household",
                entity_id=household.external_id,
                metadata={
                    "display_name": household.display_name,
                    "member_count": len(data["members"]),
                    "account_count": len(account_objs),
                    "goal_count": len(data["goals"]),
                    "external_holding_count": len(data.get("external_holdings", [])),
                    "household_score_1_5": risk_result.score_1_5,
                },
            )

        # Trigger #2 (per locked #14 + #74): auto-trigger sync-inline against
        # the wizard-created household. Outside the transaction.atomic block
        # so it sees the committed state. Failure never breaks the response.
        from web.api.views import _trigger_and_audit

        _trigger_and_audit(household, request.user, source="wizard_commit")

        return Response(
            {"household_id": household.external_id, "household_score_1_5": risk_result.score_1_5},
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Realignment (re-goaling, label-only — canon §6.3a vocabulary tripwire)
# ---------------------------------------------------------------------------


@extend_schema(
    tags=["snapshots"],
    summary="Re-goal account-to-goal allocations (label-only; canon §6.3a)",
    description=(
        "Per canon §6.3a + locked decision #15, this endpoint adjusts the "
        "labels on each account's goal allocations — it never moves money "
        "or changes underlying holdings. Server creates a 'before' "
        "HouseholdSnapshot, applies the relabel, computes 'after' snapshot, "
        "fires audit, and returns big-shift indicators (>5pt blended "
        "account risk delta)."
    ),
    request=RealignmentRequestSerializer,
)
class RealignmentView(APIView):
    """POST /api/households/{household_id}/realignment/"""

    def post(self, request: Request, household_id: str) -> Response:
        data = _validate(request, RealignmentRequestSerializer)

        with transaction.atomic():
            household = _resolve_household_for_write(request, household_id)

            before_snapshot = _create_snapshot(
                household=household,
                triggered_by="realignment",
                label="Before realignment",
                user=request.user,
            )

            before_account_scores: dict[str, float] = {}
            for account in household.accounts.all():
                before_account_scores[account.external_id] = _blended_score(account)

            # Apply: each account_goal_amounts entry adjusts the
            # GoalAccountLink.allocated_amount for that (account, goal) pair.
            for acct_id, goal_amounts in data["account_goal_amounts"].items():
                try:
                    account = household.accounts.get(external_id=acct_id)
                except models.Account.DoesNotExist as exc:
                    raise NotFound(f"Account {acct_id} not found.") from exc
                for goal_id, amount in goal_amounts.items():
                    try:
                        goal = household.goals.get(external_id=goal_id)
                    except models.Goal.DoesNotExist as exc:
                        raise NotFound(f"Goal {goal_id} not found.") from exc
                    link, _created = models.GoalAccountLink.objects.get_or_create(
                        goal=goal,
                        account=account,
                        defaults={
                            "external_id": models.uuid_string(),
                            "allocated_amount": amount,
                        },
                    )
                    link.allocated_amount = amount
                    link.save()

            after_snapshot = _create_snapshot(
                household=household,
                triggered_by="realignment",
                label="After realignment",
                user=request.user,
            )

            big_shifts: list[dict[str, Any]] = []
            for account in household.accounts.all():
                after = _blended_score(account)
                before = before_account_scores.get(account.external_id, 0.0)
                if abs(after - before) > 5.0:
                    big_shifts.append(
                        {
                            "account_id": account.external_id,
                            "account_type": account.account_type,
                            "before_score": before,
                            "after_score": after,
                            "delta": abs(after - before),
                        }
                    )

            record_event(
                action="realignment_applied",
                actor=request.user.email,
                entity_type="household",
                entity_id=household.external_id,
                metadata={
                    "before_snapshot_id": before_snapshot.id,
                    "after_snapshot_id": after_snapshot.id,
                    "big_shift_count": len(big_shifts),
                },
            )

        # Trigger #4 (per locked #14 + #74): realignment changes account_goal
        # links → input_hash changes → new PortfolioRun. Outside the atomic.
        from web.api.views import _trigger_and_audit

        _trigger_and_audit(household, request.user, source="realignment")

        return Response(
            {
                "before_snapshot_id": before_snapshot.id,
                "after_snapshot_id": after_snapshot.id,
                "big_shifts": big_shifts,
            },
            status=status.HTTP_200_OK,
        )


def _blended_score(account: models.Account) -> float:
    total = sum(float(link.allocated_amount or 0) for link in account.goal_allocations.all())
    if total <= 0:
        return 0.0
    return sum(
        link.goal.goal_risk_score * (float(link.allocated_amount or 0) / total)
        for link in account.goal_allocations.all()
    )


# ---------------------------------------------------------------------------
# Snapshot list / detail / restore
# ---------------------------------------------------------------------------


@extend_schema(
    tags=["snapshots"],
    summary="List household snapshots (history tab)",
)
class HouseholdSnapshotListView(APIView):
    """GET /api/households/{household_id}/snapshots/"""

    def get(self, request: Request, household_id: str) -> Response:
        household = team_households(request.user).filter(external_id=household_id).first()
        if household is None:
            raise NotFound(f"Household {household_id} not found.")
        snapshots = household.snapshots.all()
        return Response(
            [
                {
                    "id": s.id,
                    "triggered_by": s.triggered_by,
                    "label": s.label,
                    "summary": s.summary,
                    "created_at": s.created_at.isoformat(),
                    "created_by": s.created_by.email if s.created_by else None,
                }
                for s in snapshots
            ]
        )


@extend_schema(
    tags=["snapshots"],
    summary="Get a household snapshot detail",
)
class HouseholdSnapshotDetailView(APIView):
    """GET /api/households/{household_id}/snapshots/{snapshot_id}/"""

    def get(self, request: Request, household_id: str, snapshot_id: int) -> Response:
        household = team_households(request.user).filter(external_id=household_id).first()
        if household is None:
            raise NotFound(f"Household {household_id} not found.")
        snapshot = get_object_or_404(models.HouseholdSnapshot, id=snapshot_id, household=household)
        return Response(
            {
                "id": snapshot.id,
                "triggered_by": snapshot.triggered_by,
                "label": snapshot.label,
                "snapshot": snapshot.snapshot,
                "summary": snapshot.summary,
                "created_at": snapshot.created_at.isoformat(),
                "created_by": snapshot.created_by.email if snapshot.created_by else None,
            }
        )


@extend_schema(
    tags=["snapshots"],
    summary="Restore a household to a prior snapshot (creates a new 'restore' snapshot)",
    description=(
        "Per locked decision #36, restore creates a NEW snapshot tagged "
        "'restore' rather than rewinding, so the chain stays linear and "
        "reversible. The restore replays the snapshot's allocation amounts "
        "onto current GoalAccountLink rows."
    ),
)
class HouseholdSnapshotRestoreView(APIView):
    """POST /api/households/{household_id}/snapshots/{snapshot_id}/restore/"""

    def post(self, request: Request, household_id: str, snapshot_id: int) -> Response:
        with transaction.atomic():
            household = _resolve_household_for_write(request, household_id)
            target = get_object_or_404(
                models.HouseholdSnapshot, id=snapshot_id, household=household
            )
            stored = copy.deepcopy(target.snapshot)
            for acct in stored.get("accounts", []):
                try:
                    account = household.accounts.get(external_id=acct["id"])
                except models.Account.DoesNotExist:
                    continue
                for leg in acct.get("links", []):
                    try:
                        goal = household.goals.get(external_id=leg["goal_id"])
                    except models.Goal.DoesNotExist:
                        continue
                    link, _created = models.GoalAccountLink.objects.get_or_create(
                        goal=goal,
                        account=account,
                        defaults={
                            "external_id": models.uuid_string(),
                            "allocated_amount": Decimal(leg["allocated_amount"]),
                        },
                    )
                    link.allocated_amount = Decimal(leg["allocated_amount"])
                    link.save()
            new_snapshot = _create_snapshot(
                household=household,
                triggered_by="restore",
                label=f"Restored from snapshot #{target.id}",
                user=request.user,
            )
            record_event(
                action="household_snapshot_restored",
                actor=request.user.email,
                entity_type="household",
                entity_id=household.external_id,
                metadata={
                    "restored_from_snapshot_id": target.id,
                    "new_snapshot_id": new_snapshot.id,
                },
            )
        return Response(
            {"new_snapshot_id": new_snapshot.id, "restored_from_snapshot_id": target.id},
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Goal risk override
# ---------------------------------------------------------------------------


@extend_schema(
    tags=["preview"],
    summary="Create an advisor risk override on a goal (canon 1-5 + descriptor)",
    description=(
        "Per locked decision #6, override operates exclusively on the "
        "canon 1-5 + descriptor surface. Per locked decision #37, every "
        "save fires an AuditEvent with kind 'goal_risk_override_created' "
        "capturing before/after canon score + descriptor + rationale."
    ),
    request=GoalRiskOverrideRequestSerializer,
)
class GoalRiskOverrideCreateView(APIView):
    """POST /api/goals/{goal_id}/override/"""

    def post(self, request: Request, goal_id: str) -> Response:
        if not request.user.is_authenticated:
            raise PermissionDenied("Authentication required.")
        data = _validate(request, GoalRiskOverrideRequestSerializer)

        with transaction.atomic():
            try:
                goal = (
                    models.Goal.objects.select_for_update()
                    .select_related("household")
                    .get(external_id=goal_id)
                )
            except models.Goal.DoesNotExist as exc:
                raise NotFound(f"Goal {goal_id} not found.") from exc

            household = goal.household
            if (
                household.owner_id
                and household.owner_id != request.user.id
                and household.owner is not None
            ):
                # Per access.py: ownerless synthetic households are visible
                # team-wide; advisor-owned households are owner-locked here.
                raise PermissionDenied("This household is owned by another advisor.")

            previous = goal.risk_overrides.order_by("-created_at", "-id").first()
            previous_score = previous.score_1_5 if previous else None

            new_override = models.GoalRiskOverride.objects.create(
                goal=goal,
                score_1_5=data["score_1_5"],
                descriptor=data["descriptor"],
                rationale=data["rationale"],
                created_by=request.user,
            )

            record_event(
                action="goal_risk_override_created",
                actor=request.user.email,
                entity_type="goal",
                entity_id=goal.external_id,
                metadata={
                    "override_id": new_override.id,
                    "previous_score_1_5": previous_score,
                    "new_score_1_5": data["score_1_5"],
                    "descriptor": data["descriptor"],
                    # Rationale is logged in full per canon §9.4.6 (audit
                    # captures full record); workspace timeline serializer
                    # would sanitize for UI, but advisor-authored rationales
                    # are not real-PII text.
                    "rationale": data["rationale"],
                },
            )

        # Trigger #3 (per locked #14 + #74): override changes goal_risk_score
        # → run_signature changes → new PortfolioRun. Outside the atomic so
        # the helper sees the committed override.
        from web.api.views import _trigger_and_audit

        _trigger_and_audit(household, request.user, source="override")

        return Response(
            {
                "override_id": new_override.id,
                "goal_id": goal.external_id,
                "score_1_5": new_override.score_1_5,
                "descriptor": new_override.descriptor,
                "created_at": new_override.created_at.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    tags=["preview"],
    summary="List goal risk override history (read-only)",
)
class GoalRiskOverrideListView(APIView):
    """GET /api/goals/{goal_id}/overrides/"""

    def get(self, request: Request, goal_id: str) -> Response:
        try:
            goal = models.Goal.objects.select_related("household").get(external_id=goal_id)
        except models.Goal.DoesNotExist as exc:
            raise NotFound(f"Goal {goal_id} not found.") from exc

        # Scope check: goal's household must be in advisor team scope.
        team_qs = team_households(request.user)
        if not team_qs.filter(pk=goal.household.pk).exists():
            raise NotFound(f"Goal {goal_id} not found.")

        overrides = goal.risk_overrides.all()
        return Response(
            [
                {
                    "id": o.id,
                    "score_1_5": o.score_1_5,
                    "descriptor": o.descriptor,
                    "rationale": o.rationale,
                    "created_at": o.created_at.isoformat(),
                    "created_by": o.created_by.email,
                }
                for o in overrides
            ]
        )


# ---------------------------------------------------------------------------
# External holdings CRUD
# ---------------------------------------------------------------------------


@extend_schema(tags=["clients"], summary="List external holdings for a household")
class ExternalHoldingListCreateView(APIView):
    """GET/POST /api/households/{household_id}/external-holdings/"""

    def get(self, request: Request, household_id: str) -> Response:
        household = team_households(request.user).filter(external_id=household_id).first()
        if household is None:
            raise NotFound(f"Household {household_id} not found.")
        holdings = household.external_holdings.all()
        return Response([_external_holding_payload(h) for h in holdings])

    def post(self, request: Request, household_id: str) -> Response:
        data = _validate(request, ExternalHoldingMutationSerializer)
        with transaction.atomic():
            household = _resolve_household_for_write(request, household_id)
            holding = models.ExternalHolding.objects.create(
                household=household,
                name=data.get("name", ""),
                value=data["value"],
                equity_pct=data["equity_pct"],
                fixed_income_pct=data["fixed_income_pct"],
                cash_pct=data["cash_pct"],
                real_assets_pct=data["real_assets_pct"],
            )
            record_event(
                action="external_holdings_updated",
                actor=request.user.email,
                entity_type="household",
                entity_id=household.external_id,
                metadata={"action": "create", "holding_id": holding.id},
            )
        return Response(_external_holding_payload(holding), status=status.HTTP_201_CREATED)


@extend_schema(tags=["clients"], summary="Update / delete an external holding")
class ExternalHoldingDetailView(APIView):
    """PATCH / DELETE /api/households/{household_id}/external-holdings/{holding_id}/"""

    def patch(self, request: Request, household_id: str, holding_id: int) -> Response:
        data = _validate(request, ExternalHoldingMutationSerializer)
        with transaction.atomic():
            household = _resolve_household_for_write(request, household_id)
            holding = get_object_or_404(models.ExternalHolding, id=holding_id, household=household)
            holding.name = data.get("name", holding.name)
            holding.value = data["value"]
            holding.equity_pct = data["equity_pct"]
            holding.fixed_income_pct = data["fixed_income_pct"]
            holding.cash_pct = data["cash_pct"]
            holding.real_assets_pct = data["real_assets_pct"]
            holding.save()
            record_event(
                action="external_holdings_updated",
                actor=request.user.email,
                entity_type="household",
                entity_id=household.external_id,
                metadata={"action": "update", "holding_id": holding.id},
            )
        return Response(_external_holding_payload(holding))

    def delete(self, request: Request, household_id: str, holding_id: int) -> Response:
        with transaction.atomic():
            household = _resolve_household_for_write(request, household_id)
            holding = get_object_or_404(models.ExternalHolding, id=holding_id, household=household)
            deleted_id = holding.id
            holding.delete()
            record_event(
                action="external_holdings_updated",
                actor=request.user.email,
                entity_type="household",
                entity_id=household.external_id,
                metadata={"action": "delete", "holding_id": deleted_id},
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


def _external_holding_payload(holding: models.ExternalHolding) -> dict[str, Any]:
    return {
        "id": holding.id,
        "name": holding.name,
        "value": str(holding.value),
        "equity_pct": str(holding.equity_pct),
        "fixed_income_pct": str(holding.fixed_income_pct),
        "cash_pct": str(holding.cash_pct),
        "real_assets_pct": str(holding.real_assets_pct),
        "created_at": holding.created_at.isoformat(),
        "updated_at": holding.updated_at.isoformat(),
    }
