from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.catalog.models import Category, Service
from apps.providers.models import Provider

DEMO_SERVICES = [
    # (category_name, platform, slug, service_name, retail_per_1000_tzs, min_qty, max_qty, avg_time)
    ("Instagram", Category.Platform.INSTAGRAM, "instagram", "Instagram Followers", 5000, 100, 50000, "0-1 hour"),
    ("Instagram", Category.Platform.INSTAGRAM, "instagram", "Instagram Likes", 2000, 50, 20000, "0-30 min"),
    ("Instagram", Category.Platform.INSTAGRAM, "instagram", "Instagram Views", 800, 100, 100000, "instant"),
    ("TikTok", Category.Platform.TIKTOK, "tiktok", "TikTok Followers", 6000, 100, 50000, "0-1 hour"),
    ("TikTok", Category.Platform.TIKTOK, "tiktok", "TikTok Likes", 2500, 50, 50000, "0-30 min"),
    ("TikTok", Category.Platform.TIKTOK, "tiktok", "TikTok Views", 500, 1000, 1000000, "instant"),
    ("YouTube", Category.Platform.YOUTUBE, "youtube", "YouTube Views", 3000, 500, 100000, "0-6 hours"),
    ("YouTube", Category.Platform.YOUTUBE, "youtube", "YouTube Subscribers", 9000, 50, 10000, "0-24 hours"),
    ("Facebook", Category.Platform.FACEBOOK, "facebook", "Facebook Page Likes", 4500, 100, 20000, "0-1 hour"),
    ("Facebook", Category.Platform.FACEBOOK, "facebook", "Facebook Post Likes", 2200, 50, 20000, "0-30 min"),
]


class Command(BaseCommand):
    help = "Seeds a demo Mock provider with a starter catalog of services for local development."

    def handle(self, *args, **options):
        provider, created = Provider.objects.get_or_create(
            name="Demo Mock Provider",
            defaults={"provider_type": Provider.ProviderType.MOCK, "is_active": True},
        )
        self.stdout.write(
            self.style.SUCCESS(f"{'Created' if created else 'Using existing'} provider: {provider.name}")
        )

        categories: dict[str, Category] = {}
        created_count = 0
        updated_count = 0

        for sort_order, (cat_name, platform, slug, svc_name, retail, min_q, max_q, avg_time) in enumerate(
            DEMO_SERVICES
        ):
            if slug not in categories:
                categories[slug], _ = Category.objects.get_or_create(
                    slug=slug,
                    defaults={"name": cat_name, "platform": platform, "sort_order": sort_order},
                )
            category = categories[slug]

            provider_service_id = f"demo-{slug}-{svc_name.lower().replace(' ', '-')}"
            _, was_created = Service.objects.update_or_create(
                provider=provider,
                provider_service_id=provider_service_id,
                defaults={
                    "category": category,
                    "name": svc_name,
                    "service_type": Service.ServiceType.DEFAULT,
                    "min_quantity": min_q,
                    "max_quantity": max_q,
                    "cost_currency": "USD",
                    "cost_rate_per_1000": Decimal(retail) / Decimal(2700) / Decimal("1.4"),
                    "retail_rate_per_1000": Decimal(retail),
                    "is_active": True,
                    "average_time": avg_time,
                },
            )
            created_count += was_created
            updated_count += not was_created

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete: {created_count} services created, {updated_count} updated, "
                f"{len(categories)} categories."
            )
        )
