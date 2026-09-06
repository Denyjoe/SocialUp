from django.urls import path

from . import views

urlpatterns = [
    path("", views.WalletView.as_view(), name="wallet-detail"),
    path("ledger/", views.LedgerListView.as_view(), name="wallet-ledger"),
]
