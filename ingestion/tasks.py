from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def pull_gdelt(self):
    from ingestion.sources.gdelt import GDELTIngester
    try:
        count = GDELTIngester().run()
        logger.info(f"GDELT done — {count} new events")
        return {"status": "ok", "new_events": count}
    except Exception as exc:
        raise self.retry(exc=exc)
