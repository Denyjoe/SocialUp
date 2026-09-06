import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def recompute_service_health():
    """Celery beat: refreshes the 48h Service Health rollup for every
    service with recent orders. See apps.catalog.health for the actual
    computation — this task is just the schedule hook."""
    from .health import recompute_all_service_health

    touched = recompute_all_service_health()
    logger.info("recompute_service_health: refreshed %d service(s)", touched)
