from abc import ABC, abstractmethod

from .dto import CheckoutResult, WebhookResult


class BasePaymentGateway(ABC):
    """One pluggable payment gateway. NOWPayments (crypto) is the first
    real implementation; PesaPal is meant to slot in later as a second one
    behind this exact same interface, once it's verified."""

    @abstractmethod
    def create_checkout(self, *, transaction) -> CheckoutResult:
        """Starts a payment for this Transaction and returns where to send
        the customer to complete it."""

    @abstractmethod
    def verify_webhook_signature(self, *, raw_body: bytes, signature: str) -> bool:
        """True only if `signature` is a genuine signature of `raw_body`
        from this gateway — the only thing standing between this endpoint
        and anyone on the internet POSTing a fake "payment finished"."""

    @abstractmethod
    def parse_webhook(self, payload: dict) -> WebhookResult:
        """Maps a verified webhook payload to which Transaction it's about
        and what status it's reporting."""
