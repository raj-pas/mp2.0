"""URL config for the Phase 1 scaffold."""

from __future__ import annotations

from django.contrib import admin
from django.urls import path

from web.api import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/login/", views.LocalLoginView.as_view(), name="local-login"),
    path("api/auth/logout/", views.LocalLogoutView.as_view(), name="local-logout"),
    path("api/session/", views.SessionView.as_view(), name="session"),
    path("api/clients/", views.ClientListView.as_view(), name="client-list"),
    path("api/clients/<str:household_id>/", views.ClientDetailView.as_view(), name="client-detail"),
    path(
        "api/clients/<str:household_id>/generate-portfolio/",
        views.GeneratePortfolioView.as_view(),
        name="generate-portfolio",
    ),
    path(
        "api/clients/<str:household_id>/portfolio-runs/",
        views.PortfolioRunListView.as_view(),
        name="portfolio-run-list",
    ),
    path(
        "api/clients/<str:household_id>/portfolio-runs/<str:run_id>/decline/",
        views.PortfolioRunDeclineView.as_view(),
        name="portfolio-run-decline",
    ),
    path(
        "api/clients/<str:household_id>/portfolio-runs/<str:run_id>/audit-export/",
        views.PortfolioRunAuditExportView.as_view(),
        name="portfolio-run-audit-export",
    ),
    path(
        "api/clients/<str:household_id>/planning-versions/",
        views.PlanningVersionListView.as_view(),
        name="planning-version-list",
    ),
    path("api/cma/snapshots/", views.CMASnapshotListView.as_view(), name="cma-snapshot-list"),
    path(
        "api/cma/snapshots/<str:snapshot_id>/",
        views.CMASnapshotDetailView.as_view(),
        name="cma-snapshot-detail",
    ),
    path("api/cma/active/", views.CMAActiveView.as_view(), name="cma-active"),
    path("api/cma/audit/", views.CMAAuditView.as_view(), name="cma-audit"),
    path(
        "api/cma/snapshots/<str:snapshot_id>/publish/",
        views.CMASnapshotPublishView.as_view(),
        name="cma-snapshot-publish",
    ),
    path(
        "api/cma/snapshots/<str:snapshot_id>/frontier/",
        views.CMAFrontierView.as_view(),
        name="cma-frontier",
    ),
    path(
        "api/review-workspaces/",
        views.ReviewWorkspaceListCreateView.as_view(),
        name="review-workspace-list",
    ),
    path(
        "api/review-workspaces/<str:workspace_id>/",
        views.ReviewWorkspaceDetailView.as_view(),
        name="review-workspace-detail",
    ),
    path(
        "api/review-workspaces/<str:workspace_id>/upload/",
        views.ReviewWorkspaceUploadView.as_view(),
        name="review-workspace-upload",
    ),
    path(
        "api/review-workspaces/<str:workspace_id>/documents/<int:document_id>/retry/",
        views.ReviewDocumentRetryView.as_view(),
        name="review-document-retry",
    ),
    path(
        "api/review-workspaces/<str:workspace_id>/facts/",
        views.ReviewWorkspaceFactsView.as_view(),
        name="review-workspace-facts",
    ),
    path(
        "api/review-workspaces/<str:workspace_id>/state/",
        views.ReviewWorkspaceStateView.as_view(),
        name="review-workspace-state",
    ),
    path(
        "api/review-workspaces/<str:workspace_id>/approve-section/",
        views.ReviewWorkspaceSectionApprovalView.as_view(),
        name="review-workspace-approve-section",
    ),
    path(
        "api/review-workspaces/<str:workspace_id>/matches/",
        views.ReviewWorkspaceMatchView.as_view(),
        name="review-workspace-matches",
    ),
    path(
        "api/review-workspaces/<str:workspace_id>/manual-reconcile/",
        views.ReviewWorkspaceManualReconcileView.as_view(),
        name="review-workspace-manual-reconcile",
    ),
    path(
        "api/review-workspaces/<str:workspace_id>/commit/",
        views.ReviewWorkspaceCommitView.as_view(),
        name="review-workspace-commit",
    ),
]
