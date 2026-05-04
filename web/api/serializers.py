from __future__ import annotations

from rest_framework import serializers

from web.api import models
from web.audit.models import AuditEvent


class PersonSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="external_id")

    class Meta:
        model = models.Person
        fields = [
            "id",
            "name",
            "dob",
            "marital_status",
            "investment_knowledge",
            "employment",
            "pensions",
        ]


class HoldingSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Holding
        fields = ["sleeve_id", "sleeve_name", "weight", "market_value"]


class AccountSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="external_id")
    type = serializers.CharField(source="account_type")
    owner_person_id = serializers.CharField(source="owner_person.external_id", allow_null=True)
    holdings = HoldingSerializer(many=True)

    class Meta:
        model = models.Account
        fields = [
            "id",
            "owner_person_id",
            "type",
            "regulatory_objective",
            "regulatory_time_horizon",
            "regulatory_risk_rating",
            "current_value",
            "contribution_room",
            "is_held_at_purpose",
            "missing_holdings_confirmed",
            "cash_state",
            "holdings",
        ]


class GoalAccountLinkSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="external_id")
    goal_id = serializers.CharField(source="goal.external_id")
    account_id = serializers.CharField(source="account.external_id")

    class Meta:
        model = models.GoalAccountLink
        fields = ["id", "goal_id", "account_id", "allocated_amount", "allocated_pct"]


class GoalSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="external_id")
    account_allocations = GoalAccountLinkSerializer(many=True)

    class Meta:
        model = models.Goal
        fields = [
            "id",
            "name",
            "target_amount",
            "target_date",
            "necessity_score",
            "current_funded_amount",
            "contribution_plan",
            "goal_risk_score",
            "status",
            "notes",
            "account_allocations",
        ]


class HouseholdListSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="external_id")
    goal_count = serializers.SerializerMethodField()
    total_assets = serializers.SerializerMethodField()

    class Meta:
        model = models.Household
        fields = [
            "id",
            "display_name",
            "household_type",
            "household_risk_score",
            "goal_count",
            "total_assets",
        ]

    def get_goal_count(self, obj: models.Household) -> int:
        return obj.goals.count()

    def get_total_assets(self, obj: models.Household) -> float:
        return float(sum(account.current_value for account in obj.accounts.all()))


class HouseholdDetailSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="external_id")
    goal_count = serializers.SerializerMethodField()
    total_assets = serializers.SerializerMethodField()
    members = PersonSerializer(many=True)
    goals = GoalSerializer(many=True)
    accounts = AccountSerializer(many=True)
    latest_portfolio_run = serializers.SerializerMethodField()
    latest_portfolio_failure = serializers.SerializerMethodField()
    portfolio_runs = serializers.SerializerMethodField()

    class Meta:
        model = models.Household
        fields = [
            "id",
            "display_name",
            "household_type",
            "household_risk_score",
            "goal_count",
            "total_assets",
            "external_assets",
            "notes",
            "members",
            "goals",
            "accounts",
            "latest_portfolio_run",
            "latest_portfolio_failure",
            "portfolio_runs",
        ]

    def get_goal_count(self, obj: models.Household) -> int:
        return obj.goals.count()

    def get_total_assets(self, obj: models.Household) -> float:
        return float(sum(account.current_value for account in obj.accounts.all()))

    def get_latest_portfolio_run(self, obj: models.Household) -> dict | None:
        run = obj.portfolio_runs.order_by("-created_at").first()
        return PortfolioRunSerializer(run).data if run else None

    def get_latest_portfolio_failure(self, obj: models.Household) -> dict | None:
        """Most recent portfolio_generation_*_failed AuditEvent newer than the
        household's latest PortfolioRun (if any). Drives RecommendationBanner's
        inline-error state per locked decision #9.
        """
        from web.audit.models import AuditEvent

        latest_run = obj.portfolio_runs.order_by("-created_at").first()
        cutoff = latest_run.created_at if latest_run else obj.created_at
        failure = (
            AuditEvent.objects.filter(
                entity_type="household",
                entity_id=obj.external_id,
                action__startswith="portfolio_generation_post_",
                action__endswith="_failed",
                created_at__gt=cutoff,
            )
            .order_by("-created_at")
            .first()
        )
        if failure is None:
            return None
        return {
            "action": failure.action,
            "reason_code": failure.metadata.get("source", "unknown"),
            "exception_summary": failure.metadata.get("failure_summary")
            or failure.metadata.get("exception_summary", ""),
            "occurred_at": failure.created_at.isoformat() if failure.created_at else None,
        }

    def get_portfolio_runs(self, obj: models.Household) -> list[dict]:
        runs = obj.portfolio_runs.order_by("-created_at")[:10]
        return PortfolioRunSummarySerializer(runs, many=True).data


class PortfolioRunLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PortfolioRunLinkRecommendation
        fields = [
            "link_external_id",
            "goal_external_id",
            "account_external_id",
            "allocated_amount",
            "frontier_percentile",
            "expected_return",
            "volatility",
            "allocations",
            "current_comparison",
            "explanation",
            "warnings",
        ]


class PortfolioRunEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PortfolioRunEvent
        fields = ["event_type", "actor", "reason_code", "note", "metadata", "created_at"]


class PortfolioRunSummarySerializer(serializers.ModelSerializer):
    cma_snapshot_id = serializers.CharField(source="cma_snapshot.external_id")
    generated_by_email = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    warnings = serializers.SerializerMethodField()

    class Meta:
        model = models.PortfolioRun
        fields = [
            "id",
            "external_id",
            "status",
            "as_of_date",
            "cma_snapshot_id",
            "engine_version",
            "advisor_summary",
            "input_hash",
            "output_hash",
            "cma_hash",
            "reviewed_state_hash",
            "approval_snapshot_hash",
            "run_signature",
            "warnings",
            "generated_by_email",
            "created_at",
        ]

    def get_generated_by_email(self, obj: models.PortfolioRun) -> str:
        return obj.generated_by.email if obj.generated_by else "system"

    def get_status(self, obj: models.PortfolioRun) -> str:
        return _portfolio_run_status(obj)

    def get_warnings(self, obj: models.PortfolioRun) -> list[str]:
        return list((obj.output or {}).get("warnings") or [])


class PortfolioRunSerializer(PortfolioRunSummarySerializer):
    link_recommendation_rows = PortfolioRunLinkSerializer(many=True)
    events = PortfolioRunEventSerializer(many=True)

    class Meta(PortfolioRunSummarySerializer.Meta):
        fields = [
            *PortfolioRunSummarySerializer.Meta.fields,
            "output",
            "technical_trace",
            "link_recommendation_rows",
            "events",
        ]


def _portfolio_run_status(obj: models.PortfolioRun) -> str:
    event_types = set(obj.events.values_list("event_type", flat=True))
    if models.PortfolioRunEvent.EventType.ADVISOR_DECLINED in event_types:
        return "declined"
    if models.PortfolioRunEvent.EventType.HASH_MISMATCH in event_types:
        return "hash_mismatch"
    if {
        models.PortfolioRunEvent.EventType.INVALIDATED_BY_CMA,
        models.PortfolioRunEvent.EventType.INVALIDATED_BY_HOUSEHOLD_CHANGE,
    } & event_types:
        return "invalidated"
    newer_run_exists = models.PortfolioRun.objects.filter(
        household=obj.household,
        created_at__gt=obj.created_at,
    ).exists()
    return "superseded" if newer_run_exists else "current"


class PlanningVersionSerializer(serializers.ModelSerializer):
    created_by_email = serializers.SerializerMethodField()

    class Meta:
        model = models.PlanningVersion
        fields = [
            "id",
            "version",
            "state",
            "rationale",
            "created_by_email",
            "created_at",
        ]

    def get_created_by_email(self, obj: models.PlanningVersion) -> str:
        return obj.created_by.email if obj.created_by else "system"


class CMAFundAssumptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CMAFundAssumption
        fields = [
            "fund_id",
            "name",
            "expected_return",
            "volatility",
            "optimizer_eligible",
            "is_whole_portfolio",
            "display_order",
            "aliases",
            "asset_class_weights",
            "geography_weights",
            "tax_drag",
        ]


class CMACorrelationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CMACorrelation
        fields = ["row_fund_id", "col_fund_id", "correlation"]


class CMASnapshotSerializer(serializers.ModelSerializer):
    fund_assumptions = CMAFundAssumptionSerializer(many=True)
    correlations = CMACorrelationSerializer(many=True)
    latest_publish_note = serializers.SerializerMethodField()

    class Meta:
        model = models.CMASnapshot
        fields = [
            "id",
            "external_id",
            "name",
            "version",
            "status",
            "source",
            "notes",
            "latest_publish_note",
            "published_at",
            "created_at",
            "updated_at",
            "fund_assumptions",
            "correlations",
        ]

    def get_latest_publish_note(self, obj: models.CMASnapshot) -> str:
        event = (
            AuditEvent.objects.filter(
                action="cma_snapshot_published",
                entity_type="cma_snapshot",
                entity_id=obj.external_id,
            )
            .order_by("-created_at")
            .first()
        )
        return str((event.metadata if event else {}).get("publish_note", ""))
