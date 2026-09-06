from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.common.models import ExchangeRateSnapshot
from apps.payments.models import Transaction
from apps.payments.services import PaymentService, PaymentValidationError

pytestmark = pytest.mark.django_db

User = get_user_model()

RATES_URL = "https://open.er-api.com/v6/latest/TZS"


@pytest.fixture
def user():
    return User.objects.create_user(email="depositor@example.com", password="x")


@pytest.fixture
def rates():
    # 1 TZS = 0.0004 USD, i.e. ~2500 TZS/USD — realistic enough for the
    # minimum-deposit boundary tests below.
    return ExchangeRateSnapshot.objects.create(
        base_currency="TZS", rates={"TZS": "1", "USD": "0.0004"}, fetched_at=timezone.now()
    )


def test_create_deposit_with_mock_gateway_settles_and_credits_instantly(user, rates):
    txn = PaymentService.create_deposit(user=user, amount_local=Decimal("50000.00"))

    assert txn.gateway == Transaction.Gateway.NOWPAYMENTS
    assert txn.status == Transaction.Status.FINISHED
    assert txn.amount_quote == Decimal("20.00")  # 50000 * 0.0004
    assert txn.ledger_entry_id is not None
    assert txn.checkout_url  # mock still returns a URL, even if not a real one

    user.wallet.refresh_from_db()
    assert user.wallet.cached_balance == Decimal("50000.00")


def test_create_deposit_rejects_zero_amount(user, rates):
    with pytest.raises(PaymentValidationError):
        PaymentService.create_deposit(user=user, amount_local=Decimal("0"))


def test_create_deposit_rejects_negative_amount(user, rates):
    with pytest.raises(PaymentValidationError):
        PaymentService.create_deposit(user=user, amount_local=Decimal("-100"))


def test_create_deposit_rejects_below_the_minimum(user, rates):
    # 1000 TZS * 0.0004 = $0.40, well under the $5 floor.
    with pytest.raises(PaymentValidationError, match="minimum"):
        PaymentService.create_deposit(user=user, amount_local=Decimal("1000.00"))

    user.wallet.refresh_from_db()
    assert user.wallet.cached_balance == Decimal("0.00")


def test_create_deposit_self_heals_when_no_rate_snapshot_exists(user, requests_mock):
    assert ExchangeRateSnapshot.latest() is None
    requests_mock.get(
        RATES_URL,
        json={"result": "success", "provider": "test", "rates": {"TZS": 1, "USD": 0.0004}},
    )

    txn = PaymentService.create_deposit(user=user, amount_local=Decimal("50000.00"))

    assert txn.status == Transaction.Status.FINISHED
    assert ExchangeRateSnapshot.latest() is not None


def test_settle_is_idempotent_and_only_credits_the_wallet_once(user, rates):
    txn = Transaction.objects.create(
        user=user,
        gateway=Transaction.Gateway.NOWPAYMENTS,
        internal_reference="dep-idempotent-1",
        amount_local=Decimal("10000.00"),
        amount_quote=Decimal("4.00"),
        quote_currency="usd",
        status=Transaction.Status.WAITING,
    )

    PaymentService._settle(txn, new_status=Transaction.Status.FINISHED, raw={"first": True})
    first_entry_id = txn.ledger_entry_id
    assert first_entry_id is not None

    # A resent webhook (NOWPayments explicitly documents retrying on
    # timeout) must never credit twice.
    PaymentService._settle(txn, new_status=Transaction.Status.FINISHED, raw={"second": True})

    assert txn.ledger_entry_id == first_entry_id
    user.wallet.refresh_from_db()
    assert user.wallet.cached_balance == Decimal("10000.00")


def test_settle_does_not_credit_on_a_non_finished_status(user, rates):
    txn = Transaction.objects.create(
        user=user,
        gateway=Transaction.Gateway.NOWPAYMENTS,
        internal_reference="dep-partial-1",
        amount_local=Decimal("10000.00"),
        amount_quote=Decimal("4.00"),
        quote_currency="usd",
        status=Transaction.Status.WAITING,
    )

    PaymentService._settle(txn, new_status=Transaction.Status.PARTIALLY_PAID, raw={})

    assert txn.ledger_entry_id is None
    user.wallet.refresh_from_db()
    assert user.wallet.cached_balance == Decimal("0.00")
