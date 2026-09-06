import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

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
def provider():
    return Provider.objects.create(
        name="VinaSMM", provider_type=Provider.ProviderType.JAP_STYLE, api_key="secret-123"
    )


def test_non_staff_cannot_list_providers(provider):
    user = User.objects.create_user(email="user@example.com", password="x")
    client = APIClient()
    client.force_authenticate(user=user)
    resp = client.get(reverse("admin-provider-list"))
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_provider_api_key_is_never_returned(admin_client, provider):
    resp = admin_client.get(reverse("admin-provider-detail", kwargs={"pk": provider.id}))
    assert "api_key" not in resp.data
    assert resp.data["has_api_key"] is True


def test_updating_provider_without_api_key_does_not_clear_it(admin_client, provider):
    resp = admin_client.patch(
        reverse("admin-provider-detail", kwargs={"pk": provider.id}), {"base_url": "https://new.example.com"}
    )
    assert resp.status_code == status.HTTP_200_OK
    provider.refresh_from_db()
    assert provider.api_key == "secret-123"
    assert provider.base_url == "https://new.example.com"


def test_updating_provider_with_new_api_key_replaces_it(admin_client, provider):
    resp = admin_client.patch(
        reverse("admin-provider-detail", kwargs={"pk": provider.id}), {"api_key": "new-secret"}
    )
    assert resp.status_code == status.HTTP_200_OK
    provider.refresh_from_db()
    assert provider.api_key == "new-secret"


def test_sync_services_action_queues_and_returns_ok(admin_client, provider):
    provider.provider_type = Provider.ProviderType.MOCK
    provider.save()
    resp = admin_client.post(reverse("admin-provider-sync-services", kwargs={"pk": provider.id}))
    assert resp.status_code == status.HTTP_200_OK


def test_check_balance_action_queues_and_returns_ok(admin_client, provider):
    provider.provider_type = Provider.ProviderType.MOCK
    provider.save()
    resp = admin_client.post(reverse("admin-provider-check-balance", kwargs={"pk": provider.id}))
    assert resp.status_code == status.HTTP_200_OK
    provider.refresh_from_db()
    assert provider.balance_cached == 999999.00  # MockProviderClient.get_balance()
