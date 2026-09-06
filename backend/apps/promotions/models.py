from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel

TWO_PLACES = Decimal("0.01")


class CouponError(Exception):
    """Raised when a coupon cannot be applied. The message is customer-facing."""


class Coupon(TimeStampedModel):
    class DiscountType(models.TextChoices):
        PERCENT = "percent", "Percent off"
        FIXED = "fixed", "Fixed amount off"

    code = models.CharField(max_length=32, unique=True)
    description = models.CharField(max_length=200, blank=True)
    discount_type = models.CharField(
        max_length=20, choices=DiscountType.choices, default=DiscountType.PERCENT
    )
    # Percent (0-100) when discount_type is PERCENT, otherwise TZS.
    value = models.DecimalField(max_digits=14, decimal_places=2)
    min_order_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    max_discount_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Caps a percent discount. Leave blank for no cap.",
    )
    max_uses = models.PositiveIntegerField(
        null=True, blank=True, help_text="Total redemptions allowed. Blank means unlimited."
    )
    max_uses_per_user = models.PositiveIntegerField(default=1)
    used_count = models.PositiveIntegerField(default=0, editable=False)
    starts_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.code

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def discount_for(self, amount: Decimal) -> Decimal:
        """The discount this coupon yields on `amount`, never exceeding it."""
        if self.discount_type == self.DiscountType.PERCENT:
            discount = (amount * self.value / Decimal(100)).quantize(TWO_PLACES)
            if self.max_discount_amount is not None:
                discount = min(discount, self.max_discount_amount)
        else:
            discount = self.value
        return min(discount.quantize(TWO_PLACES), amount)

    def assert_usable(self, user, amount: Decimal) -> None:
        """Raises CouponError with a customer-facing reason, or returns None."""
        now = timezone.now()
        if not self.is_active:
            raise CouponError("This coupon is no longer active.")
        if self.starts_at and self.starts_at > now:
            raise CouponError("This coupon is not active yet.")
        if self.expires_at and self.expires_at < now:
            raise CouponError("This coupon has expired.")
        if self.max_uses is not None and self.used_count >= self.max_uses:
            raise CouponError("This coupon has reached its usage limit.")
        if amount < self.min_order_amount:
            raise CouponError(
                f"This coupon needs a minimum order of {self.min_order_amount:.2f} TZS."
            )
        used_by_user = CouponRedemption.objects.filter(coupon=self, user=user).count()
        if used_by_user >= self.max_uses_per_user:
            raise CouponError("You have already used this coupon.")


class CouponRedemption(TimeStampedModel):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name="redemptions")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="coupon_redemptions"
    )
    order = models.OneToOneField(
        "orders.Order", on_delete=models.CASCADE, null=True, blank=True, related_name="coupon_redemption"
    )
    amount_discounted = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.coupon_id} by {self.user_id}"


class DepositBonusRule(TimeStampedModel):
    """"Top up at least X, get Y% extra". The highest-threshold matching rule
    wins. Applied when a deposit is credited (see
    apps/promotions/services.py::apply_deposit_bonus)."""

    name = models.CharField(max_length=120)
    min_amount = models.DecimalField(max_digits=14, decimal_places=2)
    bonus_percent = models.DecimalField(max_digits=5, decimal_places=2)
    max_bonus_amount = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True, help_text="Blank means no cap."
    )
    is_active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-min_amount"]

    def __str__(self) -> str:
        return f"{self.name} ({self.bonus_percent}% over {self.min_amount})"

    def bonus_for(self, amount: Decimal) -> Decimal:
        bonus = (amount * self.bonus_percent / Decimal(100)).quantize(TWO_PLACES)
        if self.max_bonus_amount is not None:
            bonus = min(bonus, self.max_bonus_amount)
        return bonus
