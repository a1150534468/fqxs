from celery import shared_task
from django.core.management import call_command


@shared_task(bind=True, max_retries=1)
def crawl_inspirations_task(self, limit=50):
    """Scheduled crawling task for inspiration data ingestion."""
    try:
        call_command('run_spider', limit=limit)
        return {'status': 'success', 'limit': int(limit)}
    except Exception as exc:
        return {'status': 'error', 'message': str(exc)}
