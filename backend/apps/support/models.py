from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel
from apps.orders.models import Order


class Ticket(TimeStampedModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"  # created, awaiting first staff response
        ANSWERED = "answered", "Answered"  # staff replied, awaiting customer
        PENDING = "pending", "Pending"  # customer replied again, awaiting staff
        CLOSED = "closed", "Closed"

    class Category(models.TextChoices):
        GENERAL = "general", "General"
        BILLING = "billing", "Billing"
        ORDER_ISSUE = "order_issue", "Order issue"
        TECHNICAL = "technical", "Technical"
        OTHER = "other", "Other"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tickets"
    )
    subject = models.CharField(max_length=200)
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.GENERAL
    )
    order = models.ForeignKey(
        Order, null=True, blank=True, on_delete=models.SET_NULL, related_name="tickets"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    priority = models.CharField(
        max_length=20, choices=Priority.choices, default=Priority.NORMAL
    )

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"[{self.status}] {self.subject}"


class TicketMessage(TimeStampedModel):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )
    body = models.TextField()
    attachment = models.FileField(upload_to="ticket_attachments/%Y/%m/", blank=True, null=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Message on ticket {self.ticket_id} by {self.sender_id}"
