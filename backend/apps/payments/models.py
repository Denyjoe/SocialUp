from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel, UUIDPKModel
from apps.wallet.models import LedgerEntry


class Transaction(UUIDPKModel, TimeStampedModel):
    """A wallet deposit through an external payment gateway. Built for
    NOWPayments (crypto) first — the interim option while PesaPal
    verification is pending — but the gateway itself is pluggable
    (see apps/payments/gateways/), so PesaPal slots in later as a second
    `Gateway` choice without restructuring this model.

    Status values deliberately mirror NOWPayments' own vocabulary (see
    apps.payments.gateways.nowpayments) rather than inventing a parallel
    one — one less mapping to keep in sync.
    """

    class Gateway(models.TextChoices):
        NOWPAYMENTS = "nowpayments", "Crypto (NOWPayments)"

    class Status(models.TextChoices):
        WAITING = "waiting", "Waiting for payment"
        CONFIRMING = "confirming", "Confirming"
        CONFIRMED = "confirmed", "Confirmed"
        SENDING = "sending", "Settling"
        PARTIALLY_PAID = "partially_paid", "Partially paid"
        FINISHED = "finished", "Finished"
        FAILED = "failed", "Failed"
        EXPIRED = "expired", "Expired"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="deposits"
    )
    gateway = models.CharField(max_length=20, choices=Gateway.choices)
    # Our own reference, sent to the gateway as order_id and used to match
    # its webhook back to this row — never the gateway's own reference,
    # which does not exist yet at creation time.
    internal_reference = models.CharField(max_length=64, unique=True)
    gateway_reference = models.CharField(max_length=100, blank=True)
    # What the wallet is actually credited, in the wallet's own currency —
    # locked in at creation time so the customer knows exactly what they'll
    # receive regardless of any crypto-side rate movement afterward.
    amount_local = models.DecimalField(max_digits=14, decimal_places=2)
    # What was actually quoted to the gateway (NOWPayments prices in major
    # fiats, not TZS directly).
    amount_quote = models.DecimalField(max_digits=14, decimal_places=2)
    quote_currency = models.CharField(max_length=10, default="usd")
    # The crypto the customer ends up paying with — blank until the
    # gateway reports it (chosen on its hosted page, not on ours).
    pay_currency = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.WAITING)
    checkout_url = models.URLField(max_length=500, blank=True)
    # Last known raw gateway response/webhook payload, for support and
    # debugging — never parsed back out programmatically.
    raw_payload = models.JSONField(default=dict, blank=True)
    ledger_entry = models.OneToOneField(
        LedgerEntry, null=True, blank=True, on_delete=models.PROTECT, related_name="deposit"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_gateway_display()} deposit {self.internal_reference} ({self.status})"

    @property
    def is_settled(self) -> bool:
        return self.ledger_entry_id is not None
