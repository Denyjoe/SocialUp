from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.affiliate.models import AffiliateCommission, AffiliateSettings
from apps.affiliate.services import AffiliateService
from apps.catalog.models import Category, Service
from apps.orders.models import Order
from apps.orders.services import OrderService
from apps.providers.models import Provider
from apps.wallet.models import LedgerEntry
from apps.wallet.services import WalletService

# submit_order_to_provider fires via transaction.on_commit, which needs a
# real commit to fire under pytest-django — see apps/orders/tests/test_orders.py.
pytestmark = pytest.mark.django_db(transaction=True)

User = get_user_model()


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


def _funded_user(email, referred_by=None):
    user = User.objects.create_user(
        email=email, password="x", referred_by=referred_by, email_verified=True, phone_verified=True
    )
    WalletService.credit(user.wallet, Decimal("100000.00"), LedgerEntry.EntryType.DEPOSIT, f"seed-{email}")
    return user


def test_completed_order_credits_referrers_wallet(service):
    AffiliateSettings.objects.create(commission_percent=Decimal("10.00"))
    referrer = _funded_user("referrer@example.com")
    buyer = _funded_user("buyer@example.com", referred_by=referrer)

    order = OrderService.create_order(buyer, service, "https://instagram.com/x", quantity=1000)
    order.refresh_from_db()
    assert order.status == Order.Status.COMPLETED  # mock provider completes instantly

    referrer.wallet.refresh_from_db()
    assert referrer.wallet.cached_balance == Decimal("100000.00") + Decimal("500.00")  # 10% of 5000
    commission = AffiliateCommission.objects.get(order=order)
    assert commission.referrer_id == referrer.id
    assert commission.amount == Decimal("500.00")


def test_order_with_no_referrer_pays_no_commission(service):
    AffiliateSettings.objects.create(commission_percent=Decimal("10.00"))
    buyer = _funded_user("solo@example.com")
    order = OrderService.create_order(buyer, service, "https://instagram.com/x", quantity=1000)
    assert AffiliateCommission.objects.filter(order=order).count() == 0


def test_commission_crediting_is_idempotent(service):
    AffiliateSettings.objects.create(commission_percent=Decimal("10.00"))
    referrer = _funded_user("referrer2@example.com")
    buyer = _funded_user("buyer2@example.com", referred_by=referrer)
    order = OrderService.create_order(buyer, service, "https://instagram.com/x", quantity=1000)
    order.refresh_from_db()

    # Calling it again (simulating both completion paths firing) must not double-pay.
    AffiliateService.credit_commission_for_order(order)
    referrer.wallet.refresh_from_db()
    assert referrer.wallet.cached_balance == Decimal("100000.00") + Decimal("500.00")
    assert AffiliateCommission.objects.filter(order=order).count() == 1


def test_no_commission_for_a_refunded_order(service):
    # Constructed directly (not via OrderService.create_order) so the order
    # is REFUNDED *before* credit_commission_for_order ever sees it — with
    # the mock provider, create_order completes (and would pay commission)
    # instantly, which would confound a test that refunds afterward.
    AffiliateSettings.objects.create(commission_percent=Decimal("10.00"))
    referrer = _funded_user("referrer3@example.com")
    buyer = _funded_user("buyer3@example.com", referred_by=referrer)
    charge_entry = WalletService.debit(
        buyer.wallet, Decimal("5000.00"), LedgerEntry.EntryType.ORDER_PAYMENT, "charge-refunded-1"
    )
    refund_entry = WalletService.credit(
        buyer.wallet, Decimal("5000.00"), LedgerEntry.EntryType.ORDER_REFUND, "refund-1"
    )
    order = Order.objects.create(
        user=buyer,
        service=service,
        provider=service.provider,
        link="https://instagram.com/x",
        quantity=1000,
        charge_amount=Decimal("5000.00"),
        status=Order.Status.REFUNDED,
        ledger_entry=charge_entry,
        refund_ledger_entry=refund_entry,
    )

    result = AffiliateService.credit_commission_for_order(order)
    assert result is None
    referrer.wallet.refresh_from_db()
    assert referrer.wallet.cached_balance == Decimal("100000.00")  # never paid


def test_affiliate_summary_endpoint(service):
    AffiliateSettings.objects.create(commission_percent=Decimal("10.00"))
    referrer = _funded_user("referrer4@example.com")
    buyer = _funded_user("buyer4@example.com", referred_by=referrer)
    OrderService.create_order(buyer, service, "https://instagram.com/x", quantity=1000)

    client = APIClient()
    client.force_authenticate(user=referrer)
    resp = client.get(reverse("affiliate-summary"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["referral_code"] == referrer.referral_code
    assert resp.data["total_referrals"] == 1
    assert Decimal(resp.data["total_commission_earned"]) == Decimal("500.00")


def test_affiliate_referrals_list_shows_orders_and_commission_per_referral(service):
    AffiliateSettings.objects.create(commission_percent=Decimal("10.00"))
    referrer = _funded_user("referrer5@example.com")
    buyer = _funded_user("buyer5@example.com", referred_by=referrer)
    OrderService.create_order(buyer, service, "https://instagram.com/x", quantity=1000)
    OrderService.create_order(buyer, service, "https://instagram.com/y", quantity=1000)

    client = APIClient()
    client.force_authenticate(user=referrer)
    resp = client.get(reverse("affiliate-referrals"))
    assert resp.status_code == status.HTTP_200_OK
    row = resp.data["results"][0] if "results" in resp.data else resp.data[0]
    assert row["email"] == "buyer5@example.com"
    assert row["orders_count"] == 2
    assert Decimal(row["commission_earned"]) == Decimal("1000.00")  # 2 x 500


def test_non_staff_cannot_edit_affiliate_settings():
    user = User.objects.create_user(email="u@example.com", password="x")
    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.patch(reverse("admin-affiliate-settings"), {"commission_percent": "20.00"})
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_admin_can_update_commission_percent():
    admin = User.objects.create_superuser(email="admin@example.com", password="x")
    client = APIClient()
    client.force_authenticate(user=admin)
    resp = client.patch(reverse("admin-affiliate-settings"), {"commission_percent": "15.00"})
    assert resp.status_code == status.HTTP_200_OK
    assert AffiliateSettings.objects.first().commission_percent == Decimal("15.00")
