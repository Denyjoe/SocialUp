from rest_framework import serializers

from .models import Announcement


class AnnouncementSerializer(serializers.ModelSerializer):
    """What customers see."""

    class Meta:
        model = Announcement
        fields = ("id", "title", "body", "level", "dismissible", "created_at")


class AdminAnnouncementSerializer(serializers.ModelSerializer):
    is_live = serializers.BooleanField(read_only=True)

    class Meta:
        model = Announcement
        fields = (
            "id",
            "title",
            "body",
            "level",
            "is_active",
            "starts_at",
            "ends_at",
            "dismissible",
            "is_live",
            "emailed_at",
            "email_recipient_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("emailed_at", "email_recipient_count", "created_at", "updated_at")
