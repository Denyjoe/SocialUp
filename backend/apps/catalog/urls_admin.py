from django.urls import path

from . import views_admin

urlpatterns = [
    path("categories/", views_admin.AdminCategoryListCreateView.as_view(), name="admin-category-list"),
    path(
        "categories/<int:pk>/",
        views_admin.AdminCategoryDetailView.as_view(),
        name="admin-category-detail",
    ),
    path("services/", views_admin.AdminServiceListCreateView.as_view(), name="admin-service-list"),
    # Before the <int:pk> route, otherwise "bulk-update" is parsed as a pk.
    path(
        "services/bulk-update/",
        views_admin.AdminServiceBulkUpdateView.as_view(),
        name="admin-service-bulk-update",
    ),
    path(
        "services/<int:pk>/",
        views_admin.AdminServiceDetailView.as_view(),
        name="admin-service-detail",
    ),
    path(
        "services/reprice-from-rules/",
        views_admin.AdminServiceRepriceFromRulesView.as_view(),
        name="admin-service-reprice-from-rules",
    ),
    path(
        "platform-settings/",
        views_admin.AdminPlatformSettingView.as_view(),
        name="admin-platform-settings",
    ),
    path(
        "pricing-rules/",
        views_admin.AdminPricingRuleListCreateView.as_view(),
        name="admin-pricing-rule-list",
    ),
    path(
        "pricing-rules/<int:pk>/",
        views_admin.AdminPricingRuleDetailView.as_view(),
        name="admin-pricing-rule-detail",
    ),
]
