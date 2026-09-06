from django.urls import path

from . import views

urlpatterns = [
    path("deposits/", views.DepositListCreateView.as_view(), name="deposit-list-create"),
    path("deposits/<str:reference>/", views.DepositDetailView.as_view(), name="deposit-detail"),
    path(
        "webhooks/nowpayments/",
        views.NOWPaymentsWebhookView.as_view(),
        name="nowpayments-webhook",
    ),
]
