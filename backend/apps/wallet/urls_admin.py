from django.urls import path

from . import views_admin

urlpatterns = [
    path("", views_admin.AdminLedgerListView.as_view(), name="admin-ledger-list"),
]
