from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.catalog.models import Category, Service
from apps.orders.models import Order
from apps.orders.views import MAX_BULK_LINES
from apps.providers.models import Provider
from apps.wallet.models import LedgerEntry
from apps.wallet.services import WalletService

# transaction=True: OrderService.create_order() defers provider submission to
# a transaction.on_commit() callback, same reason test_orders.py needs it.
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


@pytest.fixture
def client(funded_user):
    api = APIClient()
    api.force_authenticate(user=funded_user)
    return api


def test_bulk_create_places_every_valid_line(client, service):
    payload = {
        "orders": [
            {"service": service.id, "link": "https://instagram.com/a", "quantity": 1000},
            {"service": service.id, "link": "https://instagram.com/b", "quantity": 2000},
        ]
    }

    response = client.post(reverse("order-bulk-create"), payload, format="json")

    assert response.status_code == status.HTTP_200_OK
    results = response.data["results"]
    assert len(results) == 2
    assert all(r["success"] for r in results)
    assert results[0]["order"]["charge_amount"] == "5000.00"
    assert results[1]["order"]["charge_amount"] == "10000.00"
    assert Order.objects.count() == 2


def test_bulk_create_reports_a_bad_line_without_blocking_the_others(client, service):
    payload = {
        "orders": [
            {"service": service.id, "link": "https://instagram.com/a", "quantity": 1000},
            {"service": service.id, "link": "https://instagram.com/b", "quantity": 50},  # below min_quantity
            {"service": service.id, "link": "https://instagram.com/c", "quantity": 1500},
        ]
    }

    response = client.post(reverse("order-bulk-create"), payload, format="json")

    assert response.status_code == status.HTTP_200_OK
    results = response.data["results"]
    assert results[0]["success"] is True
    assert results[1]["success"] is False
    assert "between" in results[1]["error"]
    assert results[2]["success"] is True
    assert Order.objects.count() == 2  # the two valid lines still went through


def test_bulk_create_stops_charging_once_balance_runs_out(client, funded_user, service):
    # Funded for exactly one 5000-charge order, not two.
    WalletService.debit(
        funded_user.wallet, Decimal("95000.00"), LedgerEntry.EntryType.ADMIN_ADJUSTMENT_DEBIT, "drain-1"
    )  # leaves exactly 5000.00

    payload = {
        "orders": [
            {"service": service.id, "link": "https://instagram.com/a", "quantity": 1000},
            {"service": service.id, "link": "https://instagram.com/b", "quantity": 1000},
        ]
    }

    response = client.post(reverse("order-bulk-create"), payload, format="json")

    results = response.data["results"]
    assert results[0]["success"] is True
    assert results[1]["success"] is False
    assert "Insufficient" in results[1]["error"]
    assert Order.objects.count() == 1


def test_bulk_create_rejects_an_unknown_service_id_as_a_line_error(client, service):
    payload = {"orders": [{"service": 999999, "link": "https://instagram.com/a", "quantity": 1000}]}

    response = client.post(reverse("order-bulk-create"), payload, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["results"][0]["success"] is False


def test_bulk_create_rejects_empty_list(client):
    response = client.post(reverse("order-bulk-create"), {"orders": []}, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_bulk_create_rejects_missing_orders_key(client):
    response = client.post(reverse("order-bulk-create"), {}, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_bulk_create_rejects_more_than_the_max_lines(client, service):
    line = {"service": service.id, "link": "https://instagram.com/a", "quantity": 1000}
    payload = {"orders": [line] * (MAX_BULK_LINES + 1)}

    response = client.post(reverse("order-bulk-create"), payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Order.objects.count() == 0


def test_bulk_create_requires_authentication(service):
    payload = {"orders": [{"service": service.id, "link": "https://instagram.com/a", "quantity": 1000}]}
    response = APIClient().post(reverse("order-bulk-create"), payload, format="json")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_bulk_create_enforces_email_verification_per_line(service):
    user = User.objects.create_user(email="unverified@example.com", password="x", email_verified=False)
    WalletService.credit(user.wallet, Decimal("100000.00"), LedgerEntry.EntryType.DEPOSIT, "seed-2")
    client = APIClient()
    client.force_authenticate(user=user)

    payload = {"orders": [{"service": service.id, "link": "https://instagram.com/a", "quantity": 1000}]}
    response = client.post(reverse("order-bulk-create"), payload, format="json")

    assert response.data["results"][0]["success"] is False
    assert "verify your email" in response.data["results"][0]["error"]
    assert Order.objects.count() == 0
