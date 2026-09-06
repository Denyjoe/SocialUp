from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

from apps.common.views import ExchangeRatesView, PublicStatsView
from apps.common.views_admin import AdminDashboardStatsView, AdminRevenueTrendView
from apps.common.views_reports import (
    AdminCategoryProfitabilityReportView,
    AdminLedgerCsvExportView,
    AdminMarginDistributionView,
    AdminOrdersCsvExportView,
    AdminReportSummaryView,
    AdminServiceMarginReportView,
    AdminTopCustomersReportView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/public/stats/", PublicStatsView.as_view(), name="public-stats"),
    path(
        "api/public/exchange-rates/",
        ExchangeRatesView.as_view(),
        name="public-exchange-rates",
    ),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/catalog/", include("apps.catalog.urls")),
    path("api/wallet/", include("apps.wallet.urls")),
    path("api/orders/", include("apps.orders.urls")),
    path("api/support/", include("apps.support.urls")),
    path("api/affiliate/", include("apps.affiliate.urls")),
    path("api/announcements/", include("apps.announcements.urls")),
    path("api/payments/", include("apps.payments.urls")),
    # This panel's own outward-facing JAP-compatible API (see apps/panelapi).
    path("api/v2/", include("apps.panelapi.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    # --- Admin dashboard API (staff-only, see apps/*/views_admin.py) ---
    path("api/admin/dashboard/stats/", AdminDashboardStatsView.as_view(), name="admin-dashboard-stats"),
    path(
        "api/admin/dashboard/revenue-trend/",
        AdminRevenueTrendView.as_view(),
        name="admin-dashboard-revenue-trend",
    ),
    path("api/admin/users/", include("apps.accounts.urls_admin")),
    path("api/admin/", include("apps.catalog.urls_admin")),
    path("api/admin/providers/", include("apps.providers.urls_admin")),
    path("api/admin/orders/", include("apps.orders.urls_admin")),
    path("api/admin/ledger/", include("apps.wallet.urls_admin")),
    path("api/admin/tickets/", include("apps.support.urls_admin")),
    path("api/admin/affiliate-settings/", include("apps.affiliate.urls_admin")),
    path("api/admin/announcements/", include("apps.announcements.urls_admin")),
    path("api/admin/", include("apps.promotions.urls_admin")),
    # Reporting and exports
    path("api/admin/reports/summary/", AdminReportSummaryView.as_view(), name="admin-report-summary"),
    path(
        "api/admin/reports/service-margins/",
        AdminServiceMarginReportView.as_view(),
        name="admin-report-service-margins",
    ),
    path(
        "api/admin/reports/top-customers/",
        AdminTopCustomersReportView.as_view(),
        name="admin-report-top-customers",
    ),
    path(
        "api/admin/reports/category-profitability/",
        AdminCategoryProfitabilityReportView.as_view(),
        name="admin-report-category-profitability",
    ),
    path(
        "api/admin/reports/margin-distribution/",
        AdminMarginDistributionView.as_view(),
        name="admin-report-margin-distribution",
    ),
    path("api/admin/exports/orders.csv", AdminOrdersCsvExportView.as_view(), name="admin-export-orders"),
    path("api/admin/exports/ledger.csv", AdminLedgerCsvExportView.as_view(), name="admin-export-ledger"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
