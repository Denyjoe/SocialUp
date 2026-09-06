from rest_framework import serializers

from .models import Order, OrderStatusHistory


class AdminOrderStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusHistory
        fields = ("old_status", "new_status", "source", "changed_at")


class AdminOrderSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True)
    provider_name = serializers.CharField(source="provider.name", read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "user",
            "user_email",
            "service",
            "service_name",
            "provider",
            "provider_name",
            "link",
            "quantity",
            "charge_amount",
            "cost_amount",
            "cost_currency",
            "status",
            "provider_order_id",
            "start_count",
            "remains",
            "progress_percent",
            "error_message",
            "refill_status",
            "cancel_status",
            "created_at",
            "last_synced_at",
        )
        read_only_fields = fields


class AdminOrderDetailSerializer(AdminOrderSerializer):
    status_history = AdminOrderStatusHistorySerializer(many=True, read_only=True)

    class Meta(AdminOrderSerializer.Meta):
        fields = AdminOrderSerializer.Meta.fields + ("status_history",)


class AdminOrderRefundSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)
