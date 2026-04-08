from django.urls import path

from apps.stats.views import dashboard_stats, stats_list

app_name = 'stats'

urlpatterns = [
    path('', stats_list, name='stats-list'),
    path('dashboard/', dashboard_stats, name='stats-dashboard'),
]
