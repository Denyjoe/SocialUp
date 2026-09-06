from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.catalog.models import Category, PlatformSetting, Service
from apps.providers.models import Provider

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin():
    return User.objects.create_user(email="owner@example.com", password="x", is_staff=True)


@pytest.fixture
def catalog():
    PlatformSetting.objects.create(usd_to_local_rate=Decimal("2500.0000"))
    provider = Provider.objects.create(name="Mock", provider_type=Provider.ProviderType.MOCK)
    instagram = Category.objects.create(name="Instagram", slug="instagram")
    tiktok = Category.objects.create(name="TikTok", slug="tiktok")

    def make(category, name, retail, locked=False):
        return Service.objects.create(
            category=category,
            provider=provider,
            provider_service_id=f"svc-{name}",
            name=name,
            cost_rate_per_1000=Decimal("1.0000"),
            retail_rate_per_1000=Decimal(retail),
            price_locked=locked,
        )

    return {
        "instagram": instagram,
        "tiktok": tiktok,
        "ig_a": make(instagram, "IG A", "5000.00"),
        "ig_locked": make(instagram, "IG Locked", "5000.00", locked=True),
        "tt_a": make(tiktok, "TT A", "4000.00"),
    }


def _post(admin, payload):
    client = APIClient()
    client.force_authenticate(user=admin)
    return client.post(reverse("admin-service-bulk-update"), payload, format="json")


def test_adjust_price_scales_a_whole_category(admin, catalog):
    resp = _post(admin, {"category": catalog["instagram"].id, "action": "adjust_price", "value": 10})
    assert resp.status_code == status.HTTP_200_OK

    catalog["ig_a"].refresh_from_db()
    catalog["tt_a"].refresh_from_db()
    assert catalog["ig_a"].retail_rate_per_1000 == Decimal("5500.00")  # +10%
    assert catalog["tt_a"].retail_rate_per_1000 == Decimal("4000.00")  # other category untouched


def test_price_locked_services_are_skipped(admin, catalog):
    _post(admin, {"category": catalog["instagram"].id, "action": "adjust_price", "value": 10})
    catalog["ig_locked"].refresh_from_db()
    assert catalog["ig_locked"].retail_rate_per_1000 == Decimal("5000.00")


def test_set_markup_reprices_from_provider_cost(admin, catalog):
    # cost 1 USD x 2500 FX = 2500 TZS, plus 40% markup = 3500
    resp = _post(admin, {"category": catalog["instagram"].id, "action": "set_markup", "value": 40})
    assert resp.status_code == status.HTTP_200_OK

    catalog["ig_a"].refresh_from_db()
    assert catalog["ig_a"].markup_percent == Decimal("40.00")
    assert catalog["ig_a"].retail_rate_per_1000 == Decimal("3500.00")


def test_bulk_activate_and_deactivate(admin, catalog):
    _post(admin, {"category": catalog["instagram"].id, "action": "deactivate"})
    catalog["ig_a"].refresh_from_db()
    catalog["ig_locked"].refresh_from_db()
    assert catalog["ig_a"].is_active is False
    # Deactivating is not a pricing action, so price_locked does not exempt it.
    assert catalog["ig_locked"].is_active is False

    _post(admin, {"category": catalog["instagram"].id, "action": "activate"})
    catalog["ig_a"].refresh_from_db()
    assert catalog["ig_a"].is_active is True


def test_unknown_action_is_rejected(admin, catalog):
    assert _post(admin, {"action": "explode"}).status_code == status.HTTP_400_BAD_REQUEST


def test_pricing_action_requires_a_numeric_value(admin, catalog):
    assert _post(admin, {"action": "adjust_price"}).status_code == status.HTTP_400_BAD_REQUEST
    assert (
        _post(admin, {"action": "adjust_price", "value": "abc"}).status_code
        == status.HTTP_400_BAD_REQUEST
    )


def test_adjustment_that_would_zero_prices_is_refused(admin, catalog):
    resp = _post(admin, {"action": "adjust_price", "value": -100})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    catalog["ig_a"].refresh_from_db()
    assert catalog["ig_a"].retail_rate_per_1000 == Decimal("5000.00")


def test_bulk_update_is_staff_only(catalog):
    customer = User.objects.create_user(email="c@example.com", password="x")
    client = APIClient()
    client.force_authenticate(user=customer)
    resp = client.post(reverse("admin-service-bulk-update"), {"action": "activate"}, format="json")
    assert resp.status_code == status.HTTP_403_FORBIDDEN
