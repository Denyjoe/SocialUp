from rest_framework import generics, permissions

from .models import Wallet
from .serializers import LedgerEntrySerializer, WalletSerializer


class WalletView(generics.RetrieveAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = WalletSerializer

    def get_object(self) -> Wallet:
        wallet, _ = Wallet.objects.get_or_create(user=self.request.user)
        return wallet


class LedgerListView(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = LedgerEntrySerializer

    def get_queryset(self):
        wallet, _ = Wallet.objects.get_or_create(user=self.request.user)
        return wallet.ledger_entries.all()
