from datetime import datetime, time

from django.db.models import Q, Count, Case, When, IntegerField
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.novels.models import NovelProject
from apps.novels.serializers import NovelProjectSerializer
from apps.chapters.models import Chapter
from celery_tasks.ai_tasks import generate_next_chapter_for_project


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

    @action(detail=True, methods=['get'], url_path='generation-status')
    def generation_status(self, request, pk=None):
        """Get chapter generation progress for a project."""
        project = self.get_object()

        chapters = Chapter.objects.filter(project=project, is_deleted=False)
        total_chapters = chapters.count()

        status_counts = chapters.aggregate(
            generating=Count(Case(When(status='generating', then=1), output_field=IntegerField())),
            pending_review=Count(Case(When(status='pending_review', then=1), output_field=IntegerField())),
            approved=Count(Case(When(status='approved', then=1), output_field=IntegerField())),
            published=Count(Case(When(status='published', then=1), output_field=IntegerField())),
            failed=Count(Case(When(status='failed', then=1), output_field=IntegerField())),
        )

        return Response({
            'project_id': project.id,
            'project_title': project.title,
            'target_chapters': project.target_chapters,
            'current_chapter': project.current_chapter,
            'total_chapters': total_chapters,
            'status_breakdown': status_counts,
            'auto_generation_enabled': project.auto_generation_enabled,
            'generation_schedule': project.generation_schedule,
            'next_generation_time': project.next_generation_time,
            'last_update_at': project.last_update_at,
        })

    @action(detail=True, methods=['post'], url_path='start-auto-generation')
    def start_auto_generation(self, request, pk=None):
        """Enable automatic chapter generation for a project."""
        project = self.get_object()

        schedule = request.data.get('generation_schedule', 'daily')
        if schedule not in ['daily', 'every_2_days', 'weekly']:
            return Response(
                {'error': 'Invalid generation_schedule. Must be daily, every_2_days, or weekly.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        project.auto_generation_enabled = True
        project.generation_schedule = schedule

        # Calculate next generation time
        now = timezone.now()
        if schedule == 'daily':
            project.next_generation_time = now.replace(hour=8, minute=0, second=0, microsecond=0)
            if project.next_generation_time <= now:
                project.next_generation_time += timezone.timedelta(days=1)
        elif schedule == 'every_2_days':
            project.next_generation_time = now.replace(hour=8, minute=0, second=0, microsecond=0) + timezone.timedelta(days=2)
        else:  # weekly
            project.next_generation_time = now.replace(hour=8, minute=0, second=0, microsecond=0) + timezone.timedelta(days=7)

        project.save(update_fields=['auto_generation_enabled', 'generation_schedule', 'next_generation_time', 'updated_at'])

        return Response({
            'message': 'Auto-generation started successfully',
            'project_id': project.id,
            'auto_generation_enabled': project.auto_generation_enabled,
            'generation_schedule': project.generation_schedule,
            'next_generation_time': project.next_generation_time,
        })

    @action(detail=True, methods=['post'], url_path='stop-auto-generation')
    def stop_auto_generation(self, request, pk=None):
        """Disable automatic chapter generation for a project."""
        project = self.get_object()

        project.auto_generation_enabled = False
        project.next_generation_time = None
        project.save(update_fields=['auto_generation_enabled', 'next_generation_time', 'updated_at'])

        return Response({
            'message': 'Auto-generation stopped successfully',
            'project_id': project.id,
            'auto_generation_enabled': project.auto_generation_enabled,
        })

    @action(detail=True, methods=['post'], url_path='generate-next-chapter')
    def generate_next_chapter(self, request, pk=None):
        """Manually trigger generation of the next chapter."""
        project = self.get_object()

        if project.current_chapter >= project.target_chapters:
            return Response(
                {'error': 'Project has reached target chapters'},
                status=status.HTTP_400_BAD_REQUEST
            )

        next_chapter_number = project.current_chapter + 1
        chapter_title = request.data.get('chapter_title', f"第{next_chapter_number}章")

        # Trigger async generation with force=True for manual trigger
        result = generate_next_chapter_for_project.delay(project.id, force=True)

        return Response({
            'message': 'Chapter generation started',
            'project_id': project.id,
            'chapter_number': next_chapter_number,
            'chapter_title': chapter_title,
            'task_id': result.id,
        }, status=status.HTTP_202_ACCEPTED)
