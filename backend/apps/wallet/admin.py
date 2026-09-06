import uuid
from decimal import Decimal

from django.contrib import admin

from .models import LedgerEntry, Wallet
from .services import WalletService

TEST_GRANT_AMOUNT = Decimal("50000.00")


@admin.action(description=f"Grant {TEST_GRANT_AMOUNT} TZS test funds to selected wallets")
def grant_test_funds(modeladmin, request, queryset):
    for wallet in queryset:
        WalletService.credit(
            wallet=wallet,
            amount=TEST_GRANT_AMOUNT,
            entry_type=LedgerEntry.EntryType.ADMIN_ADJUSTMENT_CREDIT,
            idempotency_key=f"admin-grant-{wallet.pk}-{uuid.uuid4().hex[:8]}",
            description=f"Test funds granted via admin by {request.user.email}",
            created_by=request.user,
        )


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("user", "currency", "cached_balance", "cached_balance_updated_at")
    search_fields = ("user__email",)
    actions = [grant_test_funds]


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ("wallet", "entry_type", "amount", "balance_after", "created_at")
    list_filter = ("entry_type",)
    search_fields = ("wallet__user__email", "idempotency_key")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
