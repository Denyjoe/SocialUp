from decimal import Decimal, InvalidOperation
from typing import Any

import requests

from .base import BaseProviderClient
from .dto import ProviderOrderResult, ProviderOrderStatus, ProviderServiceDTO
from .exceptions import ProviderAPIError, ProviderTimeoutError

REQUEST_TIMEOUT_SECONDS = 15


class JAPStyleClient(BaseProviderClient):
    """Real HTTP client for the common single-endpoint JAP-style reseller
    API. Verified against VinaSMM's docs (https://vinasmm.com/api) — see
    docs/provider-api-assumptions.md for the confirmed contract and the
    handful of things still to verify with real credentials."""

    def __init__(self, provider):
        self.provider = provider

    def _post(self, action: str, **params: Any) -> Any:
        payload = {"key": self.provider.api_key, "action": action, **params}
        try:
            response = requests.post(
                self.provider.base_url, data=payload, timeout=REQUEST_TIMEOUT_SECONDS
            )
        except requests.Timeout as exc:
            raise ProviderTimeoutError(f"{self.provider.name}: request timed out") from exc
        except requests.RequestException as exc:
            raise ProviderAPIError(f"{self.provider.name}: request failed: {exc}") from exc

        if not response.ok:
            raise ProviderAPIError(
                f"{self.provider.name}: HTTP {response.status_code} for action={action!r}: {response.text[:300]}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderAPIError(
                f"{self.provider.name}: non-JSON response for action={action!r}: {response.text[:300]}"
            ) from exc

        if isinstance(data, dict) and data.get("error"):
            raise ProviderAPIError(f"{self.provider.name}: {data['error']}")

        return data

    def add_order(self, service_id: str, link: str, quantity: int, **kwargs) -> ProviderOrderResult:
        # Only the default/quantity-based variant is wired up — see
        # docs/provider-api-assumptions.md "Not yet built" for drip-feed/
        # custom-comments/mentions/subscriptions.
        data = self._post("add", service=service_id, link=link, quantity=quantity, **kwargs)
        if "order" not in data:
            raise ProviderAPIError(f"{self.provider.name}: 'add' response missing 'order': {data!r}")
        # The API doesn't return a status on creation — new orders start pending.
        return ProviderOrderResult(provider_order_id=str(data["order"]), status="pending")

    def get_order_status(self, provider_order_id: str) -> ProviderOrderStatus:
        data = self._post("status", order=provider_order_id)
        return self._parse_status(data)

    def get_multi_status(self, provider_order_ids: list[str]) -> dict[str, ProviderOrderStatus]:
        if not provider_order_ids:
            return {}
        data = self._post("status", orders=",".join(str(i) for i in provider_order_ids))
        # ASSUMED shape (not shown in the fetched docs): dict keyed by order
        # id. Defensively also handle a list-of-objects shape in case the
        # real API returns that instead — see docs/provider-api-assumptions.md.
        if isinstance(data, dict):
            return {str(order_id): self._parse_status(entry) for order_id, entry in data.items()}
        if isinstance(data, list):
            result = {}
            for entry in data:
                order_id = entry.get("order")
                if order_id is not None:
                    result[str(order_id)] = self._parse_status(entry)
            return result
        raise ProviderAPIError(f"{self.provider.name}: unexpected multi-status shape: {data!r}")

    @staticmethod
    def _parse_status(entry: dict) -> ProviderOrderStatus:
        def _int_or_none(value):
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        return ProviderOrderStatus(
            status=str(entry.get("status", "")),
            start_count=_int_or_none(entry.get("start_count")),
            remains=_int_or_none(entry.get("remains")),
        )

    def get_balance(self) -> Decimal:
        data = self._post("balance")
        try:
            return Decimal(str(data["balance"]))
        except (KeyError, InvalidOperation) as exc:
            raise ProviderAPIError(f"{self.provider.name}: bad balance response: {data!r}") from exc

    def get_services(self) -> list[ProviderServiceDTO]:
        data = self._post("services")
        if not isinstance(data, list):
            raise ProviderAPIError(f"{self.provider.name}: expected a list from 'services', got {data!r}")

        services = []
        for raw in data:
            try:
                services.append(
                    ProviderServiceDTO(
                        provider_service_id=str(raw["service"]),
                        name=raw["name"],
                        category=raw.get("category", ""),
                        rate_per_1000=Decimal(str(raw["rate"])),
                        min_quantity=int(raw["min"]),
                        max_quantity=int(raw["max"]),
                        service_type=str(raw.get("type", "default")),
                    )
                )
            except (KeyError, InvalidOperation, TypeError, ValueError):
                # Skip a malformed row rather than failing the whole sync.
                continue
        return services

    def create_refill(self, provider_order_id: str) -> str:
        data = self._post("refill", order=provider_order_id)
        if "refill" not in data:
            raise ProviderAPIError(f"{self.provider.name}: 'refill' response missing 'refill': {data!r}")
        return str(data["refill"])

    def cancel_order(self, provider_order_id: str) -> bool:
        # The API takes `orders` (plural) even for a single id, and always
        # responds with a list.
        data = self._post("cancel", orders=str(provider_order_id))
        if not isinstance(data, list):
            raise ProviderAPIError(f"{self.provider.name}: expected a list from 'cancel', got {data!r}")
        return any(str(entry.get("order")) == str(provider_order_id) and entry.get("cancel") for entry in data)
