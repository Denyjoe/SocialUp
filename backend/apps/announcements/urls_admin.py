from django.urls import path

from . import views_admin

urlpatterns = [
    path("", views_admin.AdminAnnouncementListCreateView.as_view(), name="admin-announcement-list"),
    path("<int:pk>/", views_admin.AdminAnnouncementDetailView.as_view(), name="admin-announcement-detail"),
    path(
        "<int:pk>/send-email/",
        views_admin.AdminAnnouncementSendEmailView.as_view(),
        name="admin-announcement-send-email",
    ),
]
