from rest_framework import serializers

from apps.catalog.models import Service
from apps.wallet.services import InsufficientBalanceError

from .models import Order
from .services import OrderService, OrderValidationError


class OrderSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "service",
            "service_name",
            "link",
            "quantity",
            "charge_amount",
            "discount_amount",
            "status",
            "provider_order_id",
            "start_count",
            "remains",
            "progress_percent",
            "error_message",
            "created_at",
        )
        read_only_fields = fields


class OrderCreateSerializer(serializers.Serializer):
    service = serializers.PrimaryKeyRelatedField(queryset=Service.objects.filter(is_active=True))
    link = serializers.URLField(max_length=500)
    quantity = serializers.IntegerField(min_value=1)
    coupon_code = serializers.CharField(required=False, allow_blank=True)

    def create(self, validated_data):
        user = self.context["request"].user
        try:
            return OrderService.create_order(
                user=user,
                service=validated_data["service"],
                link=validated_data["link"],
                quantity=validated_data["quantity"],
                coupon_code=validated_data.get("coupon_code", ""),
            )
        except OrderValidationError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        except InsufficientBalanceError as exc:
            raise serializers.ValidationError("Insufficient wallet balance for this order.") from exc
