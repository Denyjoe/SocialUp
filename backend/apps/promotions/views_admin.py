from rest_framework import generics, permissions

from .models import Coupon, CouponRedemption, DepositBonusRule
from .serializers import (
    AdminCouponRedemptionSerializer,
    AdminCouponSerializer,
    AdminDepositBonusRuleSerializer,
)


class AdminCouponListCreateView(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = AdminCouponSerializer
    queryset = Coupon.objects.all()


class AdminCouponDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = AdminCouponSerializer
    queryset = Coupon.objects.all()


class AdminCouponRedemptionListView(generics.ListAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = AdminCouponRedemptionSerializer

    def get_queryset(self):
        qs = CouponRedemption.objects.select_related("coupon", "user")
        coupon_id = self.request.query_params.get("coupon")
        if coupon_id:
            qs = qs.filter(coupon_id=coupon_id)
        return qs


class AdminDepositBonusListCreateView(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = AdminDepositBonusRuleSerializer
    queryset = DepositBonusRule.objects.all()


class AdminDepositBonusDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = AdminDepositBonusRuleSerializer
    queryset = DepositBonusRule.objects.all()
