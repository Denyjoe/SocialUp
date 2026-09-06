from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.common.exchange import ExchangeRateError, convert, fetch_rates
from apps.common.models import ExchangeRateSnapshot
from apps.common.tasks import refresh_exchange_rates

pytestmark = pytest.mark.django_db

RATES_URL = "https://open.er-api.com/v6/latest/TZS"

GOOD_PAYLOAD = {
    "result": "success",
    "provider": "https://www.exchangerate-api.com",
    "base_code": "TZS",
    "rates": {"TZS": 1, "USD": 0.00038, "EUR": 0.00033, "KES": 0.049, "XYZ": 9.9},
}


def test_fetch_rates_keeps_only_supported_currencies(requests_mock):
    requests_mock.get(RATES_URL, json=GOOD_PAYLOAD)
    result = fetch_rates()
    assert "USD" in result["rates"]
    assert "KES" in result["rates"]
    # XYZ is not a currency we offer, so it must not reach the customer.
    assert "XYZ" not in result["rates"]


def test_fetch_rates_rejects_a_failed_response(requests_mock):
    requests_mock.get(RATES_URL, json={"result": "error", "error-type": "unsupported-code"})
    with pytest.raises(ExchangeRateError):
        fetch_rates()


def test_fetch_rates_rejects_a_response_without_usd(requests_mock):
    requests_mock.get(RATES_URL, json={"result": "success", "rates": {"TZS": 1, "KES": 0.049}})
    with pytest.raises(ExchangeRateError, match="USD"):
        fetch_rates()


def test_fetch_rates_drops_nonsense_values(requests_mock):
    requests_mock.get(
        RATES_URL,
        json={"result": "success", "rates": {"TZS": 1, "USD": 0.00038, "EUR": 0, "KES": -1}},
    )
    rates = fetch_rates()["rates"]
    # A zero or negative rate would produce nonsense prices.
    assert "EUR" not in rates
    assert "KES" not in rates


def test_fetch_rates_wraps_a_network_error(requests_mock):
    import requests as requests_lib

    requests_mock.get(RATES_URL, exc=requests_lib.ConnectionError("boom"))
    with pytest.raises(ExchangeRateError):
        fetch_rates()


def test_refresh_stores_a_snapshot(requests_mock):
    requests_mock.get(RATES_URL, json=GOOD_PAYLOAD)
    refresh_exchange_rates()

    snapshot = ExchangeRateSnapshot.latest()
    assert snapshot is not None
    assert snapshot.base_currency == "TZS"
    assert snapshot.rates["USD"] == "0.00038"


def test_failed_refresh_keeps_the_previous_snapshot(requests_mock):
    requests_mock.get(RATES_URL, json=GOOD_PAYLOAD)
    refresh_exchange_rates()
    good = ExchangeRateSnapshot.latest()

    requests_mock.get(RATES_URL, json={"result": "error"})
    refresh_exchange_rates()

    # The bad response must not wipe out usable rates.
    assert ExchangeRateSnapshot.objects.count() == 1
    assert ExchangeRateSnapshot.latest().id == good.id


def test_convert_uses_the_stored_rate():
    rates = {"USD": "0.0004", "TZS": "1"}
    assert convert(Decimal("10000.00"), "USD", rates) == Decimal("4.00")
    # The base currency passes through untouched.
    assert convert(Decimal("10000.00"), "TZS", rates) == Decimal("10000.00")


def test_convert_rejects_an_unknown_currency():
    with pytest.raises(ExchangeRateError):
        convert(Decimal("100"), "JPY", {"USD": "0.0004"})


def test_endpoint_returns_rates_and_is_public(requests_mock):
    requests_mock.get(RATES_URL, json=GOOD_PAYLOAD)
    refresh_exchange_rates()

    resp = APIClient().get(reverse("public-exchange-rates"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["base"] == "TZS"
    assert resp.data["stale"] is False
    assert "USD" in resp.data["rates"]
    assert "USD" in resp.data["supported"]


def test_endpoint_reports_base_only_when_no_snapshot_exists():
    resp = APIClient().get(reverse("public-exchange-rates"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["stale"] is True
    # With no rates we must not invent one: base currency only.
    assert resp.data["supported"] == ["TZS"]


def test_refresh_trims_old_snapshots(requests_mock):
    requests_mock.get(RATES_URL, json=GOOD_PAYLOAD)
    now = timezone.now()
    for i in range(30):
        ExchangeRateSnapshot.objects.create(
            base_currency="TZS",
            rates={"USD": "0.0004"},
            fetched_at=now - timezone.timedelta(hours=i + 1),
        )
    refresh_exchange_rates()
    assert ExchangeRateSnapshot.objects.count() == 24
