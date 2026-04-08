from rest_framework import serializers

from apps.tasks.models import Task


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = (
            'id',
            'task_type',
            'status',
            'celery_task_id',
            'related_type',
            'related_id',
            'params',
            'result',
            'error_message',
            'retry_count',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'status',
            'celery_task_id',
            'result',
            'error_message',
            'retry_count',
            'created_at',
            'updated_at',
        )
