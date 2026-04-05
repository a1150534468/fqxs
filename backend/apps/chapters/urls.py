from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.chapters.views import ChapterGenerateAsyncView, ChapterViewSet

router = SimpleRouter()
router.register('', ChapterViewSet, basename='chapter')

urlpatterns = [
    path('generate-async/', ChapterGenerateAsyncView.as_view(), name='chapter-generate-async'),
]
urlpatterns += router.urls
