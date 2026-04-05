from django.urls import path

from apps.inspirations.views import (
    InspirationBulkMarkUsedView,
    InspirationDetailView,
    InspirationListCreateView,
)

urlpatterns = [
    path('', InspirationListCreateView.as_view(), name='inspiration-list-create'),
    path('bulk-mark-used/', InspirationBulkMarkUsedView.as_view(), name='inspiration-bulk-mark-used'),
    path('<int:pk>/', InspirationDetailView.as_view(), name='inspiration-detail'),
]
