# Generated for MP2.0 Phase 1 scaffold.

from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Household",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("external_id", models.CharField(max_length=120, unique=True)),
                ("display_name", models.CharField(max_length=255)),
                (
                    "household_type",
                    models.CharField(
                        choices=[("single", "Single"), ("couple", "Couple")], max_length=20
                    ),
                ),
                ("household_risk_score", models.PositiveSmallIntegerField(default=5)),
                ("external_assets", models.JSONField(blank=True, default=list)),
                ("notes", models.TextField(blank=True)),
                ("last_engine_output", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["display_name"]},
        ),
        migrations.CreateModel(
            name="Account",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("external_id", models.CharField(max_length=120, unique=True)),
                ("account_type", models.CharField(max_length=40)),
                ("regulatory_objective", models.CharField(max_length=40)),
                ("regulatory_time_horizon", models.CharField(max_length=20)),
                ("regulatory_risk_rating", models.CharField(max_length=20)),
                ("current_value", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                (
                    "contribution_room",
                    models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True),
                ),
                ("contribution_history", models.JSONField(blank=True, default=list)),
                ("is_held_at_purpose", models.BooleanField(default=True)),
                (
                    "household",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="accounts",
                        to="api.household",
                    ),
                ),
            ],
            options={"ordering": ["account_type", "external_id"]},
        ),
        migrations.CreateModel(
            name="Goal",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("external_id", models.CharField(max_length=120, unique=True)),
                ("name", models.CharField(max_length=255)),
                ("target_amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("target_date", models.DateField()),
                ("necessity_score", models.PositiveSmallIntegerField(default=3)),
                (
                    "current_funded_amount",
                    models.DecimalField(decimal_places=2, default=0, max_digits=14),
                ),
                ("contribution_plan", models.JSONField(blank=True, default=dict)),
                ("goal_risk_score", models.PositiveSmallIntegerField(default=3)),
                ("status", models.CharField(default="watch", max_length=40)),
                ("notes", models.TextField(blank=True)),
                (
                    "household",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="goals",
                        to="api.household",
                    ),
                ),
            ],
            options={"ordering": ["target_date"]},
        ),
        migrations.CreateModel(
            name="Person",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("external_id", models.CharField(max_length=120, unique=True)),
                ("name", models.CharField(max_length=255)),
                ("dob", models.DateField()),
                ("marital_status", models.CharField(blank=True, max_length=80)),
                ("blended_family_flag", models.BooleanField(default=False)),
                ("citizenship", models.CharField(default="Canada", max_length=120)),
                ("residency", models.CharField(default="Canada", max_length=120)),
                ("health_indicators", models.JSONField(blank=True, default=dict)),
                ("longevity_assumption", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("employment", models.JSONField(blank=True, default=dict)),
                ("pensions", models.JSONField(blank=True, default=list)),
                (
                    "investment_knowledge",
                    models.CharField(
                        choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")],
                        default="medium",
                        max_length=20,
                    ),
                ),
                ("trusted_contact_person", models.CharField(blank=True, max_length=255)),
                ("poa_status", models.CharField(blank=True, max_length=120)),
                ("will_status", models.CharField(blank=True, max_length=120)),
                ("beneficiary_designations", models.JSONField(blank=True, default=list)),
                (
                    "household",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="members",
                        to="api.household",
                    ),
                ),
            ],
            options={"ordering": ["dob"]},
        ),
        migrations.AddField(
            model_name="account",
            name="owner_person",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="accounts",
                to="api.person",
            ),
        ),
        migrations.CreateModel(
            name="Holding",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("sleeve_id", models.CharField(max_length=120)),
                ("sleeve_name", models.CharField(max_length=255)),
                ("weight", models.DecimalField(decimal_places=6, max_digits=8)),
                ("market_value", models.DecimalField(decimal_places=2, max_digits=14)),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="holdings",
                        to="api.account",
                    ),
                ),
            ],
            options={"ordering": ["sleeve_name"]},
        ),
        migrations.CreateModel(
            name="GoalAccountLink",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "allocated_amount",
                    models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True),
                ),
                (
                    "allocated_pct",
                    models.DecimalField(blank=True, decimal_places=6, max_digits=8, null=True),
                ),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="goal_allocations",
                        to="api.account",
                    ),
                ),
                (
                    "goal",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="account_allocations",
                        to="api.goal",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("goal", "account"), name="unique_goal_account_link"
                    )
                ]
            },
        ),
    ]
