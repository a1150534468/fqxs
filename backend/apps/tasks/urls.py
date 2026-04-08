from django.urls import path

from apps.tasks.views import task_list, task_status

urlpatterns = [
    path('', task_list, name='task-list'),
    path('<str:task_id>/status/', task_status, name='task-status'),
]
