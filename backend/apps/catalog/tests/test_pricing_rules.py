from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.catalog.models import Category, PlatformSetting, PricingRule, Service
from apps.catalog.pricing import compute_retail_price, resolve_pricing_rule
from apps.providers.models import Provider

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin():
    return User.objects.create_user(email="owner@example.com", password="x", is_staff=True)


@pytest.fixture
def fx():
    return PlatformSetting.objects.create(
        usd_to_local_rate=Decimal("2500.0000"), default_markup_percent=Decimal("40.00")
    )


@pytest.fixture
def instagram():
    return Category.objects.create(name="Instagram", slug="instagram", platform=Category.Platform.INSTAGRAM)


@pytest.fixture
def tiktok():
    return Category.objects.create(name="TikTok", slug="tiktok", platform=Category.Platform.TIKTOK)


# ── Pure resolution logic ──────────────────────────────────────────────


def test_no_matching_rule_falls_back_to_default(fx, instagram):
    price = compute_retail_price(
        cost_rate_per_1000=Decimal("1.0000"),
        usd_to_local_rate=fx.usd_to_local_rate,
        default_markup_percent=fx.default_markup_percent,
        category=instagram,
        platform=instagram.platform,
    )
    assert price == Decimal("3500.00")  # 1 * 2500 * 1.40


def test_category_rule_overrides_the_default(fx, instagram, tiktok):
    PricingRule.objects.create(
        name="Instagram premium", scope=PricingRule.Scope.CATEGORY,
        category=instagram, markup_percent=Decimal("60.00"),
    )
    ig_price = compute_retail_price(
        cost_rate_per_1000=Decimal("1.0000"), usd_to_local_rate=fx.usd_to_local_rate,
        default_markup_percent=fx.default_markup_percent, category=instagram, platform=instagram.platform,
    )
    tt_price = compute_retail_price(
        cost_rate_per_1000=Decimal("1.0000"), usd_to_local_rate=fx.usd_to_local_rate,
        default_markup_percent=fx.default_markup_percent, category=tiktok, platform=tiktok.platform,
    )
    assert ig_price == Decimal("4000.00")  # 1 * 2500 * 1.60
    assert tt_price == Decimal("3500.00")  # untouched, still the 40% default


def test_platform_rule_applies_across_its_whole_platform(fx, instagram):
    other_ig_category = Category.objects.create(
        name="IG Story Views", slug="ig-story-views", platform=Category.Platform.INSTAGRAM
    )
    PricingRule.objects.create(
        name="All Instagram", scope=PricingRule.Scope.PLATFORM,
        platform=Category.Platform.INSTAGRAM, markup_percent=Decimal("50.00"),
    )
    for cat in (instagram, other_ig_category):
        price = compute_retail_price(
            cost_rate_per_1000=Decimal("1.0000"), usd_to_local_rate=fx.usd_to_local_rate,
            default_markup_percent=fx.default_markup_percent, category=cat, platform=cat.platform,
        )
        assert price == Decimal("3750.00")  # 1 * 2500 * 1.50


def test_cost_tier_rule_only_matches_within_its_band(fx, instagram):
    PricingRule.objects.create(
        name="Cheap services", scope=PricingRule.Scope.COST_TIER,
        max_cost_per_1000=Decimal("0.5000"), markup_percent=Decimal("80.00"),
    )
    cheap = compute_retail_price(
        cost_rate_per_1000=Decimal("0.2000"), usd_to_local_rate=fx.usd_to_local_rate,
        default_markup_percent=fx.default_markup_percent, category=instagram, platform=instagram.platform,
    )
    expensive = compute_retail_price(
        cost_rate_per_1000=Decimal("2.0000"), usd_to_local_rate=fx.usd_to_local_rate,
        default_markup_percent=fx.default_markup_percent, category=instagram, platform=instagram.platform,
    )
    assert cheap == Decimal("900.00")  # 0.2 * 2500 * 1.80
    assert expensive == Decimal("7000.00")  # falls through to the 40% default


def test_higher_priority_rule_wins_when_two_rules_match(fx, instagram):
    PricingRule.objects.create(
        name="All Instagram", scope=PricingRule.Scope.PLATFORM,
        platform=Category.Platform.INSTAGRAM, markup_percent=Decimal("50.00"), priority=1,
    )
    PricingRule.objects.create(
        name="Instagram premium", scope=PricingRule.Scope.CATEGORY,
        category=instagram, markup_percent=Decimal("70.00"), priority=10,
    )
    price = compute_retail_price(
        cost_rate_per_1000=Decimal("1.0000"), usd_to_local_rate=fx.usd_to_local_rate,
        default_markup_percent=fx.default_markup_percent, category=instagram, platform=instagram.platform,
    )
    assert price == Decimal("4250.00")  # the priority-10 rule (70%), not priority-1 (50%)


def test_inactive_rule_is_never_matched(fx, instagram):
    PricingRule.objects.create(
        name="Disabled", scope=PricingRule.Scope.CATEGORY,
        category=instagram, markup_percent=Decimal("90.00"), is_active=False,
    )
    assert resolve_pricing_rule(category_id=instagram.id, platform=instagram.platform, cost_per_1000=Decimal("1")) is None


def test_min_profit_floor_lifts_price_above_a_thin_percentage_margin(fx, instagram):
    # 0.01 USD cost * 2500 = 25 TZS local cost. A 40% margin on that is only
    # 10 TZS profit — the floor demands at least 200.
    PricingRule.objects.create(
        name="Never sell for less than 200 profit", scope=PricingRule.Scope.CATEGORY,
        category=instagram, markup_percent=Decimal("40.00"), min_profit_per_1000=Decimal("200.00"),
    )
    price = compute_retail_price(
        cost_rate_per_1000=Decimal("0.0100"), usd_to_local_rate=fx.usd_to_local_rate,
        default_markup_percent=fx.default_markup_percent, category=instagram, platform=instagram.platform,
    )
    assert price == Decimal("225.00")  # 25 cost + 200 floor, not 25 * 1.40 = 35


def test_min_profit_floor_does_not_lower_a_price_already_above_it(fx, instagram):
    PricingRule.objects.create(
        name="Floor rarely binds", scope=PricingRule.Scope.CATEGORY,
        category=instagram, markup_percent=Decimal("200.00"), min_profit_per_1000=Decimal("1.00"),
    )
    price = compute_retail_price(
        cost_rate_per_1000=Decimal("1.0000"), usd_to_local_rate=fx.usd_to_local_rate,
        default_markup_percent=fx.default_markup_percent, category=instagram, platform=instagram.platform,
    )
    assert price == Decimal("7500.00")  # 1 * 2500 * 3.00, well above the 1 TZS floor


def test_category_rule_without_a_category_is_rejected():
    rule = PricingRule(name="Bad", scope=PricingRule.Scope.CATEGORY, markup_percent=Decimal("10"))
    with pytest.raises(Exception):
        rule.clean()


def test_cost_tier_rule_needs_at_least_one_bound():
    rule = PricingRule(name="Bad", scope=PricingRule.Scope.COST_TIER, markup_percent=Decimal("10"))
    with pytest.raises(Exception):
        rule.clean()


# ── Admin API ───────────────────────────────────────────────────────────


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_admin_can_crud_pricing_rules(admin, instagram):
    client = _client(admin)

    create = client.post(
        reverse("admin-pricing-rule-list"),
        {"name": "Instagram premium", "scope": "category", "category": instagram.id, "markup_percent": "55.00"},
        format="json",
    )
    assert create.status_code == status.HTTP_201_CREATED
    rule_id = create.data["id"]

    update = client.patch(
        reverse("admin-pricing-rule-detail", args=[rule_id]), {"markup_percent": "65.00"}, format="json"
    )
    assert update.status_code == status.HTTP_200_OK
    assert update.data["markup_percent"] == "65.00"

    listing = client.get(reverse("admin-pricing-rule-list"))
    assert listing.status_code == status.HTTP_200_OK
    assert len(listing.data) == 1

    delete = client.delete(reverse("admin-pricing-rule-detail", args=[rule_id]))
    assert delete.status_code == status.HTTP_204_NO_CONTENT
    assert PricingRule.objects.count() == 0


def test_pricing_rules_are_staff_only(instagram):
    customer = User.objects.create_user(email="c@example.com", password="x")
    resp = _client(customer).get(reverse("admin-pricing-rule-list"))
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_matching_services_count_reflects_eligible_services(admin, fx, instagram):
    provider = Provider.objects.create(name="Mock", provider_type=Provider.ProviderType.MOCK)

    def make(name, **kwargs):
        return Service.objects.create(
            category=instagram, provider=provider, provider_service_id=f"svc-{name}", name=name,
            cost_rate_per_1000=Decimal("1.0000"), retail_rate_per_1000=Decimal("3500.00"), **kwargs,
        )

    make("eligible")
    make("has override", markup_percent=Decimal("99.00"))
    make("locked", price_locked=True)
    make("inactive", is_active=False)

    rule = PricingRule.objects.create(
        name="Instagram rule", scope=PricingRule.Scope.CATEGORY, category=instagram, markup_percent=Decimal("50"),
    )
    resp = _client(admin).get(reverse("admin-pricing-rule-detail", args=[rule.id]))
    assert resp.data["matching_services_count"] == 1


def test_matching_services_count_accounts_for_a_higher_priority_rule(admin, fx, instagram):
    """A service inside this rule's own scope, but ALSO inside a
    higher-priority rule's scope, should not be counted here — that other
    rule would actually win it at reprice time. An earlier version counted
    every service in a rule's own scope regardless of competing rules."""
    provider = Provider.objects.create(name="Mock", provider_type=Provider.ProviderType.MOCK)
    Service.objects.create(
        category=instagram, provider=provider, provider_service_id="svc-1", name="Contested",
        cost_rate_per_1000=Decimal("1.0000"), retail_rate_per_1000=Decimal("3500.00"),
    )

    low_priority_platform_rule = PricingRule.objects.create(
        name="All Instagram", scope=PricingRule.Scope.PLATFORM,
        platform=instagram.platform, markup_percent=Decimal("50"), priority=1,
    )
    PricingRule.objects.create(
        name="Instagram category override", scope=PricingRule.Scope.CATEGORY,
        category=instagram, markup_percent=Decimal("70"), priority=10,
    )

    resp = _client(admin).get(reverse("admin-pricing-rule-detail", args=[low_priority_platform_rule.id]))
    assert resp.data["matching_services_count"] == 0  # the priority-10 rule actually wins this service


def test_matching_services_count_previews_a_currently_inactive_rule(admin, fx, instagram):
    provider = Provider.objects.create(name="Mock", provider_type=Provider.ProviderType.MOCK)
    Service.objects.create(
        category=instagram, provider=provider, provider_service_id="svc-1", name="Eligible",
        cost_rate_per_1000=Decimal("1.0000"), retail_rate_per_1000=Decimal("3500.00"),
    )
    rule = PricingRule.objects.create(
        name="Not live yet", scope=PricingRule.Scope.CATEGORY, category=instagram,
        markup_percent=Decimal("50"), is_active=False,
    )
    resp = _client(admin).get(reverse("admin-pricing-rule-detail", args=[rule.id]))
    assert resp.data["matching_services_count"] == 1


def test_reprice_from_rules_only_touches_eligible_services(admin, fx, instagram):
    provider = Provider.objects.create(name="Mock", provider_type=Provider.ProviderType.MOCK)
    eligible = Service.objects.create(
        category=instagram, provider=provider, provider_service_id="svc-1", name="Eligible",
        cost_rate_per_1000=Decimal("1.0000"), retail_rate_per_1000=Decimal("3500.00"),
    )
    overridden = Service.objects.create(
        category=instagram, provider=provider, provider_service_id="svc-2", name="Overridden",
        cost_rate_per_1000=Decimal("1.0000"), retail_rate_per_1000=Decimal("9999.00"),
        markup_percent=Decimal("99.00"),
    )
    locked = Service.objects.create(
        category=instagram, provider=provider, provider_service_id="svc-3", name="Locked",
        cost_rate_per_1000=Decimal("1.0000"), retail_rate_per_1000=Decimal("9999.00"), price_locked=True,
    )

    PricingRule.objects.create(
        name="Instagram premium", scope=PricingRule.Scope.CATEGORY, category=instagram, markup_percent=Decimal("60"),
    )

    resp = _client(admin).post(reverse("admin-service-reprice-from-rules"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["updated"] == 1

    eligible.refresh_from_db()
    overridden.refresh_from_db()
    locked.refresh_from_db()
    assert eligible.retail_rate_per_1000 == Decimal("4000.00")  # 1 * 2500 * 1.60
    assert overridden.retail_rate_per_1000 == Decimal("9999.00")  # untouched
    assert locked.retail_rate_per_1000 == Decimal("9999.00")  # untouched


def test_reprice_from_rules_is_staff_only(instagram):
    customer = User.objects.create_user(email="c@example.com", password="x")
    resp = _client(customer).post(reverse("admin-service-reprice-from-rules"))
    assert resp.status_code == status.HTTP_403_FORBIDDEN
