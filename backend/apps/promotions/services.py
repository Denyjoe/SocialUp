from decimal import Decimal

from django.db.models import F, Q
from django.utils import timezone

from .models import Coupon, CouponError, CouponRedemption, DepositBonusRule


class PromotionService:
    @staticmethod
    def resolve_coupon(code: str, user, amount: Decimal) -> Coupon:
        """Looks a coupon up and checks it is usable by this user for this
        amount. Raises CouponError with a customer-facing message."""
        try:
            coupon = Coupon.objects.get(code=code.strip().upper())
        except Coupon.DoesNotExist:
            raise CouponError("That coupon code is not valid.")
        coupon.assert_usable(user, amount)
        return coupon

    @staticmethod
    def redeem(coupon: Coupon, user, amount_discounted: Decimal, order=None) -> CouponRedemption:
        """Records a redemption. Call inside the same transaction as the
        charge, so a failed order can never leave a coupon burned."""
        redemption = CouponRedemption.objects.create(
            coupon=coupon, user=user, order=order, amount_discounted=amount_discounted
        )
        # F() so concurrent redemptions cannot clobber each other's count.
        Coupon.objects.filter(pk=coupon.pk).update(used_count=F("used_count") + 1)
        return redemption

    @staticmethod
    def best_deposit_bonus(amount: Decimal):
        """The highest-threshold active rule matching this deposit amount,
        with the bonus it yields. Returns (None, 0.00) when nothing applies.

        Phase 4 (AzamPay) will call this when crediting a confirmed top-up.
        The `credit_wallet` management command applies it too, so the rules
        are exercisable before payments land.
        """
        now = timezone.now()
        rule = (
            DepositBonusRule.objects.filter(is_active=True, min_amount__lte=amount)
            .filter(Q(starts_at__isnull=True) | Q(starts_at__lte=now))
            .filter(Q(expires_at__isnull=True) | Q(expires_at__gte=now))
            .order_by("-min_amount")
            .first()
        )
        if rule is None:
            return None, Decimal("0.00")
        return rule, rule.bonus_for(amount)
