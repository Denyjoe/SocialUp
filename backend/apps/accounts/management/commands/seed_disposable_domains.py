from django.core.management.base import BaseCommand

from apps.accounts.disposable_domains_seed import DISPOSABLE_DOMAINS_SEED
from apps.accounts.models import DisposableEmailDomain


class Command(BaseCommand):
    help = "Seeds the starter list of known disposable email domains (idempotent)."

    def handle(self, *args, **options):
        existing = set(DisposableEmailDomain.objects.values_list("domain", flat=True))
        to_create = [
            DisposableEmailDomain(domain=d) for d in DISPOSABLE_DOMAINS_SEED if d not in existing
        ]
        DisposableEmailDomain.objects.bulk_create(to_create)
        self.stdout.write(
            self.style.SUCCESS(
                f"Added {len(to_create)} new disposable domains "
                f"({DisposableEmailDomain.objects.count()} total)."
            )
        )
