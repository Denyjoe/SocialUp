from rest_framework import serializers

from .models import LedgerEntry


class AdminLedgerEntrySerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="wallet.user.email", read_only=True)
    created_by_email = serializers.CharField(source="created_by.email", read_only=True)

    class Meta:
        model = LedgerEntry
        fields = (
            "id",
            "wallet",
            "user_email",
            "amount",
            "balance_after",
            "entry_type",
            "reference_type",
            "reference_id",
            "description",
            "created_by_email",
            "created_at",
        )
