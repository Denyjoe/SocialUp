from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Count, DecimalField, IntegerField, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order

from .models import AffiliateCommission, AffiliateSettings
from .serializers import AffiliateSummarySerializer, ReferredUserSerializer

User = get_user_model()


class AffiliateSummaryView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        settings_row = AffiliateSettings.objects.first() or AffiliateSettings.objects.create()
        total_referrals = User.objects.filter(referred_by=request.user).count()
        total_earned = AffiliateCommission.objects.filter(referrer=request.user).aggregate(
            total=Coalesce(Sum("amount"), Decimal("0"), output_field=DecimalField(max_digits=14, decimal_places=2))
        )["total"]

        data = {
            "referral_code": request.user.referral_code,
            "commission_percent": settings_row.commission_percent,
            "total_referrals": total_referrals,
            "total_commission_earned": total_earned,
        }
        return Response(AffiliateSummarySerializer(data).data)


class AffiliateReferralsListView(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ReferredUserSerializer

    def get_queryset(self):
        # Two separate reverse relations (orders, referral_commissions)
        # combined via Subquery rather than a single multi-annotate() call —
        # annotating both directly in one query would fan out the join and
        # inflate both counts/sums (a classic Django ORM gotcha).
        orders_count_sq = (
            Order.objects.filter(user=OuterRef("pk"))
            .values("user")
            .annotate(c=Count("id"))
            .values("c")
        )
        commission_sq = (
            AffiliateCommission.objects.filter(referred_user=OuterRef("pk"))
            .values("referred_user")
            .annotate(s=Sum("amount"))
            .values("s")
        )
        return (
            User.objects.filter(referred_by=self.request.user)
            .annotate(
                orders_count=Coalesce(Subquery(orders_count_sq, output_field=IntegerField()), 0),
                commission_earned=Coalesce(
                    Subquery(commission_sq, output_field=DecimalField(max_digits=14, decimal_places=2)),
                    Decimal("0"),
                ),
            )
            .order_by("-date_joined")
        )
