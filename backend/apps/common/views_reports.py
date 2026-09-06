"""Admin financial reporting and CSV export.

Money definitions used throughout, so the numbers mean the same thing
everywhere:
  revenue  = sum of Order.charge_amount (what customers actually paid,
             after any coupon discount)
  discount = sum of Order.discount_amount (revenue given away via coupons)
  cost     = sum of Order.cost_amount converted to TZS at the platform FX
             rate (what the upstream provider charged us)
  profit   = revenue - cost
Refunded orders are excluded from all of it: the money went back.
"""

import csv
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import PlatformSetting
from apps.orders.models import Order
from apps.wallet.models import LedgerEntry

MAX_RANGE_DAYS = 366


def _parse_range(request):
    """Returns (start, end, days). Defaults to the last 30 days."""
    try:
        days = int(request.query_params.get("days", 30))
    except (TypeError, ValueError):
        days = 30
    days = max(1, min(days, MAX_RANGE_DAYS))
    end = timezone.now()
    start = end - timedelta(days=days)
    return start, end, days


def _billable_orders(start, end):
    """Orders that represent real money kept: excludes refunded."""
    return Order.objects.filter(created_at__gte=start, created_at__lte=end).exclude(
        status=Order.Status.REFUNDED
    )


def _fx_rate() -> Decimal:
    # Singleton-by-convention, same access pattern as apps/common/views_admin.py.
    settings_row = PlatformSetting.objects.first()
    return settings_row.usd_to_local_rate if settings_row else Decimal("2700.0000")


class AdminReportSummaryView(APIView):
    """Headline figures plus a per-day series for the selected range."""

    permission_classes = (permissions.IsAdminUser,)

    def get(self, request, *args, **kwargs):
        start, end, days = _parse_range(request)
        fx = _fx_rate()
        orders = _billable_orders(start, end)

        totals = orders.aggregate(
            revenue=Sum("charge_amount"),
            discount=Sum("discount_amount"),
            cost_foreign=Sum("cost_amount"),
            order_count=Count("id"),
        )
        revenue = totals["revenue"] or Decimal("0.00")
        discount = totals["discount"] or Decimal("0.00")
        cost = (totals["cost_foreign"] or Decimal("0")) * fx
        profit = revenue - cost

        refunded = Order.objects.filter(
            created_at__gte=start, created_at__lte=end, status=Order.Status.REFUNDED
        ).aggregate(amount=Sum("charge_amount"), count=Count("id"))

        deposits = LedgerEntry.objects.filter(
            created_at__gte=start,
            created_at__lte=end,
            entry_type__in=[
                LedgerEntry.EntryType.DEPOSIT,
                LedgerEntry.EntryType.ADMIN_ADJUSTMENT_CREDIT,
            ],
        ).aggregate(amount=Sum("amount"))

        per_day = (
            orders.annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(
                revenue=Sum("charge_amount"),
                cost_foreign=Sum("cost_amount"),
                orders=Count("id"),
            )
            .order_by("day")
        )
        series = [
            {
                "date": row["day"].isoformat(),
                "revenue": str(row["revenue"] or Decimal("0.00")),
                "cost": str(((row["cost_foreign"] or Decimal("0")) * fx).quantize(Decimal("0.01"))),
                "profit": str(
                    (
                        (row["revenue"] or Decimal("0.00"))
                        - (row["cost_foreign"] or Decimal("0")) * fx
                    ).quantize(Decimal("0.01"))
                ),
                "orders": row["orders"],
            }
            for row in per_day
        ]

        return Response(
            {
                "range_days": days,
                "revenue": str(revenue.quantize(Decimal("0.01"))),
                "cost": str(cost.quantize(Decimal("0.01"))),
                "profit": str(profit.quantize(Decimal("0.01"))),
                "margin_percent": str(
                    (profit / revenue * 100).quantize(Decimal("0.01")) if revenue else Decimal("0.00")
                ),
                "discount_given": str(discount.quantize(Decimal("0.01"))),
                "order_count": totals["order_count"] or 0,
                "refunded_amount": str((refunded["amount"] or Decimal("0.00")).quantize(Decimal("0.01"))),
                "refunded_count": refunded["count"] or 0,
                "deposits_total": str((deposits["amount"] or Decimal("0.00")).quantize(Decimal("0.01"))),
                "series": series,
            }
        )


class AdminServiceMarginReportView(APIView):
    """Per-service profitability, worst margin first, so loss-making
    services are the first thing an admin sees."""

    permission_classes = (permissions.IsAdminUser,)

    def get(self, request, *args, **kwargs):
        start, end, _ = _parse_range(request)
        fx = _fx_rate()

        rows = (
            _billable_orders(start, end)
            .values("service__id", "service__name", "service__category__name")
            .annotate(
                orders=Count("id"),
                revenue=Sum("charge_amount"),
                cost_foreign=Sum("cost_amount"),
            )
            .order_by("-revenue")[:200]
        )

        results = []
        for row in rows:
            revenue = row["revenue"] or Decimal("0.00")
            cost = (row["cost_foreign"] or Decimal("0")) * fx
            profit = revenue - cost
            results.append(
                {
                    "service_id": row["service__id"],
                    "service_name": row["service__name"],
                    "category": row["service__category__name"],
                    "orders": row["orders"],
                    "revenue": str(revenue.quantize(Decimal("0.01"))),
                    "cost": str(cost.quantize(Decimal("0.01"))),
                    "profit": str(profit.quantize(Decimal("0.01"))),
                    "margin_percent": str(
                        (profit / revenue * 100).quantize(Decimal("0.01"))
                        if revenue
                        else Decimal("0.00")
                    ),
                }
            )
        results.sort(key=lambda r: Decimal(r["margin_percent"]))
        return Response({"results": results})


class AdminCategoryProfitabilityReportView(APIView):
    """Same revenue/cost/profit split as the summary view, but grouped by
    platform and category — "which platform actually makes me money" isn't
    answerable from a single overall total or a raw per-service list."""

    permission_classes = (permissions.IsAdminUser,)

    def get(self, request, *args, **kwargs):
        start, end, _ = _parse_range(request)
        fx = _fx_rate()

        rows = (
            _billable_orders(start, end)
            .values("service__category__platform", "service__category__name", "service__category_id")
            .annotate(orders=Count("id"), revenue=Sum("charge_amount"), cost_foreign=Sum("cost_amount"))
        )

        by_platform: dict[str, dict] = {}
        categories = []
        for row in rows:
            revenue = row["revenue"] or Decimal("0.00")
            cost = (row["cost_foreign"] or Decimal("0")) * fx
            profit = revenue - cost
            platform = row["service__category__platform"] or "other"

            bucket = by_platform.setdefault(
                platform, {"platform": platform, "orders": 0, "revenue": Decimal("0.00"), "cost": Decimal("0.00")}
            )
            bucket["orders"] += row["orders"]
            bucket["revenue"] += revenue
            bucket["cost"] += cost

            categories.append(
                {
                    "category_id": row["service__category_id"],
                    "category": row["service__category__name"],
                    "platform": platform,
                    "orders": row["orders"],
                    "revenue": str(revenue.quantize(Decimal("0.01"))),
                    "profit": str(profit.quantize(Decimal("0.01"))),
                    "margin_percent": str(
                        (profit / revenue * 100).quantize(Decimal("0.01")) if revenue else Decimal("0.00")
                    ),
                }
            )

        platforms = []
        for bucket in by_platform.values():
            profit = bucket["revenue"] - bucket["cost"]
            platforms.append(
                {
                    "platform": bucket["platform"],
                    "orders": bucket["orders"],
                    "revenue": str(bucket["revenue"].quantize(Decimal("0.01"))),
                    "cost": str(bucket["cost"].quantize(Decimal("0.01"))),
                    "profit": str(profit.quantize(Decimal("0.01"))),
                    "margin_percent": str(
                        (profit / bucket["revenue"] * 100).quantize(Decimal("0.01"))
                        if bucket["revenue"]
                        else Decimal("0.00")
                    ),
                }
            )
        platforms.sort(key=lambda p: Decimal(p["profit"]), reverse=True)
        categories.sort(key=lambda c: Decimal(c["profit"]), reverse=True)

        return Response({"platforms": platforms, "categories": categories[:100]})


class AdminMarginDistributionView(APIView):
    """A catalogue-wide health check, independent of any date range: of
    everything currently for sale, how much of it is actually priced well?
    Built for pairing with apps/catalog PricingRule — after adding or
    changing rules, this is where you'd look to confirm nothing ended up
    priced at a loss or a wafer-thin margin.
    """

    permission_classes = (permissions.IsAdminUser,)

    BANDS = [
        ("loss", None, 0, "Below 0% (loss-making)"),
        ("thin", 0, 15, "0–15%"),
        ("healthy", 15, 40, "15–40%"),
        ("strong", 40, 80, "40–80%"),
        ("premium", 80, None, "Over 80%"),
    ]

    def get(self, request, *args, **kwargs):
        from apps.catalog.models import Service

        fx = _fx_rate()
        services = Service.objects.filter(is_active=True).values(
            "id", "name", "cost_rate_per_1000", "retail_rate_per_1000", "category__name"
        )

        counts = {key: 0 for key, *_ in self.BANDS}
        worst = []
        for svc in services:
            cost_local = (svc["cost_rate_per_1000"] or Decimal("0")) * fx
            if cost_local == 0:
                continue
            margin = ((svc["retail_rate_per_1000"] - cost_local) / cost_local) * 100
            for key, low, high, _label in self.BANDS:
                if (low is None or margin >= low) and (high is None or margin < high):
                    counts[key] += 1
                    break
            worst.append(
                {
                    "service_id": svc["id"],
                    "service_name": svc["name"],
                    "category": svc["category__name"],
                    "margin_percent": str(margin.quantize(Decimal("0.1"))),
                }
            )

        worst.sort(key=lambda r: Decimal(r["margin_percent"]))

        return Response(
            {
                "bands": [
                    {"key": key, "label": label, "count": counts[key]}
                    for key, *_rest, label in self.BANDS
                ],
                "total_priced_services": sum(counts.values()),
                "worst": worst[:25],
            }
        )


class AdminTopCustomersReportView(APIView):
    permission_classes = (permissions.IsAdminUser,)

    def get(self, request, *args, **kwargs):
        start, end, _ = _parse_range(request)
        rows = (
            _billable_orders(start, end)
            .values("user__id", "user__email")
            .annotate(orders=Count("id"), spent=Sum("charge_amount"))
            .order_by("-spent")[:50]
        )
        return Response(
            {
                "results": [
                    {
                        "user_id": row["user__id"],
                        "email": row["user__email"],
                        "orders": row["orders"],
                        "spent": str((row["spent"] or Decimal("0.00")).quantize(Decimal("0.01"))),
                    }
                    for row in rows
                ]
            }
        )


class AdminOrdersCsvExportView(APIView):
    permission_classes = (permissions.IsAdminUser,)

    def get(self, request, *args, **kwargs):
        start, end, _ = _parse_range(request)
        fx = _fx_rate()

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="orders-{timezone.now():%Y%m%d}.csv"'
        )
        writer = csv.writer(response)
        writer.writerow(
            [
                "order_id",
                "created_at",
                "customer",
                "service",
                "quantity",
                "charged_tzs",
                "discount_tzs",
                "cost_tzs",
                "profit_tzs",
                "status",
                "provider_order_id",
            ]
        )

        qs = (
            Order.objects.filter(created_at__gte=start, created_at__lte=end)
            .select_related("user", "service")
            .order_by("created_at")
            .iterator(chunk_size=500)
        )
        for order in qs:
            cost = (order.cost_amount or Decimal("0")) * fx
            writer.writerow(
                [
                    order.id,
                    order.created_at.isoformat(),
                    order.user.email,
                    order.service.name,
                    order.quantity,
                    f"{order.charge_amount:.2f}",
                    f"{order.discount_amount:.2f}",
                    f"{cost:.2f}",
                    f"{order.charge_amount - cost:.2f}",
                    order.status,
                    order.provider_order_id,
                ]
            )
        return response


class AdminLedgerCsvExportView(APIView):
    permission_classes = (permissions.IsAdminUser,)

    def get(self, request, *args, **kwargs):
        start, end, _ = _parse_range(request)

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="ledger-{timezone.now():%Y%m%d}.csv"'
        )
        writer = csv.writer(response)
        writer.writerow(
            ["entry_id", "created_at", "customer", "type", "amount_tzs", "balance_after", "description"]
        )

        qs = (
            LedgerEntry.objects.filter(created_at__gte=start, created_at__lte=end)
            .select_related("wallet__user")
            .order_by("created_at")
            .iterator(chunk_size=500)
        )
        for entry in qs:
            writer.writerow(
                [
                    entry.id,
                    entry.created_at.isoformat(),
                    entry.wallet.user.email,
                    entry.entry_type,
                    f"{entry.amount:.2f}",
                    f"{entry.balance_after:.2f}",
                    entry.description,
                ]
            )
        return response
