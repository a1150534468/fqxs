from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.llm_providers.models import LLMProvider
from apps.llm_providers.serializers import LLMProviderSerializer


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
