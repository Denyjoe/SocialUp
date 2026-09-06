from rest_framework import serializers

from .models import Category, PlatformSetting, PricingRule, Service


class AdminCategorySerializer(serializers.ModelSerializer):
    services_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "platform", "sort_order", "is_active", "services_count")


class AdminServiceSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    provider_name = serializers.CharField(source="provider.name", read_only=True)
    margin_percent = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = (
            "id",
            "category",
            "category_name",
            "provider",
            "provider_name",
            "provider_service_id",
            "name",
            "description",
            "service_type",
            "min_quantity",
            "max_quantity",
            "cost_currency",
            "cost_rate_per_1000",
            "retail_rate_per_1000",
            "margin_percent",
            "markup_percent",
            "price_locked",
            "is_active",
            "refill_enabled",
            "cancel_enabled",
            "average_time",
            "last_synced_at",
        )

    def get_margin_percent(self, obj: Service):
        # Approximate margin using the platform's FX rate — informational
        # only (the true cost snapshot per order lives on Order.cost_amount).
        settings_row = PlatformSetting.objects.first()
        rate = settings_row.usd_to_local_rate if settings_row else None
        if not rate or not obj.cost_rate_per_1000:
            return None
        cost_in_local = obj.cost_rate_per_1000 * rate
        if cost_in_local == 0:
            return None
        return round(((obj.retail_rate_per_1000 - cost_in_local) / cost_in_local) * 100, 1)


class AdminPlatformSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformSetting
        fields = ("usd_to_local_rate", "default_markup_percent", "updated_at")


class AdminPricingRuleSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    # How many currently-active, non-overridden, non-locked services this
    # rule would touch right now — shown in the UI before an admin commits
    # to a change, since a badly-scoped rule could otherwise reprice
    # thousands of rows silently.
    matching_services_count = serializers.SerializerMethodField()

    class Meta:
        model = PricingRule
        fields = (
            "id",
            "name",
            "scope",
            "category",
            "category_name",
            "platform",
            "min_cost_per_1000",
            "max_cost_per_1000",
            "markup_percent",
            "min_profit_per_1000",
            "priority",
            "is_active",
            "matching_services_count",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        # Mirrors PricingRule.clean() so a bad combination surfaces as a
        # normal DRF field error here rather than an uncaught
        # ValidationError from .save() deeper down. Reads from `attrs` on a
        # partial update falls back to the existing instance's current
        # value, so a PATCH that only changes e.g. priority doesn't
        # spuriously fail this check against fields it didn't touch.
        def current(field, default=None):
            if field in attrs:
                return attrs[field]
            return getattr(self.instance, field, default)

        scope = current("scope")
        if scope == PricingRule.Scope.CATEGORY and not current("category"):
            raise serializers.ValidationError("A category-scoped rule needs a category.")
        if scope == PricingRule.Scope.PLATFORM and not current("platform"):
            raise serializers.ValidationError("A platform-scoped rule needs a platform.")

        min_cost = current("min_cost_per_1000")
        max_cost = current("max_cost_per_1000")
        if scope == PricingRule.Scope.COST_TIER and min_cost is None and max_cost is None:
            raise serializers.ValidationError(
                "A cost-range rule needs at least a minimum or a maximum."
            )
        if min_cost is not None and max_cost is not None and min_cost > max_cost:
            raise serializers.ValidationError("Minimum cost can't be greater than maximum cost.")
        return attrs

    def get_matching_services_count(self, obj: PricingRule) -> int:
        """How many services this rule would actually end up pricing right
        now — not just how many fall inside its own scope. A service inside
        this rule's scope that ALSO falls inside a higher-priority rule's
        scope is resolved to that other rule instead, exactly like
        apps.catalog.pricing.resolve_pricing_rule does at reprice time. An
        earlier version of this only checked the rule's own scope, so two
        overlapping rules (e.g. a platform rule and a more specific category
        rule) would each report every service in their own scope, even
        though only one of them would actually win each service — the exact
        number this preview exists to get right.
        """
        import copy

        from .models import Service

        if not obj.pk:
            return 0

        qs = Service.objects.filter(is_active=True, price_locked=False, markup_percent__isnull=True)
        if obj.scope == PricingRule.Scope.CATEGORY:
            qs = qs.filter(category_id=obj.category_id)
        elif obj.scope == PricingRule.Scope.PLATFORM:
            qs = qs.filter(category__platform=obj.platform)
        elif obj.scope == PricingRule.Scope.COST_TIER:
            if obj.min_cost_per_1000 is not None:
                qs = qs.filter(cost_rate_per_1000__gte=obj.min_cost_per_1000)
            if obj.max_cost_per_1000 is not None:
                qs = qs.filter(cost_rate_per_1000__lte=obj.max_cost_per_1000)

        other_rules = list(
            PricingRule.objects.filter(is_active=True).exclude(pk=obj.pk).order_by("-priority", "id")
        )
        # A shallow copy so this rule counts as active for the simulation
        # regardless of its own saved toggle — previewing "how many would
        # this reach if it were live" is exactly what you want to see
        # before switching a new or currently-off rule on. Nothing here is
        # saved back to the database.
        probe = copy.copy(obj)
        probe.is_active = True
        ranked = sorted(other_rules + [probe], key=lambda r: (-r.priority, r.pk or 0))

        count = 0
        for svc in qs.values("category_id", "category__platform", "cost_rate_per_1000"):
            for rule in ranked:
                if rule.matches(
                    category_id=svc["category_id"],
                    platform=svc["category__platform"],
                    cost_per_1000=svc["cost_rate_per_1000"],
                ):
                    if rule.pk == obj.pk:
                        count += 1
                    break
        return count
