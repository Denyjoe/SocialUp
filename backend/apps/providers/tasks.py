import logging
from decimal import ROUND_HALF_UP, Decimal

from celery import shared_task
from django.utils import timezone

from apps.catalog.pricing import compute_retail_price

from .clients.exceptions import ProviderAPIError
from .clients.registry import get_client_for_provider

logger = logging.getLogger(__name__)

_SERVICE_TYPE_MAP = {
    "default": "default",
    "custom comments": "custom_comments",
    "custom_comments": "custom_comments",
    "drip feed": "drip_feed",
    "drip-feed": "drip_feed",
    "drip_feed": "drip_feed",
}


def _map_service_type(raw: str) -> str:
    return _SERVICE_TYPE_MAP.get(raw.strip().lower(), "default")


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def sync_provider_services(self, provider_id: int):
    """Pulls the provider's live service list and upserts apps.catalog.Service.
    New services are created inactive-by-default is NOT applied here — they
    come in active, since an admin who triggers a sync presumably wants them
    sellable; deactivate manually in Django admin if that's not desired for a
    particular row. Existing services keep their retail price if
    price_locked, otherwise it's recalculated from the new cost."""
    from apps.catalog.models import Category, PlatformSetting, Service

    from .models import Provider, ProviderServiceSyncLog

    started_at = timezone.now()
    provider = Provider.objects.get(pk=provider_id)
    client = get_client_for_provider(provider)
    settings_row = PlatformSetting.objects.first() or PlatformSetting.objects.create()

    created = 0
    updated = 0
    try:
        dtos = client.get_services()
    except ProviderAPIError as exc:
        ProviderServiceSyncLog.objects.create(
            provider=provider,
            started_at=started_at,
            finished_at=timezone.now(),
            status=ProviderServiceSyncLog.Status.FAILED,
            error_text=str(exc),
        )
        logger.error("sync_provider_services failed for provider %s: %s", provider_id, exc)
        return

    for dto in dtos:
        # Postgres enforces Category.name's max_length=100; SQLite silently
        # accepts anything longer, which is how this went unnoticed — some
        # real VinaSMM category strings run past 100 characters.
        category_name = (dto.category or "Uncategorized")[:100]
        category, _ = Category.objects.get_or_create(
            slug=category_name.lower().replace(" ", "-")[:50] or "uncategorized",
            defaults={
                "name": category_name,
                # category_name ALONE — real provider catalogs bundle messy
                # per-service names (e.g. a stray "IG" mention) under a
                # cleanly-labeled category, and mixing that noise in here
                # previously misclassified e.g. a "FACEBOOK LIVESTREAM
                # VIEWS..." category as instagram.
                "platform": Category.guess_platform(category_name),
            },
        )

        existing = Service.objects.filter(
            provider=provider, provider_service_id=dto.provider_service_id
        ).first()

        retail_rate = None
        if not (existing and existing.price_locked):
            if existing and existing.markup_percent is not None:
                # Explicit per-service override — always wins over any
                # PricingRule, exactly like it did before rules existed.
                cost_local = dto.rate_per_1000 * settings_row.usd_to_local_rate
                retail_rate = (
                    cost_local * (Decimal("1") + existing.markup_percent / Decimal("100"))
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            else:
                retail_rate = compute_retail_price(
                    cost_rate_per_1000=dto.rate_per_1000,
                    usd_to_local_rate=settings_row.usd_to_local_rate,
                    default_markup_percent=settings_row.default_markup_percent,
                    category=category,
                    platform=category.platform,
                )

        defaults = {
            "category": category,
            "name": dto.name,
            "service_type": _map_service_type(dto.service_type),
            "min_quantity": dto.min_quantity,
            "max_quantity": dto.max_quantity,
            "cost_currency": "USD",
            "cost_rate_per_1000": dto.rate_per_1000,
            "last_synced_at": timezone.now(),
        }
        if retail_rate is not None:
            defaults["retail_rate_per_1000"] = retail_rate
        elif not existing:
            # New service, price_locked is meaningless yet, but calculate anyway.
            defaults["retail_rate_per_1000"] = compute_retail_price(
                cost_rate_per_1000=dto.rate_per_1000,
                usd_to_local_rate=settings_row.usd_to_local_rate,
                default_markup_percent=settings_row.default_markup_percent,
                category=category,
                platform=category.platform,
            )

        _, was_created = Service.objects.update_or_create(
            provider=provider,
            provider_service_id=dto.provider_service_id,
            defaults=defaults,
        )
        created += was_created
        updated += not was_created

    ProviderServiceSyncLog.objects.create(
        provider=provider,
        started_at=started_at,
        finished_at=timezone.now(),
        services_created=created,
        services_updated=updated,
        status=ProviderServiceSyncLog.Status.SUCCESS,
    )


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def check_provider_balance(self, provider_id: int):
    from .models import Provider

    provider = Provider.objects.get(pk=provider_id)
    client = get_client_for_provider(provider)
    try:
        balance = client.get_balance()
    except ProviderAPIError as exc:
        logger.error("check_provider_balance failed for provider %s: %s", provider_id, exc)
        return
    provider.balance_cached = balance
    provider.balance_last_checked_at = timezone.now()
    provider.save(update_fields=["balance_cached", "balance_last_checked_at"])


@shared_task
def check_provider_balance_all():
    """Celery beat: fans out check_provider_balance to every active provider."""
    from .models import Provider

    for provider_id in Provider.objects.filter(is_active=True).values_list("id", flat=True):
        check_provider_balance.delay(provider_id)
