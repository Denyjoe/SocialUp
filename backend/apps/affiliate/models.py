from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel
from apps.orders.models import Order
from apps.wallet.models import LedgerEntry


class AffiliateSettings(TimeStampedModel):
    """Singleton-by-convention, same pattern as catalog.PlatformSetting."""

    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("10.00"))

    def __str__(self) -> str:
        return f"{self.commission_percent}% commission"


class AffiliateCommission(TimeStampedModel):
    """One row per order that earned a referrer a commission. Paid
    immediately into the referrer's wallet when the order completes — see
    apps/affiliate/services.py. Deliberately NOT clawed back if the order is
    later refunded (a known simplification; see services.py docstring)."""

    referrer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="affiliate_commissions_earned"
    )
    referred_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referral_commissions"
    )
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="affiliate_commission")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    ledger_entry = models.OneToOneField(
        LedgerEntry, on_delete=models.PROTECT, related_name="affiliate_commission"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.amount} to {self.referrer_id} for order {self.order_id}"
