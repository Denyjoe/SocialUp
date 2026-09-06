from datetime import timedelta
from decimal import Decimal

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.google_oauth import GoogleTokenError, GoogleUserInfo
from apps.accounts.models import DisposableEmailDomain, EmailVerificationToken, PhoneOTP, User
from apps.catalog.models import Category, Service
from apps.orders.services import OrderService, OrderValidationError
from apps.providers.models import Provider
from apps.wallet.models import LedgerEntry
from apps.wallet.services import WalletService

# transaction=True: registration defers the verification email via
# transaction.on_commit(), which never fires under the default django_db
# transaction-rollback wrapper — see apps/orders/tests/test_orders.py for
# the same gotcha.
pytestmark = pytest.mark.django_db(transaction=True)

BEEM_REQUEST_URL = "https://apiotp.beem.africa/v1/request"
BEEM_VERIFY_URL = "https://apiotp.beem.africa/v1/verify"


@pytest.fixture
def api_client():
    return APIClient()


# --- Disposable email blocking ---


def test_registration_rejects_disposable_email(api_client):
    DisposableEmailDomain.objects.create(domain="mailinator.com")
    resp = api_client.post(
        reverse("auth-register"),
        {"email": "bot@mailinator.com", "password": "S3cure-Pass!"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert not User.objects.filter(email="bot@mailinator.com").exists()


def test_registration_accepts_normal_email_and_sends_verification(api_client):
    resp = api_client.post(
        reverse("auth-register"),
        {"email": "real@example.com", "password": "S3cure-Pass!"},
    )
    assert resp.status_code == status.HTTP_201_CREATED, resp.data
    user = User.objects.get(email="real@example.com")
    assert user.email_verified is False

    assert len(mail.outbox) == 1
    assert "verify" in mail.outbox[0].body.lower()
    token = EmailVerificationToken.objects.get(user=user)
    assert token.token in mail.outbox[0].body


# --- Email verification ---


def test_verify_email_with_valid_token(api_client):
    user = User.objects.create_user(email="user@example.com", password="x")
    token = EmailVerificationToken.objects.create(
        user=user, expires_at=timezone.now() + timedelta(hours=1)
    )
    resp = api_client.post(reverse("auth-verify-email"), {"token": token.token})
    assert resp.status_code == status.HTTP_200_OK
    user.refresh_from_db()
    assert user.email_verified is True


def test_verify_email_with_expired_token(api_client):
    user = User.objects.create_user(email="user@example.com", password="x")
    token = EmailVerificationToken.objects.create(
        user=user, expires_at=timezone.now() - timedelta(hours=1)
    )
    resp = api_client.post(reverse("auth-verify-email"), {"token": token.token})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    user.refresh_from_db()
    assert user.email_verified is False


def test_verify_email_with_bogus_token(api_client):
    resp = api_client.post(reverse("auth-verify-email"), {"token": "not-a-real-token"})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_resend_verification_email_is_rate_limited(api_client):
    user = User.objects.create_user(email="user@example.com", password="x")
    api_client.force_authenticate(user=user)
    first = api_client.post(reverse("auth-resend-verification-email"))
    assert first.status_code == status.HTTP_200_OK
    second = api_client.post(reverse("auth-resend-verification-email"))
    assert second.status_code == status.HTTP_429_TOO_MANY_REQUESTS


def test_resend_verification_email_rejects_already_verified(api_client):
    user = User.objects.create_user(email="user@example.com", password="x", email_verified=True)
    api_client.force_authenticate(user=user)
    resp = api_client.post(reverse("auth-resend-verification-email"))
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


# --- Google Sign-In ---


def test_google_auth_creates_new_user(api_client, monkeypatch):
    monkeypatch.setattr(
        "apps.accounts.views.verify_google_id_token",
        lambda token: GoogleUserInfo(sub="google-123", email="newperson@gmail.com", email_verified=True),
    )
    resp = api_client.post(reverse("auth-google"), {"id_token": "fake-token"})
    assert resp.status_code == status.HTTP_200_OK, resp.data
    user = User.objects.get(email="newperson@gmail.com")
    assert user.google_sub == "google-123"
    assert user.email_verified is True
    assert user.has_usable_password() is False
    assert "access" in resp.data and "refresh" in resp.data


def test_google_auth_links_existing_email_account(api_client, monkeypatch):
    existing = User.objects.create_user(email="existing@example.com", password="x")
    assert existing.email_verified is False

    monkeypatch.setattr(
        "apps.accounts.views.verify_google_id_token",
        lambda token: GoogleUserInfo(sub="google-456", email="existing@example.com", email_verified=True),
    )
    resp = api_client.post(reverse("auth-google"), {"id_token": "fake-token"})
    assert resp.status_code == status.HTTP_200_OK
    existing.refresh_from_db()
    assert existing.google_sub == "google-456"
    assert existing.email_verified is True  # Google's own verification is trusted


def test_google_auth_logs_in_returning_google_user(api_client, monkeypatch):
    User.objects.create_user(email="returning@example.com", password="x", google_sub="google-789")
    monkeypatch.setattr(
        "apps.accounts.views.verify_google_id_token",
        lambda token: GoogleUserInfo(sub="google-789", email="returning@example.com", email_verified=True),
    )
    resp = api_client.post(reverse("auth-google"), {"id_token": "fake-token"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["user"]["email"] == "returning@example.com"
    assert User.objects.filter(email="returning@example.com").count() == 1  # no duplicate created


def test_google_auth_rejects_invalid_token(api_client, monkeypatch):
    def _raise(token):
        raise GoogleTokenError("bad token")

    monkeypatch.setattr("apps.accounts.views.verify_google_id_token", _raise)
    resp = api_client.post(reverse("auth-google"), {"id_token": "garbage"})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_google_auth_rejects_banned_account(api_client, monkeypatch):
    User.objects.create_user(
        email="banned@example.com", password="x", google_sub="google-999", status=User.Status.BANNED
    )
    monkeypatch.setattr(
        "apps.accounts.views.verify_google_id_token",
        lambda token: GoogleUserInfo(sub="google-999", email="banned@example.com", email_verified=True),
    )
    resp = api_client.post(reverse("auth-google"), {"id_token": "fake-token"})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


# --- Phone OTP (Beem) ---


def test_send_otp_success(api_client, requests_mock):
    user = User.objects.create_user(email="user@example.com", password="x")
    api_client.force_authenticate(user=user)
    requests_mock.post(
        BEEM_REQUEST_URL,
        json={"data": {"pinId": "pin-abc", "message": {"code": 100, "message": "sent"}}},
    )
    resp = api_client.post(reverse("auth-phone-send-otp"), {"phone_number": "+255700000000"})
    assert resp.status_code == status.HTTP_200_OK, resp.data
    user.refresh_from_db()
    assert user.phone_number == "+255700000000"
    otp = PhoneOTP.objects.get(user=user)
    assert otp.provider_reference == "pin-abc"


def test_send_otp_is_rate_limited(api_client, requests_mock):
    user = User.objects.create_user(email="user@example.com", password="x", phone_number="+255700000000")
    api_client.force_authenticate(user=user)
    requests_mock.post(
        BEEM_REQUEST_URL,
        json={"data": {"pinId": "pin-abc", "message": {"code": 100, "message": "sent"}}},
    )
    first = api_client.post(reverse("auth-phone-send-otp"))
    assert first.status_code == status.HTTP_200_OK
    second = api_client.post(reverse("auth-phone-send-otp"))
    assert second.status_code == status.HTTP_429_TOO_MANY_REQUESTS


def test_send_otp_requires_a_phone_number(api_client):
    user = User.objects.create_user(email="user@example.com", password="x")
    api_client.force_authenticate(user=user)
    resp = api_client.post(reverse("auth-phone-send-otp"))
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_send_otp_surfaces_beem_error(api_client, requests_mock):
    user = User.objects.create_user(email="user@example.com", password="x", phone_number="+255700000000")
    api_client.force_authenticate(user=user)
    requests_mock.post(
        BEEM_REQUEST_URL,
        json={"data": {"message": {"code": 111, "message": "Invalid msisdn"}}},
    )
    resp = api_client.post(reverse("auth-phone-send-otp"))
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_verify_otp_success(api_client, requests_mock):
    user = User.objects.create_user(email="user@example.com", password="x")
    PhoneOTP.objects.create(
        user=user,
        phone_number="+255700000000",
        provider_reference="pin-abc",
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    api_client.force_authenticate(user=user)
    requests_mock.post(BEEM_VERIFY_URL, json={"data": {"message": {"code": 117, "message": "valid"}}})
    resp = api_client.post(reverse("auth-phone-verify-otp"), {"code": "123456"})
    assert resp.status_code == status.HTTP_200_OK
    user.refresh_from_db()
    assert user.phone_verified is True


def test_verify_otp_wrong_code_increments_attempts(api_client, requests_mock):
    user = User.objects.create_user(email="user@example.com", password="x")
    otp = PhoneOTP.objects.create(
        user=user,
        phone_number="+255700000000",
        provider_reference="pin-abc",
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    api_client.force_authenticate(user=user)
    requests_mock.post(BEEM_VERIFY_URL, json={"data": {"message": {"code": 200, "message": "invalid"}}})
    resp = api_client.post(reverse("auth-phone-verify-otp"), {"code": "000000"})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    user.refresh_from_db()
    otp.refresh_from_db()
    assert user.phone_verified is False
    assert otp.attempts == 1


def test_verify_otp_expired(api_client):
    user = User.objects.create_user(email="user@example.com", password="x")
    PhoneOTP.objects.create(
        user=user,
        phone_number="+255700000000",
        provider_reference="pin-abc",
        expires_at=timezone.now() - timedelta(minutes=1),
    )
    api_client.force_authenticate(user=user)
    resp = api_client.post(reverse("auth-phone-verify-otp"), {"code": "123456"})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_verify_otp_locks_out_after_max_attempts(api_client):
    user = User.objects.create_user(email="user@example.com", password="x")
    PhoneOTP.objects.create(
        user=user,
        phone_number="+255700000000",
        provider_reference="pin-abc",
        expires_at=timezone.now() + timedelta(minutes=10),
        attempts=5,
    )
    api_client.force_authenticate(user=user)
    resp = api_client.post(reverse("auth-phone-verify-otp"), {"code": "123456"})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_verify_otp_with_no_pending_otp(api_client):
    user = User.objects.create_user(email="user@example.com", password="x")
    api_client.force_authenticate(user=user)
    resp = api_client.post(reverse("auth-phone-verify-otp"), {"code": "123456"})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


# --- Order-creation verification gate ---


@pytest.fixture
def service():
    provider = Provider.objects.create(name="Mock", provider_type=Provider.ProviderType.MOCK)
    category = Category.objects.create(name="Instagram", slug="instagram")
    return Service.objects.create(
        category=category,
        provider=provider,
        provider_service_id="svc-1",
        name="Instagram Followers",
        cost_rate_per_1000=Decimal("1.0000"),
        retail_rate_per_1000=Decimal("5000.00"),
    )


def test_unverified_user_cannot_place_an_order(service):
    user = User.objects.create_user(email="unverified@example.com", password="x")
    WalletService.credit(user.wallet, Decimal("100000.00"), LedgerEntry.EntryType.DEPOSIT, "seed")
    with pytest.raises(OrderValidationError, match="verify"):
        OrderService.create_order(user, service, "https://instagram.com/x", quantity=1000)


def test_email_verified_user_can_order_even_with_no_phone(service):
    """Phone is optional (used only for sending customers updates) — a
    verified email is the whole gate. See
    apps/accounts/tests/test_account_linking_and_gate.py for the full set."""
    user = User.objects.create_user(email="halfverified@example.com", password="x", email_verified=True)
    WalletService.credit(user.wallet, Decimal("100000.00"), LedgerEntry.EntryType.DEPOSIT, "seed")
    order = OrderService.create_order(user, service, "https://instagram.com/x", quantity=1000)
    assert order.charge_amount == Decimal("5000.00")


# --- Cloudflare Turnstile ---

TURNSTILE_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def test_registration_works_without_a_token_when_turnstile_disabled(api_client, settings):
    settings.TURNSTILE_ENABLED = False  # the test-settings default; explicit for clarity
    resp = api_client.post(reverse("auth-register"), {"email": "noturnstile@example.com", "password": "S3cure-Pass!"})
    assert resp.status_code == status.HTTP_201_CREATED


def test_registration_rejects_invalid_turnstile_token_when_enabled(api_client, settings, requests_mock):
    settings.TURNSTILE_ENABLED = True
    settings.TURNSTILE_SECRET_KEY = "test-secret"
    requests_mock.post(TURNSTILE_URL, json={"success": False, "error-codes": ["invalid-input-response"]})
    resp = api_client.post(
        reverse("auth-register"),
        {"email": "botcheck@example.com", "password": "S3cure-Pass!", "turnstile_token": "bad-token"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert not User.objects.filter(email="botcheck@example.com").exists()


def test_registration_accepts_valid_turnstile_token_when_enabled(api_client, settings, requests_mock):
    settings.TURNSTILE_ENABLED = True
    settings.TURNSTILE_SECRET_KEY = "test-secret"
    requests_mock.post(TURNSTILE_URL, json={"success": True})
    resp = api_client.post(
        reverse("auth-register"),
        {"email": "realperson@example.com", "password": "S3cure-Pass!", "turnstile_token": "good-token"},
    )
    assert resp.status_code == status.HTTP_201_CREATED
