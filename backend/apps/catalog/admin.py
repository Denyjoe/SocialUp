from django.contrib import admin

from .models import (
    Category,
    PlatformSetting,
    PricingRule,
    Service,
    ServiceHealthStat,
    ServiceProviderMapping,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "platform", "sort_order", "is_active")
    list_filter = ("platform", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "provider",
        "retail_rate_per_1000",
        "min_quantity",
        "max_quantity",
        "is_active",
    )
    list_filter = ("category", "provider", "is_active", "service_type")
    search_fields = ("name", "provider_service_id")


@admin.register(PlatformSetting)
class PlatformSettingAdmin(admin.ModelAdmin):
    list_display = ("usd_to_local_rate", "updated_at")


@admin.register(PricingRule)
class PricingRuleAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "scope",
        "category",
        "platform",
        "markup_percent",
        "priority",
        "is_active",
    )
    list_filter = ("scope", "platform", "is_active")


@admin.register(ServiceHealthStat)
class ServiceHealthStatAdmin(admin.ModelAdmin):
    """Read-only: this is a computed cache (see apps.catalog.health), not
    something an admin edits directly — recompute by adjusting the
    underlying orders, or wait for the next hourly beat run."""

    list_display = (
        "service",
        "sample_size",
        "avg_start_minutes",
        "avg_speed_per_hour",
        "refill_rate_percent",
        "updated_at",
    )
    search_fields = ("service__name",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ServiceProviderMapping)
class ServiceProviderMappingAdmin(admin.ModelAdmin):
    """Smart API Auto-Routing groundwork — manage which provider(s) can
    fulfil a service, and at what cost, here. resolve_best_mapping()
    (apps.catalog.routing) picks the cheapest active one on an active
    provider at order time. Curating a second mapping for a service is a
    deliberate call that the two providers' SKUs are genuinely
    equivalent — use `notes` to record why."""

    list_display = (
        "service",
        "provider",
        "cost_rate_per_1000",
        "priority",
        "is_active",
    )
    list_filter = ("provider", "is_active")
    search_fields = ("service__name", "provider_service_id")
    autocomplete_fields = ("service",)
