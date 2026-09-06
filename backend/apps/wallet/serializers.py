from rest_framework import serializers

from .models import LedgerEntry, Wallet


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ("currency", "cached_balance", "cached_balance_updated_at")


class LedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerEntry
        fields = ("id", "amount", "balance_after", "entry_type", "description", "created_at")
