from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.catalog.models import Category, Service
from apps.providers.models import Provider

pytestmark = pytest.mark.django_db


@pytest.fixture
def service():
    provider = Provider.objects.create(name="Test Provider")
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


def test_calculate_charge_rounds_to_two_decimals(service):
    assert service.calculate_charge(1000) == Decimal("5000.00")
    assert service.calculate_charge(333) == Decimal("1665.00")
    assert service.calculate_charge(1) == Decimal("5.00")


def test_service_list_is_public(service):
    resp = APIClient().get(reverse("catalog-services"))
    assert resp.status_code == 200
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["name"] == "Instagram Followers"
    # cost fields must never leak to the customer-facing serializer
    assert "cost_rate_per_1000" not in resp.data["results"][0]
    assert "provider" not in resp.data["results"][0]


def test_service_list_filters_by_category(service):
    other_category = Category.objects.create(name="TikTok", slug="tiktok")
    Service.objects.create(
        category=other_category,
        provider=service.provider,
        provider_service_id="svc-2",
        name="TikTok Followers",
        cost_rate_per_1000=Decimal("2.0000"),
        retail_rate_per_1000=Decimal("6000.00"),
    )

    resp = APIClient().get(reverse("catalog-services"), {"category": service.category_id})
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["name"] == "Instagram Followers"


def test_inactive_service_is_hidden(service):
    service.is_active = False
    service.save()
    resp = APIClient().get(reverse("catalog-services"))
    assert resp.data["count"] == 0
