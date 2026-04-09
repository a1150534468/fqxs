import logging

from celery import shared_task
from django.utils import timezone

from apps.chapters.models import Chapter
from apps.tasks.models import Task

logger = logging.getLogger('celery_tasks')


@shared_task(bind=True, max_retries=2)
def publish_chapter_async(self, chapter_id, task_record_id=None):
    """Publish a chapter to Tomato Novel platform using browser automation."""
    logger.info(f'Starting chapter publishing: chapter_id={chapter_id}')

    if task_record_id:
        Task.objects.filter(id=task_record_id).update(
            status='running',
            started_at=timezone.now(),
            error_message='',
        )

    try:
        chapter = Chapter.objects.get(id=chapter_id, is_deleted=False)

        # Check if chapter is approved
        if chapter.status != 'approved':
            error_msg = f'Chapter must be approved before publishing. Current status: {chapter.status}'
            logger.error(error_msg)
            if task_record_id:
                Task.objects.filter(id=task_record_id).update(
                    status='failed',
                    error_message=error_msg,
                    completed_at=timezone.now(),
                )
            return {'status': 'error', 'reason': error_msg}

        # Import browser publisher
        from services.tomato_browser_publisher import TomatoBrowserPublisher

        publisher = TomatoBrowserPublisher()

        # Publish chapter
        result = publisher.publish_chapter(
            book_id=chapter.project.tomato_book_id,
            chapter_title=chapter.title,
            chapter_content=chapter.final_content,
        )

        if result.get('success'):
            # Update chapter status
            chapter.status = 'published'
            chapter.published_at = timezone.now()
            if result.get('chapter_id'):
                chapter.tomato_chapter_id = result['chapter_id']
            chapter.save(update_fields=['status', 'published_at', 'tomato_chapter_id', 'updated_at'])

            logger.info(f'Chapter {chapter_id} published successfully')

            if task_record_id:
                Task.objects.filter(id=task_record_id).update(
                    status='success',
                    result={'chapter_id': chapter.id, 'tomato_chapter_id': chapter.tomato_chapter_id},
                    completed_at=timezone.now(),
                    error_message='',
                )

            return {'status': 'success', 'chapter_id': chapter.id}
        else:
            error_msg = result.get('error', 'Unknown error during publishing')
            logger.error(f'Failed to publish chapter {chapter_id}: {error_msg}')

            if task_record_id:
                Task.objects.filter(id=task_record_id).update(
                    status='failed',
                    error_message=error_msg,
                    completed_at=timezone.now(),
                )

            return {'status': 'error', 'reason': error_msg}

    except Chapter.DoesNotExist:
        error_msg = f'Chapter {chapter_id} not found'
        logger.error(error_msg)
        if task_record_id:
            Task.objects.filter(id=task_record_id).update(
                status='failed',
                error_message=error_msg,
                completed_at=timezone.now(),
            )
        return {'status': 'error', 'reason': error_msg}

    except Exception as exc:
        retry_count = int(self.request.retries) + 1
        logger.error(f'Chapter publishing failed: {exc}', exc_info=True)

        if task_record_id:
            Task.objects.filter(id=task_record_id).update(
                status='retry',
                retry_count=retry_count,
                error_message=str(exc),
            )

        try:
            raise self.retry(exc=exc, countdown=300)
        except self.MaxRetriesExceededError:
            logger.error(f'Chapter publishing max retries exceeded: {exc}')
            if task_record_id:
                Task.objects.filter(id=task_record_id).update(
                    status='failed',
                    completed_at=timezone.now(),
                    error_message=str(exc),
                    retry_count=retry_count,
                )
            raise
