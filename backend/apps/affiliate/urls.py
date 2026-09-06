from django.urls import path

from . import views

urlpatterns = [
    path("summary/", views.AffiliateSummaryView.as_view(), name="affiliate-summary"),
    path("referrals/", views.AffiliateReferralsListView.as_view(), name="affiliate-referrals"),
]
