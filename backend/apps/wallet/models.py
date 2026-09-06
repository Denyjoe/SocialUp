from django.conf import settings
from django.db import IntegrityError, models

from apps.common.models import TimeStampedModel, UUIDPKModel


class Wallet(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet"
    )
    currency = models.CharField(max_length=10, default="TZS")
    cached_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cached_balance_updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.user.email} wallet ({self.cached_balance} {self.currency})"


class LedgerEntry(UUIDPKModel, TimeStampedModel):
    """Immutable. The only writer is WalletService (see services.py) — never
    create, update, or delete these directly."""

    class EntryType(models.TextChoices):
        DEPOSIT = "deposit", "Deposit"
        ORDER_PAYMENT = "order_payment", "Order payment"
        ORDER_REFUND = "order_refund", "Order refund"
        ADMIN_ADJUSTMENT_CREDIT = "admin_credit", "Admin adjustment (credit)"
        ADMIN_ADJUSTMENT_DEBIT = "admin_debit", "Admin adjustment (debit)"
        AFFILIATE_COMMISSION = "affiliate_commission", "Affiliate commission"

    wallet = models.ForeignKey(
        Wallet, on_delete=models.PROTECT, related_name="ledger_entries"
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)  # signed: +credit, -debit
    balance_after = models.DecimalField(max_digits=14, decimal_places=2)
    entry_type = models.CharField(max_length=30, choices=EntryType.choices)
    reference_type = models.CharField(max_length=30, blank=True)
    reference_id = models.CharField(max_length=64, blank=True)
    idempotency_key = models.CharField(max_length=128, unique=True)
    description = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "ledger entries"

    def save(self, *args, **kwargs):
        if self.__class__.objects.filter(pk=self.pk).exists():
            raise IntegrityError("LedgerEntry rows are immutable and cannot be updated.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise IntegrityError("LedgerEntry rows cannot be deleted.")

    def __str__(self) -> str:
        return f"{self.entry_type} {self.amount} -> wallet {self.wallet_id}"
