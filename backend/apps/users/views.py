from django.db.models import Sum
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.chapters.models import Chapter
from apps.novels.models import NovelProject
from apps.users.serializers import LoginSerializer


class LoginView(TokenObtainPairView):
    """JWT login endpoint."""

    permission_classes = (AllowAny,)
    serializer_class = LoginSerializer


class RefreshTokenView(TokenRefreshView):
    """JWT refresh endpoint."""

    permission_classes = (AllowAny,)


class UserStatsView(APIView):
    """Return aggregate project/chapter statistics for the authenticated user."""

    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        """Get project count, chapter count, and total word count."""
        project_queryset = NovelProject.objects.filter(user=request.user, is_deleted=False)
        chapter_queryset = Chapter.objects.filter(project__in=project_queryset)

        stats = chapter_queryset.aggregate(total_word_count=Sum('word_count'))

        return Response(
            {
                'project_count': project_queryset.count(),
                'chapter_count': chapter_queryset.count(),
                'total_word_count': stats['total_word_count'] or 0,
            }
        )
