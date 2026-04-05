from celery import shared_task
from django.db.models import Sum
from django.utils import timezone

from apps.chapters.models import Chapter
from apps.novels.models import NovelProject
from apps.stats.models import Stats


@shared_task
def update_daily_stats():
    """Refresh daily aggregated generation metrics."""
    today = timezone.now().date()

    project_queryset = NovelProject.objects.filter(is_deleted=False)
    chapter_queryset = Chapter.objects.filter(is_deleted=False, project__is_deleted=False)

    total_projects = project_queryset.count()
    total_chapters = chapter_queryset.count()
    total_word_count = chapter_queryset.aggregate(total=Sum('word_count')).get('total') or 0

    stats_record, _ = Stats.objects.update_or_create(
        date=today,
        metric_type='generation',
        defaults={
            'metric_data': {
                'total_projects': total_projects,
                'total_chapters': total_chapters,
                'total_word_count': total_word_count,
            }
        },
    )

    return {
        'status': 'success',
        'date': str(today),
        'stats_id': stats_record.id,
    }
