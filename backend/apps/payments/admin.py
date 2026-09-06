from django.contrib import admin

from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "internal_reference",
        "user",
        "gateway",
        "amount_local",
        "amount_quote",
        "quote_currency",
        "pay_currency",
        "status",
        "created_at",
    )
    list_filter = ("gateway", "status")
    search_fields = ("internal_reference", "gateway_reference", "user__email")
    readonly_fields = [f.name for f in Transaction._meta.fields]

    def has_add_permission(self, request):
        return False
