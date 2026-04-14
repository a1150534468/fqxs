import logging

import requests
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chapters.models import Chapter
from apps.inspirations.models import Inspiration
from apps.inspirations.serializers import (
    GenerateInspirationFromTrendsSerializer,
    InspirationBulkMarkUsedSerializer,
    InspirationSerializer,
    StartProjectFromInspirationSerializer,
    GenerateCustomInspirationSerializer,
)
from apps.novels.models import NovelProject

logger = logging.getLogger(__name__)


class InspirationListCreateView(generics.ListCreateAPIView):
    """List inspirations or create a new inspiration."""

    queryset = Inspiration.objects.all().order_by('-created_at')
    serializer_class = InspirationSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        """Filter inspirations with optional query parameters."""
        queryset = super().get_queryset()

        # Filter by is_used
        is_used = self.request.query_params.get('is_used')
        if is_used is not None:
            queryset = queryset.filter(is_used=is_used.lower() == 'true')

        # Filter by rank_type
        rank_type = self.request.query_params.get('rank_type')
        if rank_type:
            queryset = queryset.filter(rank_type=rank_type)

        # Search by title or synopsis
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(synopsis__icontains=search)
            )

        return queryset


class InspirationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete an inspiration."""

    queryset = Inspiration.objects.all()
    serializer_class = InspirationSerializer
    permission_classes = (IsAuthenticated,)


class InspirationBulkMarkUsedView(APIView):
    """Mark multiple inspirations as used or unused in one request."""

    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        """Bulk update `is_used` for the provided inspiration IDs."""
        serializer = InspirationBulkMarkUsedSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ids = serializer.validated_data['ids']
        is_used = serializer.validated_data['is_used']

        existing_ids = set(Inspiration.objects.filter(id__in=ids).values_list('id', flat=True))
        missing_ids = sorted(set(ids) - existing_ids)

        updated_count = 0
        if existing_ids:
            updated_count = Inspiration.objects.filter(id__in=existing_ids).update(is_used=is_used)

        return Response(
            {
                'requested_count': len(ids),
                'updated_count': updated_count,
                'is_used': is_used,
                'missing_ids': missing_ids,
            }
        )


class GenerateInspirationFromTrendsView(APIView):
    """Generate novel inspirations from trending books using AI."""

    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        """Call FastAPI to generate inspirations from trending books."""
        # Get top trending books from database (未使用的，按热度排序)
        trending_inspirations = Inspiration.objects.filter(is_used=False).order_by('-hot_score')[:20]

        if not trending_inspirations.exists():
            return Response(
                {'error': '没有可用的热门书数据，请先运行爬虫采集数据'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Convert to trending books format
        trending_books = [
            {
                'title': insp.title,
                'synopsis': insp.synopsis or '',
                'tags': insp.tags or [],
                'hot_score': float(insp.hot_score),
            }
            for insp in trending_inspirations
        ]

        # Get optional genre preference from request
        genre_preference = request.data.get('genre_preference', '')

        payload = {
            'trending_books': trending_books,
            'genre_preference': genre_preference,
        }

        try:
            # Get JWT token from request
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')

            # Call FastAPI service
            response = requests.post(
                f"{settings.FASTAPI_URL.rstrip('/')}/api/ai/generate/inspiration",
                json=payload,
                headers={'Authorization': auth_header} if auth_header else {},
                timeout=120,
            )
            response.raise_for_status()
            result = response.json()

            # Save generated inspirations to database
            created_count = 0
            for insp_data in result.get('inspirations', []):
                Inspiration.objects.create(
                    title=insp_data['title'],
                    synopsis=insp_data['synopsis'],
                    tags=insp_data.get('tags', []),
                    hot_score=insp_data.get('estimated_popularity', 0),
                    rank_type='ai_generated',
                    is_used=False,
                )
                created_count += 1

            logger.info(f"Generated and saved {created_count} inspirations for user {request.user.id}")

            return Response({
                'created_count': created_count,
                'inspirations': result.get('inspirations', []),
            }, status=status.HTTP_200_OK)

        except requests.RequestException as e:
            logger.error(f"Failed to generate inspirations: {e}", exc_info=True)
            return Response(
                {'error': 'Failed to generate inspirations', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class StartProjectFromInspirationView(APIView):
    """Start a complete novel project from an inspiration."""

    permission_classes = (IsAuthenticated,)

    def post(self, request, pk, *args, **kwargs):
        """Create project, generate outline, and create first chapter."""
        try:
            inspiration = Inspiration.objects.get(id=pk)
        except Inspiration.DoesNotExist:
            return Response(
                {'error': 'Inspiration not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = StartProjectFromInspirationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        title = serializer.validated_data.get('title') or inspiration.title
        genre = serializer.validated_data.get('genre') or (inspiration.tags[0] if inspiration.tags else '都市')
        target_chapters = serializer.validated_data['target_chapters']
        first_chapter_title = serializer.validated_data['first_chapter_title']

        try:
            with transaction.atomic():
                # Create novel project
                project = NovelProject.objects.create(
                    user=request.user,
                    inspiration=inspiration,
                    title=title,
                    genre=genre,
                    synopsis=inspiration.synopsis or '',
                    target_chapters=target_chapters,
                    status='active',
                )

                # Get JWT token
                auth_header = request.META.get('HTTP_AUTHORIZATION', '')

                # Generate outline via FastAPI
                outline_response = requests.post(
                    f"{settings.FASTAPI_URL.rstrip('/')}/api/ai/generate/outline",
                    json={
                        'inspiration_id': inspiration.id,
                        'genre': genre,
                        'target_chapters': target_chapters,
                    },
                    headers={'Authorization': auth_header} if auth_header else {},
                    timeout=120,
                )
                outline_response.raise_for_status()
                outline_data = outline_response.json()

                # Update project with outline
                project.outline = outline_data.get('outline', '')
                project.save(update_fields=['outline'])

                # Generate first chapter
                chapter_response = requests.post(
                    f"{settings.FASTAPI_URL.rstrip('/')}/api/ai/generate/chapter",
                    json={
                        'project_id': project.id,
                        'chapter_number': 1,
                        'chapter_title': first_chapter_title,
                        'outline_context': project.outline[:500],
                    },
                    headers={'Authorization': auth_header} if auth_header else {},
                    timeout=300,
                )
                chapter_response.raise_for_status()
                chapter_data = chapter_response.json()

                # Create chapter record
                chapter = Chapter.objects.create(
                    project=project,
                    chapter_number=1,
                    title=first_chapter_title,
                    raw_content=chapter_data.get('content', ''),
                    final_content=chapter_data.get('content', ''),
                    word_count=chapter_data.get('word_count', 0),
                    status='draft',
                    generated_at=timezone.now(),
                )

                # Update project current chapter
                project.current_chapter = 1
                project.last_update_at = timezone.now()
                project.save(update_fields=['current_chapter', 'last_update_at'])

                # Mark inspiration as used
                inspiration.is_used = True
                inspiration.save(update_fields=['is_used'])

                logger.info(
                    f"Started project {project.id} from inspiration {inspiration.id} "
                    f"for user {request.user.id}"
                )

                return Response(
                    {
                        'project_id': project.id,
                        'title': project.title,
                        'genre': project.genre,
                        'outline': project.outline,
                        'first_chapter': {
                            'id': chapter.id,
                            'title': chapter.title,
                            'word_count': chapter.word_count,
                            'status': chapter.status,
                        },
                    },
                    status=status.HTTP_201_CREATED,
                )

        except requests.RequestException as e:
            logger.error(f"Failed to generate content: {e}", exc_info=True)
            return Response(
                {'error': 'Failed to generate content', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as e:
            logger.error(f"Failed to start project: {e}", exc_info=True)
            return Response(
                {'error': 'Failed to start project', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GenerateCustomInspirationView(APIView):
    """Generate custom inspirations based on user prompt."""

    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        """Call FastAPI to generate custom inspirations."""
        serializer = GenerateCustomInspirationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        custom_prompt = serializer.validated_data['custom_prompt']
        count = serializer.validated_data['count']

        payload = {
            'custom_prompt': custom_prompt,
            'count': count,
        }

        try:
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')

            response = requests.post(
                f"{settings.FASTAPI_URL.rstrip('/')}/api/ai/generate/custom-inspiration",
                json=payload,
                headers={'Authorization': auth_header} if auth_header else {},
                timeout=120,
            )
            response.raise_for_status()
            result = response.json()

            # Save generated inspirations to database
            created_count = 0
            for insp_data in result.get('inspirations', []):
                Inspiration.objects.create(
                    title=insp_data['title'],
                    synopsis=insp_data['synopsis'],
                    tags=insp_data.get('tags', []),
                    hot_score=insp_data.get('estimated_popularity', 0),
                    rank_type='custom_generated',
                    source_url='',
                    is_used=False,
                )
                created_count += 1

            logger.info(f"Generated {created_count} custom inspirations for user {request.user.id}")

            return Response({
                'created_count': created_count,
                'inspirations': result.get('inspirations', []),
            }, status=status.HTTP_200_OK)

        except requests.RequestException as e:
            logger.error(f"Failed to generate custom inspirations: {e}", exc_info=True)
            return Response(
                {'error': 'Failed to generate custom inspirations', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
