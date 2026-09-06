from rest_framework import serializers

from .models import Coupon, CouponRedemption, DepositBonusRule


class AdminCouponSerializer(serializers.ModelSerializer):
    redemptions_count = serializers.IntegerField(source="used_count", read_only=True)

    class Meta:
        model = Coupon
        fields = (
            "id",
            "code",
            "description",
            "discount_type",
            "value",
            "min_order_amount",
            "max_discount_amount",
            "max_uses",
            "max_uses_per_user",
            "used_count",
            "redemptions_count",
            "starts_at",
            "expires_at",
            "is_active",
            "created_at",
        )
        read_only_fields = ("used_count", "created_at")

    def validate(self, attrs):
        discount_type = attrs.get("discount_type", getattr(self.instance, "discount_type", None))
        value = attrs.get("value", getattr(self.instance, "value", None))
        if discount_type == Coupon.DiscountType.PERCENT and value is not None and value > 100:
            raise serializers.ValidationError(
                {"value": "A percent discount cannot be more than 100."}
            )
        if value is not None and value <= 0:
            raise serializers.ValidationError({"value": "Discount must be greater than zero."})
        return attrs


class AdminCouponRedemptionSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    coupon_code = serializers.CharField(source="coupon.code", read_only=True)

    class Meta:
        model = CouponRedemption
        fields = ("id", "coupon_code", "user_email", "order", "amount_discounted", "created_at")


class AdminDepositBonusRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepositBonusRule
        fields = (
            "id",
            "name",
            "min_amount",
            "bonus_percent",
            "max_bonus_amount",
            "is_active",
            "starts_at",
            "expires_at",
            "created_at",
        )
        read_only_fields = ("created_at",)
