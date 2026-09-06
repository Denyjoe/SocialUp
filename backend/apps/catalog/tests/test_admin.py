from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.catalog.models import Category, PlatformSetting, Service
from apps.providers.models import Provider

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture
def admin_client():
    admin = User.objects.create_superuser(email="admin@example.com", password="x")
    client = APIClient()
    client.force_authenticate(user=admin)
    return client


@pytest.fixture
def service():
    provider = Provider.objects.create(name="Test Provider")
    category = Category.objects.create(name="Instagram", slug="instagram")
    return Service.objects.create(
        category=category,
        provider=provider,
        provider_service_id="svc-1",
        name="Instagram Followers",
        cost_rate_per_1000=Decimal("1.0000"),
        retail_rate_per_1000=Decimal("3500.00"),
    )


def test_non_staff_cannot_edit_services(service):
    user = User.objects.create_user(email="user@example.com", password="x")
    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.patch(
        reverse("admin-service-detail", kwargs={"pk": service.id}), {"retail_rate_per_1000": "1.00"}
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_admin_can_update_retail_price(admin_client, service):
    resp = admin_client.patch(
        reverse("admin-service-detail", kwargs={"pk": service.id}), {"retail_rate_per_1000": "4200.00"}
    )
    assert resp.status_code == status.HTTP_200_OK, resp.data
    service.refresh_from_db()
    assert service.retail_rate_per_1000 == Decimal("4200.00")


def test_service_margin_percent_is_calculated(admin_client, service):
    PlatformSetting.objects.create(usd_to_local_rate=Decimal("2500.0000"))
    resp = admin_client.get(reverse("admin-service-detail", kwargs={"pk": service.id}))
    # cost 1.00 USD/1000 * 2500 = 2500 TZS cost; retail 3500 -> margin 40%
    assert resp.data["margin_percent"] == 40.0


def test_admin_service_list_search(admin_client, service):
    resp = admin_client.get(reverse("admin-service-list"), {"search": "Followers"})
    assert resp.data["count"] == 1
    resp = admin_client.get(reverse("admin-service-list"), {"search": "Nonexistent"})
    assert resp.data["count"] == 0


def test_admin_can_update_platform_settings(admin_client):
    resp = admin_client.patch(
        reverse("admin-platform-settings"), {"usd_to_local_rate": "2600.0000"}
    )
    assert resp.status_code == status.HTTP_200_OK
    assert PlatformSetting.objects.first().usd_to_local_rate == Decimal("2600.0000")
