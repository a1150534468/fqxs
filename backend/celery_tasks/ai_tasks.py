import re
from typing import Any

import requests
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.chapters.models import Chapter
from apps.novels.models import NovelProject
from apps.tasks.models import Task

NON_WHITESPACE_PATTERN = re.compile(r'\S')


def _calculate_word_count(content: str | None) -> int:
    if not content:
        return 0
    return len(NON_WHITESPACE_PATTERN.findall(content))


def _update_task(task_record_id: int | None, **fields: Any) -> None:
    if not task_record_id:
        return
    Task.objects.filter(id=task_record_id).update(**fields)


@shared_task(bind=True, max_retries=3)
def generate_chapter_async(self, project_id, chapter_number, chapter_title, task_record_id=None):
    """Generate chapter content asynchronously via FastAPI AI service."""
    _update_task(
        task_record_id,
        status='running',
        started_at=timezone.now(),
        error_message='',
    )

    try:
        project = NovelProject.objects.get(id=project_id, is_deleted=False)

        response = requests.post(
            f"{settings.FASTAPI_URL.rstrip('/')}/api/ai/generate/chapter",
            json={
                'project_id': project_id,
                'chapter_number': chapter_number,
                'chapter_title': chapter_title,
            },
            timeout=300,
        )
        response.raise_for_status()
        payload = response.json()

        content = payload.get('content', '')
        chapter, created = Chapter.objects.update_or_create(
            project=project,
            chapter_number=chapter_number,
            defaults={
                'title': chapter_title,
                'raw_content': content,
                'final_content': content,
                'word_count': int(payload.get('word_count') or _calculate_word_count(content)),
                'status': 'pending_review',
                'generated_at': timezone.now(),
                'is_deleted': False,
            },
        )

        result = {
            'status': 'success',
            'chapter_id': chapter.id,
            'created': created,
        }
        _update_task(
            task_record_id,
            status='success',
            result=result,
            completed_at=timezone.now(),
            error_message='',
        )
        return result
    except Exception as exc:
        retry_count = int(self.request.retries) + 1
        _update_task(
            task_record_id,
            status='retry',
            retry_count=retry_count,
            error_message=str(exc),
        )
        try:
            raise self.retry(exc=exc, countdown=60)
        except self.MaxRetriesExceededError:
            _update_task(
                task_record_id,
                status='failed',
                completed_at=timezone.now(),
                error_message=str(exc),
                retry_count=retry_count,
            )
            raise
