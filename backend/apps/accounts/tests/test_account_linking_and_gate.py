"""Covers the two rules the user asked for explicitly:
  1. One account per email address — signing up with email/password and then
     signing in with Google (same address) must land on ONE account.
  2. The order gate is email-only. Phone is optional (updates only), and a
     Google sign-in must never be asked to verify anything.
"""

from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.google_oauth import GoogleUserInfo
from apps.accounts.models import User
from apps.catalog.models import Category, Service
from apps.orders.services import OrderService, OrderValidationError
from apps.providers.models import Provider
from apps.wallet.models import LedgerEntry
from apps.wallet.services import WalletService

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def api_client():
    return APIClient()


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


def _fund(user, amount="100000.00"):
    WalletService.credit(
        user.wallet, Decimal(amount), LedgerEntry.EntryType.DEPOSIT, f"seed-{user.pk}"
    )


# --- 1. One account per email ---


def test_email_signup_then_google_signin_is_one_account(api_client, monkeypatch):
    api_client.post(
        reverse("auth-register"),
        {"email": "same@example.com", "password": "S3cure-Pass!"},
    )
    assert User.objects.filter(email="same@example.com").count() == 1
    original = User.objects.get(email="same@example.com")

    monkeypatch.setattr(
        "apps.accounts.views.verify_google_id_token",
        lambda token: GoogleUserInfo(sub="g-abc", email="same@example.com", email_verified=True),
    )
    resp = api_client.post(reverse("auth-google"), {"id_token": "fake"})
    assert resp.status_code == status.HTTP_200_OK

    # Still exactly one account, now linked to Google.
    assert User.objects.filter(email="same@example.com").count() == 1
    original.refresh_from_db()
    assert original.google_sub == "g-abc"
    assert resp.data["user"]["id"] == original.id


def test_google_signin_then_email_signup_is_refused_with_a_useful_message(api_client, monkeypatch):
    monkeypatch.setattr(
        "apps.accounts.views.verify_google_id_token",
        lambda token: GoogleUserInfo(sub="g-xyz", email="same@example.com", email_verified=True),
    )
    api_client.post(reverse("auth-google"), {"id_token": "fake"})
    assert User.objects.filter(email="same@example.com").count() == 1

    resp = api_client.post(
        reverse("auth-register"),
        {"email": "same@example.com", "password": "S3cure-Pass!"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Google" in str(resp.data["email"])  # points them at the right button
    assert User.objects.filter(email="same@example.com").count() == 1


def test_case_variant_email_does_not_create_a_second_account(api_client, monkeypatch):
    """"Foo@Example.com" and "foo@example.com" are the same mailbox — the DB
    unique constraint is case-sensitive, so this has to be normalised."""
    api_client.post(
        reverse("auth-register"),
        {"email": "MixedCase@Example.com", "password": "S3cure-Pass!"},
    )
    assert User.objects.count() == 1
    assert User.objects.get().email == "mixedcase@example.com"  # stored lowercased

    # Same address, different casing, via the register form.
    dupe = api_client.post(
        reverse("auth-register"),
        {"email": "mixedcase@EXAMPLE.com", "password": "S3cure-Pass!"},
    )
    assert dupe.status_code == status.HTTP_400_BAD_REQUEST
    assert User.objects.count() == 1

    # ...and via Google.
    monkeypatch.setattr(
        "apps.accounts.views.verify_google_id_token",
        lambda token: GoogleUserInfo(
            sub="g-case", email="MIXEDCASE@example.com", email_verified=True
        ),
    )
    resp = api_client.post(reverse("auth-google"), {"id_token": "fake"})
    assert resp.status_code == status.HTTP_200_OK
    assert User.objects.count() == 1  # linked, not duplicated


def test_duplicate_email_signup_is_refused(api_client):
    User.objects.create_user(email="taken@example.com", password="x")
    resp = api_client.post(
        reverse("auth-register"),
        {"email": "taken@example.com", "password": "S3cure-Pass!"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert User.objects.filter(email="taken@example.com").count() == 1


# --- 2. Order gate is email-only; phone is optional ---


def test_google_user_can_order_immediately_without_verifying_anything(service, monkeypatch):
    """The whole point of signing in with Google: zero extra verification."""
    monkeypatch.setattr(
        "apps.accounts.views.verify_google_id_token",
        lambda token: GoogleUserInfo(sub="g-1", email="gmailer@example.com", email_verified=True),
    )
    APIClient().post(reverse("auth-google"), {"id_token": "fake"})

    user = User.objects.get(email="gmailer@example.com")
    assert user.email_verified is True
    assert user.phone_verified is False  # never asked, never needed
    _fund(user)

    order = OrderService.create_order(user, service, "https://instagram.com/x", quantity=1000)
    assert order.charge_amount == Decimal("5000.00")


def test_email_verified_user_can_order_without_a_phone_at_all(service):
    user = User.objects.create_user(
        email="noPhone@example.com", password="x", email_verified=True
    )
    assert user.phone_number == ""
    assert user.phone_verified is False
    _fund(user)

    order = OrderService.create_order(user, service, "https://instagram.com/x", quantity=1000)
    assert order.charge_amount == Decimal("5000.00")


def test_unverified_email_still_blocks_ordering(service):
    user = User.objects.create_user(email="unverified@example.com", password="x")
    _fund(user)
    with pytest.raises(OrderValidationError, match="verify your email"):
        OrderService.create_order(user, service, "https://instagram.com/x", quantity=1000)


def test_verified_phone_alone_does_not_unlock_ordering(service):
    """Phone is not an identity gate — only email is."""
    user = User.objects.create_user(
        email="phoneonly@example.com", password="x", phone_verified=True
    )
    _fund(user)
    with pytest.raises(OrderValidationError, match="verify your email"):
        OrderService.create_order(user, service, "https://instagram.com/x", quantity=1000)
