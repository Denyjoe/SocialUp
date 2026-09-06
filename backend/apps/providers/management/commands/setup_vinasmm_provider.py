import environ
from django.core.management.base import BaseCommand, CommandError

from apps.providers.models import Provider

env = environ.Env()

DEFAULT_BASE_URL = "https://vinasmm.com/api/v2"


class Command(BaseCommand):
    help = (
        "Creates/updates the VinaSMM Provider row from PROVIDER_API_KEY (and "
        "optionally PROVIDER_BASE_URL) in your .env. Run this once you have "
        "a real API key, then use the Django admin's 'Sync services from "
        "provider now' / 'Check balance now' actions on it to test the "
        "connection and pull VinaSMM's real catalog."
    )

    def handle(self, *args, **options):
        api_key = env("PROVIDER_API_KEY", default="")
        base_url = env("PROVIDER_BASE_URL", default=DEFAULT_BASE_URL)

        if not api_key:
            raise CommandError(
                "PROVIDER_API_KEY is not set in your .env. Add it, then re-run this command."
            )

        provider, created = Provider.objects.update_or_create(
            name="VinaSMM",
            defaults={
                "provider_type": Provider.ProviderType.JAP_STYLE,
                "base_url": base_url,
                "api_key": api_key,
                "is_active": True,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if created else 'Updated'} provider '{provider.name}' ({provider.base_url}). "
                f"Next: in Django admin, select it and run 'Check balance now' to confirm the key works, "
                f"then 'Sync services from provider now' to pull its real catalog."
            )
        )
