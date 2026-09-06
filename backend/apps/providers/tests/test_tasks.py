from decimal import Decimal

import pytest

from apps.catalog.models import PlatformSetting, Service
from apps.providers.models import Provider, ProviderServiceSyncLog
from apps.providers.tasks import check_provider_balance, sync_provider_services

pytestmark = pytest.mark.django_db

BASE_URL = "https://vinasmm.com/api/v2"


@pytest.fixture
def provider():
    return Provider.objects.create(
        name="VinaSMM",
        provider_type=Provider.ProviderType.JAP_STYLE,
        base_url=BASE_URL,
        api_key="test-key",
    )


def test_sync_creates_services_with_calculated_retail_price(requests_mock, provider):
    PlatformSetting.objects.create(
        usd_to_local_rate=Decimal("2500.0000"), default_markup_percent=Decimal("40.00")
    )
    requests_mock.post(
        BASE_URL,
        json=[
            {
                "service": 1,
                "name": "Instagram Followers",
                "category": "Instagram",
                "rate": "1.0000",
                "min": "100",
                "max": "10000",
                "type": "Default",
            }
        ],
    )

    sync_provider_services(provider.id)

    service = Service.objects.get(provider=provider, provider_service_id="1")
    # cost 1.00 USD/1000 * 2500 TZS/USD * 1.40 markup = 3500.00 TZS/1000
    assert service.retail_rate_per_1000 == Decimal("3500.00")
    assert service.category.name == "Instagram"
    assert service.category.platform == "instagram"

    log = ProviderServiceSyncLog.objects.get(provider=provider)
    assert log.status == ProviderServiceSyncLog.Status.SUCCESS
    assert log.services_created == 1
    assert log.services_updated == 0


def test_sync_classifies_category_by_category_name_not_noisy_service_name(requests_mock, provider):
    # Regression: a category clearly named for Facebook must not be
    # misclassified just because one service under it happens to mention
    # "IG" — only the category's own name should drive the platform guess.
    PlatformSetting.objects.create()
    requests_mock.post(
        BASE_URL,
        json=[
            {
                "service": 1,
                "name": "FB/IG Crossposted Livestream Views",
                "category": "FACEBOOK LIVESTREAM VIEWS [Main Provider]",
                "rate": "1.0000",
                "min": "100",
                "max": "10000",
                "type": "Default",
            }
        ],
    )

    sync_provider_services(provider.id)

    service = Service.objects.get(provider=provider, provider_service_id="1")
    assert service.category.platform == "facebook"


def test_sync_respects_price_locked_services(requests_mock, provider):
    PlatformSetting.objects.create()
    from apps.catalog.models import Category

    category = Category.objects.create(name="Instagram", slug="instagram")
    Service.objects.create(
        provider=provider,
        provider_service_id="1",
        category=category,
        name="Old name",
        cost_rate_per_1000=Decimal("1.0000"),
        retail_rate_per_1000=Decimal("9999.00"),
        price_locked=True,
    )
    requests_mock.post(
        BASE_URL,
        json=[
            {"service": 1, "name": "Instagram Followers", "category": "Instagram", "rate": "2.0000", "min": "100", "max": "10000", "type": "Default"}
        ],
    )

    sync_provider_services(provider.id)

    service = Service.objects.get(provider=provider, provider_service_id="1")
    assert service.retail_rate_per_1000 == Decimal("9999.00")  # untouched
    assert service.name == "Instagram Followers"  # non-price fields still update
    assert service.cost_rate_per_1000 == Decimal("2.0000")  # cost snapshot still updates


def test_sync_logs_failure_without_raising(requests_mock, provider):
    PlatformSetting.objects.create()
    requests_mock.post(BASE_URL, json={"error": "Invalid API key"})

    sync_provider_services(provider.id)  # must not raise

    log = ProviderServiceSyncLog.objects.get(provider=provider)
    assert log.status == ProviderServiceSyncLog.Status.FAILED
    assert "Invalid API key" in log.error_text
    assert Service.objects.filter(provider=provider).count() == 0


def test_check_provider_balance_updates_provider(requests_mock, provider):
    requests_mock.post(BASE_URL, json={"balance": "42.50", "currency": "USD"})
    check_provider_balance(provider.id)
    provider.refresh_from_db()
    assert provider.balance_cached == Decimal("42.50")
    assert provider.balance_last_checked_at is not None
