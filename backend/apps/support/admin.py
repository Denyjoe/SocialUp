from django.contrib import admin

from .models import Ticket, TicketMessage


class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 0
    readonly_fields = ("sender", "body", "attachment", "created_at")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("subject", "user", "category", "status", "priority", "updated_at")
    list_filter = ("status", "category", "priority")
    search_fields = ("subject", "user__email")
    inlines = [TicketMessageInline]
