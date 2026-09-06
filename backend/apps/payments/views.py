import logging

from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Transaction
from .serializers import CreateDepositSerializer, TransactionSerializer
from .services import PaymentService, PaymentValidationError

logger = logging.getLogger(__name__)


class DepositListCreateView(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        return CreateDepositSerializer if self.request.method == "POST" else TransactionSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            txn = PaymentService.create_deposit(
                user=request.user,
                amount_local=serializer.validated_data["amount"],
                gateway_name=serializer.validated_data.get("gateway") or Transaction.Gateway.NOWPAYMENTS,
            )
        except PaymentValidationError as exc:
            raise serializers.ValidationError({"amount": str(exc)}) from exc
        return Response(TransactionSerializer(txn).data, status=status.HTTP_201_CREATED)


class DepositDetailView(generics.RetrieveAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = TransactionSerializer
    lookup_field = "internal_reference"
    lookup_url_kwarg = "reference"

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)


class NOWPaymentsWebhookView(APIView):
    """Public by design — verified by HMAC signature (see
    apps.payments.gateways.nowpayments), not by auth. NOWPayments cannot
    reach a plain localhost during development; see
    docs/nowpayments-crypto-setup.md for how to test this for real."""

    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    def post(self, request, *args, **kwargs):
        signature = request.headers.get("x-nowpayments-sig", "")
        try:
            PaymentService.handle_webhook(
                gateway_name="nowpayments", raw_body=request.body, signature=signature
            )
        except PaymentValidationError as exc:
            logger.warning("NOWPayments webhook rejected: %s", exc)
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Transaction.DoesNotExist:
            # Acknowledge anyway — NOWPayments retries on a non-2xx, and an
            # unknown reference will never resolve itself by retrying.
            logger.warning("NOWPayments webhook for an unknown deposit reference")
            return Response({"status": "ignored"})
        return Response({"status": "ok"})
