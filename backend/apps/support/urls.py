from django.urls import path

from . import views

urlpatterns = [
    path("tickets/", views.TicketListCreateView.as_view(), name="ticket-list-create"),
    path("tickets/<int:pk>/", views.TicketDetailView.as_view(), name="ticket-detail"),
    path(
        "tickets/<int:pk>/messages/",
        views.TicketMessageCreateView.as_view(),
        name="ticket-message-create",
    ),
]
