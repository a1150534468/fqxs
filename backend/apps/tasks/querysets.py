from django.db.models import Q

from apps.chapters.models import Chapter
from apps.novels.models import NovelProject
from apps.tasks.models import Task


def scoped_task_queryset_for_user(user):
    """Return task records that belong to the current user's projects or chapters."""
    project_ids = list(
        NovelProject.objects.filter(
            user=user,
            is_deleted=False,
        ).values_list('id', flat=True)
    )
    chapter_ids = list(
        Chapter.objects.filter(
            project__user=user,
            project__is_deleted=False,
            is_deleted=False,
        ).values_list('id', flat=True)
    )

    project_query = Q(related_type='project', related_id__in=project_ids)
    chapter_query = Q(related_type='chapter', related_id__in=chapter_ids)

    # Backfill compatibility for older tasks that only stored references in params.
    project_query |= Q(params__project_id__in=project_ids)
    chapter_query |= Q(params__chapter_id__in=chapter_ids)

    return Task.objects.filter(project_query | chapter_query).distinct()
