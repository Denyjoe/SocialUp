from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.catalog.models import Category, Service
from apps.orders.models import Order
from apps.orders.services import OrderService
from apps.providers.models import Provider
from apps.wallet.models import LedgerEntry
from apps.wallet.services import WalletService

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def admin():
    return User.objects.create_user(email="owner@example.com", password="x", is_staff=True)


@pytest.fixture
def orders():
    provider = Provider.objects.create(name="Mock", provider_type=Provider.ProviderType.MOCK)
    category = Category.objects.create(name="Instagram", slug="instagram")
    service = Service.objects.create(
        category=category,
        provider=provider,
        provider_service_id="svc-1",
        name="Instagram Followers",
        cost_rate_per_1000=Decimal("1.0000"),
        retail_rate_per_1000=Decimal("5000.00"),
    )
    user = User.objects.create_user(email="buyer@example.com", password="x", email_verified=True)
    WalletService.credit(user.wallet, Decimal("100000.00"), LedgerEntry.EntryType.DEPOSIT, "seed")
    return [
        OrderService.create_order(user, service, f"https://instagram.com/{i}", 1000) for i in range(3)
    ]


def _post(admin, payload):
    client = APIClient()
    client.force_authenticate(user=admin)
    return client.post(reverse("admin-order-bulk-action"), payload, format="json")


def test_bulk_refund_refunds_every_selected_order(admin, orders):
    ids = [str(o.id) for o in orders]
    resp = _post(admin, {"order_ids": ids, "action": "refund"})

    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["processed"] == 3
    for order in Order.objects.filter(pk__in=ids):
        assert order.status == Order.Status.REFUNDED
        assert order.refund_ledger_entry_id is not None


def test_already_refunded_orders_are_skipped_not_double_refunded(admin, orders):
    from apps.wallet.models import Wallet

    wallet_id = orders[0].user.wallet_id if hasattr(orders[0].user, "wallet_id") else orders[0].user.wallet.pk

    OrderService.refund_order(orders[0], reason="manual")
    # Re-read from the DB: the wallet cached on the in-memory user object is
    # stale, since WalletService writes through its own instance.
    balance_before = Wallet.objects.get(pk=wallet_id).cached_balance

    resp = _post(admin, {"order_ids": [str(o.id) for o in orders], "action": "refund"})

    assert resp.data["processed"] == 2
    assert len(resp.data["skipped"]) == 1
    assert resp.data["skipped"][0]["reason"] == "already refunded"

    # Exactly two more refunds landed. The already-refunded order was not
    # paid out a second time.
    assert Wallet.objects.get(pk=wallet_id).cached_balance == balance_before + Decimal("10000.00")


def test_bulk_action_rejects_an_empty_selection(admin):
    assert _post(admin, {"order_ids": [], "action": "refund"}).status_code == status.HTTP_400_BAD_REQUEST


def test_bulk_action_rejects_unknown_action(admin, orders):
    resp = _post(admin, {"order_ids": [str(orders[0].id)], "action": "destroy"})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_bulk_action_caps_batch_size(admin, orders):
    resp = _post(admin, {"order_ids": [str(orders[0].id)] * 201, "action": "refund"})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "at most" in resp.data["detail"]


def test_bulk_action_is_staff_only(orders):
    customer = User.objects.create_user(email="c@example.com", password="x")
    client = APIClient()
    client.force_authenticate(user=customer)
    resp = client.post(
        reverse("admin-order-bulk-action"),
        {"order_ids": [str(orders[0].id)], "action": "refund"},
        format="json",
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN
