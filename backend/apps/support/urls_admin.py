from django.urls import path

from . import views_admin

urlpatterns = [
    path("", views_admin.AdminTicketListView.as_view(), name="admin-ticket-list"),
    path("<int:pk>/", views_admin.AdminTicketDetailView.as_view(), name="admin-ticket-detail"),
    path("<int:pk>/reply/", views_admin.AdminTicketReplyView.as_view(), name="admin-ticket-reply"),
    path("<int:pk>/status/", views_admin.AdminTicketStatusView.as_view(), name="admin-ticket-status"),
]
