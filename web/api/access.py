from __future__ import annotations

from django.conf import settings
from django.db.models import Q, QuerySet

from web.api import models

ADVISOR_GROUP = "advisor"
FINANCIAL_ANALYST_GROUP = "financial_analyst"


class Role:
    ADVISOR = "advisor"
    FINANCIAL_ANALYST = "financial_analyst"


def role_for_user(user) -> str:  # noqa: ANN001
    if not getattr(user, "is_authenticated", False):
        return ""
    group_names = set(user.groups.values_list("name", flat=True))
    if FINANCIAL_ANALYST_GROUP in group_names:
        return Role.FINANCIAL_ANALYST
    return Role.ADVISOR


def user_team_slug(user) -> str:  # noqa: ANN001
    if not getattr(user, "is_authenticated", False):
        return ""
    return getattr(settings, "MP20_REVIEW_TEAM_SLUG", "steadyhand")


def can_access_real_pii(user) -> bool:  # noqa: ANN001
    return role_for_user(user) == Role.ADVISOR


def team_households(user) -> QuerySet[models.Household]:  # noqa: ANN001
    if not getattr(user, "is_authenticated", False) or not can_access_real_pii(user):
        return models.Household.objects.none()
    return models.Household.objects.filter(Q(owner__isnull=True) | Q(owner__is_active=True))


def linkable_households(user) -> QuerySet[models.Household]:  # noqa: ANN001
    if not getattr(user, "is_authenticated", False) or not can_access_real_pii(user):
        return models.Household.objects.none()
    return models.Household.objects.filter(owner__is_active=True)


def team_workspaces(user) -> QuerySet[models.ReviewWorkspace]:  # noqa: ANN001
    if not getattr(user, "is_authenticated", False) or not can_access_real_pii(user):
        return models.ReviewWorkspace.objects.none()
    return models.ReviewWorkspace.objects.filter(owner__is_active=True)
