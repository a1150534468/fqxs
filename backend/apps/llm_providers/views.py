import logging

import requests
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.llm_providers.models import LLMProvider
from apps.llm_providers.serializers import LLMProviderSerializer

logger = logging.getLogger('apps')


class LLMProviderViewSet(viewsets.ModelViewSet):
    serializer_class = LLMProviderSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return (
            LLMProvider.objects
            .filter(user=self.request.user)
            .order_by('-priority', 'created_at')
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """Test LLM provider connection."""
        provider = self.get_object()

        try:
            response = requests.post(
                f"{provider.api_url.rstrip('/')}/chat/completions",
                headers={
                    'Authorization': f'Bearer {provider.api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': 'gpt-3.5-turbo',
                    'messages': [{'role': 'user', 'content': 'test'}],
                    'max_tokens': 5,
                },
                timeout=10,
            )

            if response.status_code == 200:
                logger.info(f'LLM provider {provider.name} connection test successful')
                return Response({
                    'status': 'success',
                    'message': 'Connection test successful',
                })
            else:
                logger.warning(f'LLM provider {provider.name} connection test failed: {response.status_code}')
                return Response({
                    'status': 'error',
                    'message': f'Connection failed with status {response.status_code}',
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f'LLM provider {provider.name} connection test error: {e}')
            return Response({
                'status': 'error',
                'message': str(e),
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def set_priority(self, request, pk=None):
        """Set provider priority."""
        provider = self.get_object()
        new_priority = request.data.get('priority')

        if new_priority is None:
            return Response({
                'error': 'priority field is required',
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_priority = int(new_priority)
            if not (0 <= new_priority <= 100):
                raise ValueError('Priority must be between 0 and 100')
        except (ValueError, TypeError) as e:
            return Response({
                'error': str(e),
            }, status=status.HTTP_400_BAD_REQUEST)

        provider.priority = new_priority
        provider.save()

        logger.info(f'LLM provider {provider.name} priority set to {new_priority}')

        return Response({
            'status': 'success',
            'priority': new_priority,
        })
