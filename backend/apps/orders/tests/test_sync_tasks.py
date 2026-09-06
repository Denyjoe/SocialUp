from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.catalog.models import Category, Service
from apps.orders.models import Order, OrderStatusHistory
from apps.orders.tasks import retry_stuck_order_submissions, sync_order_statuses
from apps.providers.models import Provider
from apps.wallet.models import LedgerEntry
from apps.wallet.services import WalletService

pytestmark = pytest.mark.django_db

User = get_user_model()
BASE_URL = "https://vinasmm.com/api/v2"


@pytest.fixture
def jap_provider():
    return Provider.objects.create(
        name="VinaSMM",
        provider_type=Provider.ProviderType.JAP_STYLE,
        base_url=BASE_URL,
        api_key="key",
        is_active=True,
    )


@pytest.fixture
def service(jap_provider):
    category = Category.objects.create(name="Instagram", slug="instagram")
    return Service.objects.create(
        provider=jap_provider,
        provider_service_id="1",
        category=category,
        name="Instagram Followers",
        cost_rate_per_1000=Decimal("1.0000"),
        retail_rate_per_1000=Decimal("3000.00"),
    )


@pytest.fixture
def user():
    return User.objects.create_user(email="buyer@example.com", password="x")


def _make_order(user, service, provider, status, provider_order_id) -> Order:
    WalletService.credit(user.wallet, Decimal("10000.00"), LedgerEntry.EntryType.DEPOSIT, f"seed-{uuid4()}")
    entry = WalletService.debit(
        user.wallet, Decimal("3000.00"), LedgerEntry.EntryType.ORDER_PAYMENT, f"charge-{uuid4()}"
    )
    return Order.objects.create(
        user=user,
        service=service,
        provider=provider,
        link="https://instagram.com/example",
        quantity=1000,
        charge_amount=Decimal("3000.00"),
        status=status,
        provider_order_id=provider_order_id,
        ledger_entry=entry,
    )


def test_sync_updates_status_and_records_history(requests_mock, jap_provider, service, user):
    order = _make_order(user, service, jap_provider, Order.Status.IN_PROGRESS, "1001")

    requests_mock.post(BASE_URL, json={"1001": {"status": "Completed", "start_count": "0", "remains": "0"}})
    sync_order_statuses()

    order.refresh_from_db()
    assert order.status == Order.Status.COMPLETED
    assert order.remains == 0
    assert OrderStatusHistory.objects.filter(order=order, new_status="completed").exists()


def test_sync_refunds_wallet_when_provider_reports_canceled(requests_mock, jap_provider, service, user):
    order = _make_order(user, service, jap_provider, Order.Status.PENDING, "1002")
    user.wallet.refresh_from_db()
    balance_before = user.wallet.cached_balance

    requests_mock.post(BASE_URL, json={"1002": {"status": "Canceled", "start_count": None, "remains": "1000"}})
    sync_order_statuses()

    order.refresh_from_db()
    user.wallet.refresh_from_db()
    # refund_order() sets the terminal status to REFUNDED (more informative
    # to the customer than leaving it at CANCELED) after crediting back.
    assert order.status == Order.Status.REFUNDED
    assert order.refund_ledger_entry_id is not None
    assert user.wallet.cached_balance == balance_before + order.charge_amount


def test_sync_skips_terminal_orders_without_calling_provider(requests_mock, jap_provider, service, user):
    _make_order(user, service, jap_provider, Order.Status.COMPLETED, "1003")

    requests_mock.post(BASE_URL, json={})
    sync_order_statuses()

    assert not requests_mock.called


def test_sync_survives_provider_error_without_raising(requests_mock, jap_provider, service, user):
    order = _make_order(user, service, jap_provider, Order.Status.IN_PROGRESS, "1004")

    requests_mock.post(BASE_URL, json={"error": "provider down"})
    sync_order_statuses()  # must not raise

    order.refresh_from_db()
    assert order.status == Order.Status.IN_PROGRESS  # unchanged


def test_retry_stuck_order_submissions_refires_old_unsent_orders(monkeypatch, jap_provider, service, user):
    order = _make_order(user, service, jap_provider, Order.Status.PENDING, "")
    Order.objects.filter(pk=order.pk).update(created_at=timezone.now() - timedelta(minutes=20))

    called_with = []
    monkeypatch.setattr(
        "apps.orders.tasks.submit_order_to_provider.delay", lambda order_id: called_with.append(order_id)
    )
    retry_stuck_order_submissions()
    assert called_with == [str(order.id)]


def test_retry_stuck_order_submissions_ignores_recent_orders(monkeypatch, jap_provider, service, user):
    _make_order(user, service, jap_provider, Order.Status.PENDING, "")  # created_at = now

    called_with = []
    monkeypatch.setattr(
        "apps.orders.tasks.submit_order_to_provider.delay", lambda order_id: called_with.append(order_id)
    )
    retry_stuck_order_submissions()
    assert called_with == []


def test_retry_stuck_order_submissions_ignores_orders_already_submitted(monkeypatch, jap_provider, service, user):
    order = _make_order(user, service, jap_provider, Order.Status.PENDING, "1005")  # has a provider_order_id
    Order.objects.filter(pk=order.pk).update(created_at=timezone.now() - timedelta(minutes=20))

    called_with = []
    monkeypatch.setattr(
        "apps.orders.tasks.submit_order_to_provider.delay", lambda order_id: called_with.append(order_id)
    )
    retry_stuck_order_submissions()
    assert called_with == []
