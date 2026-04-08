from django.utils.dateparse import parse_date

from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

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
