from celery import shared_task
from django.conf import settings
from django.core.mail import get_connection, EmailMessage
from django.utils import timezone

EMAIL_BATCH_SIZE = 50


@shared_task
def send_announcement_email(announcement_id):
    """Emails an announcement to every active customer. Sent in batches over
    one SMTP connection, with each recipient BCC'd so addresses are never
    exposed to other customers."""
    from django.contrib.auth import get_user_model

    from .models import Announcement

    User = get_user_model()
    try:
        announcement = Announcement.objects.get(pk=announcement_id)
    except Announcement.DoesNotExist:
        return

    recipients = list(
        User.objects.filter(status=User.Status.ACTIVE)
        .exclude(email="")
        .values_list("email", flat=True)
    )
    if not recipients:
        return

    connection = get_connection()
    connection.open()
    try:
        for start in range(0, len(recipients), EMAIL_BATCH_SIZE):
            batch = recipients[start : start + EMAIL_BATCH_SIZE]
            EmailMessage(
                subject=announcement.title,
                body=announcement.body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[settings.DEFAULT_FROM_EMAIL],
                bcc=batch,
                connection=connection,
            ).send(fail_silently=False)
    finally:
        connection.close()

    announcement.emailed_at = timezone.now()
    announcement.email_recipient_count = len(recipients)
    announcement.save(update_fields=["emailed_at", "email_recipient_count", "updated_at"])
