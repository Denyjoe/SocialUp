from django.db.models import Count
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Ticket
from .serializers_admin import (
    AdminTicketDetailSerializer,
    AdminTicketListSerializer,
    AdminTicketReplySerializer,
    AdminTicketStatusSerializer,
)
from .services import SupportService


class AdminTicketListView(generics.ListAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = AdminTicketListSerializer

    def get_queryset(self):
        qs = Ticket.objects.select_related("user").annotate(message_count=Count("messages"))
        if status_filter := self.request.query_params.get("status"):
            qs = qs.filter(status=status_filter)
        if user_search := self.request.query_params.get("user"):
            qs = qs.filter(user__email__icontains=user_search)
        return qs.order_by("-updated_at")


class AdminTicketDetailView(generics.RetrieveAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = AdminTicketDetailSerializer
    queryset = Ticket.objects.select_related("user").prefetch_related("messages__sender")


class AdminTicketReplyView(APIView):
    permission_classes = (permissions.IsAdminUser,)

    def post(self, request, pk):
        ticket = generics.get_object_or_404(Ticket, pk=pk)
        serializer = AdminTicketReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        SupportService.add_message(ticket=ticket, sender=request.user, body=serializer.validated_data["body"])
        ticket.refresh_from_db()
        return Response(AdminTicketDetailSerializer(ticket).data)


class AdminTicketStatusView(APIView):
    permission_classes = (permissions.IsAdminUser,)

    def post(self, request, pk):
        ticket = generics.get_object_or_404(Ticket, pk=pk)
        serializer = AdminTicketStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket.status = serializer.validated_data["status"]
        ticket.save(update_fields=["status", "updated_at"])
        return Response(AdminTicketListSerializer(ticket).data, status=status.HTTP_200_OK)
