from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Order
from .serializers_admin import (
    AdminOrderDetailSerializer,
    AdminOrderRefundSerializer,
    AdminOrderSerializer,
)
from .services import OrderService
from .tasks import submit_order_to_provider


class AdminOrderListView(generics.ListAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = AdminOrderSerializer

    def get_queryset(self):
        qs = Order.objects.select_related("user", "service", "provider")
        params = self.request.query_params
        if status_filter := params.get("status"):
            qs = qs.filter(status=status_filter)
        if user_search := params.get("user"):
            qs = qs.filter(user__email__icontains=user_search)
        if service_id := params.get("service"):
            qs = qs.filter(service_id=service_id)
        if date_from := params.get("date_from"):
            qs = qs.filter(created_at__gte=date_from)
        if date_to := params.get("date_to"):
            qs = qs.filter(created_at__lte=date_to)
        return qs.order_by("-created_at")


class AdminOrderDetailView(generics.RetrieveAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = AdminOrderDetailSerializer
    queryset = Order.objects.select_related("user", "service", "provider").prefetch_related(
        "status_history"
    )


class AdminOrderRefundView(APIView):
    permission_classes = (permissions.IsAdminUser,)

    def post(self, request, pk):
        order = generics.get_object_or_404(Order, pk=pk)
        serializer = AdminOrderRefundSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if order.refund_ledger_entry_id:
            return Response({"detail": "This order was already refunded."}, status=status.HTTP_400_BAD_REQUEST)

        reason = serializer.validated_data.get("reason") or f"Manual refund by {request.user.email}"
        OrderService.refund_order(order, reason=reason)
        order.refresh_from_db()
        return Response(AdminOrderSerializer(order).data)


class AdminOrderRetrySubmitView(APIView):
    permission_classes = (permissions.IsAdminUser,)

    def post(self, request, pk):
        order = generics.get_object_or_404(Order, pk=pk)
        if order.provider_order_id:
            return Response(
                {"detail": "This order already has a provider order id, so there is nothing to retry."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        submit_order_to_provider.delay(str(order.id))
        order.refresh_from_db()
        return Response(AdminOrderSerializer(order).data)


MAX_BULK_ORDERS = 200


class AdminOrderBulkActionView(APIView):
    """POST { order_ids: [...], action: "refund" | "retry", reason? }

    Each order is handled independently and already-refunded or
    already-submitted ones are reported as skipped rather than failing the
    whole batch, so one bad row cannot block the rest.
    """

    permission_classes = (permissions.IsAdminUser,)

    def post(self, request, *args, **kwargs):
        action = request.data.get("action")
        order_ids = request.data.get("order_ids") or []

        if action not in {"refund", "retry"}:
            return Response({"detail": "Unknown action."}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(order_ids, list) or not order_ids:
            return Response({"detail": "Select at least one order."}, status=status.HTTP_400_BAD_REQUEST)
        if len(order_ids) > MAX_BULK_ORDERS:
            return Response(
                {"detail": f"Select at most {MAX_BULK_ORDERS} orders at a time."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        orders = Order.objects.filter(pk__in=order_ids)
        processed, skipped = 0, []

        for order in orders:
            if action == "refund":
                if order.refund_ledger_entry_id:
                    skipped.append({"order": str(order.id), "reason": "already refunded"})
                    continue
                reason = request.data.get("reason") or f"Bulk refund by {request.user.email}"
                OrderService.refund_order(order, reason=reason)
                processed += 1
            else:
                if order.provider_order_id:
                    skipped.append({"order": str(order.id), "reason": "already submitted"})
                    continue
                submit_order_to_provider.delay(str(order.id))
                processed += 1

        return Response(
            {
                "detail": f"{action.title()} applied to {processed} of {len(order_ids)} orders.",
                "processed": processed,
                "skipped": skipped,
            }
        )
