from rest_framework import generics, permissions

from .models import LedgerEntry
from .serializers_admin import AdminLedgerEntrySerializer


class AdminLedgerListView(generics.ListAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = AdminLedgerEntrySerializer

    def get_queryset(self):
        qs = LedgerEntry.objects.select_related("wallet__user", "created_by")
        params = self.request.query_params
        if user_search := params.get("user"):
            qs = qs.filter(wallet__user__email__icontains=user_search)
        if entry_type := params.get("entry_type"):
            qs = qs.filter(entry_type=entry_type)
        return qs
