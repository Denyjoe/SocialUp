from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Announcement
from .serializers import AdminAnnouncementSerializer
from .tasks import send_announcement_email


class AdminAnnouncementListCreateView(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = AdminAnnouncementSerializer
    queryset = Announcement.objects.all()


class AdminAnnouncementDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = AdminAnnouncementSerializer
    queryset = Announcement.objects.all()


class AdminAnnouncementSendEmailView(APIView):
    """Deliberately a separate explicit action: saving a banner must never
    mail every customer as a side effect."""

    permission_classes = (permissions.IsAdminUser,)

    def post(self, request, pk, *args, **kwargs):
        try:
            announcement = Announcement.objects.get(pk=pk)
        except Announcement.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if announcement.emailed_at:
            return Response(
                {"detail": "This announcement has already been emailed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        send_announcement_email.delay(announcement.id)
        return Response({"detail": "Email blast queued."})
