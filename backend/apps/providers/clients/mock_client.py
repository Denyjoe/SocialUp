import uuid
from decimal import Decimal

from .base import BaseProviderClient
from .dto import ProviderOrderResult, ProviderOrderStatus, ProviderServiceDTO


class MockProviderClient(BaseProviderClient):
    """Instant-complete fake provider — no network calls, no real money.
    Used for local development and tests until a real upstream provider is
    wired up in Phase 3 (see docs/provider-api-assumptions.md)."""

    def add_order(self, service_id: str, link: str, quantity: int, **kwargs) -> ProviderOrderResult:
        return ProviderOrderResult(
            provider_order_id=f"mock-{uuid.uuid4().hex[:12]}",
            status="completed",
        )

    def get_order_status(self, provider_order_id: str) -> ProviderOrderStatus:
        return ProviderOrderStatus(status="completed", start_count=0, remains=0)

    def get_multi_status(self, provider_order_ids: list[str]) -> dict[str, ProviderOrderStatus]:
        return {pid: self.get_order_status(pid) for pid in provider_order_ids}

    def get_balance(self) -> Decimal:
        return Decimal("999999.00")

    def get_services(self) -> list[ProviderServiceDTO]:
        return []

    def create_refill(self, provider_order_id: str) -> str:
        return f"mock-refill-{uuid.uuid4().hex[:12]}"

    def cancel_order(self, provider_order_id: str) -> bool:
        return True
