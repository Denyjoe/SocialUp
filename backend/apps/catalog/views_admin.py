from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Count
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Category, PlatformSetting, PricingRule, Service
from .pricing import compute_retail_price
from .serializers_admin import (
    AdminCategorySerializer,
    AdminPlatformSettingSerializer,
    AdminPricingRuleSerializer,
    AdminServiceSerializer,
)


class AdminCategoryListCreateView(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = AdminCategorySerializer
    pagination_class = None

    def get_queryset(self):
        return Category.objects.annotate(services_count=Count("services")).order_by(
            "sort_order", "name"
        )


class AdminCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = AdminCategorySerializer
    queryset = Category.objects.annotate(services_count=Count("services"))


class AdminServiceListCreateView(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = AdminServiceSerializer

    def get_queryset(self):
        qs = Service.objects.select_related("category", "provider")
        params = self.request.query_params
        if search := params.get("search"):
            qs = qs.filter(name__icontains=search)
        if category := params.get("category"):
            qs = qs.filter(category_id=category)
        if provider := params.get("provider"):
            qs = qs.filter(provider_id=provider)
        if (is_active := params.get("is_active")) is not None:
            qs = qs.filter(is_active=is_active.lower() in ("1", "true", "yes"))
        return qs.order_by("category__sort_order", "name")


class AdminServiceDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = AdminServiceSerializer
    queryset = Service.objects.select_related("category", "provider")


class AdminPlatformSettingView(generics.RetrieveUpdateAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = AdminPlatformSettingSerializer

    def get_object(self):
        # Singleton-by-convention (see PlatformSetting docstring) — always
        # operate on the first row, creating it with defaults if none exists.
        return PlatformSetting.objects.first() or PlatformSetting.objects.create()


class AdminPricingRuleListCreateView(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = AdminPricingRuleSerializer
    pagination_class = None
    queryset = PricingRule.objects.select_related("category").all()


class AdminPricingRuleDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = AdminPricingRuleSerializer
    queryset = PricingRule.objects.select_related("category").all()


class AdminServiceRepriceFromRulesView(APIView):
    """Re-evaluates PricingRule matches against whatever is already in the
    catalog — the counterpart to sync applying rules automatically for
    services it touches. Only services with no per-service markup_percent
    override, not price_locked, and currently active are touched, exactly
    matching AdminPricingRuleSerializer's own "how many would this affect"
    preview count, so what an admin sees before clicking is what changes.
    """

    permission_classes = (permissions.IsAdminUser,)

    def post(self, request, *args, **kwargs):
        settings_row = PlatformSetting.objects.first() or PlatformSetting.objects.create()
        qs = Service.objects.filter(
            is_active=True, price_locked=False, markup_percent__isnull=True
        ).select_related("category")

        updated = 0
        with transaction.atomic():
            for service in qs.select_for_update():
                new_price = compute_retail_price(
                    cost_rate_per_1000=service.cost_rate_per_1000,
                    usd_to_local_rate=settings_row.usd_to_local_rate,
                    default_markup_percent=settings_row.default_markup_percent,
                    category=service.category,
                    platform=service.category.platform,
                )
                if new_price != service.retail_rate_per_1000:
                    service.retail_rate_per_1000 = new_price
                    service.save(update_fields=["retail_rate_per_1000", "updated_at"])
                    updated += 1

        return Response({"detail": f"Repriced {updated} services.", "updated": updated})


class AdminServiceBulkUpdateView(APIView):
    """Repricing 1,950 services one at a time is not workable, so this
    applies one change across a whole filtered set at once.

    POST { category?, provider?, action, value? }
      action "set_markup"     -> set markup_percent and reprice from cost
      action "adjust_price"   -> multiply retail price by (1 + value/100)
      action "activate" / "deactivate"
    Services with price_locked are skipped by the pricing actions, which is
    the entire point of that flag.
    """

    permission_classes = (permissions.IsAdminUser,)

    def post(self, request, *args, **kwargs):
        action = request.data.get("action")
        if action not in {"set_markup", "adjust_price", "activate", "deactivate"}:
            return Response({"detail": "Unknown action."}, status=status.HTTP_400_BAD_REQUEST)

        qs = Service.objects.all()
        if category := request.data.get("category"):
            qs = qs.filter(category_id=category)
        if provider := request.data.get("provider"):
            qs = qs.filter(provider_id=provider)

        if action == "activate":
            updated = qs.update(is_active=True)
            return Response({"detail": f"Activated {updated} services.", "updated": updated})
        if action == "deactivate":
            updated = qs.update(is_active=False)
            return Response({"detail": f"Deactivated {updated} services.", "updated": updated})

        try:
            value = Decimal(str(request.data.get("value")))
        except (TypeError, ValueError, InvalidOperation):
            return Response(
                {"detail": "A numeric 'value' is required for this action."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = qs.filter(price_locked=False)
        fx = PlatformSetting.objects.first()
        rate = fx.usd_to_local_rate if fx else Decimal("2700.0000")

        updated = 0
        with transaction.atomic():
            for service in qs.select_for_update():
                if action == "set_markup":
                    if value < 0:
                        return Response(
                            {"detail": "Markup cannot be negative."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    service.markup_percent = value
                    cost_local = service.cost_rate_per_1000 * rate
                    service.retail_rate_per_1000 = (
                        cost_local * (Decimal(1) + value / Decimal(100))
                    ).quantize(Decimal("0.01"))
                else:  # adjust_price
                    factor = Decimal(1) + value / Decimal(100)
                    if factor <= 0:
                        return Response(
                            {"detail": "That adjustment would make prices zero or negative."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    service.retail_rate_per_1000 = (
                        service.retail_rate_per_1000 * factor
                    ).quantize(Decimal("0.01"))
                service.save(update_fields=["markup_percent", "retail_rate_per_1000", "updated_at"])
                updated += 1

        return Response({"detail": f"Updated {updated} services.", "updated": updated})
