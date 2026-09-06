import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.providers.clients.exceptions import ProviderAPIError
from apps.providers.clients.registry import get_client_for_provider

logger = logging.getLogger(__name__)

# An order stuck "pending" with no provider_order_id this long means its
# submission task likely failed to even run (worker outage, etc.) rather
# than the provider being slow — worth a fresh attempt.
STUCK_SUBMISSION_THRESHOLD = timedelta(minutes=10)

# Statuses still worth polling. Anything else (completed/canceled/refunded/
# error) is terminal and sync_order_statuses skips it.
ACTIVE_STATUSES = ("pending", "in_progress", "processing")

_STATUS_MAP = {
    "pending": "pending",
    "in progress": "in_progress",
    "processing": "processing",
    "completed": "completed",
    "partial": "partial",
    "canceled": "canceled",
    "cancelled": "canceled",
    "error": "error",
}


def _map_provider_status(raw: str) -> str:
    from .models import Order

    return _STATUS_MAP.get(raw.lower(), Order.Status.IN_PROGRESS)


def _maybe_credit_affiliate_commission(order) -> None:
    """Called from both places an order can reach COMPLETED (instant mock
    completion in submit_order_to_provider, or later via sync_order_statuses
    for a real async provider). AffiliateService itself is idempotent per
    order, so it's safe to call this speculatively any time status becomes
    completed rather than tracking which path got there first."""
    from .models import Order

    if order.status != Order.Status.COMPLETED:
        return
    from apps.affiliate.services import AffiliateService

    AffiliateService.credit_commission_for_order(order)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def submit_order_to_provider(self, order_id: str):
    """Fired via transaction.on_commit right after an Order is created.
    Talks to the order's provider (mock in Phase 2, a real API in Phase 3)
    and records the result. On failure, refunds the customer automatically."""
    from .models import Order, OrderStatusHistory
    from .services import OrderService

    try:
        order = Order.objects.select_related("service", "provider").get(pk=order_id)
    except Order.DoesNotExist:
        logger.error("submit_order_to_provider: order %s not found", order_id)
        return

    client = get_client_for_provider(order.provider)
    old_status = order.status

    try:
        result = client.add_order(
            # The mapping resolved at order-creation time, not whatever
            # service.provider_service_id happens to be right now — those
            # can disagree once a service has more than one active
            # mapping. Falls back for pre-migration orders that predate
            # this field.
            service_id=order.provider_service_id or order.service.provider_service_id,
            link=order.link,
            quantity=order.quantity,
        )
    except ProviderAPIError as exc:
        order.status = Order.Status.ERROR
        order.error_message = str(exc)
        order.save(update_fields=["status", "error_message", "updated_at"])
        OrderStatusHistory.objects.create(
            order=order,
            old_status=old_status,
            new_status=order.status,
            source=OrderStatusHistory.Source.SYSTEM_SYNC,
        )
        OrderService.refund_order(order, reason=f"Provider submission failed: {exc}")
        return

    order.provider_order_id = result.provider_order_id
    order.status = _map_provider_status(result.status)
    order.save(update_fields=["provider_order_id", "status", "updated_at"])
    OrderStatusHistory.objects.create(
        order=order,
        old_status=old_status,
        new_status=order.status,
        source=OrderStatusHistory.Source.SYSTEM_SYNC,
    )
    _maybe_credit_affiliate_commission(order)


@shared_task
def sync_order_statuses():
    """Celery beat: polls every provider's still-active orders for status
    updates. Batches per provider via get_multi_status so N orders costs one
    HTTP call per provider, not N. A provider that errors out doesn't stop
    the others — this loops providers, not one all-or-nothing call."""
    from apps.providers.models import Provider

    from .models import Order, OrderProgressSample, OrderStatusHistory
    from .services import OrderService

    for provider in Provider.objects.filter(is_active=True):
        orders = list(
            Order.objects.filter(
                provider=provider, status__in=ACTIVE_STATUSES
            ).exclude(provider_order_id="")
        )
        if not orders:
            continue

        orders_by_id = {str(o.provider_order_id): o for o in orders}
        client = get_client_for_provider(provider)
        try:
            statuses = client.get_multi_status(list(orders_by_id.keys()))
        except ProviderAPIError as exc:
            logger.error("sync_order_statuses: provider %s failed: %s", provider.name, exc)
            continue

        now = timezone.now()
        for provider_order_id, order in orders_by_id.items():
            result = statuses.get(provider_order_id)
            if result is None:
                continue

            new_status = _map_provider_status(result.status)
            old_status = order.status
            order.start_count = result.start_count
            order.remains = result.remains
            order.last_synced_at = now
            changed = new_status != old_status
            order.status = new_status
            order.save(
                update_fields=["start_count", "remains", "last_synced_at", "status", "updated_at"]
            )
            # Feeds apps.catalog.health's speed-per-hour calculation — a
            # single remains value can't express a rate, only a series of
            # timestamped ones can.
            if result.remains is not None:
                OrderProgressSample.objects.create(order=order, remains=result.remains)
            if changed:
                OrderStatusHistory.objects.create(
                    order=order,
                    old_status=old_status,
                    new_status=new_status,
                    source=OrderStatusHistory.Source.SYSTEM_SYNC,
                )
                if new_status in ("canceled", "error"):
                    OrderService.refund_order(order, reason=f"Provider reported status: {result.status}")
                else:
                    _maybe_credit_affiliate_commission(order)


@shared_task
def retry_stuck_order_submissions():
    """Celery beat: re-fires submission for orders that never made it to the
    provider at all (worker/broker outage right after order creation)."""
    from .models import Order

    cutoff = timezone.now() - STUCK_SUBMISSION_THRESHOLD
    stuck = Order.objects.filter(
        status=Order.Status.PENDING, provider_order_id="", created_at__lt=cutoff
    )
    for order in stuck:
        submit_order_to_provider.delay(str(order.id))


# The Service Health dashboard only ever looks at the last 48h; a week of
# buffer is plenty of margin without letting this table grow forever.
PROGRESS_SAMPLE_RETENTION = timedelta(days=7)


@shared_task
def prune_progress_samples():
    """Celery beat: deletes OrderProgressSample rows older than the
    retention window. These are pure telemetry with no user-facing meaning
    on their own, so there's nothing to archive — just delete."""
    from .models import OrderProgressSample

    cutoff = timezone.now() - PROGRESS_SAMPLE_RETENTION
    OrderProgressSample.objects.filter(sampled_at__lt=cutoff).delete()
