from datetime import datetime, time

from django.conf import settings as django_settings
from django.db.models import Q, Count, Case, When, IntegerField
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

import httpx

from apps.novels.models import (
    DraftSetting,
    NovelDraft,
    NovelProject,
    NovelSetting,
)
from apps.novels.serializers import (
    DraftSettingSerializer,
    ForeshadowItemSerializer,
    KnowledgeFactSerializer,
    NovelDraftSerializer,
    NovelProjectSerializer,
    NovelSettingSerializer,
    PlotArcPointSerializer,
    StorylineSerializer,
    StyleProfileSerializer,
)
from apps.novels.knowledge_graph import build_graph_from_settings
from apps.novels.services.assets import build_generation_context, initialize_project_assets
from apps.novels.services.workbench import build_workbench_context
from apps.chapters.models import Chapter
from celery_tasks.ai_tasks import generate_next_chapter_for_project

WIZARD_ORDER = [
    'worldview', 'characters', 'map', 'storyline', 'plot_arc',
    'opening',
]


def _clean_title_candidates(candidates):
    cleaned_titles = []
    seen_titles = set()

    for candidate in candidates or []:
        if candidate is None:
            continue
        title = str(candidate).strip()
        if not title or title in seen_titles:
            continue
        seen_titles.add(title)
        cleaned_titles.append(title)

    return cleaned_titles


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
            draft=Count(Case(When(status='draft', then=1), output_field=IntegerField())),
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
        project = self.get_object()
        project.auto_generation_enabled = True
        project.save(update_fields=['auto_generation_enabled', 'updated_at'])
        return Response({
            'message': 'Auto-generation started',
            'project_id': project.id,
            'auto_generation_enabled': True,
        })

    @action(detail=True, methods=['post'], url_path='stop-auto-generation')
    def stop_auto_generation(self, request, pk=None):
        project = self.get_object()
        project.auto_generation_enabled = False
        project.save(update_fields=['auto_generation_enabled', 'updated_at'])
        return Response({
            'message': 'Auto-generation stopped',
            'project_id': project.id,
            'auto_generation_enabled': False,
        })

    @action(detail=True, methods=['post'], url_path='generate-setting')
    def generate_setting(self, request, pk=None):
        """Generate a novel setting via FastAPI AI service with prior setting context."""
        project = self.get_object()
        setting_type = request.data.get('setting_type')
        context = request.data.get('context', '')

        if not setting_type:
            return Response(
                {'error': 'setting_type is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if setting_type not in WIZARD_ORDER:
            return Response(
                {'error': f'Invalid setting_type: {setting_type}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        idx = WIZARD_ORDER.index(setting_type)
        prior_rows = NovelSetting.objects.filter(
            project=project,
            setting_type__in=WIZARD_ORDER[:idx],
        ).order_by('order')
        prior = [
            {
                'setting_type': r.setting_type,
                'title': r.title or '',
                'content': r.content or '',
                'structured_data': r.structured_data or {},
            }
            for r in prior_rows
        ]

        payload = {
            'setting_type': setting_type,
            'book_title': project.title,
            'genre': project.genre or '',
            'context': context,
            'prior_settings': prior,
        }
        headers = {'Authorization': request.headers.get('Authorization', '')}

        try:
            resp = httpx.post(
                f"{django_settings.FASTAPI_URL}/api/ai/generate/setting",
                json=payload,
                headers=headers,
                timeout=90.0,
            )
        except httpx.HTTPError as e:
            return Response(
                {'error': f'AI service error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if resp.status_code != 200:
            return Response(
                {'error': f'AI service returned {resp.status_code}: {resp.text}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        data = resp.json()
        setting, _created = NovelSetting.objects.update_or_create(
            project=project,
            setting_type=setting_type,
            defaults={
                'title': data.get('title', ''),
                'content': data.get('content', ''),
                'structured_data': data.get('structured_data', {}),
                'ai_generated': True,
                'source': 'regenerated',
                'order': idx,
            },
        )
        return Response(NovelSettingSerializer(setting).data)

    @action(detail=True, methods=['post'], url_path='wizard-step')
    def wizard_step(self, request, pk=None):
        """Save a wizard step setting and advance wizard_step."""
        project = self.get_object()
        setting_type = request.data.get('setting_type')
        title = request.data.get('title', '')
        content = request.data.get('content', '')
        structured_data = request.data.get('structured_data', {})

        if not setting_type:
            return Response(
                {'error': 'setting_type is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if setting_type not in WIZARD_ORDER:
            return Response(
                {'error': f'Invalid setting_type: {setting_type}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        idx = WIZARD_ORDER.index(setting_type)
        setting, _created = NovelSetting.objects.update_or_create(
            project=project,
            setting_type=setting_type,
            defaults={
                'title': title,
                'content': content,
                'structured_data': structured_data,
                'source': 'wizard',
                'order': idx,
            },
        )

        new_step = min(idx + 1, 6)
        if new_step > project.wizard_step:
            project.wizard_step = new_step
            project.save(update_fields=['wizard_step', 'updated_at'])

        return Response(NovelSettingSerializer(setting).data)

    @action(detail=True, methods=['get'], url_path='knowledge-graph')
    def knowledge_graph(self, request, pk=None):
        """Aggregate novel settings into an ECharts-compatible knowledge graph."""
        project = self.get_object()
        settings_qs = NovelSetting.objects.filter(project=project).order_by('order')
        nodes, links = build_graph_from_settings(settings_qs)
        return Response({
            'project_id': project.id,
            'nodes': nodes,
            'links': links,
            'categories': [
                {'name': 'character'},
                {'name': 'region'},
                {'name': 'faction'},
                {'name': 'plot'},
            ],
        })

    @action(detail=True, methods=['get'], url_path='settings')
    def settings_list(self, request, pk=None):
        """List all settings for a novel project."""
        project = self.get_object()
        settings = NovelSetting.objects.filter(project=project)
        return Response(NovelSettingSerializer(settings, many=True).data)

    @action(detail=True, methods=['post'], url_path='complete-wizard')
    def complete_wizard(self, request, pk=None):
        """Mark the wizard as completed."""
        project = self.get_object()
        project.wizard_completed = True
        project.save(update_fields=['wizard_completed', 'updated_at'])
        initialize_project_assets(project)
        return Response(NovelProjectSerializer(project).data)

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

    @action(detail=True, methods=['get'], url_path='storylines')
    def storylines(self, request, pk=None):
        project = self.get_object()
        return Response(StorylineSerializer(project.storylines.all(), many=True).data)

    @action(detail=True, methods=['get'], url_path='plot-arcs')
    def plot_arcs(self, request, pk=None):
        project = self.get_object()
        return Response(PlotArcPointSerializer(project.plot_arc_points.all(), many=True).data)

    @action(detail=True, methods=['get'], url_path='knowledge-facts')
    def knowledge_facts(self, request, pk=None):
        project = self.get_object()
        return Response(KnowledgeFactSerializer(project.knowledge_facts.all(), many=True).data)

    @action(detail=True, methods=['get'], url_path='foreshadow-items')
    def foreshadow_items(self, request, pk=None):
        project = self.get_object()
        return Response(ForeshadowItemSerializer(project.foreshadow_items.all(), many=True).data)

    @action(detail=True, methods=['get'], url_path='style-profiles')
    def style_profiles(self, request, pk=None):
        project = self.get_object()
        return Response(StyleProfileSerializer(project.style_profiles.all(), many=True).data)


class WorkbenchContextView(APIView):
    """Aggregate the workbench payload for a single project."""

    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request, project_id):
        try:
            project = NovelProject.objects.get(
                id=project_id,
                user=request.user,
                is_deleted=False,
            )
        except NovelProject.DoesNotExist:
            return Response({'error': 'Project not found'}, status=status.HTTP_404_NOT_FOUND)

        return Response(build_workbench_context(project))


class GenerationContextView(APIView):
    """Return a compact context package for chapter generation."""

    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request, project_id):
        try:
            project = NovelProject.objects.get(
                id=project_id,
                user=request.user,
                is_deleted=False,
            )
        except NovelProject.DoesNotExist:
            return Response({'error': 'Project not found'}, status=status.HTTP_404_NOT_FOUND)

        chapter_number = request.query_params.get('chapter_number')
        try:
            target_chapter_number = int(chapter_number) if chapter_number else project.current_chapter + 1
        except (TypeError, ValueError):
            return Response({'error': 'chapter_number must be an integer'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(build_generation_context(project, target_chapter_number))


class DraftViewSet(viewsets.ModelViewSet):
    """CRUD + wizard actions for novel drafts (pre-project stage)."""
    serializer_class = NovelDraftSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return NovelDraft.objects.filter(user=self.request.user).order_by('-updated_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], url_path='save-step')
    def save_step(self, request, pk=None):
        """Save a single wizard step to DraftSetting."""
        draft = self.get_object()
        setting_type = request.data.get('setting_type')
        title = request.data.get('title', '')
        content = request.data.get('content', '')
        structured_data = request.data.get('structured_data', {})

        if not setting_type:
            return Response({'error': 'setting_type is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if setting_type not in WIZARD_ORDER:
            return Response({'error': f'Invalid setting_type: {setting_type}.'}, status=status.HTTP_400_BAD_REQUEST)

        idx = WIZARD_ORDER.index(setting_type)
        setting_obj, _created = DraftSetting.objects.update_or_create(
            draft=draft,
            setting_type=setting_type,
            defaults={
                'title': title,
                'content': content,
                'structured_data': structured_data,
                'source': 'wizard',
                'order': idx,
            },
        )

        new_step = min(idx + 1, 6)
        if new_step > draft.current_step:
            draft.current_step = new_step
            draft.save(update_fields=['current_step', 'updated_at'])

        return Response(DraftSettingSerializer(setting_obj).data)

    @action(detail=True, methods=['get'], url_path='settings')
    def settings_list(self, request, pk=None):
        """List all settings for a draft."""
        draft = self.get_object()
        settings_qs = DraftSetting.objects.filter(draft=draft)
        return Response(DraftSettingSerializer(settings_qs, many=True).data)

    @action(detail=True, methods=['post'], url_path='generate-titles')
    def generate_titles(self, request, pk=None):
        """Generate draft title candidates via the FastAPI AI service."""
        draft = self.get_object()
        if draft.is_completed:
            return Response({'error': 'Draft already completed.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            count = int(request.data.get('count', 3))
        except (TypeError, ValueError):
            count = 3
        count = max(3, min(count, 5))

        payload = {
            'inspiration': draft.inspiration,
            'genre': draft.genre,
            'style_preference': draft.style_preference,
            'count': count,
        }
        headers = {'Authorization': request.headers.get('Authorization', '')}

        try:
            resp = httpx.post(
                f"{django_settings.FASTAPI_URL.rstrip('/')}/api/ai/generate/titles",
                json=payload,
                headers=headers,
                timeout=90.0,
            )
        except httpx.HTTPError as e:
            return Response(
                {'error': f'AI service error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if resp.status_code != 200:
            return Response(
                {'error': f'AI service returned {resp.status_code}: {resp.text}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        data = resp.json()
        titles = _clean_title_candidates(data.get('titles', []))
        return Response({
            'titles': titles,
            'style_preference': draft.style_preference,
        })

    @action(detail=True, methods=['post'], url_path='complete')
    def complete(self, request, pk=None):
        """Complete the wizard: create NovelProject from draft, copy settings."""
        draft = self.get_object()
        if draft.is_completed:
            return Response({'error': 'Draft already completed.'}, status=status.HTTP_400_BAD_REQUEST)

        # Create the NovelProject
        project = NovelProject.objects.create(
            user=draft.user,
            title=draft.title or draft.inspiration[:100],
            genre=draft.genre,
            synopsis=draft.inspiration,
            wizard_completed=True,
            wizard_step=6,
        )

        # Copy DraftSettings -> NovelSettings
        draft_settings = DraftSetting.objects.filter(draft=draft)
        novel_settings = []
        for ds in draft_settings:
            novel_settings.append(NovelSetting(
                project=project,
                setting_type=ds.setting_type,
                title=ds.title,
                content=ds.content,
                structured_data=ds.structured_data,
                ai_generated=ds.ai_generated,
                source=ds.source,
                order=ds.order,
            ))
        if novel_settings:
            NovelSetting.objects.bulk_create(novel_settings)

        initialize_project_assets(project)

        # Mark draft completed
        draft.is_completed = True
        draft.converted_project = project
        draft.save(update_fields=['is_completed', 'converted_project', 'updated_at'])

        return Response(NovelProjectSerializer(project).data, status=status.HTTP_201_CREATED)
