"""Project RBAC hook.

The scaffold started with an allow-all hook so endpoints could adopt a shared
authorization surface early. Real-data review now exists, so the safe default is
authenticated access; views that must be public opt out explicitly with
``AllowAny``.
"""

from __future__ import annotations

from rest_framework.permissions import BasePermission


class AllowPhaseOneAccess(BasePermission):
    def has_permission(self, request, view) -> bool:  # noqa: ANN001
        return bool(request.user and request.user.is_authenticated)
