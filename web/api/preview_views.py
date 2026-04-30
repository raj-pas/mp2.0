"""DRF preview endpoints for the v36 advisor console (Phase R1).

Read-only computation surfaces consumed by the new UI for live updates
in the wizard, slider, fan chart, and goal allocation views. Per locked
decision #2, all math goes through the engine — these endpoints are
thin wrappers that translate DRF requests into engine calls and back.

Per locked decision #18, latency budget is P50 < 250ms / P99 < 1000ms;
no backend cache layer (TanStack Query handles client cache); each
request recomputes fresh.

Per locked decision #6, Goal_50 is internal — endpoints expose canon
1-5 + descriptor + flags + derivation; never the raw 0-50 number.

Auth: every endpoint requires authentication via the project default
``AllowPhaseOneAccess``; advisor-team-scoping applied where the body
references a household_id (``team_households(request.user)``).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from engine.collapse import collapse_suggestion as engine_collapse_suggestion
from engine.collapse import match_score as engine_match_score
from engine.goal_scoring import (
    GoalRiskOverride as EngineGoalRiskOverride,
)
from engine.goal_scoring import (
    effective_score_and_descriptor,
    tier_for_necessity,
)
from engine.moves import compute_rebalance_moves
from engine.projections import (
    BUCKET_REPRESENTATIVE_SCORE,
    lognormal_quantile,
    prob_above_target,
    projection_bands,
    projection_path,
)
from engine.risk_profile import RiskProfileInput, compute_risk_profile
from engine.schemas import FundAssumption
from engine.sleeves import FUND_NAMES, SLEEVE_REF_POINTS
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from web.api import models
from web.api.access import team_households

# ---------------------------------------------------------------------------
# Serializers — request shapes only. Responses are dict[str, Any] driven by
# engine return shapes; @extend_schema declares the response inline.
# ---------------------------------------------------------------------------


class RiskProfileRequestSerializer(serializers.Serializer):
    q1 = serializers.IntegerField(min_value=0, max_value=10)
    q2 = serializers.ChoiceField(choices=["A", "B", "C", "D"])
    q3 = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    q4 = serializers.ChoiceField(choices=["A", "B", "C", "D"])


class GoalScoreOverrideSerializer(serializers.Serializer):
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


class GoalScoreRequestSerializer(serializers.Serializer):
    """Per locked decision #6: API takes canon-shaped inputs, never Goal_50.

    The server computes Goal_50 internally from anchor + tier + size and
    returns canon 1-5 + descriptor + flags + derivation breakdown.
    """

    anchor = serializers.FloatField(min_value=0, max_value=50)
    necessity_score = serializers.IntegerField(
        min_value=1, max_value=5, required=False, allow_null=True
    )
    goal_amount = serializers.FloatField(min_value=0)
    household_aum = serializers.FloatField(min_value=0.01)
    horizon_years = serializers.FloatField(min_value=0)
    override = GoalScoreOverrideSerializer(required=False, allow_null=True)


class SleeveMixRequestSerializer(serializers.Serializer):
    score_1_5 = serializers.IntegerField(min_value=1, max_value=5)


class ProjectionRequestSerializer(serializers.Serializer):
    start = serializers.FloatField(min_value=0.01)
    score_1_5 = serializers.IntegerField(min_value=1, max_value=5)
    horizon_years = serializers.FloatField(min_value=0)
    mode = serializers.ChoiceField(choices=["ideal", "current"], default="ideal")
    is_external = serializers.BooleanField(default=False)
    tier = serializers.ChoiceField(choices=["need", "want", "wish", "unsure"], default="want")


class ProjectionPathsRequestSerializer(serializers.Serializer):
    start = serializers.FloatField(min_value=0.01)
    score_1_5 = serializers.IntegerField(min_value=1, max_value=5)
    horizon_years = serializers.FloatField(min_value=0)
    percentiles = serializers.ListField(
        child=serializers.FloatField(min_value=0.001, max_value=0.999),
        min_length=1,
        max_length=10,
    )
    n_steps = serializers.IntegerField(min_value=2, max_value=200, default=50)
    mode = serializers.ChoiceField(choices=["ideal", "current"], default="ideal")
    is_external = serializers.BooleanField(default=False)


class ProbabilityRequestSerializer(serializers.Serializer):
    start = serializers.FloatField(min_value=0.01)
    score_1_5 = serializers.IntegerField(min_value=1, max_value=5)
    horizon_years = serializers.FloatField(min_value=0)
    target = serializers.FloatField(min_value=0.01)
    mode = serializers.ChoiceField(choices=["ideal", "current"], default="ideal")
    is_external = serializers.BooleanField(default=False)


class OptimizerOutputRequestSerializer(serializers.Serializer):
    household_id = serializers.CharField()
    goal_id = serializers.CharField()


class MovesRequestSerializer(serializers.Serializer):
    household_id = serializers.CharField()
    goal_id = serializers.CharField()


class BlendedAccountRiskRequestSerializer(serializers.Serializer):
    household_id = serializers.CharField()
    account_id = serializers.CharField()
    candidate_goal_amounts = serializers.DictField(
        child=serializers.FloatField(min_value=0),
    )


class CollapseSuggestionRequestSerializer(serializers.Serializer):
    """Body: blend = {fund_id: weight}, threshold optional (default 0.92)."""

    blend = serializers.DictField(child=serializers.FloatField(min_value=0))
    threshold = serializers.FloatField(min_value=0, max_value=1, required=False, default=0.92)


# ---------------------------------------------------------------------------
# Helper: validated request → ``{cleaned_data}`` or raise.
# ---------------------------------------------------------------------------


def _validate(request: Request, serializer_cls: type[serializers.Serializer]) -> dict[str, Any]:
    serializer = serializer_cls(data=request.data)
    serializer.is_valid(raise_exception=True)
    return dict(serializer.validated_data)


def _resolve_household(request: Request, household_id: str) -> models.Household:
    qs = team_households(request.user)
    try:
        return qs.get(external_id=household_id)
    except models.Household.DoesNotExist as exc:
        raise NotFound(f"Household {household_id} not found in advisor scope.") from exc


def _eligible_funds(snapshot: models.CMASnapshot) -> list[FundAssumption]:
    """Convert a CMA snapshot's optimizer-eligible funds to engine schemas."""

    rows = list(snapshot.fund_assumptions.filter(optimizer_eligible=True))
    return [
        FundAssumption(
            id=fund.fund_id,
            name=fund.name,
            expected_return=float(fund.expected_return),
            volatility=float(fund.volatility),
            optimizer_eligible=fund.optimizer_eligible,
            is_whole_portfolio=fund.is_whole_portfolio,
            aliases=list(fund.aliases or []),
            asset_class_weights=dict(fund.asset_class_weights or {}),
            geography_weights=dict(fund.geography_weights or {}),
            tax_drag=dict(fund.tax_drag or {}),
        )
        for fund in rows
    ]


def _active_cma_snapshot() -> models.CMASnapshot | None:
    return models.CMASnapshot.objects.filter(status="active").first()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@extend_schema(
    tags=["preview"],
    summary="Compute household risk profile from Q1-Q4",
    description=(
        "Wizard step 2 live recompute. Returns canon 1-5 + descriptor + "
        "anchor + tolerance/capacity scores + consistency flags. Per "
        "locked decision #6, Goal_50 / T / C are surfaced as advisor-"
        "transparent intermediates here (T/C in 0-100, anchor in 0-50)."
    ),
    request=RiskProfileRequestSerializer,
    responses={
        200: inline_serializer(
            name="RiskProfileResponse",
            fields={
                "tolerance_score": serializers.FloatField(),
                "capacity_score": serializers.FloatField(),
                "tolerance_descriptor": serializers.CharField(),
                "capacity_descriptor": serializers.CharField(),
                "household_descriptor": serializers.CharField(),
                "score_1_5": serializers.IntegerField(),
                "anchor": serializers.FloatField(),
                "flags": serializers.ListField(child=serializers.CharField()),
            },
        ),
    },
)
class RiskProfilePreviewView(APIView):
    """POST /api/preview/risk-profile/"""

    def post(self, request: Request) -> Response:
        data = _validate(request, RiskProfileRequestSerializer)
        result = compute_risk_profile(
            RiskProfileInput(
                q1=data["q1"],
                q2=data["q2"],
                q3=data.get("q3", []),
                q4=data["q4"],
            )
        )
        return Response(result.model_dump())


@extend_schema(
    tags=["preview"],
    summary="Resolve goal-level risk score (canon 1-5 + descriptor)",
    description=(
        "Live wizard step 3 recompute. Per locked decision #6, the "
        "response intentionally omits the internal Goal_50 number; the "
        "advisor sees only the canon 1-5 score + descriptor + horizon-"
        "cap-binding flag + override-active flag + derivation breakdown "
        "(anchor / imp_shift / size_shift)."
    ),
    request=GoalScoreRequestSerializer,
)
class GoalScorePreviewView(APIView):
    """POST /api/preview/goal-score/"""

    def post(self, request: Request) -> Response:
        data = _validate(request, GoalScoreRequestSerializer)
        override_payload = data.get("override")
        override = (
            EngineGoalRiskOverride(
                score_1_5=override_payload["score_1_5"],
                descriptor=override_payload["descriptor"],
                rationale=override_payload["rationale"],
            )
            if override_payload
            else None
        )
        try:
            result = effective_score_and_descriptor(
                anchor=data["anchor"],
                necessity_score=data.get("necessity_score"),
                goal_amount=data["goal_amount"],
                household_aum=data["household_aum"],
                horizon_years=data["horizon_years"],
                override=override,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result.model_dump())


@extend_schema(
    tags=["preview"],
    summary="Sleeve mix at canonical risk score",
    description=(
        "Returns the calibration-reference SLEEVE_REF_POINTS mix for a "
        "canon 1-5 score. NOT the optimizer output — the optimizer uses "
        "frontier optimization (canon §4.1). This endpoint serves the "
        "advisor methodology page + visual sleeve-mix preview, not the "
        "production allocation."
    ),
    request=SleeveMixRequestSerializer,
)
class SleeveMixPreviewView(APIView):
    """POST /api/preview/sleeve-mix/"""

    def post(self, request: Request) -> Response:
        data = _validate(request, SleeveMixRequestSerializer)
        score = data["score_1_5"]
        rep_score = int(BUCKET_REPRESENTATIVE_SCORE[score])  # 5/15/25/35/45
        mix = SLEEVE_REF_POINTS[rep_score]
        return Response(
            {
                "score_1_5": score,
                "reference_score": rep_score,
                "mix": dict(mix),
                "fund_names": dict(FUND_NAMES),
                "source": "engine.sleeves.SLEEVE_REF_POINTS (calibration only)",
            }
        )


@extend_schema(
    tags=["preview"],
    summary="Lognormal projection bands at horizon",
    request=ProjectionRequestSerializer,
)
class ProjectionPreviewView(APIView):
    """POST /api/preview/projection/"""

    def post(self, request: Request) -> Response:
        data = _validate(request, ProjectionRequestSerializer)
        rep_score = BUCKET_REPRESENTATIVE_SCORE[data["score_1_5"]]
        try:
            bands = projection_bands(
                start=data["start"],
                score=rep_score,
                horizon_years=data["horizon_years"],
                tier=data["tier"],
                mode=data["mode"],
                is_external=data["is_external"],
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(bands.model_dump())


@extend_schema(
    tags=["preview"],
    summary="Lognormal paths along constant-percentile curves",
    request=ProjectionPathsRequestSerializer,
)
class ProjectionPathsPreviewView(APIView):
    """POST /api/preview/projection-paths/"""

    def post(self, request: Request) -> Response:
        data = _validate(request, ProjectionPathsRequestSerializer)
        rep_score = BUCKET_REPRESENTATIVE_SCORE[data["score_1_5"]]
        try:
            paths = [
                {
                    "percentile": pct,
                    "points": [
                        point.model_dump()
                        for point in projection_path(
                            start=data["start"],
                            score=rep_score,
                            horizon_years=data["horizon_years"],
                            percentile=pct,
                            n_steps=data["n_steps"],
                            mode=data["mode"],
                            is_external=data["is_external"],
                        )
                    ],
                }
                for pct in data["percentiles"]
            ]
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"paths": paths})


@extend_schema(
    tags=["preview"],
    summary="Probability that S_T >= target (lognormal)",
    description=("Drives the fan-chart hover crosshair callout per v36 mockup §35."),
    request=ProbabilityRequestSerializer,
)
class ProbabilityPreviewView(APIView):
    """POST /api/preview/probability/"""

    def post(self, request: Request) -> Response:
        data = _validate(request, ProbabilityRequestSerializer)
        rep_score = BUCKET_REPRESENTATIVE_SCORE[data["score_1_5"]]
        try:
            probability = prob_above_target(
                start=data["start"],
                score=rep_score,
                horizon_years=data["horizon_years"],
                target=data["target"],
                mode=data["mode"],
                is_external=data["is_external"],
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"probability": probability})


@extend_schema(
    tags=["preview"],
    summary="Optimizer output widget — improvement % at P_score downside",
    description=(
        "Mockup v34: improvement_pct = (ideal_low − current_low) / "
        "current_low × 100, where p = goal_risk_score / 5 → percentile."
    ),
    request=OptimizerOutputRequestSerializer,
)
class OptimizerOutputPreviewView(APIView):
    """POST /api/preview/optimizer-output/"""

    def post(self, request: Request) -> Response:
        data = _validate(request, OptimizerOutputRequestSerializer)
        household = _resolve_household(request, data["household_id"])
        try:
            goal = household.goals.get(external_id=data["goal_id"])
        except models.Goal.DoesNotExist as exc:
            raise NotFound(f"Goal {data['goal_id']} not found.") from exc

        # Effective score: latest override beats system; horizon-cap honored.
        anchor = (
            float(household.risk_profile.anchor) if hasattr(household, "risk_profile") else 25.0
        )
        from web.api.engine_adapter import active_goal_override, household_aum

        override = active_goal_override(goal)
        # Goal amount = sum of allocated_amounts on its links.
        goal_amount = sum(
            float(link.allocated_amount or 0) for link in goal.account_allocations.all()
        )
        horizon_days = (goal.target_date - household.updated_at.date()).days
        horizon_years = max(horizon_days / 365.25, 0.25)
        try:
            resolved = effective_score_and_descriptor(
                anchor=anchor,
                necessity_score=goal.necessity_score,
                goal_amount=goal_amount,
                household_aum=household_aum(household),
                horizon_years=horizon_years,
                override=override,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        rep_score = BUCKET_REPRESENTATIVE_SCORE[resolved.score_1_5]
        # P_score = score_1_5 / 5 maps to {0.05, 0.15, 0.25, 0.35, 0.45} per
        # canon §4.2 RISK_TO_PERCENTILE; flip to a downside percentile by
        # using (5 - score)/5? Mockup: p = effective_score/100 → for 1-5 ×
        # 5/15/25/35/45 we use the percentile at downside as the score%/100.
        p_used = rep_score / 100.0
        ideal_low = lognormal_quantile(
            start=goal_amount or 1.0,
            score=rep_score,
            horizon_years=horizon_years,
            percentile=p_used,
            mode="ideal",
        )
        current_low = lognormal_quantile(
            start=goal_amount or 1.0,
            score=rep_score,
            horizon_years=horizon_years,
            percentile=p_used,
            mode="current",
        )
        improvement_pct = (ideal_low - current_low) / current_low * 100.0 if current_low else 0.0
        return Response(
            {
                "ideal_low": ideal_low,
                "current_low": current_low,
                "improvement_pct": improvement_pct,
                "effective_score_1_5": resolved.score_1_5,
                "effective_descriptor": resolved.descriptor,
                "p_used": p_used,
                "tier": tier_for_necessity(goal.necessity_score),
            }
        )


@extend_schema(
    tags=["preview"],
    summary="Rebalance moves to bring current to ideal (canon §8.10)",
    request=MovesRequestSerializer,
)
class MovesPreviewView(APIView):
    """POST /api/preview/moves/"""

    def post(self, request: Request) -> Response:
        data = _validate(request, MovesRequestSerializer)
        household = _resolve_household(request, data["household_id"])
        try:
            goal = household.goals.get(external_id=data["goal_id"])
        except models.Goal.DoesNotExist as exc:
            raise NotFound(f"Goal {data['goal_id']} not found.") from exc

        # Aggregate current sleeve mix across the goal's account legs,
        # weighted by allocated_amount.
        snapshot = _active_cma_snapshot()
        if snapshot is None:
            return Response(
                {"detail": "No active CMA snapshot available."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        eligible = _eligible_funds(snapshot)
        if not eligible:
            return Response(
                {"detail": "Active CMA has no optimizer-eligible funds."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from web.api.engine_adapter import current_holdings_to_pct

        current_pct: dict[str, float] = {}
        total_amount = 0.0
        for link in goal.account_allocations.all():
            amount = float(link.allocated_amount or 0)
            if amount <= 0:
                continue
            account_mix = current_holdings_to_pct(link.account)
            for fund_id, weight in account_mix.items():
                current_pct[fund_id] = current_pct.get(fund_id, 0.0) + weight * amount
            total_amount += amount
        if total_amount > 0:
            current_pct = {fid: w / total_amount for fid, w in current_pct.items()}

        # Use SLEEVE_REF_POINTS as the ideal mix for the goal's resolved
        # canon score. This is calibration-grade preview, not full
        # frontier optimization (which lives in /api/clients/.../generate-portfolio/).
        anchor = (
            float(household.risk_profile.anchor) if hasattr(household, "risk_profile") else 25.0
        )
        from web.api.engine_adapter import active_goal_override, household_aum

        try:
            resolved = effective_score_and_descriptor(
                anchor=anchor,
                necessity_score=goal.necessity_score,
                goal_amount=sum(
                    float(link.allocated_amount or 0) for link in goal.account_allocations.all()
                ),
                household_aum=household_aum(household),
                horizon_years=max(
                    (goal.target_date - household.updated_at.date()).days / 365.25, 0.25
                ),
                override=active_goal_override(goal),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        rep_score = int(BUCKET_REPRESENTATIVE_SCORE[resolved.score_1_5])
        ideal_pct_int = SLEEVE_REF_POINTS[rep_score]
        ideal_pct = {fid: pct / 100.0 for fid, pct in ideal_pct_int.items()}

        if total_amount <= 0:
            return Response(
                {"moves": [], "total_buy": 0.0, "total_sell": 0.0},
            )
        result = compute_rebalance_moves(
            current_pct=current_pct,
            ideal_pct=ideal_pct,
            goal_total_dollars=total_amount,
            fund_names=dict(FUND_NAMES),
        )
        return Response(result.model_dump())


@extend_schema(
    tags=["preview"],
    summary="Blended account risk before/after candidate goal-amount edit",
    description=(
        "Used by the realignment modal: when the advisor proposes new "
        "goal allocations on an account, this endpoint reports whether "
        "the blended account risk would shift > 5pts (canon §6.3a "
        "banner threshold)."
    ),
    request=BlendedAccountRiskRequestSerializer,
)
class BlendedAccountRiskPreviewView(APIView):
    """POST /api/preview/blended-account-risk/"""

    def post(self, request: Request) -> Response:
        data = _validate(request, BlendedAccountRiskRequestSerializer)
        household = _resolve_household(request, data["household_id"])
        try:
            account = household.accounts.get(external_id=data["account_id"])
        except models.Account.DoesNotExist as exc:
            raise NotFound(f"Account {data['account_id']} not found.") from exc

        before_score = _account_blended_score(account)

        # After: replace the account's link allocated_amounts with the
        # candidate dict (without saving — pure simulation).
        candidate = data["candidate_goal_amounts"]
        after_score = _account_blended_score_with_candidate(account, candidate)

        delta = abs(after_score - before_score)
        return Response(
            {
                "before_score": before_score,
                "after_score": after_score,
                "delta": delta,
                "would_trigger_banner": delta > 5.0,
                "banner_threshold": 5.0,
            }
        )


def _account_blended_score(account: models.Account) -> float:
    total = sum(float(link.allocated_amount or 0) for link in account.goal_allocations.all())
    if total <= 0:
        return 0.0
    score = 0.0
    for link in account.goal_allocations.all():
        amount = float(link.allocated_amount or 0)
        if amount <= 0:
            continue
        score += link.goal.goal_risk_score * (amount / total)
    return score


def _account_blended_score_with_candidate(
    account: models.Account, candidate: dict[str, float]
) -> float:
    total = sum(amount for amount in candidate.values() if amount > 0)
    if total <= 0:
        return 0.0
    score = 0.0
    for link in account.goal_allocations.all():
        amount = float(candidate.get(link.goal.external_id, 0.0))
        if amount <= 0:
            continue
        score += link.goal.goal_risk_score * (amount / total)
    return score


@extend_schema(
    tags=["preview"],
    summary="FoF collapse suggestion for a building-block blend (canon §4.3b)",
    request=CollapseSuggestionRequestSerializer,
)
class CollapseSuggestionPreviewView(APIView):
    """POST /api/preview/collapse-suggestion/"""

    def post(self, request: Request) -> Response:
        data = _validate(request, CollapseSuggestionRequestSerializer)
        snapshot = _active_cma_snapshot()
        if snapshot is None:
            return Response(
                {"detail": "No active CMA snapshot available."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        eligible = _eligible_funds(snapshot)

        suggestion = engine_collapse_suggestion(
            blend=dict(data["blend"]),
            eligible_funds=eligible,
            threshold=data["threshold"],
        )
        if suggestion is None:
            # Surface best-effort match score for transparency even when
            # below threshold, so the UI can show why no FoF was suggested.
            best_score = 0.0
            best_fund: FundAssumption | None = None
            for fund in eligible:
                if not fund.is_whole_portfolio:
                    continue
                score = engine_match_score(
                    blend=dict(data["blend"]),
                    whole_portfolio_fund=fund,
                    eligible_funds=eligible,
                )
                if score > best_score:
                    best_score = score
                    best_fund = fund
            return Response(
                {
                    "suggested_fund_id": None,
                    "best_score": best_score,
                    "best_candidate_id": best_fund.id if best_fund else None,
                    "threshold": data["threshold"],
                }
            )
        return Response(suggestion.model_dump())


# ---------------------------------------------------------------------------
# Treemap data — read-only aggregation for the v36 main canvas (mockup §7779).
# Implementation NOTE: per locked decision #15, the squarified treemap layout
# itself runs in the frontend (d3-hierarchy); this endpoint only returns the
# hierarchical input data.
# ---------------------------------------------------------------------------


@extend_schema(
    tags=["preview"],
    summary="Treemap hierarchical data for HouseholdRoute",
    description=(
        "Returns hierarchical {id, label, value, color, children[]} per "
        "the requested mode: by_account / by_goal / by_fund / by_asset. "
        "Frontend (d3-hierarchy) computes the squarified layout."
    ),
    parameters=[
        OpenApiParameter(name="household_id", type=OpenApiTypes.STR, required=True),
        OpenApiParameter(
            name="mode",
            type=OpenApiTypes.STR,
            required=False,
            enum=["by_account", "by_goal", "by_fund", "by_asset"],
        ),
    ],
)
class TreemapDataView(APIView):
    """GET /api/treemap/?household_id=...&mode=by_account"""

    def get(self, request: Request) -> Response:
        household_id = request.query_params.get("household_id", "")
        mode = request.query_params.get("mode", "by_account")
        if mode not in ("by_account", "by_goal", "by_fund", "by_asset"):
            return Response(
                {"detail": f"Invalid mode: {mode}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not household_id:
            return Response(
                {"detail": "household_id query param required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        household = _resolve_household(request, household_id)

        if mode == "by_account":
            data = _treemap_by_account(household)
        elif mode == "by_goal":
            data = _treemap_by_goal(household)
        elif mode == "by_fund":
            data = _treemap_by_fund(household)
        else:  # by_asset
            data = _treemap_by_asset(household)
        return Response({"mode": mode, "household_id": household_id, "data": data})


def _treemap_by_account(household: models.Household) -> dict[str, Any]:
    children: list[dict[str, Any]] = []
    for account in household.accounts.all():
        leg_children = []
        for link in account.goal_allocations.all():
            amount = float(link.allocated_amount or 0)
            if amount <= 0:
                continue
            leg_children.append(
                {
                    "id": f"{account.external_id}:{link.goal.external_id}",
                    "label": link.goal.name,
                    "value": amount,
                }
            )
        children.append(
            {
                "id": account.external_id,
                "label": f"{account.account_type}",
                "value": float(account.current_value),
                "children": leg_children,
            }
        )
    return {"id": household.external_id, "label": household.display_name, "children": children}


def _treemap_by_goal(household: models.Household) -> dict[str, Any]:
    children: list[dict[str, Any]] = []
    for goal in household.goals.all():
        leg_children = [
            {
                "id": f"{goal.external_id}:{link.account.external_id}",
                "label": link.account.account_type,
                "value": float(link.allocated_amount or 0),
            }
            for link in goal.account_allocations.all()
            if (link.allocated_amount or Decimal(0)) > 0
        ]
        children.append(
            {
                "id": goal.external_id,
                "label": goal.name,
                "value": sum(child["value"] for child in leg_children),
                "children": leg_children,
            }
        )
    return {"id": household.external_id, "label": household.display_name, "children": children}


def _treemap_by_fund(household: models.Household) -> dict[str, Any]:
    fund_totals: dict[str, float] = {}
    for account in household.accounts.all():
        for holding in account.holdings.all():
            fund_id = holding.sleeve_id
            fund_totals[fund_id] = fund_totals.get(fund_id, 0.0) + float(holding.market_value)
    children = [
        {"id": fund_id, "label": FUND_NAMES.get(fund_id, fund_id), "value": value}
        for fund_id, value in fund_totals.items()
    ]
    return {"id": household.external_id, "label": household.display_name, "children": children}


def _treemap_by_asset(household: models.Household) -> dict[str, Any]:
    snapshot = _active_cma_snapshot()
    fund_lookup: dict[str, FundAssumption] = {}
    if snapshot is not None:
        for fund in _eligible_funds(snapshot):
            fund_lookup[fund.id] = fund
    asset_totals: dict[str, float] = {}
    for account in household.accounts.all():
        for holding in account.holdings.all():
            fund = fund_lookup.get(holding.sleeve_id)
            if fund is None:
                continue
            for asset_class, weight in fund.asset_class_weights.items():
                asset_totals[asset_class] = asset_totals.get(asset_class, 0.0) + (
                    float(holding.market_value) * weight
                )
    children = [
        {"id": ac, "label": ac.replace("_", " ").title(), "value": value}
        for ac, value in asset_totals.items()
    ]
    return {"id": household.external_id, "label": household.display_name, "children": children}
