import hashlib
import hmac
import json

from apps.payments.gateways.mock import MockPaymentGateway
from apps.payments.gateways.nowpayments import NOWPaymentsGateway

IPN_SECRET = "test-ipn-secret"


def _gateway() -> NOWPaymentsGateway:
    return NOWPaymentsGateway(
        api_key="test-api-key",
        ipn_secret=IPN_SECRET,
        ipn_callback_url="https://backend.example/api/payments/webhooks/nowpayments/",
        frontend_base_url="https://app.example",
    )


def _sign(payload: dict) -> str:
    sorted_message = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return hmac.new(IPN_SECRET.encode(), sorted_message.encode(), hashlib.sha512).hexdigest()


def test_verify_webhook_signature_accepts_a_correctly_signed_payload():
    gateway = _gateway()
    payload = {"order_id": "dep-abc", "payment_status": "finished", "price_amount": 10}
    raw_body = json.dumps(payload).encode()  # arbitrary key order — verification sorts its own copy

    assert gateway.verify_webhook_signature(raw_body=raw_body, signature=_sign(payload)) is True


def test_verify_webhook_signature_rejects_a_tampered_payload():
    gateway = _gateway()
    payload = {"order_id": "dep-abc", "payment_status": "finished", "price_amount": 10}
    signature = _sign(payload)

    tampered = dict(payload, payment_status="failed")
    raw_body = json.dumps(tampered).encode()

    assert gateway.verify_webhook_signature(raw_body=raw_body, signature=signature) is False


def test_verify_webhook_signature_rejects_a_wrong_secret():
    gateway = _gateway()
    payload = {"order_id": "dep-abc", "payment_status": "finished"}
    sorted_message = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    wrong_signature = hmac.new(b"not-the-secret", sorted_message.encode(), hashlib.sha512).hexdigest()

    assert gateway.verify_webhook_signature(raw_body=json.dumps(payload).encode(), signature=wrong_signature) is False


def test_verify_webhook_signature_rejects_missing_signature():
    gateway = _gateway()
    assert gateway.verify_webhook_signature(raw_body=b"{}", signature="") is False


def test_verify_webhook_signature_rejects_invalid_json():
    gateway = _gateway()
    assert gateway.verify_webhook_signature(raw_body=b"not json", signature="anything") is False


def test_parse_webhook_maps_the_documented_fields():
    gateway = _gateway()
    result = gateway.parse_webhook(
        {"order_id": "dep-abc", "payment_status": "finished", "pay_currency": "btc"}
    )
    assert result.internal_reference == "dep-abc"
    assert result.status == "finished"
    assert result.pay_currency == "btc"


def test_parse_webhook_handles_a_missing_order_id():
    gateway = _gateway()
    result = gateway.parse_webhook({"payment_status": "finished"})
    assert result.internal_reference == ""


def test_mock_gateway_settles_immediately():
    gateway = MockPaymentGateway()

    class _FakeTxn:
        internal_reference = "dep-mock-1"

    result = gateway.create_checkout(transaction=_FakeTxn())

    assert result.immediate_status == "finished"
    assert result.gateway_reference.startswith("mock-")
