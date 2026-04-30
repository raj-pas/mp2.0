from __future__ import annotations

import datetime
import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import web.api.models


def delete_v1_portfolio_runs(apps, schema_editor):  # noqa: ANN001, ARG001
    PortfolioRunLinkRecommendation = apps.get_model("api", "PortfolioRunLinkRecommendation")
    PortfolioRun = apps.get_model("api", "PortfolioRun")
    PortfolioRunLinkRecommendation.objects.all().delete()
    PortfolioRun.objects.all().delete()


def populate_goal_account_link_ids(apps, schema_editor):  # noqa: ANN001, ARG001
    GoalAccountLink = apps.get_model("api", "GoalAccountLink")
    for link in GoalAccountLink.objects.filter(external_id__isnull=True):
        link.external_id = str(uuid.uuid4())
        link.save(update_fields=["external_id"])


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("api", "0006_household_risk_five_point"),
    ]

    operations = [
        migrations.RunPython(delete_v1_portfolio_runs, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="household",
            name="last_engine_output",
        ),
        migrations.AddField(
            model_name="account",
            name="cash_state",
            field=models.CharField(
                choices=[
                    ("invested", "Invested"),
                    ("onboarding_cash", "Onboarding cash"),
                    ("pending_investment", "Pending investment"),
                ],
                default="invested",
                max_length=40,
            ),
        ),
        migrations.AddField(
            model_name="goalaccountlink",
            name="external_id",
            field=models.CharField(blank=True, max_length=120, null=True),
        ),
        migrations.RunPython(populate_goal_account_link_ids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="goalaccountlink",
            name="external_id",
            field=models.CharField(
                default=web.api.models.uuid_string,
                max_length=120,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="cmafundassumption",
            name="aliases",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="cmafundassumption",
            name="geography_weights",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="portfoliorun",
            name="as_of_date",
            field=models.DateField(default=datetime.date(2026, 1, 1)),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="portfoliorun",
            name="approval_snapshot_hash",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="portfoliorun",
            name="cma_hash",
            field=models.CharField(default="", max_length=64),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="portfoliorun",
            name="reviewed_state_hash",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="portfoliorun",
            name="run_signature",
            field=models.CharField(db_index=True, default="", max_length=64),
            preserve_default=False,
        ),
        migrations.RemoveField(
            model_name="portfoliorun",
            name="stale_reason",
        ),
        migrations.RemoveField(
            model_name="portfoliorun",
            name="status",
        ),
        migrations.AddField(
            model_name="portfoliorunlinkrecommendation",
            name="current_comparison",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="portfoliorunlinkrecommendation",
            name="explanation",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="portfoliorunlinkrecommendation",
            name="goal_account_link",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="api.goalaccountlink",
            ),
        ),
        migrations.AddField(
            model_name="portfoliorunlinkrecommendation",
            name="link_external_id",
            field=models.CharField(default="", max_length=120),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="portfoliorunlinkrecommendation",
            name="warnings",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.CreateModel(
            name="PortfolioRunEvent",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "event_type",
                    models.CharField(
                        choices=[
                            ("generated", "Generated"),
                            ("reused", "Reused"),
                            ("regenerated_after_decline", "Regenerated after decline"),
                            ("invalidated_by_cma", "Invalidated by CMA"),
                            (
                                "invalidated_by_household_change",
                                "Invalidated by household change",
                            ),
                            ("advisor_declined", "Advisor declined"),
                            ("audit_exported", "Audit exported"),
                            ("generation_failed", "Generation failed"),
                            ("hash_mismatch", "Hash mismatch"),
                        ],
                        max_length=80,
                    ),
                ),
                ("actor", models.CharField(default="system", max_length=255)),
                ("reason_code", models.CharField(blank=True, max_length=120)),
                ("note", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "household",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="portfolio_run_events",
                        to="api.household",
                    ),
                ),
                (
                    "portfolio_run",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="events",
                        to="api.portfoliorun",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
    ]
