from django.conf import settings

from .base import BasePaymentGateway
from .mock import MockPaymentGateway
from .nowpayments import NOWPaymentsGateway


def get_gateway(name: str) -> BasePaymentGateway:
    if name == "nowpayments":
        if settings.NOWPAYMENTS_API_KEY and settings.NOWPAYMENTS_IPN_SECRET:
            return NOWPaymentsGateway(
                api_key=settings.NOWPAYMENTS_API_KEY,
                ipn_secret=settings.NOWPAYMENTS_IPN_SECRET,
                ipn_callback_url=settings.NOWPAYMENTS_IPN_CALLBACK_URL,
                frontend_base_url=settings.FRONTEND_BASE_URL,
            )
        return MockPaymentGateway()
    raise ValueError(f"Unknown payment gateway: {name!r}")
