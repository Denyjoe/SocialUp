import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("smm_panel")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "sync-order-statuses": {
        "task": "apps.orders.tasks.sync_order_statuses",
        # Tightened from 3 minutes for the live progress tracker — the
        # frontend polls every 10s, so the number behind it should move
        # more often too. Still one batched get_multi_status call per
        # active provider, not per order, so this is cheap to run often.
        "schedule": 90.0,
    },
    "retry-stuck-order-submissions": {
        "task": "apps.orders.tasks.retry_stuck_order_submissions",
        "schedule": 300.0,  # 5 minutes
    },
    "refresh-exchange-rates": {
        "task": "apps.common.tasks.refresh_exchange_rates",
        "schedule": 3600.0,  # 1 hour; FX moves slowly enough for display
    },
    "check-provider-balances": {
        "task": "apps.providers.tasks.check_provider_balance_all",
        "schedule": 3600.0,  # 1 hour
    },
    "recompute-service-health": {
        "task": "apps.catalog.tasks.recompute_service_health",
        "schedule": 3600.0,  # 1 hour; the public Service Health dashboard reads this cache, never live
    },
    "prune-order-progress-samples": {
        "task": "apps.orders.tasks.prune_progress_samples",
        "schedule": 86400.0,  # daily
    },
    # Deliberately NOT scheduling sync_provider_services here — a full
    # catalog re-sync overwrites pricing and is triggered manually (Django
    # admin action) until Phase 5 adds a reviewable diff before it goes live.
    # Phase 6: wallet reconciliation nightly check.
}
