from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.catalog.models import Category, Service, ServiceProviderMapping
from apps.orders.models import Order
from apps.orders.services import OrderService, OrderValidationError
from apps.providers.models import Provider
from apps.wallet.models import LedgerEntry
from apps.wallet.services import InsufficientBalanceError, WalletService

# transaction=True: OrderService.create_order() defers provider submission to
# a transaction.on_commit() callback, which never fires under the default
# django_db transaction-rollback wrapper — it needs a real commit to happen.
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
        min_quantity=100,
        max_quantity=10000,
        cost_rate_per_1000=Decimal("1.5000"),
        retail_rate_per_1000=Decimal("5000.00"),
    )


@pytest.fixture
def funded_user(service):
    user = User.objects.create_user(
        email="buyer@example.com", password="x", email_verified=True, phone_verified=True
    )
    WalletService.credit(user.wallet, Decimal("100000.00"), LedgerEntry.EntryType.DEPOSIT, "seed-1")
    return user


def test_create_order_debits_wallet_and_instantly_completes_via_mock(funded_user, service):
    order = OrderService.create_order(
        user=funded_user, service=service, link="https://instagram.com/example", quantity=1000
    )

    funded_user.wallet.refresh_from_db()
    assert funded_user.wallet.cached_balance == Decimal("95000.00")  # 100000 - 5000

    order.refresh_from_db()
    # CELERY_TASK_ALWAYS_EAGER=True in test settings -> submit_order_to_provider
    # already ran synchronously by the time create_order() returns.
    assert order.status == Order.Status.COMPLETED
    assert order.provider_order_id.startswith("mock-")
    assert order.charge_amount == Decimal("5000.00")


def test_create_order_routes_to_the_cheaper_of_two_mappings(funded_user, service):
    # Smart API Auto-Routing groundwork: a second, cheaper provider for the
    # exact same service should win at order time — proving create_order
    # actually resolves a mapping rather than always using service.provider.
    cheaper_provider = Provider.objects.create(
        name="Cheaper Mock", provider_type=Provider.ProviderType.MOCK
    )
    ServiceProviderMapping.objects.create(
        service=service,
        provider=cheaper_provider,
        provider_service_id="cheaper-sku",
        cost_rate_per_1000=Decimal("0.5000"),  # service's own default mapping costs 1.5000
    )

    order = OrderService.create_order(
        user=funded_user, service=service, link="https://instagram.com/example", quantity=1000
    )

    order.refresh_from_db()
    assert order.provider == cheaper_provider
    assert order.provider_service_id == "cheaper-sku"
    assert order.cost_amount == Decimal("0.5000")  # 0.5000 * 1000 / 1000
    # Retail pricing is unaffected — the customer pays the service's own
    # listed rate regardless of which provider ends up fulfilling it.
    assert order.charge_amount == Decimal("5000.00")


def test_create_order_rejects_when_service_has_no_usable_mapping(funded_user, service):
    ServiceProviderMapping.objects.filter(service=service).update(is_active=False)

    with pytest.raises(OrderValidationError, match="no available provider"):
        OrderService.create_order(
            user=funded_user, service=service, link="https://instagram.com/example", quantity=1000
        )


def test_create_order_rejects_quantity_below_minimum(funded_user, service):
    with pytest.raises(OrderValidationError):
        OrderService.create_order(funded_user, service, "https://instagram.com/example", quantity=1)
    funded_user.wallet.refresh_from_db()
    assert funded_user.wallet.cached_balance == Decimal("100000.00")  # untouched


def test_create_order_with_insufficient_balance_raises_and_does_not_create_order(service):
    poor_user = User.objects.create_user(
        email="poor@example.com", password="x", email_verified=True, phone_verified=True
    )
    with pytest.raises(InsufficientBalanceError):
        OrderService.create_order(poor_user, service, "https://instagram.com/example", quantity=1000)
    assert Order.objects.filter(user=poor_user).count() == 0


def test_refund_order_credits_wallet_back_and_is_idempotent(funded_user, service):
    order = OrderService.create_order(funded_user, service, "https://instagram.com/example", quantity=1000)
    funded_user.wallet.refresh_from_db()
    balance_after_order = funded_user.wallet.cached_balance

    OrderService.refund_order(order, reason="test refund")
    funded_user.wallet.refresh_from_db()
    assert funded_user.wallet.cached_balance == balance_after_order + order.charge_amount
    assert order.status == Order.Status.REFUNDED

    # Calling refund again must be a no-op (idempotent), not a double credit.
    OrderService.refund_order(order, reason="test refund again")
    funded_user.wallet.refresh_from_db()
    assert funded_user.wallet.cached_balance == balance_after_order + order.charge_amount


# --- API-level tests ---


def test_order_create_endpoint_full_flow(funded_user, service):
    client = APIClient()
    client.force_authenticate(user=funded_user)

    resp = client.post(
        reverse("order-list-create"),
        {"service": service.id, "link": "https://instagram.com/example", "quantity": 1000},
    )
    assert resp.status_code == status.HTTP_201_CREATED, resp.data
    assert resp.data["status"] == Order.Status.COMPLETED
    assert Decimal(resp.data["charge_amount"]) == Decimal("5000.00")

    list_resp = client.get(reverse("order-list-create"))
    assert list_resp.status_code == status.HTTP_200_OK
    assert list_resp.data["count"] == 1

    wallet_resp = client.get(reverse("wallet-detail"))
    assert Decimal(wallet_resp.data["cached_balance"]) == Decimal("95000.00")


def test_order_create_endpoint_rejects_unauthenticated(service):
    client = APIClient()
    resp = client.post(
        reverse("order-list-create"),
        {"service": service.id, "link": "https://instagram.com/example", "quantity": 1000},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_order_create_endpoint_surfaces_insufficient_balance_as_400(service):
    poor_user = User.objects.create_user(email="poor2@example.com", password="x")
    client = APIClient()
    client.force_authenticate(user=poor_user)
    resp = client.post(
        reverse("order-list-create"),
        {"service": service.id, "link": "https://instagram.com/example", "quantity": 1000},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_user_cannot_see_another_users_order(funded_user, service):
    order = OrderService.create_order(funded_user, service, "https://instagram.com/example", quantity=1000)
    other_user = User.objects.create_user(email="other@example.com", password="x")
    client = APIClient()
    client.force_authenticate(user=other_user)
    resp = client.get(reverse("order-detail", kwargs={"pk": order.id}))
    assert resp.status_code == status.HTTP_404_NOT_FOUND
