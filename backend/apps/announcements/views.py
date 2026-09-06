from rest_framework import generics, permissions

from .models import Announcement
from .serializers import AnnouncementSerializer


class AnnouncementListView(generics.ListAPIView):
    """Live announcements for the signed-in customer's dashboard banner."""

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = AnnouncementSerializer
    pagination_class = None

    def get_queryset(self):
        return Announcement.live()
