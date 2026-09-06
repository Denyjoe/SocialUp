from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.catalog.models import Category, Service
from apps.orders.services import OrderService, OrderValidationError
from apps.promotions.models import Coupon, CouponRedemption, DepositBonusRule
from apps.promotions.services import PromotionService
from apps.providers.models import Provider
from apps.wallet.models import LedgerEntry
from apps.wallet.services import WalletService

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def service():
    provider = Provider.objects.create(name="Mock", provider_type=Provider.ProviderType.MOCK)
    category = Category.objects.create(name="Instagram", slug="instagram")
    return Service.objects.create(
        category=category,
        provider=provider,
        provider_service_id="svc-1",
        name="Instagram Followers",
        cost_rate_per_1000=Decimal("1.0000"),
        retail_rate_per_1000=Decimal("5000.00"),
    )


@pytest.fixture
def buyer():
    user = User.objects.create_user(email="buyer@example.com", password="x", email_verified=True)
    WalletService.credit(user.wallet, Decimal("100000.00"), LedgerEntry.EntryType.DEPOSIT, "seed")
    return user


def test_percent_coupon_reduces_the_charge(buyer, service):
    Coupon.objects.create(code="SAVE10", discount_type=Coupon.DiscountType.PERCENT, value=Decimal("10"))

    order = OrderService.create_order(buyer, service, "https://instagram.com/x", 1000, coupon_code="SAVE10")

    assert order.charge_amount == Decimal("4500.00")  # 5000 less 10%
    assert order.discount_amount == Decimal("500.00")
    buyer.wallet.refresh_from_db()
    assert buyer.wallet.cached_balance == Decimal("95500.00")


def test_fixed_coupon_reduces_the_charge(buyer, service):
    Coupon.objects.create(code="FLAT750", discount_type=Coupon.DiscountType.FIXED, value=Decimal("750"))
    order = OrderService.create_order(buyer, service, "https://instagram.com/x", 1000, coupon_code="FLAT750")
    assert order.charge_amount == Decimal("4250.00")
    assert order.discount_amount == Decimal("750.00")


def test_coupon_code_is_case_insensitive(buyer, service):
    Coupon.objects.create(code="save10", discount_type=Coupon.DiscountType.PERCENT, value=Decimal("10"))
    order = OrderService.create_order(buyer, service, "https://instagram.com/x", 1000, coupon_code="sAvE10")
    assert order.discount_amount == Decimal("500.00")


def test_percent_discount_respects_its_cap(buyer, service):
    Coupon.objects.create(
        code="BIG",
        discount_type=Coupon.DiscountType.PERCENT,
        value=Decimal("50"),
        max_discount_amount=Decimal("400.00"),
    )
    order = OrderService.create_order(buyer, service, "https://instagram.com/x", 1000, coupon_code="BIG")
    assert order.discount_amount == Decimal("400.00")  # not 2500


def test_discount_can_never_exceed_the_order_total(buyer, service):
    Coupon.objects.create(
        code="HUGE", discount_type=Coupon.DiscountType.FIXED, value=Decimal("999999")
    )
    order = OrderService.create_order(buyer, service, "https://instagram.com/x", 1000, coupon_code="HUGE")
    assert order.discount_amount == Decimal("5000.00")
    assert order.charge_amount == Decimal("0.00")  # free, never negative


def test_unknown_coupon_is_rejected(buyer, service):
    with pytest.raises(OrderValidationError, match="not valid"):
        OrderService.create_order(buyer, service, "https://instagram.com/x", 1000, coupon_code="NOPE")


def test_expired_coupon_is_rejected(buyer, service):
    Coupon.objects.create(
        code="OLD",
        discount_type=Coupon.DiscountType.PERCENT,
        value=Decimal("10"),
        expires_at=timezone.now() - timedelta(days=1),
    )
    with pytest.raises(OrderValidationError, match="expired"):
        OrderService.create_order(buyer, service, "https://instagram.com/x", 1000, coupon_code="OLD")


def test_inactive_coupon_is_rejected(buyer, service):
    Coupon.objects.create(
        code="OFF", discount_type=Coupon.DiscountType.PERCENT, value=Decimal("10"), is_active=False
    )
    with pytest.raises(OrderValidationError, match="no longer active"):
        OrderService.create_order(buyer, service, "https://instagram.com/x", 1000, coupon_code="OFF")


def test_per_user_limit_is_enforced(buyer, service):
    Coupon.objects.create(
        code="ONCE",
        discount_type=Coupon.DiscountType.PERCENT,
        value=Decimal("10"),
        max_uses_per_user=1,
    )
    OrderService.create_order(buyer, service, "https://instagram.com/x", 1000, coupon_code="ONCE")
    with pytest.raises(OrderValidationError, match="already used"):
        OrderService.create_order(buyer, service, "https://instagram.com/x", 1000, coupon_code="ONCE")


def test_global_usage_limit_is_enforced(service):
    Coupon.objects.create(
        code="FIRST2",
        discount_type=Coupon.DiscountType.PERCENT,
        value=Decimal("10"),
        max_uses=1,
        max_uses_per_user=5,
    )
    first = User.objects.create_user(email="a@example.com", password="x", email_verified=True)
    second = User.objects.create_user(email="b@example.com", password="x", email_verified=True)
    for user in (first, second):
        WalletService.credit(user.wallet, Decimal("50000.00"), LedgerEntry.EntryType.DEPOSIT, f"s-{user.pk}")

    OrderService.create_order(first, service, "https://instagram.com/x", 1000, coupon_code="FIRST2")
    with pytest.raises(OrderValidationError, match="usage limit"):
        OrderService.create_order(second, service, "https://instagram.com/x", 1000, coupon_code="FIRST2")


def test_minimum_order_amount_is_enforced(buyer, service):
    Coupon.objects.create(
        code="BIGORDER",
        discount_type=Coupon.DiscountType.PERCENT,
        value=Decimal("10"),
        min_order_amount=Decimal("9000.00"),
    )
    with pytest.raises(OrderValidationError, match="minimum order"):
        OrderService.create_order(buyer, service, "https://instagram.com/x", 1000, coupon_code="BIGORDER")


def test_redemption_is_recorded_and_counted(buyer, service):
    coupon = Coupon.objects.create(
        code="TRACK", discount_type=Coupon.DiscountType.PERCENT, value=Decimal("10")
    )
    order = OrderService.create_order(buyer, service, "https://instagram.com/x", 1000, coupon_code="TRACK")

    redemption = CouponRedemption.objects.get(coupon=coupon)
    assert redemption.user == buyer
    assert redemption.order == order
    assert redemption.amount_discounted == Decimal("500.00")
    coupon.refresh_from_db()
    assert coupon.used_count == 1


def test_failed_order_does_not_burn_the_coupon(service):
    """An insufficient balance must roll the redemption back with the charge."""
    coupon = Coupon.objects.create(
        code="ROLLBACK", discount_type=Coupon.DiscountType.PERCENT, value=Decimal("10")
    )
    broke = User.objects.create_user(email="broke@example.com", password="x", email_verified=True)

    with pytest.raises(Exception):
        OrderService.create_order(broke, service, "https://instagram.com/x", 1000, coupon_code="ROLLBACK")

    coupon.refresh_from_db()
    assert coupon.used_count == 0
    assert CouponRedemption.objects.count() == 0


def test_order_endpoint_accepts_a_coupon_code(buyer, service):
    Coupon.objects.create(code="API10", discount_type=Coupon.DiscountType.PERCENT, value=Decimal("10"))
    client = APIClient()
    client.force_authenticate(user=buyer)
    resp = client.post(
        reverse("order-list-create"),
        {
            "service": service.id,
            "link": "https://instagram.com/x",
            "quantity": 1000,
            "coupon_code": "API10",
        },
    )
    assert resp.status_code == status.HTTP_201_CREATED, resp.data
    assert Decimal(resp.data["charge_amount"]) == Decimal("4500.00")
    assert Decimal(resp.data["discount_amount"]) == Decimal("500.00")


# --- Deposit bonus rules ---


def test_best_deposit_bonus_picks_the_highest_matching_tier():
    DepositBonusRule.objects.create(name="Small", min_amount=Decimal("10000"), bonus_percent=Decimal("5"))
    big = DepositBonusRule.objects.create(
        name="Big", min_amount=Decimal("50000"), bonus_percent=Decimal("10")
    )

    rule, bonus = PromotionService.best_deposit_bonus(Decimal("60000"))
    assert rule == big
    assert bonus == Decimal("6000.00")


def test_deposit_bonus_below_every_threshold_yields_nothing():
    DepositBonusRule.objects.create(name="Small", min_amount=Decimal("10000"), bonus_percent=Decimal("5"))
    rule, bonus = PromotionService.best_deposit_bonus(Decimal("500"))
    assert rule is None
    assert bonus == Decimal("0.00")


def test_deposit_bonus_respects_its_cap():
    DepositBonusRule.objects.create(
        name="Capped",
        min_amount=Decimal("10000"),
        bonus_percent=Decimal("50"),
        max_bonus_amount=Decimal("2000"),
    )
    _, bonus = PromotionService.best_deposit_bonus(Decimal("100000"))
    assert bonus == Decimal("2000.00")


def test_inactive_deposit_bonus_is_ignored():
    DepositBonusRule.objects.create(
        name="Off", min_amount=Decimal("1000"), bonus_percent=Decimal("10"), is_active=False
    )
    rule, bonus = PromotionService.best_deposit_bonus(Decimal("50000"))
    assert rule is None
    assert bonus == Decimal("0.00")
