from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.catalog.models import Category, PlatformSetting, Service
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


def test_non_staff_cannot_view_dashboard_stats():
    user = User.objects.create_user(email="user@example.com", password="x")
    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.get(reverse("admin-dashboard-stats"))
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_dashboard_stats_reflects_real_orders_and_wallets(admin_client):
    PlatformSetting.objects.create(usd_to_local_rate=Decimal("2500.0000"))
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
    buyer = User.objects.create_user(
        email="buyer@example.com", password="x", email_verified=True, phone_verified=True
    )
    WalletService.credit(buyer.wallet, Decimal("100000.00"), LedgerEntry.EntryType.DEPOSIT, "seed-1")
    OrderService.create_order(buyer, service, "https://instagram.com/x", quantity=1000)

    resp = admin_client.get(reverse("admin-dashboard-stats"))
    assert resp.status_code == status.HTTP_200_OK, resp.data

    assert resp.data["orders"]["total"] == 1
    assert resp.data["orders"]["today"] == 1
    assert Decimal(resp.data["today"]["revenue"]) == Decimal("5000.00")
    # cost 1.00 USD/1000 * 1000qty = 1.00 USD -> * 2500 = 2500.00 TZS cost -> profit 2500.00
    assert Decimal(resp.data["today"]["cost"]) == Decimal("2500.00")
    assert Decimal(resp.data["today"]["profit"]) == Decimal("2500.00")
    # buyer has 95000 left (100000 - 5000 charge); admin has 0 -> total liability 95000
    assert Decimal(resp.data["wallet_liability"]) == Decimal("95000.00")


def test_revenue_trend_endpoint_returns_requested_number_of_days(admin_client):
    resp = admin_client.get(reverse("admin-dashboard-revenue-trend"), {"days": 7})
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.data) == 7
