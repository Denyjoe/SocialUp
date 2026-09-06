from django.urls import path

from . import views_admin

urlpatterns = [
    path("", views_admin.AdminUserListView.as_view(), name="admin-user-list"),
    path("<int:pk>/", views_admin.AdminUserDetailView.as_view(), name="admin-user-detail"),
    path(
        "<int:pk>/adjust-balance/",
        views_admin.AdminUserAdjustBalanceView.as_view(),
        name="admin-user-adjust-balance",
    ),
    path("<int:pk>/status/", views_admin.AdminUserStatusView.as_view(), name="admin-user-status"),
]
