from decimal import Decimal

from rest_framework import serializers

from .models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    gateway_label = serializers.CharField(source="get_gateway_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Transaction
        fields = (
            "id",
            "gateway",
            "gateway_label",
            "internal_reference",
            "amount_local",
            "amount_quote",
            "quote_currency",
            "pay_currency",
            "status",
            "status_label",
            "checkout_url",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class CreateDepositSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    gateway = serializers.ChoiceField(
        choices=Transaction.Gateway.choices, default=Transaction.Gateway.NOWPAYMENTS, required=False
    )
