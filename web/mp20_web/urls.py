"""URL config for the Phase 1 scaffold."""

from __future__ import annotations

from django.contrib import admin
from django.urls import path

from web.api import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/session/", views.SessionView.as_view(), name="session"),
    path("api/clients/", views.ClientListView.as_view(), name="client-list"),
    path("api/clients/<str:household_id>/", views.ClientDetailView.as_view(), name="client-detail"),
    path(
        "api/clients/<str:household_id>/generate-portfolio/",
        views.GeneratePortfolioView.as_view(),
        name="generate-portfolio",
    ),
]
