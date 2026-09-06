"""Smart API Auto-Routing — groundwork.

resolve_best_mapping() is the single choke point that decides which
provider fulfils a new order for a given service. Today, in production,
every service has exactly one active ServiceProviderMapping (see the data
migration that created one per existing Service), so this always resolves
to that one mapping and nothing about order submission actually changes.
The moment a second, genuinely-equivalent mapping is curated for a
service (see ServiceProviderMapping.notes on why that's a human decision,
not an automatic one), this starts actually choosing between them.

Deliberately NOT filtering by provider balance here: Provider.balance_cached
is a periodic snapshot (see apps.providers.tasks.check_provider_balance_all,
hourly), not a live number. Pre-filtering on it risks ruling out the only
real, funded provider a service has off a stale read and breaking order
creation outright. A provider that's actually out of funds fails at
submission instead, which apps.orders.tasks.submit_order_to_provider
already handles — refunding the customer automatically. That's a proven,
tested path; a second, redundant balance gate here would just be a new
way to get it wrong. Worth revisiting once there's a real second provider
to weigh that trade-off against.
"""

from .models import Service, ServiceProviderMapping


def resolve_best_mapping(service: Service) -> ServiceProviderMapping | None:
    """The cheapest active mapping on an active provider wins; a tie in
    cost is broken by priority (higher first). Returns None only when a
    service has no usable mapping at all — a data problem (e.g. every
    mapping got deactivated), not a normal runtime state."""
    candidates = list(
        service.provider_mappings.filter(is_active=True, provider__is_active=True).select_related(
            "provider"
        )
    )
    if not candidates:
        return None
    return min(candidates, key=lambda mapping: (mapping.cost_rate_per_1000, -mapping.priority))
