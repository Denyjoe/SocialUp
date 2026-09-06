from django.urls import path

from . import views

urlpatterns = [
    path("", views.OrderListCreateView.as_view(), name="order-list-create"),
    path("bulk/", views.BulkOrderCreateView.as_view(), name="order-bulk-create"),
    path("<uuid:pk>/", views.OrderDetailView.as_view(), name="order-detail"),
]
