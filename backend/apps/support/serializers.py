from rest_framework import serializers

from apps.orders.models import Order

from .models import Ticket, TicketMessage


class TicketMessageSerializer(serializers.ModelSerializer):
    sender_email = serializers.CharField(source="sender.email", read_only=True)
    is_staff_reply = serializers.BooleanField(source="sender.is_staff", read_only=True)
    attachment_url = serializers.FileField(source="attachment", read_only=True, use_url=True)

    class Meta:
        model = TicketMessage
        fields = ("id", "sender_email", "is_staff_reply", "body", "attachment_url", "created_at")


class TicketListSerializer(serializers.ModelSerializer):
    message_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Ticket
        fields = (
            "id",
            "subject",
            "category",
            "status",
            "priority",
            "order",
            "message_count",
            "created_at",
            "updated_at",
        )


class TicketDetailSerializer(TicketListSerializer):
    messages = TicketMessageSerializer(many=True, read_only=True)

    class Meta(TicketListSerializer.Meta):
        fields = TicketListSerializer.Meta.fields + ("messages",)


class TicketCreateSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=200)
    category = serializers.ChoiceField(choices=Ticket.Category.choices, default=Ticket.Category.GENERAL)
    order = serializers.PrimaryKeyRelatedField(
        required=False, allow_null=True, queryset=Order.objects.none()
    )
    message = serializers.CharField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Scoped per-request so a customer can only link their own orders to a ticket.
        request = self.context.get("request")
        if request:
            self.fields["order"].queryset = Order.objects.filter(user=request.user)


class TicketMessageCreateSerializer(serializers.Serializer):
    body = serializers.CharField()
    attachment = serializers.FileField(required=False, allow_null=True)
