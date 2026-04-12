from django.urls import path

from apps.stats.views import (
    dashboard_stats,
    recent_generations,
    stats_list,
    stats_tasks_summary,
    stats_trend,
)

app_name = 'stats'

urlpatterns = [
    path('', stats_list, name='stats-list'),
    path('dashboard/', dashboard_stats, name='stats-dashboard'),
    path('trend/', stats_trend, name='stats-trend'),
    path('recent-generations/', recent_generations, name='stats-recent-generations'),
    path('tasks-summary/', stats_tasks_summary, name='stats-tasks-summary'),
]
