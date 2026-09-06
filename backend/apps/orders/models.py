from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.catalog.models import Service
from apps.common.models import TimeStampedModel, UUIDPKModel
from apps.providers.models import Provider
from apps.wallet.models import LedgerEntry


class Order(UUIDPKModel, TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In progress"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        PARTIAL = "partial", "Partial"
        CANCELED = "canceled", "Canceled"
        REFUNDED = "refunded", "Refunded"
        ERROR = "error", "Error"

    class RequestState(models.TextChoices):
        REQUESTED = "requested", "Requested"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        COMPLETED = "completed", "Completed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders"
    )
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="orders")
    # Snapshot of the resolved ServiceProviderMapping at order time — both
    # of these together, not service.provider/service.provider_service_id,
    # since a service can now have more than one mapping and the cheapest
    # one can change between when this order was placed and later. Without
    # this snapshot, submission and a later re-resolve could disagree on
    # which provider's SKU to actually call.
    provider = models.ForeignKey(Provider, on_delete=models.PROTECT, related_name="orders")
    provider_service_id = models.CharField(max_length=100, blank=True)
    link = models.URLField(max_length=500)
    quantity = models.PositiveIntegerField()
    # What the customer actually paid, after any coupon discount. Revenue
    # reporting reads this, so the gross list price is charge + discount.
    charge_amount = models.DecimalField(max_digits=14, decimal_places=2)
    discount_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    cost_amount = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    cost_currency = models.CharField(max_length=10, default="USD")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    provider_order_id = models.CharField(max_length=100, blank=True)
    start_count = models.PositiveIntegerField(null=True, blank=True)
    remains = models.PositiveIntegerField(null=True, blank=True)
    ledger_entry = models.OneToOneField(
        LedgerEntry, on_delete=models.PROTECT, related_name="order_charge"
    )
    refund_ledger_entry = models.OneToOneField(
        LedgerEntry, null=True, blank=True, on_delete=models.PROTECT, related_name="order_refund"
    )
    error_message = models.TextField(blank=True)
    refill_status = models.CharField(
        max_length=20, choices=RequestState.choices, null=True, blank=True
    )
    cancel_status = models.CharField(
        max_length=20, choices=RequestState.choices, null=True, blank=True
    )
    last_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Order {self.id} ({self.status})"

    @property
    def progress_percent(self) -> int | None:
        """0-100 delivery progress, for the live order tracker. None when
        there isn't enough information yet to show a bar at all (no
        remains reported by the provider so far and the order hasn't
        completed) — the frontend falls back to just the status badge
        in that case rather than a misleading 0%."""
        if self.remains is None:
            return 100 if self.status == self.Status.COMPLETED else None
        if self.quantity <= 0:
            return None
        delivered = max(0, self.quantity - self.remains)
        return max(0, min(100, round((delivered / self.quantity) * 100)))


class OrderStatusHistory(TimeStampedModel):
    class Source(models.TextChoices):
        USER = "user", "User"
        SYSTEM_SYNC = "system_sync", "System sync"
        ADMIN = "admin", "Admin"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")
    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20)
    source = models.CharField(max_length=20, choices=Source.choices)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]
        verbose_name_plural = "order status histories"


class OrderProgressSample(models.Model):
    """A timestamped snapshot of Order.remains, recorded on every sync tick
    for an order still in progress. A single remains value can't tell you a
    delivery rate — you need at least two timestamped points — so this is
    the raw material apps.catalog.health's speed-per-hour calculation reads
    from. Pruned after a week (see apps.orders.tasks.prune_progress_samples);
    the 48h Service Health window never needs anything older than that."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="progress_samples")
    remains = models.PositiveIntegerField()
    sampled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order_id", "sampled_at"]
        indexes = [models.Index(fields=["order", "sampled_at"])]
