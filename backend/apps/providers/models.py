from django.db import models

from apps.common.models import TimeStampedModel


class Provider(TimeStampedModel):
    """An upstream service we buy from and resell. 'mock' needs no real
    credentials and instant-completes orders — used until Phase 3 wires up
    a real reseller API (see docs/provider-api-assumptions.md)."""

    class ProviderType(models.TextChoices):
        MOCK = "mock", "Mock (local testing)"
        JAP_STYLE = "jap_style", "JAP-style reseller API"

    name = models.CharField(max_length=100)
    provider_type = models.CharField(
        max_length=20, choices=ProviderType.choices, default=ProviderType.MOCK
    )
    base_url = models.URLField(blank=True)
    # TODO Phase 3: encrypt at rest (e.g. django-encrypted-model-fields) once a real key lives here.
    api_key = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    balance_cached = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    balance_currency = models.CharField(max_length=10, default="USD")
    balance_last_checked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return self.name


class ProviderServiceSyncLog(TimeStampedModel):
    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    provider = models.ForeignKey(
        Provider, on_delete=models.CASCADE, related_name="sync_logs"
    )
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    services_created = models.PositiveIntegerField(default=0)
    services_updated = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.SUCCESS
    )
    error_text = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]
