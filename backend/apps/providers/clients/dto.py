from dataclasses import dataclass
from decimal import Decimal


@dataclass
class ProviderOrderResult:
    provider_order_id: str
    status: str


@dataclass
class ProviderOrderStatus:
    status: str
    start_count: int | None = None
    remains: int | None = None


@dataclass
class ProviderServiceDTO:
    provider_service_id: str
    name: str
    category: str
    rate_per_1000: Decimal
    min_quantity: int
    max_quantity: int
    service_type: str = "default"
