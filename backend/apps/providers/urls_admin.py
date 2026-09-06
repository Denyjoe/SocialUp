from django.urls import path

from . import views_admin

urlpatterns = [
    path("", views_admin.AdminProviderListCreateView.as_view(), name="admin-provider-list"),
    path("<int:pk>/", views_admin.AdminProviderDetailView.as_view(), name="admin-provider-detail"),
    path(
        "<int:pk>/sync-services/",
        views_admin.AdminProviderSyncServicesView.as_view(),
        name="admin-provider-sync-services",
    ),
    path(
        "<int:pk>/check-balance/",
        views_admin.AdminProviderCheckBalanceView.as_view(),
        name="admin-provider-check-balance",
    ),
    path(
        "sync-logs/",
        views_admin.AdminProviderSyncLogListView.as_view(),
        name="admin-provider-sync-logs",
    ),
]
