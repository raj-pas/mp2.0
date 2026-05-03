from __future__ import annotations

from django.contrib import admin

from web.api import models

admin.site.register(models.Household)
admin.site.register(models.Person)
admin.site.register(models.Account)
admin.site.register(models.Holding)
admin.site.register(models.Goal)
admin.site.register(models.GoalAccountLink)
admin.site.register(models.CMASnapshot)
admin.site.register(models.CMAFundAssumption)
admin.site.register(models.CMACorrelation)
admin.site.register(models.PortfolioRun)
admin.site.register(models.PortfolioRunLinkRecommendation)
admin.site.register(models.PlanningVersion)
admin.site.register(models.AdvisorProfile)
admin.site.register(models.FactOverride)


@admin.register(models.Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("id", "advisor", "severity", "status", "route", "created_at")
    list_filter = ("status", "severity")
    search_fields = ("description", "ops_notes", "linear_issue_url")
    readonly_fields = (
        "advisor",
        "severity",
        "description",
        "what_were_you_trying",
        "route",
        "session_id",
        "browser_user_agent",
        "created_at",
    )
