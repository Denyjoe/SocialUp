from rest_framework import serializers

from .models import AffiliateSettings


class AdminAffiliateSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AffiliateSettings
        fields = ("commission_percent", "updated_at")
