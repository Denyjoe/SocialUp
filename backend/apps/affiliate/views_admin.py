from rest_framework import generics, permissions

from .models import AffiliateSettings
from .serializers_admin import AdminAffiliateSettingsSerializer


class AdminAffiliateSettingsView(generics.RetrieveUpdateAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = AdminAffiliateSettingsSerializer

    def get_object(self):
        return AffiliateSettings.objects.first() or AffiliateSettings.objects.create()
