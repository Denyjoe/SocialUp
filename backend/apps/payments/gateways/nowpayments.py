import hashlib
import hmac
import json

import requests

from .base import BasePaymentGateway
from .dto import CheckoutResult, WebhookResult
from .exceptions import PaymentGatewayError

API_BASE = "https://api.nowpayments.io/v1"
REQUEST_TIMEOUT_SECONDS = 15


class NOWPaymentsGateway(BasePaymentGateway):
    """Real HTTP client. Confirmed against NOWPayments' published API
    contract (https://documenter.getpostman.com/view/7907941/2s93JusNJt) —
    see docs/nowpayments-crypto-setup.md for what was confirmed vs.
    assumed.

    Uses the "Create invoice" (hosted checkout) endpoint rather than
    "Create payment" (build-your-own address/QR UI) deliberately: the
    hosted page already handles currency selection, minimum-amount
    checking, and price estimation for us, so there's no need to
    replicate NOWPayments' own /min-amount and /estimate endpoints here —
    the whole point of the invoice flow is that their page owns that UI.
    """

    def __init__(self, api_key: str, ipn_secret: str, ipn_callback_url: str, frontend_base_url: str):
        self.api_key = api_key
        self.ipn_secret = ipn_secret
        self.ipn_callback_url = ipn_callback_url
        self.frontend_base_url = frontend_base_url

    def create_checkout(self, *, transaction) -> CheckoutResult:
        return_base = f"{self.frontend_base_url}/dashboard/add-funds?deposit={transaction.internal_reference}"
        payload = {
            "price_amount": float(transaction.amount_quote),
            "price_currency": transaction.quote_currency,
            "order_id": transaction.internal_reference,
            "order_description": f"Wallet deposit — {transaction.user.email}",
            "ipn_callback_url": self.ipn_callback_url,
            "success_url": f"{return_base}&result=success",
            "cancel_url": f"{return_base}&result=cancelled",
            "partially_paid_url": f"{return_base}&result=partial",
        }
        try:
            response = requests.post(
                f"{API_BASE}/invoice",
                json=payload,
                headers={"x-api-key": self.api_key, "Content-Type": "application/json"},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise PaymentGatewayError(f"NOWPayments request failed: {exc}") from exc

        if not response.ok:
            raise PaymentGatewayError(
                f"NOWPayments HTTP {response.status_code}: {response.text[:300]}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise PaymentGatewayError("NOWPayments returned a non-JSON response") from exc

        return CheckoutResult(checkout_url=data["invoice_url"], gateway_reference=str(data["id"]))

    def verify_webhook_signature(self, *, raw_body: bytes, signature: str) -> bool:
        if not signature:
            return False
        try:
            payload = json.loads(raw_body)
        except ValueError:
            return False
        # This is NOWPayments' own documented Python recipe verbatim
        # (sort_keys=True sorts nested dicts too, not just the top level) —
        # matching it exactly matters, since re-serializing the payload
        # any other way can produce a byte-different string and a
        # signature that never matches.
        sorted_message = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        expected = hmac.new(
            self.ipn_secret.encode(), sorted_message.encode(), hashlib.sha512
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def parse_webhook(self, payload: dict) -> WebhookResult:
        return WebhookResult(
            internal_reference=str(payload.get("order_id") or ""),
            status=str(payload.get("payment_status") or ""),
            pay_currency=str(payload.get("pay_currency") or ""),
        )
