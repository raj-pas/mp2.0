from __future__ import annotations

from rest_framework import serializers

from web.api import models


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
            "holdings",
        ]


class GoalAccountLinkSerializer(serializers.ModelSerializer):
    goal_id = serializers.CharField(source="goal.external_id")
    account_id = serializers.CharField(source="account.external_id")

    class Meta:
        model = models.GoalAccountLink
        fields = ["goal_id", "account_id", "allocated_amount", "allocated_pct"]


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
            "last_engine_output",
        ]

    def get_goal_count(self, obj: models.Household) -> int:
        return obj.goals.count()

    def get_total_assets(self, obj: models.Household) -> float:
        return float(sum(account.current_value for account in obj.accounts.all()))
