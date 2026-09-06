import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


def test_register_creates_user_with_api_key_and_referral_code(api_client):
    url = reverse("auth-register")
    resp = api_client.post(
        url, {"email": "user@example.com", "password": "S3cure-Pass!"}
    )
    assert resp.status_code == status.HTTP_201_CREATED, resp.data
    user = User.objects.get(email="user@example.com")
    assert user.api_key
    assert user.referral_code
    assert user.status == User.Status.ACTIVE


def test_register_with_referral_code_links_referrer(api_client):
    referrer = User.objects.create_user(email="ref@example.com", password="x")
    api_client.post(
        reverse("auth-register"),
        {
            "email": "referred@example.com",
            "password": "S3cure-Pass!",
            "referral_code": referrer.referral_code,
        },
    )
    referred = User.objects.get(email="referred@example.com")
    assert referred.referred_by_id == referrer.id


def test_login_returns_tokens_and_user_profile(api_client):
    User.objects.create_user(email="user@example.com", password="S3cure-Pass!")
    resp = api_client.post(
        reverse("auth-login"),
        {"email": "user@example.com", "password": "S3cure-Pass!"},
    )
    assert resp.status_code == status.HTTP_200_OK, resp.data
    assert "access" in resp.data and "refresh" in resp.data
    assert resp.data["user"]["email"] == "user@example.com"


def test_login_rejects_wrong_password(api_client):
    User.objects.create_user(email="user@example.com", password="S3cure-Pass!")
    resp = api_client.post(
        reverse("auth-login"),
        {"email": "user@example.com", "password": "wrong"},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_login_rejects_suspended_account(api_client):
    user = User.objects.create_user(email="user@example.com", password="S3cure-Pass!")
    user.status = User.Status.SUSPENDED
    user.save()
    resp = api_client.post(
        reverse("auth-login"),
        {"email": "user@example.com", "password": "S3cure-Pass!"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_me_requires_authentication(api_client):
    resp = api_client.get(reverse("auth-me"))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_me_returns_profile_when_authenticated(api_client):
    user = User.objects.create_user(email="user@example.com", password="S3cure-Pass!")
    api_client.force_authenticate(user=user)
    resp = api_client.get(reverse("auth-me"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["email"] == "user@example.com"


def test_me_patch_updates_phone_only(api_client):
    user = User.objects.create_user(email="user@example.com", password="S3cure-Pass!")
    api_client.force_authenticate(user=user)
    resp = api_client.patch(
        reverse("auth-me"),
        {"phone_number": "+255700000000", "email": "hacked@example.com"},
    )
    assert resp.status_code == status.HTTP_200_OK
    user.refresh_from_db()
    assert user.phone_number == "+255700000000"
    assert user.email == "user@example.com"  # email untouched, as intended


def test_api_key_regenerate_changes_the_key(api_client):
    user = User.objects.create_user(email="user@example.com", password="S3cure-Pass!")
    api_client.force_authenticate(user=user)
    old_key = user.api_key
    resp = api_client.post(reverse("auth-api-key-regenerate"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["api_key"] != old_key


def test_logout_blacklists_refresh_token(api_client):
    User.objects.create_user(email="user@example.com", password="S3cure-Pass!")
    login_resp = api_client.post(
        reverse("auth-login"),
        {"email": "user@example.com", "password": "S3cure-Pass!"},
    )
    access, refresh = login_resp.data["access"], login_resp.data["refresh"]

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    logout_resp = api_client.post(reverse("auth-logout"), {"refresh": refresh})
    assert logout_resp.status_code == status.HTTP_205_RESET_CONTENT

    refresh_resp = api_client.post(reverse("auth-token-refresh"), {"refresh": refresh})
    assert refresh_resp.status_code == status.HTTP_401_UNAUTHORIZED
