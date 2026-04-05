from rest_framework import serializers

from apps.inspirations.models import Inspiration


class InspirationSerializer(serializers.ModelSerializer):
    """Serializer for inspiration CRUD APIs."""

    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
    )

    class Meta:
        model = Inspiration
        fields = (
            'id',
            'source_url',
            'title',
            'synopsis',
            'tags',
            'hot_score',
            'rank_type',
            'is_used',
            'collected_at',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'collected_at',
            'created_at',
            'updated_at',
        )

    def validate_hot_score(self, value):
        """Hot score must be non-negative."""
        if value < 0:
            raise serializers.ValidationError('hot_score must be greater than or equal to 0.')
        return value


class InspirationBulkMarkUsedSerializer(serializers.Serializer):
    """Request payload for marking multiple inspirations as used/unused."""

    ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )
    is_used = serializers.BooleanField(default=True)
