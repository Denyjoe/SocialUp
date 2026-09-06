from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Ticket
from .serializers import (
    TicketCreateSerializer,
    TicketDetailSerializer,
    TicketListSerializer,
    TicketMessageCreateSerializer,
    TicketMessageSerializer,
)
from .services import SupportService


class TicketListCreateView(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        from django.db.models import Count

        return (
            Ticket.objects.filter(user=self.request.user)
            .annotate(message_count=Count("messages"))
            .order_by("-updated_at")
        )

    def get_serializer_class(self):
        return TicketCreateSerializer if self.request.method == "POST" else TicketListSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = SupportService.create_ticket(
            user=request.user,
            subject=serializer.validated_data["subject"],
            category=serializer.validated_data["category"],
            message_body=serializer.validated_data["message"],
            order=serializer.validated_data.get("order"),
        )
        return Response(TicketDetailSerializer(ticket).data, status=status.HTTP_201_CREATED)


class TicketDetailView(generics.RetrieveAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = TicketDetailSerializer

    def get_queryset(self):
        return Ticket.objects.filter(user=self.request.user).prefetch_related("messages__sender")


class TicketMessageCreateView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, pk):
        ticket = generics.get_object_or_404(Ticket, pk=pk, user=request.user)
        serializer = TicketMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = SupportService.add_message(
            ticket=ticket,
            sender=request.user,
            body=serializer.validated_data["body"],
            attachment=serializer.validated_data.get("attachment"),
        )
        return Response(TicketMessageSerializer(message).data, status=status.HTTP_201_CREATED)
