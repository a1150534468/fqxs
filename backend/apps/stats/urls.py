from django.urls import path

from apps.stats.views import (
    chapter_analytics,
    character_graph,
    dashboard_stats,
    recent_generations,
    stats_list,
    stats_overview,
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
    path('overview/', stats_overview, name='stats-overview'),
    path('chapter-analytics/', chapter_analytics, name='stats-chapter-analytics'),
    path('character-graph/', character_graph, name='stats-character-graph'),
]
