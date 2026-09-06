from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.catalog.models import Category, Service
from apps.orders.models import Order
from apps.orders.services import OrderService
from apps.providers.models import Provider
from apps.wallet.models import LedgerEntry
from apps.wallet.services import WalletService

pytestmark = pytest.mark.django_db(transaction=True)

User = get_user_model()


@pytest.fixture
def admin_client():
    admin = User.objects.create_superuser(email="admin@example.com", password="x")
    client = APIClient()
    client.force_authenticate(user=admin)
    return client


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
def funded_order(service):
    user = User.objects.create_user(
        email="buyer@example.com", password="x", email_verified=True, phone_verified=True
    )
    WalletService.credit(user.wallet, Decimal("100000.00"), LedgerEntry.EntryType.DEPOSIT, "seed-1")
    order = OrderService.create_order(user, service, "https://instagram.com/example", quantity=1000)
    # CELERY_TASK_ALWAYS_EAGER runs submit_order_to_provider synchronously via
    # on_commit, but it mutates the row through its own separate fetch — this
    # in-memory `order` object is stale (still "pending"/no provider_order_id)
    # until refreshed.
    order.refresh_from_db()
    return order


def test_admin_can_list_all_orders(admin_client, funded_order):
    resp = admin_client.get(reverse("admin-order-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1


def test_non_staff_cannot_list_admin_orders(funded_order):
    client = APIClient()
    client.force_authenticate(user=funded_order.user)
    resp = client.get(reverse("admin-order-list"))
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_admin_order_list_filters_by_status(admin_client, funded_order):
    resp = admin_client.get(reverse("admin-order-list"), {"status": "error"})
    assert resp.data["count"] == 0
    resp = admin_client.get(reverse("admin-order-list"), {"status": funded_order.status})
    assert resp.data["count"] == 1


def test_admin_can_refund_an_order(admin_client, funded_order):
    funded_order.user.wallet.refresh_from_db()  # same staleness as the order — see fixture comment
    balance_before = funded_order.user.wallet.cached_balance
    resp = admin_client.post(
        reverse("admin-order-refund", kwargs={"pk": funded_order.id}), {"reason": "Customer complaint"}
    )
    assert resp.status_code == status.HTTP_200_OK, resp.data
    funded_order.user.wallet.refresh_from_db()
    assert funded_order.user.wallet.cached_balance == balance_before + funded_order.charge_amount
    assert resp.data["status"] == Order.Status.REFUNDED


def test_admin_cannot_double_refund(admin_client, funded_order):
    admin_client.post(reverse("admin-order-refund", kwargs={"pk": funded_order.id}))
    resp = admin_client.post(reverse("admin-order-refund", kwargs={"pk": funded_order.id}))
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_admin_retry_submit_rejected_when_already_has_provider_id(admin_client, funded_order):
    # The mock provider completes instantly, so by now it already has a provider_order_id.
    assert funded_order.provider_order_id
    resp = admin_client.post(reverse("admin-order-retry-submit", kwargs={"pk": funded_order.id}))
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
