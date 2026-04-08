from celery.result import AsyncResult
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.tasks.models import Task
from apps.tasks.serializers import TaskSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def task_status(request, task_id):
    """Query Celery task state and cached result by task id."""
    async_result = AsyncResult(task_id)
    task_record = Task.objects.filter(celery_task_id=task_id).order_by('-id').first()

    response_payload = {
        'task_id': task_id,
        'status': async_result.status,
        'result': async_result.result if async_result.ready() else None,
    }

    if task_record is not None:
        response_payload['task_record'] = {
            'id': task_record.id,
            'task_type': task_record.task_type,
            'status': task_record.status,
            'retry_count': task_record.retry_count,
            'error_message': task_record.error_message,
            'created_at': task_record.created_at,
            'updated_at': task_record.updated_at,
        }

    return Response(response_payload)


class TaskPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def task_list(request):
    queryset = Task.objects.all().order_by('-created_at')

    task_type = request.query_params.get('task_type', '').strip()
    if task_type:
        queryset = queryset.filter(task_type=task_type)

    status_filter = request.query_params.get('status', '').strip()
    if status_filter:
        queryset = queryset.filter(status=status_filter)

    paginator = TaskPagination()
    page = paginator.paginate_queryset(queryset, request)
    serializer = TaskSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)
