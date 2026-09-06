from django.contrib import admin

from .models import Provider, ProviderServiceSyncLog
from .tasks import check_provider_balance, sync_provider_services


@admin.action(description="Sync services from provider now")
def sync_services_action(modeladmin, request, queryset):
    for provider in queryset:
        sync_provider_services.delay(provider.id)
    modeladmin.message_user(request, f"Queued service sync for {queryset.count()} provider(s).")


@admin.action(description="Check balance now")
def check_balance_action(modeladmin, request, queryset):
    for provider in queryset:
        check_provider_balance.delay(provider.id)
    modeladmin.message_user(request, f"Queued balance check for {queryset.count()} provider(s).")


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "provider_type",
        "is_active",
        "balance_cached",
        "balance_currency",
        "balance_last_checked_at",
    )
    list_filter = ("provider_type", "is_active")
    search_fields = ("name",)
    actions = [sync_services_action, check_balance_action]


@admin.register(ProviderServiceSyncLog)
class ProviderServiceSyncLogAdmin(admin.ModelAdmin):
    list_display = (
        "provider",
        "status",
        "services_created",
        "services_updated",
        "started_at",
        "finished_at",
    )
    list_filter = ("status", "provider")
