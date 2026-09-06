"""Computes the 48-hour Service Health rollup (apps.catalog.models.ServiceHealthStat)
that backs the public Service Health dashboard. Run hourly by Celery beat
(apps.catalog.tasks.recompute_service_health) — never computed live per
request.

Three numbers, each honest about what it actually measures:
- avg_start_minutes: time from order placed to the first observed
  transition into "in progress", averaged over orders that got there.
- avg_speed_per_hour: pooled units delivered / pooled hours elapsed,
  using OrderProgressSample snapshots (falling back to the order's own
  created_at/updated_at when no sample exists yet, e.g. a very short-lived
  order that completed between two sync ticks).
- refill_rate_percent: share of delivered orders that needed a refill.
  This is a proxy for drops, not a directly measured one — a true drop
  rate would mean re-checking the target profile itself days later, which
  this panel has no way to do (see the Sept 2026 feature discussion).
"""

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from .models import ServiceHealthStat

WINDOW = timedelta(hours=48)

# Below this many orders in the window, an average is more noise than
# signal — e.g. one slow order would make a service look permanently
# broken. Leave the averages null rather than show a misleadingly
# precise-looking number.
MIN_SAMPLE_SIZE = 3


def _round1(value: float) -> Decimal:
    """Route a Python float through str() before Decimal() — constructing
    a Decimal directly from a float preserves its binary-fraction noise
    (Decimal(12.34) can print as 12.339999999999999...)."""
    return Decimal(str(round(value, 1)))


@dataclass
class _Accumulator:
    start_deltas_minutes: list[float]
    delivered_units: int
    elapsed_hours: float
    deliverable_count: int
    refilled_count: int


def _compute_one(orders: list) -> _Accumulator:
    from apps.orders.models import Order

    acc = _Accumulator([], 0, 0.0, 0, 0)
    for order in orders:
        history = sorted(order.status_history.all(), key=lambda h: h.changed_at)
        first_in_progress = next(
            (h for h in history if h.new_status == Order.Status.IN_PROGRESS), None
        )
        if first_in_progress:
            delta_minutes = (first_in_progress.changed_at - order.created_at).total_seconds() / 60
            acc.start_deltas_minutes.append(delta_minutes)

        if order.remains is not None:
            samples = list(order.progress_samples.all())
            latest_time = max((s.sampled_at for s in samples), default=order.updated_at)
            elapsed_hours = (latest_time - order.created_at).total_seconds() / 3600
            if elapsed_hours > 0:
                acc.delivered_units += max(0, order.quantity - order.remains)
                acc.elapsed_hours += elapsed_hours

        if order.status in (Order.Status.COMPLETED, Order.Status.PARTIAL):
            acc.deliverable_count += 1
            if order.refill_status is not None:
                acc.refilled_count += 1

    return acc


def recompute_all_service_health() -> int:
    """Recomputes every service's health stat from orders placed in the
    last 48h. Returns the number of services touched (had at least one
    order in the window). Services that drop out of the window entirely
    age back down to "not enough data" rather than keeping a stale number."""
    from apps.orders.models import Order

    cutoff = timezone.now() - WINDOW
    recent_orders = (
        Order.objects.filter(created_at__gte=cutoff)
        .exclude(status=Order.Status.ERROR)
        .select_related("service")
        .prefetch_related("status_history", "progress_samples")
    )

    by_service: dict[int, list] = {}
    for order in recent_orders:
        by_service.setdefault(order.service_id, []).append(order)

    for service_id, orders in by_service.items():
        sample_size = len(orders)
        defaults = {"sample_size": sample_size}

        if sample_size < MIN_SAMPLE_SIZE:
            defaults.update(avg_start_minutes=None, avg_speed_per_hour=None, refill_rate_percent=None)
        else:
            acc = _compute_one(orders)
            avg_start = (
                sum(acc.start_deltas_minutes) / len(acc.start_deltas_minutes)
                if acc.start_deltas_minutes
                else None
            )
            avg_speed = acc.delivered_units / acc.elapsed_hours if acc.elapsed_hours > 0 else None
            refill_rate = (
                acc.refilled_count / acc.deliverable_count * 100
                if acc.deliverable_count > 0
                else None
            )
            defaults.update(
                avg_start_minutes=_round1(avg_start) if avg_start is not None else None,
                avg_speed_per_hour=_round1(avg_speed) if avg_speed is not None else None,
                refill_rate_percent=_round1(refill_rate) if refill_rate is not None else None,
            )

        ServiceHealthStat.objects.update_or_create(service_id=service_id, defaults=defaults)

    # Services with a cached stat but nothing in the window any more —
    # don't leave a stale "healthy" number showing from days ago.
    ServiceHealthStat.objects.exclude(service_id__in=by_service.keys()).update(
        sample_size=0, avg_start_minutes=None, avg_speed_per_hour=None, refill_rate_percent=None
    )

    return len(by_service)
