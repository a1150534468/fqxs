from rest_framework.routers import SimpleRouter

from apps.novels.views import NovelProjectViewSet

router = SimpleRouter()
router.register('', NovelProjectViewSet, basename='novelproject')

urlpatterns = router.urls
