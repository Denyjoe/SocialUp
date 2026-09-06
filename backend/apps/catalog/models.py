from decimal import ROUND_HALF_UP, Decimal

from django.db import models

from apps.common.models import TimeStampedModel
from apps.providers.models import Provider


class Category(TimeStampedModel):
    class Platform(models.TextChoices):
        INSTAGRAM = "instagram", "Instagram"
        TIKTOK = "tiktok", "TikTok"
        YOUTUBE = "youtube", "YouTube"
        FACEBOOK = "facebook", "Facebook"
        TWITTER = "twitter", "Twitter / X"
        TELEGRAM = "telegram", "Telegram"
        WHATSAPP = "whatsapp", "WhatsApp"
        SPOTIFY = "spotify", "Spotify"
        OTHER = "other", "Other"

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    platform = models.CharField(
        max_length=20, choices=Platform.choices, default=Platform.OTHER
    )
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name_plural = "categories"

    def __str__(self) -> str:
        return self.name

    @classmethod
    def guess_platform(cls, text: str) -> str:
        """Best-effort platform detection from a provider's free-text
        category/service name — used when syncing a provider's catalog,
        where 'category' is just a string, not one of our Platform choices."""
        lowered = text.lower()
        keyword_map = {
            cls.Platform.INSTAGRAM: ("instagram", "insta", " ig "),
            cls.Platform.TIKTOK: ("tiktok", "tik tok"),
            cls.Platform.YOUTUBE: ("youtube", "yt "),
            cls.Platform.FACEBOOK: ("facebook", "fb "),
            cls.Platform.TWITTER: ("twitter", " x "),
            cls.Platform.TELEGRAM: ("telegram",),
            cls.Platform.WHATSAPP: ("whatsapp",),
            cls.Platform.SPOTIFY: ("spotify",),
        }
        padded = f" {lowered} "
        for platform, keywords in keyword_map.items():
            if any(keyword in padded for keyword in keywords):
                return platform
        return cls.Platform.OTHER


class Service(TimeStampedModel):
    class ServiceType(models.TextChoices):
        DEFAULT = "default", "Default"
        CUSTOM_COMMENTS = "custom_comments", "Custom comments"
        DRIP_FEED = "drip_feed", "Drip-feed"

    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="services"
    )
    provider = models.ForeignKey(
        Provider, on_delete=models.PROTECT, related_name="services"
    )
    provider_service_id = models.CharField(max_length=100)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    service_type = models.CharField(
        max_length=20, choices=ServiceType.choices, default=ServiceType.DEFAULT
    )
    min_quantity = models.PositiveIntegerField(default=100)
    max_quantity = models.PositiveIntegerField(default=10000)
    cost_currency = models.CharField(max_length=10, default="USD")
    cost_rate_per_1000 = models.DecimalField(max_digits=14, decimal_places=4)
    retail_rate_per_1000 = models.DecimalField(max_digits=14, decimal_places=2)
    markup_percent = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    price_locked = models.BooleanField(
        default=False,
        help_text="If set, syncing from the provider won't overwrite retail_rate_per_1000.",
    )
    is_active = models.BooleanField(default=True)
    refill_enabled = models.BooleanField(default=False)
    cancel_enabled = models.BooleanField(default=False)
    average_time = models.CharField(max_length=50, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["category__sort_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_service_id"],
                name="unique_provider_service_id",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.category.name})"

    def calculate_charge(self, quantity: int) -> Decimal:
        raw = (self.retail_rate_per_1000 * quantity) / Decimal(1000)
        return raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class PlatformSetting(TimeStampedModel):
    """Holds the FX rate used to auto-price a Service's retail rate from its
    provider cost on sync (Phase 3), unless price_locked is set. At most one
    row is expected; enforced by convention rather than a DB constraint."""

    usd_to_local_rate = models.DecimalField(
        max_digits=10, decimal_places=4, default=Decimal("2700.0000")
    )
    default_markup_percent = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("40.00"),
        help_text="Applied when syncing a service's retail price from provider cost, unless the service itself sets markup_percent, is price_locked, or a PricingRule below matches it.",
    )

    def __str__(self) -> str:
        return f"1 USD = {self.usd_to_local_rate}"


class PricingRule(TimeStampedModel):
    """A markup applied automatically to whatever it matches, instead of an
    admin setting retail_rate_per_1000 on ~2,000 services by hand.

    Resolution order (see apps/catalog/pricing.py): a service's own
    markup_percent, if set, always wins — that per-service override predates
    this model and stays the most specific level. Otherwise, the
    highest-priority ACTIVE rule that matches the service's category,
    platform, or cost band is used. Nothing matching falls back to
    PlatformSetting.default_markup_percent.

    Applied automatically on every provider sync for the services it
    touches, and on demand via the "reprice from rules" admin action for
    everything else already in the catalog.
    """

    class Scope(models.TextChoices):
        CATEGORY = "category", "Specific category"
        PLATFORM = "platform", "Whole platform"
        COST_TIER = "cost_tier", "Cost range (USD per 1000)"

    name = models.CharField(
        max_length=100,
        help_text="Your own label, e.g. \"Cheap services need a higher %\".",
    )
    scope = models.CharField(max_length=20, choices=Scope.choices)
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, null=True, blank=True, related_name="pricing_rules"
    )
    platform = models.CharField(max_length=20, choices=Category.Platform.choices, blank=True)
    min_cost_per_1000 = models.DecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True,
        help_text="USD, inclusive. Leave blank for no lower bound.",
    )
    max_cost_per_1000 = models.DecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True,
        help_text="USD, inclusive. Leave blank for no upper bound.",
    )
    markup_percent = models.DecimalField(max_digits=6, decimal_places=2)
    min_profit_per_1000 = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        help_text=(
            "Optional floor, in your local currency. A flat % margin on a very "
            "cheap service can round to almost nothing — this guarantees at "
            "least this much profit per 1000 regardless of the % above."
        ),
    )
    priority = models.PositiveIntegerField(
        default=0, help_text="Higher runs first when a service matches more than one rule."
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-priority", "id"]

    def __str__(self) -> str:
        return self.name

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.scope == self.Scope.CATEGORY and not self.category_id:
            raise ValidationError("A category-scoped rule needs a category.")
        if self.scope == self.Scope.PLATFORM and not self.platform:
            raise ValidationError("A platform-scoped rule needs a platform.")
        if self.scope == self.Scope.COST_TIER and self.min_cost_per_1000 is None and self.max_cost_per_1000 is None:
            raise ValidationError("A cost-range rule needs at least a minimum or a maximum.")
        if (
            self.min_cost_per_1000 is not None
            and self.max_cost_per_1000 is not None
            and self.min_cost_per_1000 > self.max_cost_per_1000
        ):
            raise ValidationError("Minimum cost can't be greater than maximum cost.")

    def matches(self, *, category_id, platform: str, cost_per_1000: Decimal) -> bool:
        if not self.is_active:
            return False
        if self.scope == self.Scope.CATEGORY:
            return category_id is not None and category_id == self.category_id
        if self.scope == self.Scope.PLATFORM:
            return platform == self.platform
        if self.scope == self.Scope.COST_TIER:
            if self.min_cost_per_1000 is not None and cost_per_1000 < self.min_cost_per_1000:
                return False
            if self.max_cost_per_1000 is not None and cost_per_1000 > self.max_cost_per_1000:
                return False
            return True
        return False


class ServiceHealthStat(TimeStampedModel):
    """A cached 48-hour rollup for one service, recomputed hourly by
    apps.catalog.health.recompute_all_service_health — this is the backing
    data for the public Service Health dashboard.

    Never computed live per request: that would mean scanning recent
    orders for every service on every page load. `refill_rate_percent` is
    deliberately a *refill*-rate, not a true drop-rate — verifying an
    actual drop means re-checking the target profile itself days later,
    which this panel has no way to do. The share of delivered orders that
    needed a refill is the closest honest proxy available from data we
    actually have.
    """

    service = models.OneToOneField(
        Service, on_delete=models.CASCADE, related_name="health_stat"
    )
    # How many orders fed the numbers below. Below MIN_SAMPLE_SIZE (see
    # apps/catalog/health.py) the averages are left null rather than shown
    # misleadingly precise off one or two orders.
    sample_size = models.PositiveIntegerField(default=0)
    avg_start_minutes = models.DecimalField(
        max_digits=10, decimal_places=1, null=True, blank=True,
        help_text="Average minutes between order placed and delivery visibly starting.",
    )
    avg_speed_per_hour = models.DecimalField(
        max_digits=14, decimal_places=1, null=True, blank=True,
        help_text="Pooled units delivered per hour across recent orders.",
    )
    refill_rate_percent = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True,
        help_text="Share of delivered orders in the window that needed a refill.",
    )

    class Meta:
        verbose_name = "service health stat"
        verbose_name_plural = "service health stats"

    def __str__(self) -> str:
        return f"Health for {self.service_id}"


class ServiceProviderMapping(TimeStampedModel):
    """One provider capable of fulfilling a Service, and at what cost.

    Groundwork for Smart API Auto-Routing: today, in production, every
    service has exactly one of these (see the 0005 data migration, which
    backfilled one row per existing Service from its own provider/
    provider_service_id/cost_rate_per_1000 — so nothing changes in
    production behaviour until a second mapping actually exists).
    apps.catalog.routing.resolve_best_mapping() is what picks the winner
    at order time.

    Deciding two providers' SKUs are genuinely interchangeable is a human
    judgement call, not something this panel infers by name-matching —
    get it wrong and an order for real followers could silently ship as
    bot followers. That's what `notes` is for: record *why* this mapping
    was curated as equivalent, not just that it was.
    """

    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="provider_mappings"
    )
    provider = models.ForeignKey(
        Provider, on_delete=models.CASCADE, related_name="service_mappings"
    )
    provider_service_id = models.CharField(max_length=100)
    cost_rate_per_1000 = models.DecimalField(max_digits=14, decimal_places=4)
    priority = models.PositiveIntegerField(
        default=0,
        help_text="Tie-breaker when two mappings cost the same — higher wins.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Turn off to stop new orders routing here without deleting the mapping.",
    )
    notes = models.TextField(
        blank=True,
        help_text="Why this provider's SKU was confirmed equivalent to this service (quality, type, anything a future admin should know before trusting this mapping).",
    )

    class Meta:
        ordering = ["service_id", "cost_rate_per_1000"]
        constraints = [
            models.UniqueConstraint(
                fields=["service", "provider"], name="unique_service_provider_mapping"
            ),
            models.UniqueConstraint(
                fields=["provider", "provider_service_id"],
                name="unique_mapping_provider_service_id",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.service.name} via {self.provider.name}"
