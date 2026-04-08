from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.llm_providers.views import LLMProviderViewSet

router = SimpleRouter()
router.register('', LLMProviderViewSet, basename='llm-provider')

app_name = 'llm_providers'

urlpatterns = router.urls
