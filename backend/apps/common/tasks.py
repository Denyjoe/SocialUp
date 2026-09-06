import logging

from celery import shared_task

from .exchange import BASE_CURRENCY, ExchangeRateError, fetch_rates

logger = logging.getLogger(__name__)


@shared_task
def refresh_exchange_rates():
    """Stores a fresh FX snapshot. On failure the previous snapshot is left
    in place, so the panel keeps showing the last known good rates rather
    than falling back to nothing."""
    from .models import ExchangeRateSnapshot

    try:
        payload = fetch_rates(BASE_CURRENCY)
    except ExchangeRateError as exc:
        logger.warning("Exchange rate refresh failed, keeping the last snapshot: %s", exc)
        return None

    snapshot = ExchangeRateSnapshot.objects.create(
        base_currency=BASE_CURRENCY,
        rates=payload["rates"],
        source=payload["source"],
        fetched_at=payload["fetched_at"],
    )

    # Keep a short history for debugging a suspicious rate, not a full log.
    stale_ids = ExchangeRateSnapshot.objects.order_by("-fetched_at").values_list(
        "id", flat=True
    )[24:]
    if stale_ids:
        ExchangeRateSnapshot.objects.filter(id__in=list(stale_ids)).delete()

    return snapshot.id
