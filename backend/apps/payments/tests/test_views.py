import hashlib
import hmac
import json
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.common.models import ExchangeRateSnapshot
from apps.payments.models import Transaction

pytestmark = pytest.mark.django_db

User = get_user_model()

TEST_IPN_SECRET = "test-ipn-secret"


@pytest.fixture
def user():
    return User.objects.create_user(email="depositor@example.com", password="x")


@pytest.fixture
def client(user):
    api = APIClient()
    api.force_authenticate(user=user)
    return api


@pytest.fixture
def rates():
    return ExchangeRateSnapshot.objects.create(
        base_currency="TZS", rates={"TZS": "1", "USD": "0.0004"}, fetched_at=timezone.now()
    )


def _sign(payload: dict, secret: str = TEST_IPN_SECRET) -> str:
    sorted_message = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return hmac.new(secret.encode(), sorted_message.encode(), hashlib.sha512).hexdigest()


# ── Deposit creation (mock gateway — no real credentials configured) ──────


def test_create_deposit_returns_a_checkout_and_settles_via_mock(client, rates):
    response = client.post(reverse("deposit-list-create"), {"amount": "50000.00"}, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["status"] == "finished"
    assert response.data["checkout_url"]
    assert Transaction.objects.count() == 1


def test_create_deposit_rejects_a_bad_amount(client, rates):
    response = client.post(reverse("deposit-list-create"), {"amount": "100.00"}, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_create_deposit_requires_authentication(rates):
    response = APIClient().post(reverse("deposit-list-create"), {"amount": "50000.00"}, format="json")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_list_deposits_only_shows_the_caller_own(client, user, rates):
    from apps.payments.services import PaymentService

    PaymentService.create_deposit(user=user, amount_local=Decimal("50000.00"))
    other = User.objects.create_user(email="other@example.com", password="x")
    PaymentService.create_deposit(user=other, amount_local=Decimal("50000.00"))

    response = client.get(reverse("deposit-list-create"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1


def test_deposit_detail_by_reference(client, user, rates):
    from apps.payments.services import PaymentService

    txn = PaymentService.create_deposit(user=user, amount_local=Decimal("50000.00"))

    response = client.get(reverse("deposit-detail", args=[txn.internal_reference]))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["internal_reference"] == txn.internal_reference


def test_deposit_detail_hides_another_users_deposit(client, rates):
    from apps.payments.services import PaymentService

    other = User.objects.create_user(email="other2@example.com", password="x")
    txn = PaymentService.create_deposit(user=other, amount_local=Decimal("50000.00"))

    response = client.get(reverse("deposit-detail", args=[txn.internal_reference]))

    assert response.status_code == status.HTTP_404_NOT_FOUND


# ── NOWPayments webhook (real gateway class, test credentials — no network) ──


@override_settings(NOWPAYMENTS_API_KEY="test-api-key", NOWPAYMENTS_IPN_SECRET=TEST_IPN_SECRET)
def test_webhook_credits_the_wallet_end_to_end(user):
    txn = Transaction.objects.create(
        user=user,
        gateway=Transaction.Gateway.NOWPAYMENTS,
        internal_reference="dep-webhook-1",
        amount_local=Decimal("50000.00"),
        amount_quote=Decimal("20.00"),
        quote_currency="usd",
        status=Transaction.Status.WAITING,
    )
    payload = {"order_id": "dep-webhook-1", "payment_status": "finished", "pay_currency": "btc"}
    raw_body = json.dumps(payload).encode()

    response = APIClient().post(
        reverse("nowpayments-webhook"),
        data=raw_body,
        content_type="application/json",
        HTTP_X_NOWPAYMENTS_SIG=_sign(payload),
    )

    assert response.status_code == status.HTTP_200_OK
    txn.refresh_from_db()
    assert txn.status == "finished"
    assert txn.pay_currency == "btc"
    assert txn.ledger_entry_id is not None
    user.wallet.refresh_from_db()
    assert user.wallet.cached_balance == Decimal("50000.00")


@override_settings(NOWPAYMENTS_API_KEY="test-api-key", NOWPAYMENTS_IPN_SECRET=TEST_IPN_SECRET)
def test_webhook_rejects_a_bad_signature_and_does_not_credit(user):
    txn = Transaction.objects.create(
        user=user,
        gateway=Transaction.Gateway.NOWPAYMENTS,
        internal_reference="dep-webhook-2",
        amount_local=Decimal("50000.00"),
        amount_quote=Decimal("20.00"),
        quote_currency="usd",
        status=Transaction.Status.WAITING,
    )
    payload = {"order_id": "dep-webhook-2", "payment_status": "finished"}

    response = APIClient().post(
        reverse("nowpayments-webhook"),
        data=json.dumps(payload).encode(),
        content_type="application/json",
        HTTP_X_NOWPAYMENTS_SIG="0" * 128,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    txn.refresh_from_db()
    assert txn.status == "waiting"
    assert txn.ledger_entry_id is None


@override_settings(NOWPAYMENTS_API_KEY="test-api-key", NOWPAYMENTS_IPN_SECRET=TEST_IPN_SECRET)
def test_webhook_delivered_twice_only_credits_once(user):
    Transaction.objects.create(
        user=user,
        gateway=Transaction.Gateway.NOWPAYMENTS,
        internal_reference="dep-webhook-3",
        amount_local=Decimal("50000.00"),
        amount_quote=Decimal("20.00"),
        quote_currency="usd",
        status=Transaction.Status.WAITING,
    )
    payload = {"order_id": "dep-webhook-3", "payment_status": "finished"}
    raw_body = json.dumps(payload).encode()
    signature = _sign(payload)

    api = APIClient()
    for _ in range(2):
        response = api.post(
            reverse("nowpayments-webhook"),
            data=raw_body,
            content_type="application/json",
            HTTP_X_NOWPAYMENTS_SIG=signature,
        )
        assert response.status_code == status.HTTP_200_OK

    user.wallet.refresh_from_db()
    assert user.wallet.cached_balance == Decimal("50000.00")  # not doubled


@override_settings(NOWPAYMENTS_API_KEY="test-api-key", NOWPAYMENTS_IPN_SECRET=TEST_IPN_SECRET)
def test_webhook_for_an_unknown_reference_is_acknowledged_not_errored():
    payload = {"order_id": "dep-does-not-exist", "payment_status": "finished"}
    response = APIClient().post(
        reverse("nowpayments-webhook"),
        data=json.dumps(payload).encode(),
        content_type="application/json",
        HTTP_X_NOWPAYMENTS_SIG=_sign(payload),
    )
    assert response.status_code == status.HTTP_200_OK
