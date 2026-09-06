import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.catalog.health import MIN_SAMPLE_SIZE, recompute_all_service_health
from apps.catalog.models import Category, Service, ServiceHealthStat
from apps.orders.models import Order, OrderProgressSample, OrderStatusHistory
from apps.providers.models import Provider
from apps.wallet.models import LedgerEntry
from apps.wallet.services import WalletService

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture
def service():
    provider = Provider.objects.create(name="Mock", provider_type=Provider.ProviderType.MOCK)
    category = Category.objects.create(name="Instagram", slug="instagram")
    return Service.objects.create(
        category=category,
        provider=provider,
        provider_service_id="svc-1",
        name="Instagram Followers",
        cost_rate_per_1000=Decimal("1.5000"),
        retail_rate_per_1000=Decimal("5000.00"),
    )


@pytest.fixture
def buyer():
    return User.objects.create_user(
        email="buyer@example.com", password="x", email_verified=True, phone_verified=True
    )


def _make_order(service, buyer, *, quantity, remains, status, created_hours_ago, refill_status=None):
    """Builds an Order directly (bypassing OrderService) so every field is
    under test control, then backdates created_at since it's auto_now_add."""
    entry = WalletService.credit(
        buyer.wallet,
        Decimal("100000.00"),
        LedgerEntry.EntryType.DEPOSIT,
        f"seed-{uuid.uuid4()}",
    )
    order = Order.objects.create(
        user=buyer,
        service=service,
        provider=service.provider,
        link="https://instagram.com/x",
        quantity=quantity,
        charge_amount=Decimal("10.00"),
        status=status,
        remains=remains,
        refill_status=refill_status,
        ledger_entry=entry,
    )
    backdated = timezone.now() - timedelta(hours=created_hours_ago)
    Order.objects.filter(pk=order.pk).update(created_at=backdated, updated_at=backdated)
    order.refresh_from_db()
    return order


def _add_status_history(order, new_status, hours_ago):
    history = OrderStatusHistory.objects.create(
        order=order, old_status="", new_status=new_status, source=OrderStatusHistory.Source.SYSTEM_SYNC
    )
    OrderStatusHistory.objects.filter(pk=history.pk).update(
        changed_at=timezone.now() - timedelta(hours=hours_ago)
    )


def _add_sample(order, remains, hours_ago):
    sample = OrderProgressSample.objects.create(order=order, remains=remains)
    OrderProgressSample.objects.filter(pk=sample.pk).update(
        sampled_at=timezone.now() - timedelta(hours=hours_ago)
    )


def test_recompute_computes_start_time_speed_and_refill_rate(service, buyer):
    # Order 1: in progress, 500/1000 delivered, started 30min in, sampled 1h ago.
    o1 = _make_order(service, buyer, quantity=1000, remains=500, status=Order.Status.IN_PROGRESS, created_hours_ago=4)
    _add_status_history(o1, Order.Status.IN_PROGRESS, hours_ago=3.5)
    _add_sample(o1, remains=500, hours_ago=1)

    # Order 2: completed, fully delivered, started 15min in, sampled 30min ago, no refill.
    o2 = _make_order(service, buyer, quantity=2000, remains=0, status=Order.Status.COMPLETED, created_hours_ago=4)
    _add_status_history(o2, Order.Status.IN_PROGRESS, hours_ago=3.75)
    _add_sample(o2, remains=0, hours_ago=0.5)

    # Order 3: partial, 800/1000 delivered, started 6min in, sampled 2h ago, refill requested.
    o3 = _make_order(
        service, buyer, quantity=1000, remains=200, status=Order.Status.PARTIAL,
        created_hours_ago=4, refill_status=Order.RequestState.REQUESTED,
    )
    _add_status_history(o3, Order.Status.IN_PROGRESS, hours_ago=3.9)
    _add_sample(o3, remains=200, hours_ago=2)

    touched = recompute_all_service_health()
    assert touched == 1

    stat = ServiceHealthStat.objects.get(service=service)
    assert stat.sample_size == 3
    # (30 + 15 + 6) / 3 minutes
    assert stat.avg_start_minutes == Decimal("17.0")
    # (500 + 2000 + 800) delivered / (3 + 3.5 + 2) hours elapsed = 3300 / 8.5
    assert stat.avg_speed_per_hour == Decimal("388.2")
    # 1 of 2 deliverable (completed/partial) orders needed a refill
    assert stat.refill_rate_percent == Decimal("50.0")


def test_recompute_leaves_averages_null_below_minimum_sample_size(service, buyer):
    assert MIN_SAMPLE_SIZE > 1  # sanity check the fixture below is actually under it
    _make_order(service, buyer, quantity=1000, remains=0, status=Order.Status.COMPLETED, created_hours_ago=1)

    recompute_all_service_health()

    stat = ServiceHealthStat.objects.get(service=service)
    assert stat.sample_size == 1
    assert stat.avg_start_minutes is None
    assert stat.avg_speed_per_hour is None
    assert stat.refill_rate_percent is None


def test_recompute_ignores_orders_outside_the_48h_window(service, buyer):
    for _ in range(MIN_SAMPLE_SIZE):
        _make_order(service, buyer, quantity=1000, remains=0, status=Order.Status.COMPLETED, created_hours_ago=50)

    recompute_all_service_health()

    assert not ServiceHealthStat.objects.filter(service=service).exists()


def test_recompute_ignores_error_orders(service, buyer):
    for _ in range(MIN_SAMPLE_SIZE):
        _make_order(service, buyer, quantity=1000, remains=1000, status=Order.Status.ERROR, created_hours_ago=1)

    recompute_all_service_health()

    assert not ServiceHealthStat.objects.filter(service=service).exists()


def test_recompute_ages_out_a_stat_with_no_recent_orders(service):
    # A stale stat from a service that used to have volume but has none now.
    ServiceHealthStat.objects.create(
        service=service,
        sample_size=10,
        avg_start_minutes=Decimal("5.0"),
        avg_speed_per_hour=Decimal("100.0"),
        refill_rate_percent=Decimal("2.0"),
    )

    recompute_all_service_health()

    stat = ServiceHealthStat.objects.get(service=service)
    assert stat.sample_size == 0
    assert stat.avg_start_minutes is None
    assert stat.avg_speed_per_hour is None
    assert stat.refill_rate_percent is None


def test_recompute_falls_back_to_updated_at_when_no_progress_sample_exists(service, buyer):
    # A very short-lived order: completed between two sync ticks, so it
    # never got an OrderProgressSample row of its own.
    orders = [
        _make_order(service, buyer, quantity=1000, remains=0, status=Order.Status.COMPLETED, created_hours_ago=2)
        for _ in range(MIN_SAMPLE_SIZE)
    ]
    for order in orders:
        Order.objects.filter(pk=order.pk).update(updated_at=timezone.now() - timedelta(hours=1))

    recompute_all_service_health()

    stat = ServiceHealthStat.objects.get(service=service)
    assert stat.sample_size == MIN_SAMPLE_SIZE
    # Each order: 1000 delivered over 1h elapsed (created 2h ago, "sampled" via updated_at 1h ago).
    assert stat.avg_speed_per_hour == Decimal("1000.0")
