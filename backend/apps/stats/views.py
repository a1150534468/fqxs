from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.dateparse import parse_date

from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.chapters.models import Chapter
from apps.novels.models import NovelProject
from apps.tasks.models import Task
from apps.stats.models import Stats
from apps.stats.serializers import StatsSerializer


class StatsPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def stats_list(request):
    queryset = Stats.objects.all().order_by('-date')

    date_after = request.query_params.get('date_after', '').strip()
    if date_after:
        parsed = parse_date(date_after)
        if parsed:
            queryset = queryset.filter(date__gte=parsed)

    date_before = request.query_params.get('date_before', '').strip()
    if date_before:
        parsed = parse_date(date_before)
        if parsed:
            queryset = queryset.filter(date__lte=parsed)

    metric_type = request.query_params.get('metric_type', '').strip()
    if metric_type:
        queryset = queryset.filter(metric_type=metric_type)

    paginator = StatsPagination()
    page = paginator.paginate_queryset(queryset, request)
    serializer = StatsSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """Aggregated dashboard data from all metric types."""
    data = {}
    for metric_type, _ in Stats.METRIC_TYPES:
        latest = (
            Stats.objects
            .filter(metric_type=metric_type)
            .order_by('-date')
            .first()
        )
        if latest:
            data[metric_type] = {
                'date': latest.date,
                'data': latest.metric_data,
            }

    return Response({'metrics': data})


REVENUE_PER_WORD = 0.002  # 0.2 分/字的粗略估算


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def stats_trend(request):
    """Return per-day trend data for reading/revenue metrics."""
    metric_type = (request.query_params.get('metric_type') or 'reading').lower()
    try:
        days = int(request.query_params.get('days') or 7)
    except ValueError:
        days = 7
    days = max(1, min(days, 60))

    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days - 1)

    chapter_qs = (
        Chapter.objects
        .filter(
            project__user=request.user,
            project__is_deleted=False,
            is_deleted=False,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        )
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(
            total_word_count=Sum('word_count'),
            total_count=Count('id'),
        )
    )
    aggregated = {item['day']: item for item in chapter_qs}

    data = []
    for offset in range(days):
        current_day = start_date + timedelta(days=offset)
        entry = aggregated.get(current_day, {'total_word_count': 0, 'total_count': 0})
        word_count = int(entry.get('total_word_count') or 0)
        if metric_type == 'revenue':
            value = round(word_count * REVENUE_PER_WORD, 2)
        elif metric_type == 'count':
            value = int(entry.get('total_count') or 0)
        else:  # reading 默认使用字数
            value = word_count

        data.append({
            'date': current_day.isoformat(),
            'value': value,
        })

    return Response(data)


def _map_chapter_status(status: str) -> str:
    if status in {'approved', 'published'}:
        return 'success'
    if status in {'pending_review', 'generating'}:
        return 'warning'
    return 'error'


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_generations(request):
    """Return latest chapter generation records for the current user."""
    try:
        limit = int(request.query_params.get('limit') or 10)
    except ValueError:
        limit = 10
    limit = max(1, min(limit, 50))

    chapters = (
        Chapter.objects
        .select_related('project')
        .filter(
            project__user=request.user,
            project__is_deleted=False,
            is_deleted=False,
        )
        .order_by('-created_at')[:limit]
    )

    payload = [
        {
            'id': chapter.id,
            'project': chapter.project.title,
            'chapter': f'第{chapter.chapter_number}章',
            'status': _map_chapter_status(chapter.status),
            'time': chapter.created_at.isoformat(),
            'word_count': chapter.word_count,
        }
        for chapter in chapters
    ]
    return Response(payload)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def stats_tasks_summary(request):
    """Provide queue summary and latest task snapshots for dashboard widgets."""
    project_ids = NovelProject.objects.filter(
        user=request.user,
        is_deleted=False,
    ).values_list('id', flat=True)
    chapter_ids = Chapter.objects.filter(
        project__user=request.user,
        project__is_deleted=False,
        is_deleted=False,
    ).values_list('id', flat=True)

    tasks = Task.objects.filter(
        Q(related_type='project', related_id__in=project_ids)
        | Q(related_type='chapter', related_id__in=chapter_ids)
        | Q(related_type__isnull=True)
        | Q(related_id__isnull=True)
    )

    total = tasks.count()
    status_counts = {
        item['status']: item['count']
        for item in tasks.values('status').annotate(count=Count('id'))
    }
    recent = [
        {
            'id': task.id,
            'task_type': task.task_type,
            'status': task.status,
            'created_at': task.created_at.isoformat(),
            'started_at': task.started_at.isoformat() if task.started_at else None,
        }
        for task in tasks.order_by('-created_at')[:10]
    ]

    return Response({
        'total': total,
        'status_counts': status_counts,
        'recent_tasks': recent,
    })
