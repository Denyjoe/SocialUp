import uuid

from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base adding created_at / updated_at to any model."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDPKModel(models.Model):
    """Abstract base giving a model a UUID primary key instead of a bigint.

    Used for models where the ID may be exposed externally (e.g. referenced
    in a payment gateway callback or a provider API payload) and we don't
    want to leak sequential integer IDs.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class ExchangeRateSnapshot(TimeStampedModel):
    """Live FX rates for showing prices in a customer's own currency.

    Display only. Wallets, orders and every ledger entry stay in the base
    currency, so a moving rate can never change what someone was actually
    charged. Rates are stored as "1 base unit = X foreign units".
    """

    base_currency = models.CharField(max_length=10, default="TZS")
    rates = models.JSONField(default=dict)
    source = models.CharField(max_length=120, blank=True)
    fetched_at = models.DateTimeField()

    class Meta:
        ordering = ["-fetched_at"]

    def __str__(self) -> str:
        return f"{self.base_currency} rates at {self.fetched_at:%Y-%m-%d %H:%M}"

    @classmethod
    def latest(cls):
        return cls.objects.first()
