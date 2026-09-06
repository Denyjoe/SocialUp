from rest_framework import serializers

from .models import Category, Service, ServiceHealthStat


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "platform", "sort_order")


class ServiceHealthSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceHealthStat
        fields = (
            "sample_size",
            "avg_start_minutes",
            "avg_speed_per_hour",
            "refill_rate_percent",
            "updated_at",
        )


class ServiceSerializer(serializers.ModelSerializer):
    """Customer-facing: deliberately excludes provider/cost fields — those
    are internal (see apps/catalog/views_admin.py in Phase 5)."""

    category = CategorySerializer(read_only=True)
    health = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = (
            "id",
            "category",
            "name",
            "description",
            "service_type",
            "min_quantity",
            "max_quantity",
            "retail_rate_per_1000",
            "refill_enabled",
            "cancel_enabled",
            "average_time",
            "health",
        )

    def get_health(self, obj: Service) -> dict | None:
        # select_related("health_stat") makes this a no-op extra query;
        # a service with no recent orders simply has no row yet.
        stat = getattr(obj, "health_stat", None)
        if stat is None:
            return None
        return ServiceHealthSerializer(stat).data
