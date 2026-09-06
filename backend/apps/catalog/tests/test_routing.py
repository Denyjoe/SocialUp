from decimal import Decimal

import pytest

from apps.catalog.models import Category, Service, ServiceProviderMapping
from apps.catalog.routing import resolve_best_mapping
from apps.providers.models import Provider

pytestmark = pytest.mark.django_db


@pytest.fixture
def category():
    return Category.objects.create(name="Instagram", slug="instagram")


@pytest.fixture
def provider_a():
    return Provider.objects.create(name="Provider A", provider_type=Provider.ProviderType.MOCK)


@pytest.fixture
def provider_b():
    return Provider.objects.create(name="Provider B", provider_type=Provider.ProviderType.MOCK)


@pytest.fixture
def service(category, provider_a):
    # apps.catalog.signals auto-creates one ServiceProviderMapping for
    # provider_a right here (service.provider), mirroring its own
    # provider_service_id/cost_rate_per_1000 — the same thing the old
    # 0006 data migration did for pre-existing rows. Tests below fetch
    # and adjust that mapping rather than re-creating it, and only
    # .create() a fresh mapping for provider_b, which the service was
    # never natively tied to.
    return Service.objects.create(
        category=category,
        provider=provider_a,
        provider_service_id="a-1",
        name="Instagram Followers",
        cost_rate_per_1000=Decimal("1.5000"),
        retail_rate_per_1000=Decimal("5000.00"),
    )


@pytest.fixture
def mapping_a(service, provider_a):
    return ServiceProviderMapping.objects.get(service=service, provider=provider_a)


def test_service_creation_auto_creates_its_default_mapping(service, mapping_a):
    assert mapping_a.provider_service_id == "a-1"
    assert mapping_a.cost_rate_per_1000 == Decimal("1.5000")
    assert mapping_a.is_active is True


def test_resolve_returns_the_only_mapping(service, mapping_a):
    assert resolve_best_mapping(service) == mapping_a


def test_resolve_picks_the_cheapest_active_mapping(service, mapping_a, provider_b):
    mapping_a.cost_rate_per_1000 = Decimal("2.0000")
    mapping_a.save(update_fields=["cost_rate_per_1000"])
    cheaper = ServiceProviderMapping.objects.create(
        service=service, provider=provider_b, provider_service_id="b-1",
        cost_rate_per_1000=Decimal("1.0000"),
    )
    assert resolve_best_mapping(service) == cheaper


def test_resolve_breaks_a_cost_tie_by_priority(service, mapping_a, provider_b):
    mapping_a.cost_rate_per_1000 = Decimal("1.0000")
    mapping_a.priority = 0
    mapping_a.save(update_fields=["cost_rate_per_1000", "priority"])
    high_priority = ServiceProviderMapping.objects.create(
        service=service, provider=provider_b, provider_service_id="b-1",
        cost_rate_per_1000=Decimal("1.0000"), priority=5,
    )
    assert resolve_best_mapping(service) == high_priority


def test_resolve_ignores_inactive_mappings(service, mapping_a, provider_b):
    mapping_a.cost_rate_per_1000 = Decimal("1.0000")
    mapping_a.is_active = False
    mapping_a.save(update_fields=["cost_rate_per_1000", "is_active"])
    active = ServiceProviderMapping.objects.create(
        service=service, provider=provider_b, provider_service_id="b-1",
        cost_rate_per_1000=Decimal("9.0000"),
    )
    assert resolve_best_mapping(service) == active


def test_resolve_ignores_mappings_on_an_inactive_provider(service, mapping_a, provider_b):
    provider_b.is_active = False
    provider_b.save(update_fields=["is_active"])
    ServiceProviderMapping.objects.create(
        service=service, provider=provider_b, provider_service_id="b-1",
        cost_rate_per_1000=Decimal("0.5000"),  # cheaper, but provider is down
    )
    assert resolve_best_mapping(service) == mapping_a


def test_resolve_returns_none_when_service_has_no_usable_mapping(service):
    ServiceProviderMapping.objects.filter(service=service).update(is_active=False)
    assert resolve_best_mapping(service) is None
