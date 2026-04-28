from __future__ import annotations

from django.db import models


class Household(models.Model):
    external_id = models.CharField(max_length=120, unique=True)
    display_name = models.CharField(max_length=255)
    household_type = models.CharField(
        max_length=20, choices=[("single", "Single"), ("couple", "Couple")]
    )
    household_risk_score = models.PositiveSmallIntegerField(default=5)
    external_assets = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)
    last_engine_output = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_name"]

    def __str__(self) -> str:
        return self.display_name


class Person(models.Model):
    external_id = models.CharField(max_length=120, unique=True)
    household = models.ForeignKey(Household, related_name="members", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    dob = models.DateField()
    marital_status = models.CharField(max_length=80, blank=True)
    blended_family_flag = models.BooleanField(default=False)
    citizenship = models.CharField(max_length=120, default="Canada")
    residency = models.CharField(max_length=120, default="Canada")
    health_indicators = models.JSONField(default=dict, blank=True)
    longevity_assumption = models.PositiveSmallIntegerField(null=True, blank=True)
    employment = models.JSONField(default=dict, blank=True)
    pensions = models.JSONField(default=list, blank=True)
    investment_knowledge = models.CharField(
        max_length=20,
        choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")],
        default="medium",
    )
    trusted_contact_person = models.CharField(max_length=255, blank=True)
    poa_status = models.CharField(max_length=120, blank=True)
    will_status = models.CharField(max_length=120, blank=True)
    beneficiary_designations = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["dob"]

    def __str__(self) -> str:
        return self.name


class Account(models.Model):
    external_id = models.CharField(max_length=120, unique=True)
    household = models.ForeignKey(Household, related_name="accounts", on_delete=models.CASCADE)
    owner_person = models.ForeignKey(
        Person,
        related_name="accounts",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    account_type = models.CharField(max_length=40)
    regulatory_objective = models.CharField(max_length=40)
    regulatory_time_horizon = models.CharField(max_length=20)
    regulatory_risk_rating = models.CharField(max_length=20)
    current_value = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    contribution_room = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    contribution_history = models.JSONField(default=list, blank=True)
    is_held_at_purpose = models.BooleanField(default=True)

    class Meta:
        ordering = ["account_type", "external_id"]

    def __str__(self) -> str:
        return f"{self.household.display_name} {self.account_type}"


class Holding(models.Model):
    account = models.ForeignKey(Account, related_name="holdings", on_delete=models.CASCADE)
    sleeve_id = models.CharField(max_length=120)
    sleeve_name = models.CharField(max_length=255)
    weight = models.DecimalField(max_digits=8, decimal_places=6)
    market_value = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        ordering = ["sleeve_name"]

    def __str__(self) -> str:
        return f"{self.sleeve_name} {self.weight}"


class Goal(models.Model):
    external_id = models.CharField(max_length=120, unique=True)
    household = models.ForeignKey(Household, related_name="goals", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    target_amount = models.DecimalField(max_digits=14, decimal_places=2)
    target_date = models.DateField()
    necessity_score = models.PositiveSmallIntegerField(default=3)
    current_funded_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    contribution_plan = models.JSONField(default=dict, blank=True)
    goal_risk_score = models.PositiveSmallIntegerField(default=3)
    status = models.CharField(max_length=40, default="watch")
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["target_date"]

    def __str__(self) -> str:
        return self.name


class GoalAccountLink(models.Model):
    goal = models.ForeignKey(Goal, related_name="account_allocations", on_delete=models.CASCADE)
    account = models.ForeignKey(Account, related_name="goal_allocations", on_delete=models.CASCADE)
    allocated_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    allocated_pct = models.DecimalField(max_digits=8, decimal_places=6, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["goal", "account"], name="unique_goal_account_link")
        ]

    def __str__(self) -> str:
        return f"{self.goal} ← {self.account}"
