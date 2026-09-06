import pytest
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


def _uid(user):
    return urlsafe_base64_encode(force_bytes(user.pk))


def test_reset_request_sends_email_for_existing_user(api_client):
    user = User.objects.create_user(email="someone@example.com", password="OldPass123!")
    resp = api_client.post(reverse("auth-password-reset"), {"email": "someone@example.com"})
    assert resp.status_code == status.HTTP_200_OK
    assert len(mail.outbox) == 1
    assert "reset-password?uid=" in mail.outbox[0].body
    assert user.email in mail.outbox[0].to


def test_reset_request_for_unknown_email_looks_identical(api_client):
    """No account enumeration — the response must not reveal whether the
    address is registered."""
    known = User.objects.create_user(email="known@example.com", password="OldPass123!")
    known_resp = api_client.post(reverse("auth-password-reset"), {"email": known.email})
    mail.outbox.clear()
    unknown_resp = api_client.post(reverse("auth-password-reset"), {"email": "nobody@example.com"})

    assert known_resp.status_code == unknown_resp.status_code == status.HTTP_200_OK
    assert known_resp.data == unknown_resp.data
    assert len(mail.outbox) == 0  # nothing sent for the unknown address


def test_reset_confirm_sets_new_password(api_client):
    user = User.objects.create_user(email="someone@example.com", password="OldPass123!")
    resp = api_client.post(
        reverse("auth-password-reset-confirm"),
        {
            "uid": _uid(user),
            "token": default_token_generator.make_token(user),
            "new_password": "BrandNewPass456!",
        },
    )
    assert resp.status_code == status.HTTP_200_OK
    user.refresh_from_db()
    assert user.check_password("BrandNewPass456!")
    assert not user.check_password("OldPass123!")


def test_reset_token_cannot_be_reused(api_client):
    user = User.objects.create_user(email="someone@example.com", password="OldPass123!")
    token = default_token_generator.make_token(user)
    payload = {"uid": _uid(user), "token": token, "new_password": "BrandNewPass456!"}

    first = api_client.post(reverse("auth-password-reset-confirm"), payload)
    assert first.status_code == status.HTTP_200_OK

    # Django's token is derived from the password hash, so changing the
    # password invalidates it automatically.
    second = api_client.post(
        reverse("auth-password-reset-confirm"),
        {**payload, "new_password": "YetAnotherPass789!"},
    )
    assert second.status_code == status.HTTP_400_BAD_REQUEST
    user.refresh_from_db()
    assert user.check_password("BrandNewPass456!")  # unchanged by the replay


def test_reset_confirm_rejects_bad_token(api_client):
    user = User.objects.create_user(email="someone@example.com", password="OldPass123!")
    resp = api_client.post(
        reverse("auth-password-reset-confirm"),
        {"uid": _uid(user), "token": "not-a-real-token", "new_password": "BrandNewPass456!"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    user.refresh_from_db()
    assert user.check_password("OldPass123!")


def test_reset_confirm_enforces_password_strength(api_client):
    user = User.objects.create_user(email="someone@example.com", password="OldPass123!")
    resp = api_client.post(
        reverse("auth-password-reset-confirm"),
        {
            "uid": _uid(user),
            "token": default_token_generator.make_token(user),
            "new_password": "123",
        },
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_google_only_user_can_set_a_password_via_reset(api_client):
    """A Google signup has no usable password; the reset flow is how they
    add one if they ever want to log in without Google."""
    user = User.objects.create_user(email="google@example.com", password=None, google_sub="g-1")
    user.set_unusable_password()
    user.save(update_fields=["password"])
    assert not user.has_usable_password()

    resp = api_client.post(
        reverse("auth-password-reset-confirm"),
        {
            "uid": _uid(user),
            "token": default_token_generator.make_token(user),
            "new_password": "BrandNewPass456!",
        },
    )
    assert resp.status_code == status.HTTP_200_OK
    user.refresh_from_db()
    assert user.has_usable_password()
    assert user.check_password("BrandNewPass456!")
