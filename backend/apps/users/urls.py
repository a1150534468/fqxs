from django.urls import path

from apps.users.views import LoginView, RefreshTokenView, UserStatsView

urlpatterns = [
    path('login/', LoginView.as_view(), name='user-login'),
    path('refresh/', RefreshTokenView.as_view(), name='token-refresh'),
    path('me/stats/', UserStatsView.as_view(), name='user-stats'),
]
