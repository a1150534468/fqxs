from celery.result import AsyncResult
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.tasks.models import Task


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
