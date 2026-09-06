from datetime import timedelta

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.announcements.models import Announcement

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def admin():
    return User.objects.create_user(email="owner@example.com", password="x", is_staff=True)


@pytest.fixture
def customer():
    return User.objects.create_user(email="cust@example.com", password="x")


def test_customer_sees_only_live_announcements(customer):
    Announcement.objects.create(title="Live one", body="visible")
    Announcement.objects.create(title="Switched off", body="hidden", is_active=False)
    Announcement.objects.create(
        title="Not started", body="hidden", starts_at=timezone.now() + timedelta(days=1)
    )
    Announcement.objects.create(
        title="Finished", body="hidden", ends_at=timezone.now() - timedelta(days=1)
    )

    client = APIClient()
    client.force_authenticate(user=customer)
    resp = client.get(reverse("announcement-list"))

    assert resp.status_code == status.HTTP_200_OK
    titles = [row["title"] for row in resp.data]
    assert titles == ["Live one"]


def test_announcements_require_sign_in():
    assert APIClient().get(reverse("announcement-list")).status_code == status.HTTP_401_UNAUTHORIZED


def test_admin_can_create_an_announcement(admin):
    client = APIClient()
    client.force_authenticate(user=admin)
    resp = client.post(
        reverse("admin-announcement-list"),
        {"title": "Scheduled maintenance", "body": "Back at 09:00.", "level": "warning"},
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert Announcement.objects.count() == 1


def test_non_staff_cannot_manage_announcements(customer):
    client = APIClient()
    client.force_authenticate(user=customer)
    assert client.get(reverse("admin-announcement-list")).status_code == status.HTTP_403_FORBIDDEN


def test_email_blast_sends_to_active_customers_and_is_recorded(admin, customer):
    User.objects.create_user(email="banned@example.com", password="x", status=User.Status.BANNED)
    announcement = Announcement.objects.create(title="Sale", body="20% off today.")

    client = APIClient()
    client.force_authenticate(user=admin)
    resp = client.post(reverse("admin-announcement-send-email", kwargs={"pk": announcement.pk}))

    assert resp.status_code == status.HTTP_200_OK
    assert len(mail.outbox) == 1
    recipients = mail.outbox[0].bcc
    assert "cust@example.com" in recipients
    assert "owner@example.com" in recipients
    assert "banned@example.com" not in recipients  # banned accounts excluded

    announcement.refresh_from_db()
    assert announcement.emailed_at is not None
    assert announcement.email_recipient_count == 2


def test_email_blast_cannot_be_sent_twice(admin):
    announcement = Announcement.objects.create(
        title="Once", body="only once", emailed_at=timezone.now()
    )
    client = APIClient()
    client.force_authenticate(user=admin)
    resp = client.post(reverse("admin-announcement-send-email", kwargs={"pk": announcement.pk}))
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert len(mail.outbox) == 0
