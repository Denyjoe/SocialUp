from django.contrib.auth import get_user_model
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

User = get_user_model()


class PublicStatsView(APIView):
    """Feeds the marketing homepage's live stats counters. Deliberately
    public and minimal — no per-user or financial data, just headline counts."""

    permission_classes = (AllowAny,)

    def get(self, request):
        from apps.catalog.models import Service
        from apps.orders.models import Order

        return Response(
            {
                "users": User.objects.count(),
                "services": Service.objects.filter(is_active=True).count(),
                "orders_completed": Order.objects.filter(status=Order.Status.COMPLETED).count(),
            }
        )


class ExchangeRatesView(APIView):
    """Live FX rates for showing prices in a customer's own currency.

    Display only. Every wallet, order and ledger entry stays in the base
    currency, which is why the response says so explicitly rather than
    leaving the client to assume.
    """

    permission_classes = (AllowAny,)

    def get(self, request):
        from .exchange import BASE_CURRENCY, SUPPORTED_CURRENCIES
        from .models import ExchangeRateSnapshot

        snapshot = ExchangeRateSnapshot.latest()
        if snapshot is None:
            # No snapshot yet: report the base currency only, so the client
            # shows real prices instead of guessing at a rate.
            return Response(
                {
                    "base": BASE_CURRENCY,
                    "rates": {BASE_CURRENCY: "1"},
                    "supported": [BASE_CURRENCY],
                    "fetched_at": None,
                    "stale": True,
                }
            )

        return Response(
            {
                "base": snapshot.base_currency,
                "rates": snapshot.rates,
                "supported": [c for c in SUPPORTED_CURRENCIES if c in snapshot.rates],
                "fetched_at": snapshot.fetched_at.isoformat(),
                "source": snapshot.source,
                "stale": False,
            }
        )
