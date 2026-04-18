from datetime import timedelta

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.dateparse import parse_date

from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.chapters.models import Chapter
from apps.novels.models import NovelProject
from apps.tasks.querysets import scoped_task_queryset_for_user
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
    """Realtime dashboard data aggregated from the current user's projects."""
    start_date = parse_date((request.query_params.get('start_date') or '').strip())
    end_date = parse_date((request.query_params.get('end_date') or '').strip())

    chapters_qs = Chapter.objects.filter(
        project__user=request.user,
        project__is_deleted=False,
        is_deleted=False,
    )
    if start_date:
        chapters_qs = chapters_qs.filter(created_at__date__gte=start_date)
    if end_date:
        chapters_qs = chapters_qs.filter(created_at__date__lte=end_date)

    chapters = list(chapters_qs.select_related('project'))
    tasks_qs = scoped_task_queryset_for_user(request.user)
    active_projects_qs = NovelProject.objects.filter(
        user=request.user,
        is_deleted=False,
        status='active',
    )

    total_chapters = len(chapters)
    success_count = sum(1 for chapter in chapters if chapter.status in {'draft', 'published'})
    total_words = sum(chapter.word_count or 0 for chapter in chapters)
    avg_word_count = round(total_words / total_chapters) if total_chapters else 0

    total_api_calls = 0
    total_tokens = 0
    estimated_cost = 0.0
    latency_values = []
    warning_count = 0
    risky_count = 0

    for chapter in chapters:
        generation_meta = chapter.generation_meta or {}
        total_api_calls += int(generation_meta.get('api_calls') or (1 if generation_meta else 0))

        input_tokens = int(generation_meta.get('input_tokens') or 0)
        output_tokens = int(generation_meta.get('output_tokens') or 0)
        chapter_tokens = input_tokens + output_tokens
        total_tokens += chapter_tokens

        if generation_meta.get('latency_ms'):
            latency_values.append(float(generation_meta['latency_ms']) / 1000)

        chapter_cost = generation_meta.get('estimated_cost')
        if chapter_cost is None:
            chapter_cost = round((chapter_tokens / 1000) * 0.02, 4)
        estimated_cost += float(chapter_cost or 0)

        consistency_status = chapter.consistency_status or {}
        if consistency_status.get('status') == 'warning':
            warning_count += 1
        if consistency_status.get('risks'):
            risky_count += 1

    success_rate = round((success_count / total_chapters) * 100, 2) if total_chapters else 0
    avg_generation_time = (
        round(sum(latency_values) / len(latency_values), 2)
        if latency_values
        else 0
    )
    published_count = sum(1 for chapter in chapters if chapter.status == 'published')

    response_payload = {
        'generation': {
            'total_chapters': total_chapters,
            'success_rate': success_rate,
            'avg_word_count': avg_word_count,
        },
        'cost': {
            'total_api_calls': total_api_calls,
            'total_tokens': total_tokens,
            'estimated_cost': round(estimated_cost, 4),
        },
        'performance': {
            'avg_generation_time': avg_generation_time,
            'current_queue': tasks_qs.filter(status__in=['pending', 'running', 'retry']).count(),
        },
        'novels': {
            'active_count': active_projects_qs.count(),
            'total_chapters_published': published_count,
        },
        'quality': {
            'warning_count': warning_count,
            'chapters_with_risk': risky_count,
            'consistency_ok_rate': round(
                ((total_chapters - warning_count) / total_chapters) * 100,
                2,
            ) if total_chapters else 0,
        },
    }

    return Response(response_payload)


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
    if status in {'draft', 'published'}:
        return 'success'
    if status in {'generating'}:
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
    tasks = scoped_task_queryset_for_user(request.user)

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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def stats_overview(request):
    """Global overview stats: total books, chapters, words, status breakdown."""
    user = request.user
    projects = NovelProject.objects.filter(user=user, is_deleted=False)
    chapters = Chapter.objects.filter(
        project__user=user, project__is_deleted=False, is_deleted=False,
    )

    total_books = projects.count()
    total_chapters = chapters.count()
    total_words = chapters.aggregate(s=Sum('word_count'))['s'] or 0

    status_counts = {}
    for item in projects.values('status').annotate(count=Count('id')):
        status_counts[item['status']] = item['count']

    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_new_chapters = chapters.filter(created_at__gte=today_start).count()

    return Response({
        'total_books': total_books,
        'total_chapters': total_chapters,
        'total_words': total_words,
        'status_counts': status_counts,
        'today_new_chapters': today_new_chapters,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chapter_analytics(request):
    """Per-chapter analytics with optional project_id filter."""
    user = request.user
    qs = Chapter.objects.select_related('project').filter(
        project__user=user, project__is_deleted=False, is_deleted=False,
    )

    project_id = request.query_params.get('project_id')
    if project_id:
        qs = qs.filter(project_id=project_id)

    chapters_data = []
    for ch in qs.order_by('project', 'chapter_number'):
        chapters_data.append({
            'id': ch.id,
            'chapter_number': ch.chapter_number,
            'title': ch.title,
            'word_count': ch.word_count,
            'read_count': ch.read_count,
            'status': ch.status,
            'project_title': ch.project.title,
            'created_at': ch.created_at.isoformat(),
        })

    total_words = sum(c['word_count'] for c in chapters_data)
    total_chapters = len(chapters_data)
    avg_words = round(total_words / total_chapters) if total_chapters else 0
    published_count = sum(1 for c in chapters_data if c['status'] == 'published')
    publish_rate = round(published_count / total_chapters * 100, 1) if total_chapters else 0

    return Response({
        'chapters': chapters_data,
        'summary': {
            'total_words': total_words,
            'total_chapters': total_chapters,
            'avg_words': avg_words,
            'published_count': published_count,
            'publish_rate': publish_rate,
        },
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def character_graph(request):
    """Return character relationship graph nodes/links from NovelSetting."""
    project_id = request.query_params.get('project_id')
    if not project_id:
        return Response({'error': 'project_id is required.'}, status=400)

    try:
        setting = NovelSetting.objects.get(
            project_id=project_id,
            setting_type='characters',
            project__user=request.user,
            project__is_deleted=False,
        )
        data = setting.structured_data or {}
        nodes = data.get('nodes', [])
        links = data.get('links', [])
        if nodes or links:
            return Response({'nodes': nodes, 'links': links})
    except NovelSetting.DoesNotExist:
        pass

    # Return mock data when no real data exists
    return Response({
        'nodes': [
            {'name': '主角', 'category': 'protagonist', 'symbolSize': 60, 'value': '故事核心人物'},
            {'name': '师父', 'category': 'mentor', 'symbolSize': 40, 'value': '引导者'},
            {'name': '反派', 'category': 'antagonist', 'symbolSize': 50, 'value': '主要对手'},
        ],
        'links': [
            {'source': '主角', 'target': '师父', 'value': '师徒'},
            {'source': '主角', 'target': '反派', 'value': '宿敌'},
        ],
    })
