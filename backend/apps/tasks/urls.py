from django.urls import path

from apps.tasks.views import task_status

urlpatterns = [
    path('<str:task_id>/status/', task_status, name='task-status'),
]
