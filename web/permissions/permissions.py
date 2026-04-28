"""Phase 1 RBAC hook.

All requests pass for now, but endpoints depend on this permission class so the
authorization surface can be tightened without touching every view.
"""

from __future__ import annotations

from rest_framework.permissions import BasePermission


class AllowPhaseOneAccess(BasePermission):
    def has_permission(self, request, view) -> bool:  # noqa: ANN001
        return True
