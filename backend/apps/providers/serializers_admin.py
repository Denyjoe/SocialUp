from rest_framework import serializers

from .models import Provider, ProviderServiceSyncLog


class AdminProviderSerializer(serializers.ModelSerializer):
    services_count = serializers.IntegerField(read_only=True)
    # Write-only: an admin can SET the key, but it's never sent back down —
    # this is the same secret used to spend the provider's real balance.
    api_key = serializers.CharField(write_only=True, required=False, allow_blank=True)
    has_api_key = serializers.SerializerMethodField()

    class Meta:
        model = Provider
        fields = (
            "id",
            "name",
            "provider_type",
            "base_url",
            "api_key",
            "has_api_key",
            "is_active",
            "balance_cached",
            "balance_currency",
            "balance_last_checked_at",
            "services_count",
        )

    def get_has_api_key(self, obj: Provider) -> bool:
        return bool(obj.api_key)


class AdminProviderSyncLogSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source="provider.name", read_only=True)

    class Meta:
        model = ProviderServiceSyncLog
        fields = (
            "id",
            "provider",
            "provider_name",
            "started_at",
            "finished_at",
            "services_created",
            "services_updated",
            "status",
            "error_text",
        )
