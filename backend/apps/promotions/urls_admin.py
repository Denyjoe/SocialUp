from django.urls import path

from . import views_admin

urlpatterns = [
    path("coupons/", views_admin.AdminCouponListCreateView.as_view(), name="admin-coupon-list"),
    path("coupons/<int:pk>/", views_admin.AdminCouponDetailView.as_view(), name="admin-coupon-detail"),
    path(
        "coupon-redemptions/",
        views_admin.AdminCouponRedemptionListView.as_view(),
        name="admin-coupon-redemptions",
    ),
    path(
        "deposit-bonuses/",
        views_admin.AdminDepositBonusListCreateView.as_view(),
        name="admin-deposit-bonus-list",
    ),
    path(
        "deposit-bonuses/<int:pk>/",
        views_admin.AdminDepositBonusDetailView.as_view(),
        name="admin-deposit-bonus-detail",
    ),
]
