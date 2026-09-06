from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.catalog.models import Category, Service
from apps.orders.models import Order
from apps.providers.models import Provider
from apps.wallet.models import LedgerEntry
from apps.wallet.services import WalletService

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


@pytest.fixture
def user():
    u = User.objects.create_user(
        email="reseller@example.com", password="x", email_verified=True, phone_verified=True
    )
    WalletService.credit(u.wallet, Decimal("100000.00"), LedgerEntry.EntryType.DEPOSIT, "seed")
    return u


def test_missing_key_is_unauthorized(service):
    resp = APIClient().post(reverse("panel-api"), {"action": "balance"})
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_invalid_key_is_rejected():
    resp = APIClient().post(reverse("panel-api"), {"key": "not-a-real-key", "action": "balance"})
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_suspended_user_key_is_rejected(user):
    user.status = User.Status.SUSPENDED
    user.save()
    resp = APIClient().post(reverse("panel-api"), {"key": user.api_key, "action": "balance"})
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_balance_action(user):
    resp = APIClient().post(reverse("panel-api"), {"key": user.api_key, "action": "balance"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data == {"balance": "100000.00", "currency": "TZS"}


def test_services_action_excludes_provider_fields(user, service):
    resp = APIClient().post(reverse("panel-api"), {"key": user.api_key, "action": "services"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data == [
        {
            "service": service.id,
            "name": "Instagram Followers",
            "type": "default",
            "category": "Instagram",
            "rate": "5000.00",
            "min": 100,
            "max": 10000,
        }
    ]


def test_add_action_creates_order_and_debits_wallet(user, service):
    resp = APIClient().post(
        reverse("panel-api"),
        {"key": user.api_key, "action": "add", "service": service.id, "link": "https://instagram.com/x", "quantity": 1000},
    )
    assert resp.status_code == status.HTTP_200_OK, resp.data
    order = Order.objects.get(pk=resp.data["order"])
    assert order.user_id == user.id
    assert order.status == Order.Status.COMPLETED

    user.wallet.refresh_from_db()
    assert user.wallet.cached_balance == Decimal("95000.00")


def test_add_action_rejects_insufficient_balance(service):
    poor_user = User.objects.create_user(email="poor@example.com", password="x")
    resp = APIClient().post(
        reverse("panel-api"),
        {"key": poor_user.api_key, "action": "add", "service": service.id, "link": "https://instagram.com/x", "quantity": 1000},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "error" in resp.data


def test_add_action_rejects_unknown_service(user):
    resp = APIClient().post(
        reverse("panel-api"),
        {"key": user.api_key, "action": "add", "service": 999999, "link": "https://instagram.com/x", "quantity": 1000},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_status_action_single_order(user, service):
    add_resp = APIClient().post(
        reverse("panel-api"),
        {"key": user.api_key, "action": "add", "service": service.id, "link": "https://instagram.com/x", "quantity": 1000},
    )
    order_id = add_resp.data["order"]

    resp = APIClient().post(reverse("panel-api"), {"key": user.api_key, "action": "status", "order": order_id})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["status"] == "Completed"
    assert resp.data["charge"] == "5000.00"


def test_status_action_cannot_see_another_users_order(user, service):
    other = User.objects.create_user(
        email="other@example.com", password="x", email_verified=True, phone_verified=True
    )
    WalletService.credit(other.wallet, Decimal("100000.00"), LedgerEntry.EntryType.DEPOSIT, "seed2")
    add_resp = APIClient().post(
        reverse("panel-api"),
        {"key": other.api_key, "action": "add", "service": service.id, "link": "https://instagram.com/x", "quantity": 1000},
    )
    order_id = add_resp.data["order"]

    resp = APIClient().post(reverse("panel-api"), {"key": user.api_key, "action": "status", "order": order_id})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_unknown_action_returns_error(user):
    resp = APIClient().post(reverse("panel-api"), {"key": user.api_key, "action": "bogus"})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
