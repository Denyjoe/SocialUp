from django.contrib import admin

from .models import Coupon, CouponRedemption, DepositBonusRule


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_type", "value", "used_count", "max_uses", "is_active", "expires_at")
    list_filter = ("discount_type", "is_active")
    search_fields = ("code", "description")


@admin.register(CouponRedemption)
class CouponRedemptionAdmin(admin.ModelAdmin):
    list_display = ("coupon", "user", "amount_discounted", "created_at")
    search_fields = ("coupon__code", "user__email")


@admin.register(DepositBonusRule)
class DepositBonusRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "min_amount", "bonus_percent", "is_active")
    list_filter = ("is_active",)
