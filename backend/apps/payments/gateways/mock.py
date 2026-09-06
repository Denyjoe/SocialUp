import uuid

from .base import BasePaymentGateway
from .dto import CheckoutResult, WebhookResult


class MockPaymentGateway(BasePaymentGateway):
    """Used whenever NOWPAYMENTS_API_KEY/NOWPAYMENTS_IPN_SECRET aren't set —
    same role apps.providers.clients.mock_client plays for the reseller
    API: the whole deposit flow works end-to-end in local dev and tests
    with zero external credentials. Settles instantly via
    `immediate_status` rather than actually redirecting anywhere, since a
    real crypto checkout is a hosted page a mock has no honest way to
    fake."""

    def create_checkout(self, *, transaction) -> CheckoutResult:
        return CheckoutResult(
            checkout_url=f"mock-checkout://{transaction.internal_reference}",
            gateway_reference=f"mock-{uuid.uuid4().hex[:12]}",
            immediate_status="finished",
        )

    def verify_webhook_signature(self, *, raw_body: bytes, signature: str) -> bool:
        # The mock never receives a real webhook — it settles inline from
        # create_checkout's immediate_status instead.
        return True

    def parse_webhook(self, payload: dict) -> WebhookResult:
        raise NotImplementedError("MockPaymentGateway settles inline; it never parses a webhook.")
