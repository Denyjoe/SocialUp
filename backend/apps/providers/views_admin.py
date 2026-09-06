from django.db.models import Count
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Provider, ProviderServiceSyncLog
from .serializers_admin import AdminProviderSerializer, AdminProviderSyncLogSerializer
from .tasks import check_provider_balance, sync_provider_services


class AdminProviderListCreateView(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = AdminProviderSerializer
    pagination_class = None

    def get_queryset(self):
        return Provider.objects.annotate(services_count=Count("services")).order_by("name")


class AdminProviderDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = AdminProviderSerializer
    queryset = Provider.objects.annotate(services_count=Count("services"))

    def perform_update(self, serializer):
        # Blank api_key in a PATCH means "leave it as-is", not "clear it" —
        # an admin editing base_url shouldn't accidentally wipe the key.
        if not serializer.validated_data.get("api_key"):
            serializer.validated_data.pop("api_key", None)
        serializer.save()


class AdminProviderSyncServicesView(APIView):
    permission_classes = (permissions.IsAdminUser,)

    def post(self, request, pk):
        generics.get_object_or_404(Provider, pk=pk)
        sync_provider_services.delay(pk)
        return Response({"detail": "Service sync queued."})


class AdminProviderCheckBalanceView(APIView):
    permission_classes = (permissions.IsAdminUser,)

    def post(self, request, pk):
        generics.get_object_or_404(Provider, pk=pk)
        check_provider_balance.delay(pk)
        return Response({"detail": "Balance check queued."})


class AdminProviderSyncLogListView(generics.ListAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = AdminProviderSyncLogSerializer

    def get_queryset(self):
        qs = ProviderServiceSyncLog.objects.select_related("provider")
        if provider_id := self.request.query_params.get("provider"):
            qs = qs.filter(provider_id=provider_id)
        return qs
