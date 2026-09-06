from django.urls import path

from . import views_admin

urlpatterns = [
    path("", views_admin.AdminAffiliateSettingsView.as_view(), name="admin-affiliate-settings"),
]
