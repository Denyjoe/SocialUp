import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.support.models import Ticket

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture
def user():
    return User.objects.create_user(email="user@example.com", password="x")


@pytest.fixture
def admin():
    return User.objects.create_superuser(email="admin@example.com", password="x")


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def admin_client(admin):
    c = APIClient()
    c.force_authenticate(user=admin)
    return c


def test_create_ticket_creates_first_message(client, user):
    resp = client.post(
        reverse("ticket-list-create"),
        {"subject": "Order not delivered", "category": "order_issue", "message": "Help please"},
    )
    assert resp.status_code == status.HTTP_201_CREATED, resp.data
    assert resp.data["status"] == Ticket.Status.OPEN
    assert len(resp.data["messages"]) == 1
    assert resp.data["messages"][0]["body"] == "Help please"


def test_user_only_sees_own_tickets(client, user):
    other = User.objects.create_user(email="other@example.com", password="x")
    Ticket.objects.create(user=other, subject="Not mine", category="general")
    client.post(reverse("ticket-list-create"), {"subject": "Mine", "category": "general", "message": "hi"})

    resp = client.get(reverse("ticket-list-create"))
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["subject"] == "Mine"


def test_customer_reply_sets_status_pending_after_staff_answered(client, admin_client, user):
    create_resp = client.post(
        reverse("ticket-list-create"), {"subject": "Help", "category": "general", "message": "hi"}
    )
    ticket_id = create_resp.data["id"]

    admin_client.post(reverse("admin-ticket-reply", kwargs={"pk": ticket_id}), {"body": "We're on it"})
    ticket = Ticket.objects.get(pk=ticket_id)
    assert ticket.status == Ticket.Status.ANSWERED

    client.post(reverse("ticket-message-create", kwargs={"pk": ticket_id}), {"body": "Still broken"})
    ticket.refresh_from_db()
    assert ticket.status == Ticket.Status.PENDING


def test_user_cannot_message_another_users_ticket(client, user):
    other = User.objects.create_user(email="other@example.com", password="x")
    ticket = Ticket.objects.create(user=other, subject="Not mine", category="general")
    resp = client.post(reverse("ticket-message-create", kwargs={"pk": ticket.id}), {"body": "hi"})
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_non_staff_cannot_access_admin_ticket_list(client):
    resp = client.get(reverse("admin-ticket-list"))
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_admin_can_filter_tickets_by_status(admin_client, user):
    Ticket.objects.create(user=user, subject="Open one", category="general", status=Ticket.Status.OPEN)
    Ticket.objects.create(user=user, subject="Closed one", category="general", status=Ticket.Status.CLOSED)
    resp = admin_client.get(reverse("admin-ticket-list"), {"status": "closed"})
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["subject"] == "Closed one"


def test_admin_can_close_a_ticket(admin_client, user):
    ticket = Ticket.objects.create(user=user, subject="Help", category="general")
    resp = admin_client.post(reverse("admin-ticket-status", kwargs={"pk": ticket.id}), {"status": "closed"})
    assert resp.status_code == status.HTTP_200_OK
    ticket.refresh_from_db()
    assert ticket.status == Ticket.Status.CLOSED
