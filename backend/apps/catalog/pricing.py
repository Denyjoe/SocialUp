"""Single source of truth for turning a provider's cost into a retail price.

Used by apps.providers.tasks.sync_provider_services (every service touched
by a catalog sync) and by AdminServiceRepriceView (an on-demand sweep over
whatever's already in the catalog). Keeping this in one place means a rule
change behaves identically whether it takes effect on the next sync or the
next manual reprice.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from .models import Category, PricingRule


def resolve_pricing_rule(
    *, category_id: Optional[int], platform: str, cost_per_1000: Decimal
) -> Optional[PricingRule]:
    """Highest-priority ACTIVE rule that matches, or None if nothing does."""
    for rule in PricingRule.objects.filter(is_active=True).order_by("-priority", "id"):
        if rule.matches(category_id=category_id, platform=platform, cost_per_1000=cost_per_1000):
            return rule
    return None


def compute_retail_price(
    *,
    cost_rate_per_1000: Decimal,
    usd_to_local_rate: Decimal,
    default_markup_percent: Decimal,
    category: Optional[Category] = None,
    platform: str = "",
) -> Decimal:
    """cost_rate_per_1000 is always USD (Service.cost_currency is fixed at
    "USD" today); usd_to_local_rate converts it into the panel's own
    currency before the markup is applied.

    Precedence: a matching PricingRule beats the platform-wide default.
    A per-service markup_percent override, which predates this module, is
    NOT considered here — callers check that first and only reach this
    function once they've confirmed there isn't one (see
    apps/providers/tasks.py and AdminServiceRepriceView).
    """
    rule = resolve_pricing_rule(
        category_id=category.id if category else None,
        platform=platform,
        cost_per_1000=cost_rate_per_1000,
    )
    markup_percent = rule.markup_percent if rule else default_markup_percent

    cost_local = cost_rate_per_1000 * usd_to_local_rate
    price = (cost_local * (Decimal("1") + markup_percent / Decimal("100"))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    if rule and rule.min_profit_per_1000 is not None:
        floor = (cost_local + rule.min_profit_per_1000).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if price < floor:
            price = floor

    return price
