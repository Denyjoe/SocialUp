from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Service, ServiceProviderMapping


@receiver(post_save, sender=Service)
def sync_default_provider_mapping(sender, instance: Service, **kwargs):
    """Keeps the ServiceProviderMapping for a service's own designated
    provider in step with its provider_service_id/cost_rate_per_1000 —
    the two fields that alone represented "how to fulfil this service"
    before multi-provider routing existed, and still do for the mapping
    tied to Service.provider itself.

    Fires on every save, not just creation, so an ongoing catalog sync
    (apps.providers.tasks.sync_provider_services, which also goes through
    update_or_create -> save()) updating a service's cost keeps that
    mapping priced correctly too. Only ever touches the mapping matching
    `instance.provider` — a second, deliberately curated mapping to a
    different provider (see ServiceProviderMapping.notes) is never
    touched here, and neither is that mapping's own is_active/priority."""
    ServiceProviderMapping.objects.update_or_create(
        service=instance,
        provider_id=instance.provider_id,
        defaults={
            "provider_service_id": instance.provider_service_id,
            "cost_rate_per_1000": instance.cost_rate_per_1000,
        },
    )
