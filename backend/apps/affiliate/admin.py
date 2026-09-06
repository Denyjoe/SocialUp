from django.contrib import admin

from .models import AffiliateCommission, AffiliateSettings


@admin.register(AffiliateSettings)
class AffiliateSettingsAdmin(admin.ModelAdmin):
    list_display = ("commission_percent", "updated_at")


@admin.register(AffiliateCommission)
class AffiliateCommissionAdmin(admin.ModelAdmin):
    list_display = ("referrer", "referred_user", "order", "amount", "created_at")
    search_fields = ("referrer__email", "referred_user__email")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
