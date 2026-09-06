"""Live exchange rates, used only to display prices in a customer's own
currency. Nothing here ever affects what a wallet is charged: orders, the
ledger and every stored amount stay in the base currency.

Source: open.er-api.com, which is free, needs no API key and quotes TZS.
"""

import logging
from decimal import Decimal

import requests
from django.utils import timezone

logger = logging.getLogger(__name__)

BASE_CURRENCY = "TZS"
REQUEST_TIMEOUT_SECONDS = 15
RATES_URL = "https://open.er-api.com/v6/latest/{base}"

# Only the currencies we actually offer, so a customer is never shown a
# rate we have not sanity checked.
SUPPORTED_CURRENCIES = ["TZS", "USD", "EUR", "GBP", "KES", "UGX", "RWF", "ZAR", "NGN", "INR"]


class ExchangeRateError(Exception):
    pass


def fetch_rates(base: str = BASE_CURRENCY) -> dict:
    """Returns {"rates": {...}, "source": str, "fetched_at": datetime}.

    Raises ExchangeRateError rather than returning partial data, so a bad
    response can never overwrite a good snapshot.
    """
    try:
        response = requests.get(
            RATES_URL.format(base=base), timeout=REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise ExchangeRateError(f"Could not reach the rate provider: {exc}") from exc

    if payload.get("result") != "success":
        raise ExchangeRateError(f"Rate provider returned: {payload.get('result')!r}")

    all_rates = payload.get("rates") or {}
    rates = {}
    for code in SUPPORTED_CURRENCIES:
        value = all_rates.get(code)
        # A zero or negative rate would produce nonsense prices, so drop it
        # rather than storing it.
        if value is None or float(value) <= 0:
            continue
        rates[code] = str(value)

    if "USD" not in rates:
        # USD is the one currency international customers will expect, so
        # a response without it is treated as unusable.
        raise ExchangeRateError("Rate provider response did not include USD.")

    return {
        "rates": rates,
        "source": payload.get("provider") or "open.er-api.com",
        "fetched_at": timezone.now(),
    }


def convert(amount: Decimal, to_currency: str, rates: dict) -> Decimal:
    """Converts an amount in the base currency into `to_currency`."""
    if to_currency == BASE_CURRENCY:
        return amount
    rate = rates.get(to_currency)
    if rate is None:
        raise ExchangeRateError(f"No rate available for {to_currency}.")
    return (amount * Decimal(str(rate))).quantize(Decimal("0.01"))
