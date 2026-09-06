from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel


class Announcement(TimeStampedModel):
    """A notice shown to signed-in customers as a dashboard banner, and
    optionally emailed out as a one-off blast."""

    class Level(models.TextChoices):
        INFO = "info", "Info"
        SUCCESS = "success", "Success"
        WARNING = "warning", "Warning"

    title = models.CharField(max_length=140)
    body = models.TextField()
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.INFO)
    is_active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    dismissible = models.BooleanField(default=True)

    # Email blast bookkeeping. Sending is a deliberate, separate action so
    # editing a banner never accidentally mails every customer.
    emailed_at = models.DateTimeField(null=True, blank=True)
    email_recipient_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title

    @property
    def is_live(self) -> bool:
        now = timezone.now()
        if not self.is_active:
            return False
        if self.starts_at and self.starts_at > now:
            return False
        if self.ends_at and self.ends_at < now:
            return False
        return True

    @classmethod
    def live(cls):
        now = timezone.now()
        return cls.objects.filter(is_active=True).filter(
            models.Q(starts_at__isnull=True) | models.Q(starts_at__lte=now)
        ).filter(models.Q(ends_at__isnull=True) | models.Q(ends_at__gte=now))
