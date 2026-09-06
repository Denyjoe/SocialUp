import uuid
from decimal import Decimal

from django.db.models import Count
from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.wallet.models import LedgerEntry
from apps.wallet.services import InsufficientBalanceError, WalletService

from .models import User


class AdminUserSerializer(serializers.ModelSerializer):
    wallet_balance = serializers.DecimalField(
        source="wallet.cached_balance", max_digits=14, decimal_places=2, read_only=True
    )
    wallet_currency = serializers.CharField(source="wallet.currency", read_only=True)
    orders_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "phone_number",
            "status",
            "is_staff",
            "referral_code",
            "date_joined",
            "wallet_balance",
            "wallet_currency",
            "orders_count",
        )


class AdminUserListView(generics.ListAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = AdminUserSerializer

    def get_queryset(self):
        qs = User.objects.select_related("wallet").annotate(orders_count=Count("orders"))
        search = self.request.query_params.get("search")
        status_filter = self.request.query_params.get("status")
        if search:
            qs = qs.filter(email__icontains=search)
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs.order_by("-date_joined")


class AdminUserDetailView(generics.RetrieveAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = AdminUserSerializer
    queryset = User.objects.select_related("wallet").annotate(orders_count=Count("orders"))


class AdminUserAdjustBalanceSerializer(serializers.Serializer):
    direction = serializers.ChoiceField(choices=("credit", "debit"))
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)


class AdminUserAdjustBalanceView(APIView):
    permission_classes = (permissions.IsAdminUser,)

    def post(self, request, pk):
        user = generics.get_object_or_404(User.objects.select_related("wallet"), pk=pk)
        serializer = AdminUserAdjustBalanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        entry_type = (
            LedgerEntry.EntryType.ADMIN_ADJUSTMENT_CREDIT
            if data["direction"] == "credit"
            else LedgerEntry.EntryType.ADMIN_ADJUSTMENT_DEBIT
        )
        op = WalletService.credit if data["direction"] == "credit" else WalletService.debit
        try:
            entry = op(
                wallet=user.wallet,
                amount=data["amount"],
                entry_type=entry_type,
                idempotency_key=f"admin-api-{uuid.uuid4()}",
                description=data.get("reason", "") or f"Manual {data['direction']} by {request.user.email}",
                created_by=request.user,
            )
        except InsufficientBalanceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "balance": entry.balance_after,
                "entry_id": entry.id,
            }
        )


class AdminUserStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=User.Status.choices)


class AdminUserStatusView(APIView):
    permission_classes = (permissions.IsAdminUser,)

    def post(self, request, pk):
        user = generics.get_object_or_404(User, pk=pk)
        serializer = AdminUserStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.status = serializer.validated_data["status"]
        user.save(update_fields=["status"])
        return Response(AdminUserSerializer(user).data)
