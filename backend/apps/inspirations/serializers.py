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


class TrendingBookSerializer(serializers.Serializer):
    """Trending book data for inspiration generation."""
    title = serializers.CharField(max_length=200)
    synopsis = serializers.CharField(max_length=5000, required=False, allow_blank=True)
    tags = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    hot_score = serializers.FloatField(default=0.0, min_value=0)


class GenerateInspirationFromTrendsSerializer(serializers.Serializer):
    """Request to generate inspirations from trending books."""
    trending_books = serializers.ListField(
        child=TrendingBookSerializer(),
        min_length=1,
        max_length=50,
    )
    genre_preference = serializers.CharField(max_length=100, required=False, allow_blank=True)


class StartProjectFromInspirationSerializer(serializers.Serializer):
    """Request to start a novel project from an inspiration."""
    title = serializers.CharField(max_length=200, required=False)
    genre = serializers.CharField(max_length=50, required=False)
    target_chapters = serializers.IntegerField(min_value=1, max_value=2000, default=100)
    first_chapter_title = serializers.CharField(max_length=200, default="第一章")


class GenerateCustomInspirationSerializer(serializers.Serializer):
    """Request to generate custom inspirations from user prompt."""
    custom_prompt = serializers.CharField(max_length=2000, required=True)
    count = serializers.IntegerField(min_value=1, max_value=10, default=3)
