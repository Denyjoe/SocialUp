from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.wallet.models import LedgerEntry

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_user():
    return User.objects.create_superuser(email="admin@example.com", password="x")


@pytest.fixture
def plain_user():
    return User.objects.create_user(email="user@example.com", password="x")


@pytest.fixture
def admin_client(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


def test_non_staff_cannot_list_users(plain_user):
    client = APIClient()
    client.force_authenticate(user=plain_user)
    resp = client.get(reverse("admin-user-list"))
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_unauthenticated_cannot_list_users():
    resp = APIClient().get(reverse("admin-user-list"))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_admin_can_list_users_with_wallet_and_order_count(admin_client, plain_user):
    resp = admin_client.get(reverse("admin-user-list"))
    assert resp.status_code == status.HTTP_200_OK
    row = next(r for r in resp.data["results"] if r["email"] == "user@example.com")
    assert Decimal(row["wallet_balance"]) == Decimal("0.00")
    assert row["orders_count"] == 0


def test_admin_search_filters_by_email(admin_client, plain_user):
    resp = admin_client.get(reverse("admin-user-list"), {"search": "nonexistent"})
    assert resp.data["count"] == 0


def test_admin_credit_adjustment_increases_balance(admin_client, plain_user):
    resp = admin_client.post(
        reverse("admin-user-adjust-balance", kwargs={"pk": plain_user.pk}),
        {"direction": "credit", "amount": "5000.00", "reason": "Goodwill credit"},
    )
    assert resp.status_code == status.HTTP_200_OK, resp.data
    assert Decimal(resp.data["balance"]) == Decimal("5000.00")

    entry = LedgerEntry.objects.get(wallet=plain_user.wallet)
    assert entry.entry_type == LedgerEntry.EntryType.ADMIN_ADJUSTMENT_CREDIT
    assert entry.description == "Goodwill credit"


def test_admin_debit_adjustment_rejects_insufficient_balance(admin_client, plain_user):
    resp = admin_client.post(
        reverse("admin-user-adjust-balance", kwargs={"pk": plain_user.pk}),
        {"direction": "debit", "amount": "100.00"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_non_staff_cannot_adjust_balance(plain_user):
    other = User.objects.create_user(email="other@example.com", password="x")
    client = APIClient()
    client.force_authenticate(user=plain_user)
    resp = client.post(
        reverse("admin-user-adjust-balance", kwargs={"pk": other.pk}),
        {"direction": "credit", "amount": "100.00"},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_admin_can_suspend_a_user(admin_client, plain_user):
    resp = admin_client.post(
        reverse("admin-user-status", kwargs={"pk": plain_user.pk}), {"status": "suspended"}
    )
    assert resp.status_code == status.HTTP_200_OK
    plain_user.refresh_from_db()
    assert plain_user.status == User.Status.SUSPENDED


def test_suspended_user_cannot_log_in(admin_client, plain_user):
    admin_client.post(reverse("admin-user-status", kwargs={"pk": plain_user.pk}), {"status": "banned"})
    resp = APIClient().post(reverse("auth-login"), {"email": plain_user.email, "password": "x"})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
