from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Service
from apps.wallet.services import InsufficientBalanceError

from .models import Order
from .serializers import OrderCreateSerializer, OrderSerializer
from .services import OrderService, OrderValidationError


class OrderListCreateView(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).select_related("service")

    def get_serializer_class(self):
        return OrderCreateSerializer if self.request.method == "POST" else OrderSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        # In eager/dev mode the provider task has likely already run and
        # mutated the DB row via its own fetch (a different Python object)
        # by this point; in real async mode it hasn't yet. Either way, the
        # response should reflect the current DB state, not this stale
        # in-memory instance from right after INSERT.
        order.refresh_from_db()
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderDetailView(generics.RetrieveAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


# A real wallet debit and a real provider submission per line, so this
# stays well short of the admin bulk action's 200 — generous for a
# legitimate multi-post campaign, bounded against a scripted flood.
MAX_BULK_LINES = 25


class BulkOrderLineSerializer(serializers.Serializer):
    service = serializers.PrimaryKeyRelatedField(queryset=Service.objects.filter(is_active=True))
    link = serializers.URLField(max_length=500)
    quantity = serializers.IntegerField(min_value=1)
    coupon_code = serializers.CharField(required=False, allow_blank=True)


def _flatten_errors(errors: dict) -> str:
    messages = [str(err) for field_errors in errors.values() for err in field_errors]
    return " ".join(messages) if messages else "Invalid order."


class BulkOrderCreateView(APIView):
    """POST { orders: [{service, link, quantity, coupon_code?}, ...] }

    Each line is charged and submitted independently through the exact
    same OrderService.create_order() a single New Order uses — a bad line
    (invalid service, quantity out of range, insufficient balance at that
    point in the batch) is reported against that line only and never
    blocks the rest, the same "process what you can, report what you
    can't" shape as AdminOrderBulkActionView.
    """

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        lines = request.data.get("orders")
        if not isinstance(lines, list) or not lines:
            return Response(
                {"detail": "Provide a non-empty list of orders."}, status=status.HTTP_400_BAD_REQUEST
            )
        if len(lines) > MAX_BULK_LINES:
            return Response(
                {"detail": f"Submit at most {MAX_BULK_LINES} orders at a time."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        results = []
        for raw_line in lines:
            line_serializer = BulkOrderLineSerializer(data=raw_line if isinstance(raw_line, dict) else {})
            if not line_serializer.is_valid():
                results.append({"success": False, "error": _flatten_errors(line_serializer.errors)})
                continue

            data = line_serializer.validated_data
            try:
                order = OrderService.create_order(
                    user=request.user,
                    service=data["service"],
                    link=data["link"],
                    quantity=data["quantity"],
                    coupon_code=data.get("coupon_code", ""),
                )
                order.refresh_from_db()
                results.append({"success": True, "order": OrderSerializer(order).data})
            except OrderValidationError as exc:
                results.append({"success": False, "error": str(exc)})
            except InsufficientBalanceError:
                results.append({"success": False, "error": "Insufficient wallet balance for this order."})

        return Response({"results": results}, status=status.HTTP_200_OK)
