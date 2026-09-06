from rest_framework import serializers

from .models import Ticket, TicketMessage


class AdminTicketMessageSerializer(serializers.ModelSerializer):
    sender_email = serializers.CharField(source="sender.email", read_only=True)
    is_staff_reply = serializers.BooleanField(source="sender.is_staff", read_only=True)
    attachment_url = serializers.FileField(source="attachment", read_only=True, use_url=True)

    class Meta:
        model = TicketMessage
        fields = ("id", "sender_email", "is_staff_reply", "body", "attachment_url", "created_at")


class AdminTicketListSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)
    message_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Ticket
        fields = (
            "id",
            "user_email",
            "subject",
            "category",
            "status",
            "priority",
            "order",
            "message_count",
            "created_at",
            "updated_at",
        )


class AdminTicketDetailSerializer(AdminTicketListSerializer):
    messages = AdminTicketMessageSerializer(many=True, read_only=True)

    class Meta(AdminTicketListSerializer.Meta):
        fields = AdminTicketListSerializer.Meta.fields + ("messages",)


class AdminTicketStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Ticket.Status.choices)


class AdminTicketReplySerializer(serializers.Serializer):
    body = serializers.CharField()
