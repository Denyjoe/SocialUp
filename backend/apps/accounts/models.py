import secrets
import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.common.models import TimeStampedModel

from .managers import UserManager


def _generate_api_key() -> str:
    return secrets.token_hex(20)


def _generate_referral_code() -> str:
    return uuid.uuid4().hex[:10]


class User(AbstractUser, TimeStampedModel):
    """Custom user: email is the login identifier, no separate username."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        BANNED = "banned", "Banned"

    username = None
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    api_key = models.CharField(max_length=64, unique=True, editable=False)
    referral_code = models.CharField(max_length=20, unique=True, editable=False)
    referred_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="referrals",
    )

    # --- Registration hardening (Phase 7) ---
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    # Google's stable per-account subject id. null (not blank-only) so many
    # unlinked users don't collide on the unique constraint — SQL NULL != NULL.
    google_sub = models.CharField(max_length=64, blank=True, null=True, unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def save(self, *args, **kwargs):
        if not self.api_key:
            self.api_key = self._unique_value(_generate_api_key, "api_key")
        if not self.referral_code:
            self.referral_code = self._unique_value(
                _generate_referral_code, "referral_code"
            )
        super().save(*args, **kwargs)

    @classmethod
    def _unique_value(cls, generator, field_name: str) -> str:
        for _ in range(10):
            value = generator()
            if not cls.objects.filter(**{field_name: value}).exists():
                return value
        raise RuntimeError(f"Could not generate a unique {field_name} after 10 tries.")

    def __str__(self) -> str:
        return self.email

    @property
    def is_active_account(self) -> bool:
        return self.status == self.Status.ACTIVE


def _generate_email_token() -> str:
    return secrets.token_urlsafe(32)


class EmailVerificationToken(TimeStampedModel):
    """At most one live token per user — regenerating (e.g. on resend)
    overwrites rather than accumulating history."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="email_verification")
    token = models.CharField(max_length=64, unique=True, default=_generate_email_token)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Email verification for {self.user_id}"


class PhoneOTP(TimeStampedModel):
    """One row per OTP attempt. No code or hash of it is ever stored here —
    Beem hosts the code and tells us valid/invalid via the verify call, so
    there's nothing sensitive on our side to leak."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="phone_otps")
    phone_number = models.CharField(max_length=20)
    provider_reference = models.CharField(max_length=100, blank=True)  # Beem's pinId
    attempts = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Phone OTP for {self.user_id} ({self.phone_number})"


class DisposableEmailDomain(TimeStampedModel):
    """Seeded from disposable_domains_seed.py via `manage.py
    seed_disposable_domains`; extend through Django admin as new ones turn up."""

    domain = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ["domain"]

    def __str__(self) -> str:
        return self.domain
