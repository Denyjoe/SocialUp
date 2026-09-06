from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Service
from apps.orders.models import Order
from apps.orders.services import OrderService, OrderValidationError
from apps.wallet.services import InsufficientBalanceError

from .authentication import ApiKeyAuthentication

# Internal status -> the display string other JAP-style panels use, so
# scripts/tools already written against that convention parse ours correctly.
_STATUS_DISPLAY = {
    Order.Status.PENDING: "Pending",
    Order.Status.IN_PROGRESS: "In progress",
    Order.Status.PROCESSING: "Processing",
    Order.Status.COMPLETED: "Completed",
    Order.Status.PARTIAL: "Partial",
    Order.Status.CANCELED: "Canceled",
    Order.Status.REFUNDED: "Canceled",  # a refund is a cancellation from the caller's point of view
    Order.Status.ERROR: "Error",
}


def _order_status_payload(order: Order) -> dict:
    return {
        "charge": str(order.charge_amount),
        "start_count": order.start_count if order.start_count is not None else "",
        "status": _STATUS_DISPLAY.get(order.status, order.status),
        "remains": order.remains if order.remains is not None else "",
        "currency": order.user.wallet.currency,
    }


class PanelAPIView(APIView):
    """This panel's own outward-facing API, mounted at POST /api/v2/ — the
    same convention documented in docs/provider-api-assumptions.md for the
    upstream provider we consume. Lets a panel user's own resale
    tools/scripts automate against THIS panel exactly like they would
    against any other JAP-style reseller. Supports the core actions
    (services/add/status/balance); refill/cancel aren't wired up since the
    panel doesn't have an internal refill/cancel flow yet either — add both
    together when that's built."""

    authentication_classes = (ApiKeyAuthentication,)
    permission_classes = (IsAuthenticated,)
    # Accept whatever encoding a reseller's HTTP client happens to send —
    # different third-party tools default to different ones.
    parser_classes = (JSONParser, FormParser, MultiPartParser)

    def post(self, request):
        action = request.data.get("action")
        handler = {
            "services": self._services,
            "add": self._add,
            "status": self._status,
            "balance": self._balance,
        }.get(action)
        if handler is None:
            return Response({"error": f"Unknown or missing action: {action!r}"}, status=400)
        return handler(request)

    def _services(self, request):
        services = Service.objects.filter(is_active=True).select_related("category")
        return Response(
            [
                {
                    "service": s.id,
                    "name": s.name,
                    "type": s.service_type,
                    "category": s.category.name,
                    "rate": str(s.retail_rate_per_1000),
                    "min": s.min_quantity,
                    "max": s.max_quantity,
                }
                for s in services
            ]
        )

    def _add(self, request):
        service_id = request.data.get("service")
        link = request.data.get("link")
        quantity = request.data.get("quantity")
        if not (service_id and link and quantity):
            return Response({"error": "service, link and quantity are required."}, status=400)

        try:
            service = Service.objects.get(pk=service_id, is_active=True)
        except (Service.DoesNotExist, ValueError):
            return Response({"error": "Incorrect service ID."}, status=400)

        try:
            quantity = int(quantity)
        except ValueError:
            return Response({"error": "quantity must be an integer."}, status=400)

        try:
            order = OrderService.create_order(request.user, service, link, quantity)
        except OrderValidationError as exc:
            return Response({"error": str(exc)}, status=400)
        except InsufficientBalanceError:
            return Response({"error": "Not enough funds."}, status=400)

        return Response({"order": str(order.id)})

    def _status(self, request):
        single_id = request.data.get("order")
        multi_ids = request.data.get("orders")

        if single_id:
            order = Order.objects.filter(pk=single_id, user=request.user).select_related("user__wallet").first()
            if not order:
                return Response({"error": "Incorrect order ID."}, status=400)
            return Response(_order_status_payload(order))

        if multi_ids:
            ids = [i.strip() for i in multi_ids.split(",") if i.strip()][:100]
            orders = Order.objects.filter(pk__in=ids, user=request.user).select_related("user__wallet")
            by_id = {str(o.id): _order_status_payload(o) for o in orders}
            return Response(by_id)

        return Response({"error": "order or orders is required."}, status=400)

    def _balance(self, request):
        wallet = request.user.wallet
        return Response({"balance": str(wallet.cached_balance), "currency": wallet.currency})
