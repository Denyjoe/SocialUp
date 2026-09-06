from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

EMAIL_TOKEN_LIFETIME = timedelta(hours=48)


@shared_task
def send_verification_email(user_id):
    from django.contrib.auth import get_user_model

    from .models import EmailVerificationToken

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return
    if user.email_verified:
        return

    token_row, _ = EmailVerificationToken.objects.update_or_create(
        user=user,
        defaults={"expires_at": timezone.now() + EMAIL_TOKEN_LIFETIME, "verified_at": None},
    )
    # update_or_create's defaults don't regenerate the token field (it only
    # has a default at creation time) — force a fresh one on every send,
    # including resends, so an old emailed link stops working once a new one
    # is issued.
    from .models import _generate_email_token

    token_row.token = _generate_email_token()
    token_row.save(update_fields=["token"])

    verify_url = f"{settings.FRONTEND_BASE_URL}/verify-email?token={token_row.token}"
    send_mail(
        subject="Verify your email address",
        message=(
            f"Hi,\n\nConfirm your email address by opening this link:\n{verify_url}\n\n"
            f"This link expires in 48 hours. If you did not create this account, ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


@shared_task
def send_password_reset_email(user_id):
    """Uses Django's built-in signed token generator rather than a token
    table: it needs no storage, expires via PASSWORD_RESET_TIMEOUT, and
    self-invalidates the moment the password actually changes (the token is
    derived from the current password hash)."""
    from django.contrib.auth import get_user_model
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.encoding import force_bytes
    from django.utils.http import urlsafe_base64_encode

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_url = f"{settings.FRONTEND_BASE_URL}/reset-password?uid={uid}&token={token}"

    send_mail(
        subject="Reset your password",
        message=(
            f"Hi,\n\nReset your password by opening this link:\n{reset_url}\n\n"
            f"If you did not request this, ignore this email. Your password stays unchanged."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
