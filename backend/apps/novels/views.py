from datetime import datetime, time

from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.novels.models import NovelProject
from apps.novels.serializers import NovelProjectSerializer


class NovelProjectViewSet(viewsets.ModelViewSet):
    """CRUD API for novel projects scoped to the authenticated user."""

    serializer_class = NovelProjectSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def _parse_datetime_query_param(self, param_name, default_time):
        """Parse an ISO-8601 datetime/date query parameter into an aware datetime."""
        raw_value = self.request.query_params.get(param_name)
        if not raw_value:
            return None

        parsed_value = parse_datetime(raw_value)
        if parsed_value is None:
            parsed_date = parse_date(raw_value)
            if parsed_date is not None:
                parsed_value = datetime.combine(parsed_date, default_time)

        if parsed_value is None:
            raise ValidationError(
                {param_name: 'Use ISO 8601 datetime or YYYY-MM-DD format.'}
            )

        if timezone.is_naive(parsed_value):
            parsed_value = timezone.make_aware(
                parsed_value,
                timezone.get_current_timezone(),
            )

        return parsed_value

    def get_queryset(self):
        """Return filtered, non-deleted projects owned by the current user."""
        queryset = (
            NovelProject.objects.select_related('user', 'inspiration')
            .filter(user=self.request.user, is_deleted=False)
            .order_by('-created_at')
        )

        status_filter = self.request.query_params.get('status', '')
        statuses = [status.strip() for status in status_filter.split(',') if status.strip()]
        if statuses:
            queryset = queryset.filter(status__in=statuses)

        type_filter = self.request.query_params.get('type') or self.request.query_params.get('genre', '')
        genres = [genre.strip() for genre in type_filter.split(',') if genre.strip()]
        if genres:
            genre_query = Q()
            for genre in genres:
                genre_query |= Q(genre__iexact=genre)
            queryset = queryset.filter(genre_query)

        keyword = self.request.query_params.get('search', '').strip()
        if keyword:
            queryset = queryset.filter(
                Q(title__icontains=keyword)
                | Q(genre__icontains=keyword)
                | Q(synopsis__icontains=keyword)
                | Q(outline__icontains=keyword)
            )

        created_after = self._parse_datetime_query_param('created_after', time.min)
        if created_after is None:
            created_after = self._parse_datetime_query_param('created_from', time.min)

        created_before = self._parse_datetime_query_param('created_before', time.max)
        if created_before is None:
            created_before = self._parse_datetime_query_param('created_to', time.max)

        if created_after and created_before and created_after > created_before:
            raise ValidationError(
                {'created_after': 'created_after must be earlier than created_before.'}
            )

        if created_after:
            queryset = queryset.filter(created_at__gte=created_after)
        if created_before:
            queryset = queryset.filter(created_at__lte=created_before)

        return queryset

    def perform_create(self, serializer):
        """Create a project for the authenticated user."""
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        """Soft delete the project instead of removing the database row."""
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted', 'updated_at'])
