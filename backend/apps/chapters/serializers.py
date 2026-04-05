import re

from rest_framework import serializers

from apps.chapters.models import Chapter
from apps.novels.models import NovelProject

PUBLISH_STATUS_CHOICES = ('draft', 'published', 'failed')
PUBLISH_TO_INTERNAL_STATUS = {
    'draft': 'pending_review',
    'published': 'published',
    'failed': 'failed',
}
INTERNAL_TO_PUBLISH_STATUS = {
    'generating': 'draft',
    'pending_review': 'draft',
    'approved': 'draft',
    'published': 'published',
    'failed': 'failed',
}


class ChapterSerializer(serializers.ModelSerializer):
    """Serializer for chapter CRUD APIs with publish status mapping."""

    project = serializers.PrimaryKeyRelatedField(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        queryset=NovelProject.objects.all(),
        source='project',
        write_only=True,
        required=True,
    )
    publish_status = serializers.SerializerMethodField()

    class Meta:
        model = Chapter
        fields = (
            'id',
            'project',
            'project_id',
            'chapter_number',
            'title',
            'raw_content',
            'final_content',
            'word_count',
            'generation_prompt',
            'llm_provider',
            'status',
            'publish_status',
            'generated_at',
            'reviewed_at',
            'published_at',
            'tomato_chapter_id',
            'read_count',
            'created_at',
            'updated_at',
            'is_deleted',
        )
        read_only_fields = (
            'id',
            'word_count',
            'created_at',
            'updated_at',
            'is_deleted',
            'status',
            'publish_status',
        )

    def get_publish_status(self, obj):
        """Expose simplified publish status values for clients."""
        return INTERNAL_TO_PUBLISH_STATUS.get(obj.status, 'draft')

    def validate_project_id(self, value):
        """Ensure users can only attach chapters to their own projects."""
        request = self.context.get('request')
        if request is None:
            return value

        if value.user_id != request.user.id:
            raise serializers.ValidationError('project_id must belong to the authenticated user.')
        if value.is_deleted:
            raise serializers.ValidationError('project_id refers to a deleted project.')

        return value

    def validate_chapter_number(self, value):
        """Ensure chapter numbers are positive."""
        if value <= 0:
            raise serializers.ValidationError('chapter_number must be greater than 0.')
        return value

    def _extract_publish_status(self):
        """Read and validate publish_status from request payload when provided."""
        publish_status = self.initial_data.get('publish_status')
        if publish_status is None:
            return None

        if publish_status not in PUBLISH_STATUS_CHOICES:
            raise serializers.ValidationError(
                {'publish_status': f'publish_status must be one of {", ".join(PUBLISH_STATUS_CHOICES)}.'}
            )

        return publish_status

    def validate(self, attrs):
        """Apply publish status mapping before create/update persistence."""
        attrs = super().validate(attrs)

        publish_status = self._extract_publish_status()
        if publish_status is not None:
            attrs['status'] = PUBLISH_TO_INTERNAL_STATUS[publish_status]
        elif self.instance is None and 'status' not in attrs:
            attrs['status'] = PUBLISH_TO_INTERNAL_STATUS['draft']

        return attrs

    def _calculate_word_count(self, content):
        """Calculate word count from non-whitespace characters in final content."""
        if not content:
            return 0
        return len(re.findall(r'\S', content))

    def create(self, validated_data):
        """Create chapters with auto-calculated word count."""
        final_content = validated_data.get('final_content')
        validated_data['word_count'] = self._calculate_word_count(final_content)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Recalculate word count whenever final content is updated."""
        if 'final_content' in validated_data:
            validated_data['word_count'] = self._calculate_word_count(
                validated_data.get('final_content')
            )
        return super().update(instance, validated_data)
