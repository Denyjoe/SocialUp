from django.contrib import admin

from .models import Order, OrderStatusHistory


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ("old_status", "new_status", "source", "changed_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "service",
        "quantity",
        "charge_amount",
        "status",
        "provider_order_id",
        "created_at",
    )
    list_filter = ("status", "provider")
    search_fields = ("id", "user__email", "link", "provider_order_id")
    inlines = [OrderStatusHistoryInline]
