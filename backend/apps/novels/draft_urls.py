from rest_framework.routers import SimpleRouter

from apps.novels.views import DraftViewSet

router = SimpleRouter()
router.register('', DraftViewSet, basename='draft')

urlpatterns = router.urls
