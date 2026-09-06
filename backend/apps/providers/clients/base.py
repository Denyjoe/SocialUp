from abc import ABC, abstractmethod
from decimal import Decimal

from .dto import ProviderOrderResult, ProviderOrderStatus, ProviderServiceDTO


class BaseProviderClient(ABC):
    """Every upstream reseller provider is accessed through this interface,
    so `apps/orders` never needs to know which concrete provider it's
    talking to. See docs/provider-api-assumptions.md for the contract
    JAPStyleClient (Phase 3) is built against."""

    @abstractmethod
    def add_order(self, service_id: str, link: str, quantity: int, **kwargs) -> ProviderOrderResult: ...

    @abstractmethod
    def get_order_status(self, provider_order_id: str) -> ProviderOrderStatus: ...

    @abstractmethod
    def get_multi_status(self, provider_order_ids: list[str]) -> dict[str, ProviderOrderStatus]: ...

    @abstractmethod
    def get_balance(self) -> Decimal: ...

    @abstractmethod
    def get_services(self) -> list[ProviderServiceDTO]: ...

    @abstractmethod
    def create_refill(self, provider_order_id: str) -> str: ...

    @abstractmethod
    def cancel_order(self, provider_order_id: str) -> bool: ...
