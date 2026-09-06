from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Count, DecimalField, F, Sum
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

User = get_user_model()

ZERO = DecimalField(max_digits=14, decimal_places=2)


def _period_bounds(now):
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)
    return today_start, week_start, month_start


def _revenue_and_profit(orders_qs, fx_rate):
    """Net revenue/profit for a queryset of orders: refunded orders
    contribute nothing (their charge came back out of the till), everything
    else counts at its charge_amount, with cost converted to local currency
    via the platform's FX rate for an approximate gross-profit figure."""
    from apps.orders.models import Order

    non_refunded = orders_qs.exclude(status=Order.Status.REFUNDED)
    agg = non_refunded.aggregate(
        revenue=Coalesce(Sum("charge_amount"), 0, output_field=ZERO),
        cost_usd=Coalesce(Sum("cost_amount"), 0, output_field=ZERO),
        count=Count("id"),
    )
    revenue = agg["revenue"]
    cost_local = (agg["cost_usd"] * fx_rate).quantize(Decimal("0.01"))
    return {
        "revenue": revenue,
        "cost": cost_local,
        "profit": revenue - cost_local,
        "order_count": agg["count"],
    }


class AdminDashboardStatsView(APIView):
    permission_classes = (permissions.IsAdminUser,)

    def get(self, request):
        from apps.catalog.models import PlatformSetting
        from apps.orders.models import Order
        from apps.providers.models import Provider
        from apps.wallet.models import Wallet

        now = timezone.now()
        today_start, week_start, month_start = _period_bounds(now)
        settings_row = PlatformSetting.objects.first()
        fx_rate = settings_row.usd_to_local_rate if settings_row else 1

        orders_all = Order.objects.all()
        orders_today = orders_all.filter(created_at__gte=today_start)
        orders_week = orders_all.filter(created_at__gte=week_start)
        orders_month = orders_all.filter(created_at__gte=month_start)

        by_status = dict(
            orders_all.values("status").annotate(count=Count("id")).values_list("status", "count")
        )

        top_services = list(
            orders_month.exclude(status=Order.Status.REFUNDED)
            .values("service_id", name=F("service__name"))
            .annotate(order_count=Count("id"), revenue=Sum("charge_amount"))
            .order_by("-order_count")[:5]
        )

        return Response(
            {
                "generated_at": now,
                "users": {
                    "total": User.objects.count(),
                    "new_today": User.objects.filter(date_joined__gte=today_start).count(),
                    "new_this_week": User.objects.filter(date_joined__gte=week_start).count(),
                },
                "orders": {
                    "total": orders_all.count(),
                    "today": orders_today.count(),
                    "this_week": orders_week.count(),
                    "by_status": by_status,
                },
                "today": _revenue_and_profit(orders_today, fx_rate),
                "this_week": _revenue_and_profit(orders_week, fx_rate),
                "this_month": _revenue_and_profit(orders_month, fx_rate),
                "all_time": _revenue_and_profit(orders_all, fx_rate),
                "wallet_liability": Wallet.objects.aggregate(
                    total=Coalesce(Sum("cached_balance"), 0, output_field=ZERO)
                )["total"],
                "providers": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "is_active": p.is_active,
                        "balance_cached": p.balance_cached,
                        "balance_currency": p.balance_currency,
                        "balance_last_checked_at": p.balance_last_checked_at,
                    }
                    for p in Provider.objects.all()
                ],
                "top_services_this_month": top_services,
            }
        )


class AdminRevenueTrendView(APIView):
    permission_classes = (permissions.IsAdminUser,)

    def get(self, request):
        from apps.catalog.models import PlatformSetting
        from apps.orders.models import Order

        days = min(int(request.query_params.get("days", 14)), 90)
        settings_row = PlatformSetting.objects.first()
        fx_rate = settings_row.usd_to_local_rate if settings_row else 1
        since = timezone.now() - timedelta(days=days - 1)
        since = since.replace(hour=0, minute=0, second=0, microsecond=0)

        rows = (
            Order.objects.filter(created_at__gte=since)
            .exclude(status=Order.Status.REFUNDED)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(
                revenue=Coalesce(Sum("charge_amount"), 0, output_field=ZERO),
                cost_usd=Coalesce(Sum("cost_amount"), 0, output_field=ZERO),
                orders=Count("id"),
            )
            .order_by("day")
        )
        by_day = {row["day"]: row for row in rows}

        result = []
        for i in range(days):
            day = (since + timedelta(days=i)).date()
            row = by_day.get(day)
            if row:
                result.append(
                    {
                        "date": day,
                        "revenue": row["revenue"],
                        "profit": row["revenue"] - (row["cost_usd"] * fx_rate),
                        "orders": row["orders"],
                    }
                )
            else:
                result.append({"date": day, "revenue": 0, "profit": 0, "orders": 0})

        return Response(result)
