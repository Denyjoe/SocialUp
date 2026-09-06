from django.urls import path

from . import views_admin

urlpatterns = [
    path("", views_admin.AdminOrderListView.as_view(), name="admin-order-list"),
    path(
        "bulk-action/",
        views_admin.AdminOrderBulkActionView.as_view(),
        name="admin-order-bulk-action",
    ),
    path("<uuid:pk>/", views_admin.AdminOrderDetailView.as_view(), name="admin-order-detail"),
    path("<uuid:pk>/refund/", views_admin.AdminOrderRefundView.as_view(), name="admin-order-refund"),
    path(
        "<uuid:pk>/retry-submit/",
        views_admin.AdminOrderRetrySubmitView.as_view(),
        name="admin-order-retry-submit",
    ),
]
