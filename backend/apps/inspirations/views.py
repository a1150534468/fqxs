from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.inspirations.models import Inspiration
from apps.inspirations.serializers import (
    InspirationBulkMarkUsedSerializer,
    InspirationSerializer,
)


class InspirationListCreateView(generics.ListCreateAPIView):
    """List inspirations or create a new inspiration."""

    queryset = Inspiration.objects.all()
    serializer_class = InspirationSerializer
    permission_classes = (IsAuthenticated,)


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
