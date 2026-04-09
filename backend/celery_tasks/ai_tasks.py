import logging
import re
from typing import Any

import requests
from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.chapters.models import Chapter
from apps.inspirations.models import Inspiration
from apps.novels.models import NovelProject
from apps.tasks.models import Task
from utils.monitoring import log_celery_task

logger = logging.getLogger('celery_tasks')
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
@log_celery_task
def generate_chapter_async(self, project_id, chapter_number, chapter_title, task_record_id=None):
    """Generate chapter content asynchronously via FastAPI AI service."""
    logger.info(f'Starting chapter generation: project={project_id}, chapter={chapter_number}')
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
        logger.info(f'Chapter generation completed: chapter_id={chapter.id}, created={created}')
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
        logger.error(f'Chapter generation failed: {exc}', exc_info=True)
        _update_task(
            task_record_id,
            status='retry',
            retry_count=retry_count,
            error_message=str(exc),
        )
        try:
            raise self.retry(exc=exc, countdown=60)
        except self.MaxRetriesExceededError:
            logger.error(f'Chapter generation max retries exceeded: {exc}')
            _update_task(
                task_record_id,
                status='failed',
                completed_at=timezone.now(),
                error_message=str(exc),
                retry_count=retry_count,
            )
            raise


@shared_task(bind=True, max_retries=3)
@log_celery_task
def generate_inspiration_from_trends(self, task_record_id=None):
    """Analyze trending books and generate novel inspirations."""
    logger.info('Starting inspiration generation from trends')
    _update_task(
        task_record_id,
        status='running',
        started_at=timezone.now(),
        error_message='',
    )

    try:
        # Get top trending inspirations as reference
        trending_books = Inspiration.objects.filter(
            is_used=False
        ).order_by('-hot_score')[:20]

        if not trending_books:
            logger.warning('No trending books found for inspiration generation')
            result = {'status': 'skipped', 'reason': 'No trending books available'}
            _update_task(
                task_record_id,
                status='success',
                result=result,
                completed_at=timezone.now(),
            )
            return result

        # Prepare data for FastAPI
        trending_data = [
            {
                'title': book.title,
                'synopsis': book.synopsis or '',
                'tags': book.tags or [],
                'hot_score': float(book.hot_score),
            }
            for book in trending_books
        ]

        # Call FastAPI to generate inspirations
        response = requests.post(
            f"{settings.FASTAPI_URL.rstrip('/')}/api/ai/generate/inspiration",
            json={
                'trending_books': trending_data,
                'genre_preference': '',
            },
            timeout=120,
        )
        response.raise_for_status()
        result_data = response.json()

        # Save generated inspirations
        created_count = 0
        for insp_data in result_data.get('inspirations', []):
            Inspiration.objects.create(
                source_url='',
                title=insp_data.get('title', ''),
                synopsis=insp_data.get('synopsis', ''),
                tags=insp_data.get('selling_points', []),
                hot_score=insp_data.get('estimated_popularity', 0),
                rank_type='AI生成',
                is_used=False,
            )
            created_count += 1

        result = {
            'status': 'success',
            'created_count': created_count,
            'analysis_summary': result_data.get('analysis_summary', ''),
        }
        logger.info(f'Generated {created_count} inspirations from trends')
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
        logger.error(f'Inspiration generation failed: {exc}', exc_info=True)
        _update_task(
            task_record_id,
            status='retry',
            retry_count=retry_count,
            error_message=str(exc),
        )
        try:
            raise self.retry(exc=exc, countdown=120)
        except self.MaxRetriesExceededError:
            logger.error(f'Inspiration generation max retries exceeded: {exc}')
            _update_task(
                task_record_id,
                status='failed',
                completed_at=timezone.now(),
                error_message=str(exc),
                retry_count=retry_count,
            )
            raise


@shared_task(bind=True, max_retries=2)
@log_celery_task
def start_novel_project_from_inspiration(
    self, user_id, inspiration_id, title=None, genre=None, target_chapters=100, task_record_id=None
):
    """Complete workflow: create project, generate outline, and first chapter."""
    logger.info(f'Starting novel project from inspiration {inspiration_id} for user {user_id}')
    _update_task(
        task_record_id,
        status='running',
        started_at=timezone.now(),
        error_message='',
    )

    try:
        from apps.users.models import User

        user = User.objects.get(id=user_id)
        inspiration = Inspiration.objects.get(id=inspiration_id)

        project_title = title or inspiration.title
        project_genre = genre or (inspiration.tags[0] if inspiration.tags else '都市')

        with transaction.atomic():
            # Create project
            project = NovelProject.objects.create(
                user=user,
                inspiration=inspiration,
                title=project_title,
                genre=project_genre,
                synopsis=inspiration.synopsis or '',
                target_chapters=target_chapters,
                status='active',
            )

            # Generate outline
            outline_response = requests.post(
                f"{settings.FASTAPI_URL.rstrip('/')}/api/ai/generate/outline",
                json={
                    'inspiration_id': inspiration.id,
                    'genre': project_genre,
                    'target_chapters': target_chapters,
                },
                timeout=120,
            )
            outline_response.raise_for_status()
            outline_data = outline_response.json()

            project.outline = outline_data.get('outline', '')
            project.save(update_fields=['outline'])

            # Generate first chapter
            chapter_response = requests.post(
                f"{settings.FASTAPI_URL.rstrip('/')}/api/ai/generate/chapter",
                json={
                    'project_id': project.id,
                    'chapter_number': 1,
                    'chapter_title': '第一章',
                    'outline_context': project.outline[:500],
                },
                timeout=300,
            )
            chapter_response.raise_for_status()
            chapter_data = chapter_response.json()

            # Create chapter
            chapter = Chapter.objects.create(
                project=project,
                chapter_number=1,
                title='第一章',
                raw_content=chapter_data.get('content', ''),
                final_content=chapter_data.get('content', ''),
                word_count=chapter_data.get('word_count', 0),
                status='pending_review',
                generated_at=timezone.now(),
            )

            # Update project
            project.current_chapter = 1
            project.last_update_at = timezone.now()
            project.save(update_fields=['current_chapter', 'last_update_at'])

            # Mark inspiration as used
            inspiration.is_used = True
            inspiration.save(update_fields=['is_used'])

            result = {
                'status': 'success',
                'project_id': project.id,
                'chapter_id': chapter.id,
                'title': project.title,
            }
            logger.info(f'Novel project {project.id} created successfully')
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
        logger.error(f'Project creation failed: {exc}', exc_info=True)
        _update_task(
            task_record_id,
            status='retry',
            retry_count=retry_count,
            error_message=str(exc),
        )
        try:
            raise self.retry(exc=exc, countdown=120)
        except self.MaxRetriesExceededError:
            logger.error(f'Project creation max retries exceeded: {exc}')
            _update_task(
                task_record_id,
                status='failed',
                completed_at=timezone.now(),
                error_message=str(exc),
                retry_count=retry_count,
            )
            raise


@shared_task
def generate_next_chapter_for_project(project_id, force=False):
    """Generate the next chapter for a project.

    Args:
        project_id: Project ID
        force: If True, skip auto_generation_enabled check (for manual triggers)
    """
    try:
        project = NovelProject.objects.get(id=project_id, is_deleted=False)

        if not force and not project.auto_generation_enabled:
            logger.info(f"Auto-generation disabled for project {project_id}")
            return {'status': 'skipped', 'reason': 'auto_generation_disabled'}

        if project.current_chapter >= project.target_chapters:
            logger.info(f"Project {project_id} has reached target chapters")
            return {'status': 'skipped', 'reason': 'target_reached'}

        next_chapter_number = project.current_chapter + 1
        chapter_title = f"第{next_chapter_number}章"

        # Create task record
        task_record = Task.objects.create(
            task_type='generate_chapter',
            related_type='project',
            related_id=project.id,
            status='pending',
            params={
                'project_id': project.id,
                'chapter_number': next_chapter_number,
                'chapter_title': chapter_title,
            },
        )

        # Trigger generation
        result = generate_chapter_async.delay(
            project.id,
            next_chapter_number,
            chapter_title,
            task_record_id=task_record.id,
        )

        task_record.celery_task_id = result.id
        task_record.save(update_fields=['celery_task_id', 'updated_at'])

        # Update next generation time
        now = timezone.now()
        if project.generation_schedule == 'daily':
            project.next_generation_time = now + timezone.timedelta(days=1)
        elif project.generation_schedule == 'every_2_days':
            project.next_generation_time = now + timezone.timedelta(days=2)
        else:  # weekly
            project.next_generation_time = now + timezone.timedelta(days=7)

        project.save(update_fields=['next_generation_time', 'updated_at'])

        logger.info(f"Started generation for chapter {next_chapter_number} of project {project_id}")
        return {'status': 'started', 'chapter_number': next_chapter_number, 'task_id': result.id}

    except NovelProject.DoesNotExist:
        logger.error(f"Project {project_id} not found")
        return {'status': 'error', 'reason': 'project_not_found'}
    except Exception as e:
        logger.error(f"Failed to generate next chapter for project {project_id}: {e}", exc_info=True)
        return {'status': 'error', 'reason': str(e)}


@shared_task
def auto_generate_chapters_daily():
    """Daily task to generate chapters for all projects with auto-generation enabled."""
    now = timezone.now()

    projects = NovelProject.objects.filter(
        auto_generation_enabled=True,
        is_deleted=False,
        next_generation_time__lte=now,
    )

    results = []
    for project in projects:
        try:
            result = generate_next_chapter_for_project(project.id)
            results.append({
                'project_id': project.id,
                'project_title': project.title,
                'result': result,
            })
        except Exception as e:
            logger.error(f"Failed to auto-generate for project {project.id}: {e}", exc_info=True)
            results.append({
                'project_id': project.id,
                'project_title': project.title,
                'result': {'status': 'error', 'reason': str(e)},
            })

    logger.info(f"Auto-generation completed for {len(results)} projects")
    return {'total_projects': len(results), 'results': results}
