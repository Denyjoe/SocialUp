from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.catalog.models import Category, PlatformSetting, Service
from apps.orders.services import OrderService
from apps.providers.models import Provider
from apps.wallet.models import LedgerEntry
from apps.wallet.services import WalletService

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def admin():
    return User.objects.create_user(email="owner@example.com", password="x", is_staff=True)


@pytest.fixture
def service():
    PlatformSetting.objects.create(usd_to_local_rate=Decimal("2500.0000"))
    provider = Provider.objects.create(name="Mock", provider_type=Provider.ProviderType.MOCK)
    category = Category.objects.create(name="Instagram", slug="instagram")
    return Service.objects.create(
        category=category,
        provider=provider,
        provider_service_id="svc-1",
        name="Instagram Followers",
        cost_rate_per_1000=Decimal("1.0000"),  # $1 per 1000 -> 2500 TZS at the fixture rate
        retail_rate_per_1000=Decimal("5000.00"),
    )


@pytest.fixture
def buyer_with_order(service):
    user = User.objects.create_user(email="buyer@example.com", password="x", email_verified=True)
    WalletService.credit(user.wallet, Decimal("100000.00"), LedgerEntry.EntryType.DEPOSIT, "seed")
    OrderService.create_order(user, service, "https://instagram.com/x", 1000)
    return user


def test_summary_reports_revenue_cost_and_profit(admin, buyer_with_order):
    client = APIClient()
    client.force_authenticate(user=admin)
    resp = client.get(reverse("admin-report-summary"))

    assert resp.status_code == status.HTTP_200_OK
    assert Decimal(resp.data["revenue"]) == Decimal("5000.00")
    assert Decimal(resp.data["cost"]) == Decimal("2500.00")  # $1 x 2500 FX
    assert Decimal(resp.data["profit"]) == Decimal("2500.00")
    assert Decimal(resp.data["margin_percent"]) == Decimal("50.00")
    assert resp.data["order_count"] == 1
    assert len(resp.data["series"]) == 1


def test_refunded_orders_are_excluded_from_revenue(admin, buyer_with_order, service):
    from apps.orders.models import Order

    order = Order.objects.get()
    OrderService.refund_order(order, reason="test")

    client = APIClient()
    client.force_authenticate(user=admin)
    resp = client.get(reverse("admin-report-summary"))

    assert Decimal(resp.data["revenue"]) == Decimal("0.00")
    assert resp.data["order_count"] == 0
    assert Decimal(resp.data["refunded_amount"]) == Decimal("5000.00")
    assert resp.data["refunded_count"] == 1


def test_service_margin_report_lists_per_service_profit(admin, buyer_with_order):
    client = APIClient()
    client.force_authenticate(user=admin)
    resp = client.get(reverse("admin-report-service-margins"))

    assert resp.status_code == status.HTTP_200_OK
    row = resp.data["results"][0]
    assert row["service_name"] == "Instagram Followers"
    assert Decimal(row["revenue"]) == Decimal("5000.00")
    assert Decimal(row["profit"]) == Decimal("2500.00")
    assert Decimal(row["margin_percent"]) == Decimal("50.00")


def test_category_profitability_groups_by_platform_and_category(admin, buyer_with_order, service):
    client = APIClient()
    client.force_authenticate(user=admin)
    resp = client.get(reverse("admin-report-category-profitability"))

    assert resp.status_code == status.HTTP_200_OK
    platform_row = resp.data["platforms"][0]
    assert platform_row["platform"] == service.category.platform
    assert Decimal(platform_row["revenue"]) == Decimal("5000.00")
    assert Decimal(platform_row["profit"]) == Decimal("2500.00")

    category_row = resp.data["categories"][0]
    assert category_row["category"] == "Instagram"
    assert Decimal(category_row["profit"]) == Decimal("2500.00")


def test_margin_distribution_buckets_the_whole_catalogue(admin, service):
    # service fixture: cost 2500 TZS, retail 5000.00 -> 100% margin -> "premium" band.
    Service.objects.create(
        category=service.category, provider=service.provider, provider_service_id="svc-loss",
        name="Underpriced", cost_rate_per_1000=Decimal("2.0000"), retail_rate_per_1000=Decimal("4000.00"),
    )  # cost 5000 TZS, retail 4000 -> -20% margin -> "loss" band

    client = APIClient()
    client.force_authenticate(user=admin)
    resp = client.get(reverse("admin-report-margin-distribution"))

    assert resp.status_code == status.HTTP_200_OK
    bands = {b["key"]: b["count"] for b in resp.data["bands"]}
    assert bands["loss"] == 1
    assert bands["premium"] == 1
    assert resp.data["total_priced_services"] == 2
    assert resp.data["worst"][0]["service_name"] == "Underpriced"


def test_top_customers_report(admin, buyer_with_order):
    client = APIClient()
    client.force_authenticate(user=admin)
    resp = client.get(reverse("admin-report-top-customers"))

    assert resp.status_code == status.HTTP_200_OK
    row = resp.data["results"][0]
    assert row["email"] == "buyer@example.com"
    assert Decimal(row["spent"]) == Decimal("5000.00")
    assert row["orders"] == 1


def test_orders_csv_export(admin, buyer_with_order):
    client = APIClient()
    client.force_authenticate(user=admin)
    resp = client.get(reverse("admin-export-orders"))

    assert resp.status_code == status.HTTP_200_OK
    assert resp["Content-Type"] == "text/csv"
    body = resp.content.decode()
    assert "order_id,created_at,customer" in body
    assert "buyer@example.com" in body
    assert "5000.00" in body


def test_ledger_csv_export(admin, buyer_with_order):
    client = APIClient()
    client.force_authenticate(user=admin)
    resp = client.get(reverse("admin-export-ledger"))

    assert resp.status_code == status.HTTP_200_OK
    body = resp.content.decode()
    assert "entry_id,created_at,customer" in body
    assert "buyer@example.com" in body


def test_reports_are_staff_only():
    customer = User.objects.create_user(email="c@example.com", password="x")
    client = APIClient()
    client.force_authenticate(user=customer)
    for name in (
        "admin-report-summary",
        "admin-report-service-margins",
        "admin-report-top-customers",
        "admin-report-category-profitability",
        "admin-report-margin-distribution",
        "admin-export-orders",
        "admin-export-ledger",
    ):
        assert client.get(reverse(name)).status_code == status.HTTP_403_FORBIDDEN, name
