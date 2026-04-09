from django.urls import path

from apps.inspirations.views import (
    GenerateInspirationFromTrendsView,
    InspirationBulkMarkUsedView,
    InspirationDetailView,
    InspirationListCreateView,
    StartProjectFromInspirationView,
    GenerateCustomInspirationView,
)

urlpatterns = [
    path('', InspirationListCreateView.as_view(), name='inspiration-list-create'),
    path('bulk-mark-used/', InspirationBulkMarkUsedView.as_view(), name='inspiration-bulk-mark-used'),
    path('generate-from-trends/', GenerateInspirationFromTrendsView.as_view(), name='inspiration-generate-from-trends'),
    path('generate-custom/', GenerateCustomInspirationView.as_view(), name='inspiration-generate-custom'),
    path('<int:pk>/', InspirationDetailView.as_view(), name='inspiration-detail'),
    path('<int:pk>/start-project/', StartProjectFromInspirationView.as_view(), name='inspiration-start-project'),
]
