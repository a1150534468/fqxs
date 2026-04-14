from datetime import datetime, time

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.chapters.models import Chapter
from apps.chapters.serializers import ChapterSerializer
from apps.novels.models import NovelProject
from apps.tasks.models import Task
from celery_tasks.ai_tasks import generate_chapter_async
from celery_tasks.publish_tasks import publish_chapter_async

PUBLISH_STATUS_TO_INTERNAL = {
    'draft': ('generating', 'draft'),
    'published': ('published',),
    'failed': ('failed',),
}


class ChapterViewSet(viewsets.ModelViewSet):
    """CRUD API for chapters scoped to the authenticated user's projects."""

    serializer_class = ChapterSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def _parse_datetime_query_param(self, param_name, default_time):
        """Parse datetime/date query values into timezone-aware datetimes."""
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
        """Return filtered chapters owned by the current authenticated user."""
        queryset = (
            Chapter.objects.select_related('project', 'project__user', 'llm_provider')
            .filter(
                project__user=self.request.user,
                project__is_deleted=False,
                is_deleted=False,
            )
            .order_by('-created_at')
        )

        project_id = self.request.query_params.get('project_id', '').strip()
        if project_id:
            if not project_id.isdigit():
                raise ValidationError({'project_id': 'project_id must be a positive integer.'})
            queryset = queryset.filter(project_id=int(project_id))

        publish_status_filter = self.request.query_params.get('publish_status', '').strip()
        if publish_status_filter:
            publish_statuses = [
                value.strip() for value in publish_status_filter.split(',') if value.strip()
            ]
            unknown_statuses = [
                status for status in publish_statuses if status not in PUBLISH_STATUS_TO_INTERNAL
            ]
            if unknown_statuses:
                raise ValidationError(
                    {'publish_status': f'Unsupported values: {", ".join(unknown_statuses)}.'}
                )

            internal_statuses = []
            for status in publish_statuses:
                internal_statuses.extend(PUBLISH_STATUS_TO_INTERNAL[status])
            queryset = queryset.filter(status__in=internal_statuses)

        title_keyword = (
            self.request.query_params.get('search')
            or self.request.query_params.get('title')
            or ''
        ).strip()
        if title_keyword:
            queryset = queryset.filter(Q(title__icontains=title_keyword))

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

    def perform_destroy(self, instance):
        """Soft delete the chapter instead of removing the row."""
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted', 'updated_at'])

    @action(detail=True, methods=['post'], url_path='publish')
    def publish(self, request, pk=None):
        """Publish a chapter to Tomato Novel platform."""
        chapter = self.get_object()

        # Check if chapter is in draft status (ready to publish)
        if chapter.status != 'draft':
            return Response(
                {'error': 'Chapter must be in draft status before publishing. Current status: ' + chapter.status},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create task record
        task_record = Task.objects.create(
            task_type='publish_chapter',
            related_type='chapter',
            related_id=chapter.id,
            status='pending',
            params={
                'chapter_id': chapter.id,
                'project_id': chapter.project.id,
            },
        )

        # Trigger async publish task
        async_result = publish_chapter_async.delay(
            chapter.id,
            task_record_id=task_record.id,
        )
        task_record.celery_task_id = async_result.id
        task_record.save(update_fields=['celery_task_id', 'updated_at'])

        return Response(
            {
                'task_id': async_result.id,
                'task_record_id': task_record.id,
                'status': task_record.status,
                'message': 'Chapter publishing task started',
            },
            status=status.HTTP_202_ACCEPTED,
        )


class ChapterGenerateAsyncRequestSerializer(serializers.Serializer):
    """Payload schema for async chapter generation endpoint."""

    project_id = serializers.IntegerField(min_value=1)
    chapter_number = serializers.IntegerField(min_value=1)
    chapter_title = serializers.CharField(max_length=200)


class ChapterGenerateAsyncView(APIView):
    """Trigger async chapter generation task via Celery."""

    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        serializer = ChapterGenerateAsyncRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        project_id = serializer.validated_data['project_id']
        chapter_number = serializer.validated_data['chapter_number']
        chapter_title = serializer.validated_data['chapter_title']

        project = get_object_or_404(
            NovelProject,
            id=project_id,
            user=request.user,
            is_deleted=False,
        )

        task_record = Task.objects.create(
            task_type='generate_chapter',
            related_type='project',
            related_id=project.id,
            status='pending',
            params={
                'project_id': project.id,
                'chapter_number': chapter_number,
                'chapter_title': chapter_title,
            },
        )

        async_result = generate_chapter_async.delay(
            project.id,
            chapter_number,
            chapter_title,
            task_record_id=task_record.id,
        )
        task_record.celery_task_id = async_result.id
        task_record.save(update_fields=['celery_task_id', 'updated_at'])

        return Response(
            {
                'task_id': async_result.id,
                'task_record_id': task_record.id,
                'status': task_record.status,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class GenerateFromWSView(APIView):
    """Called by FastAPI WebSocket handler to save a generated chapter as draft."""
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        from django.db import transaction
        project_id = request.data.get('project_id')
        content = request.data.get('content', '')
        word_count = request.data.get('word_count', 0)

        if not project_id:
            return Response({'error': 'project_id required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                project = NovelProject.objects.select_for_update().get(
                    id=project_id, user=request.user, is_deleted=False
                )
                next_number = project.chapters.filter(is_deleted=False).count() + 1
                chapter, _ = Chapter.objects.update_or_create(
                    project=project,
                    chapter_number=next_number,
                    defaults={
                        'title': f'第{next_number}章',
                        'raw_content': content,
                        'final_content': content,
                        'word_count': word_count,
                        'status': 'draft',
                        'generated_at': timezone.now(),
                        'is_deleted': False,
                    },
                )
                project.current_chapter = next_number
                project.last_update_at = timezone.now()
                project.save(update_fields=['current_chapter', 'last_update_at', 'updated_at'])
        except NovelProject.DoesNotExist:
            return Response({'error': 'Project not found'}, status=status.HTTP_404_NOT_FOUND)

        return Response(ChapterSerializer(chapter).data, status=status.HTTP_201_CREATED)
