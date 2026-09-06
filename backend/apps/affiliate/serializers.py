from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class AffiliateSummarySerializer(serializers.Serializer):
    referral_code = serializers.CharField()
    commission_percent = serializers.DecimalField(max_digits=5, decimal_places=2)
    total_referrals = serializers.IntegerField()
    total_commission_earned = serializers.DecimalField(max_digits=14, decimal_places=2)


class ReferredUserSerializer(serializers.ModelSerializer):
    orders_count = serializers.IntegerField(read_only=True)
    commission_earned = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "date_joined", "orders_count", "commission_earned")
