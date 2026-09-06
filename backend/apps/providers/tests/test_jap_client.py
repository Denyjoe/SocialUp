from decimal import Decimal
from urllib.parse import parse_qsl

import pytest

from apps.providers.clients.exceptions import ProviderAPIError
from apps.providers.clients.jap_client import JAPStyleClient
from apps.providers.models import Provider

pytestmark = pytest.mark.django_db

BASE_URL = "https://vinasmm.com/api/v2"


@pytest.fixture
def provider():
    return Provider(
        name="VinaSMM",
        provider_type=Provider.ProviderType.JAP_STYLE,
        base_url=BASE_URL,
        api_key="test-key-123",
    )


@pytest.fixture
def client(provider):
    return JAPStyleClient(provider)


def test_add_order_sends_correct_payload_and_parses_response(requests_mock, client):
    requests_mock.post(BASE_URL, json={"order": 12345})
    result = client.add_order(service_id="1", link="https://instagram.com/x", quantity=1000)

    assert result.provider_order_id == "12345"
    assert result.status == "pending"
    sent = dict(parse_qsl(requests_mock.last_request.text))
    assert sent == {
        "key": "test-key-123",
        "action": "add",
        "service": "1",
        "link": "https://instagram.com/x",
        "quantity": "1000",
    }


def test_add_order_raises_on_error_response(requests_mock, client):
    requests_mock.post(BASE_URL, json={"error": "Not enough funds"})
    with pytest.raises(ProviderAPIError, match="Not enough funds"):
        client.add_order(service_id="1", link="https://instagram.com/x", quantity=1000)


def test_add_order_raises_on_http_error(requests_mock, client):
    requests_mock.post(BASE_URL, status_code=500, text="server error")
    with pytest.raises(ProviderAPIError, match="HTTP 500"):
        client.add_order(service_id="1", link="https://instagram.com/x", quantity=1000)


def test_get_order_status_parses_fields(requests_mock, client):
    requests_mock.post(
        BASE_URL,
        json={"charge": "5.00", "start_count": "100", "status": "In progress", "remains": "50", "currency": "USD"},
    )
    status = client.get_order_status("12345")
    assert status.status == "In progress"
    assert status.start_count == 100
    assert status.remains == 50


def test_get_multi_status_handles_dict_keyed_response(requests_mock, client):
    requests_mock.post(
        BASE_URL,
        json={
            "1": {"status": "Completed", "start_count": "0", "remains": "0"},
            "2": {"status": "Partial", "start_count": "10", "remains": "5"},
        },
    )
    statuses = client.get_multi_status(["1", "2"])
    assert statuses["1"].status == "Completed"
    assert statuses["2"].remains == 5


def test_get_multi_status_handles_list_response(requests_mock, client):
    requests_mock.post(
        BASE_URL,
        json=[
            {"order": 1, "status": "Completed", "remains": "0"},
            {"order": 2, "status": "Partial", "remains": "5"},
        ],
    )
    statuses = client.get_multi_status(["1", "2"])
    assert statuses["1"].status == "Completed"
    assert statuses["2"].status == "Partial"


def test_get_multi_status_empty_list_makes_no_request(requests_mock, client):
    statuses = client.get_multi_status([])
    assert statuses == {}
    assert not requests_mock.called


def test_get_balance(requests_mock, client):
    requests_mock.post(BASE_URL, json={"balance": "123.45", "currency": "USD"})
    assert client.get_balance() == Decimal("123.45")


def test_get_services_parses_list_and_skips_malformed_rows(requests_mock, client):
    requests_mock.post(
        BASE_URL,
        json=[
            {"service": 1, "name": "IG Followers", "category": "Instagram", "rate": "1.5", "min": "100", "max": "10000", "type": "Default"},
            {"service": 2, "name": "Broken row"},  # missing required fields -> skipped
        ],
    )
    services = client.get_services()
    assert len(services) == 1
    assert services[0].provider_service_id == "1"
    assert services[0].rate_per_1000 == Decimal("1.5")


def test_create_refill(requests_mock, client):
    requests_mock.post(BASE_URL, json={"refill": "999"})
    assert client.create_refill("12345") == "999"


def test_cancel_order_true_when_cancel_id_present(requests_mock, client):
    requests_mock.post(BASE_URL, json=[{"order": 12345, "cancel": 555}])
    assert client.cancel_order("12345") is True


def test_cancel_order_false_when_order_not_found_in_response(requests_mock, client):
    requests_mock.post(BASE_URL, json=[{"order": 99999, "cancel": 555}])
    assert client.cancel_order("12345") is False
