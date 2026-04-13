from rest_framework import serializers

from apps.inspirations.models import Inspiration
from apps.novels.models import NovelProject, NovelSetting, NovelDraft, DraftSetting


class NovelSettingSerializer(serializers.ModelSerializer):
    """Serializer for novel setting (worldview, characters, map, etc.)."""

    class Meta:
        model = NovelSetting
        fields = (
            'id',
            'setting_type',
            'title',
            'content',
            'structured_data',
            'ai_generated',
            'order',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class NovelProjectSerializer(serializers.ModelSerializer):
    """Serializer for novel project CRUD APIs."""

    user = serializers.PrimaryKeyRelatedField(read_only=True)
    inspiration = serializers.PrimaryKeyRelatedField(
        queryset=Inspiration.objects.all(),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = NovelProject
        fields = (
            'id',
            'user',
            'inspiration',
            'title',
            'genre',
            'synopsis',
            'outline',
            'ai_prompt_template',
            'status',
            'target_chapters',
            'current_chapter',
            'update_frequency',
            'last_update_at',
            'tomato_book_id',
            'wizard_completed',
            'wizard_step',
            'auto_generation_enabled',
            'generation_schedule',
            'next_generation_time',
            'created_at',
            'updated_at',
            'is_deleted',
        )
        read_only_fields = (
            'id',
            'user',
            'created_at',
            'updated_at',
        )

    def validate_title(self, value):
        """Ensure the title is not blank after trimming whitespace."""
        value = value.strip()
        if not value:
            raise serializers.ValidationError('title cannot be blank.')
        return value

    def validate_genre(self, value):
        """Ensure the genre is not blank after trimming whitespace."""
        value = value.strip()
        if not value:
            raise serializers.ValidationError('genre cannot be blank.')
        return value

    def validate_target_chapters(self, value):
        """Ensure the target chapter count is positive."""
        if value <= 0:
            raise serializers.ValidationError('target_chapters must be greater than 0.')
        return value

    def validate_current_chapter(self, value):
        """Ensure the current chapter count is non-negative."""
        if value < 0:
            raise serializers.ValidationError('current_chapter must be greater than or equal to 0.')
        return value

    def validate_update_frequency(self, value):
        """Ensure the planned update frequency is positive."""
        if value <= 0:
            raise serializers.ValidationError('update_frequency must be greater than 0.')
        return value

    def validate(self, attrs):
        """Ensure the current chapter count does not exceed the target."""
        target_chapters = attrs.get(
            'target_chapters',
            getattr(self.instance, 'target_chapters', None),
        )
        current_chapter = attrs.get(
            'current_chapter',
            getattr(self.instance, 'current_chapter', None),
        )

        if (
            target_chapters is not None
            and current_chapter is not None
            and current_chapter > target_chapters
        ):
            raise serializers.ValidationError(
                {'current_chapter': 'current_chapter cannot exceed target_chapters.'}
            )

        return attrs


class DraftSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = DraftSetting
        fields = ['id', 'setting_type', 'title', 'content', 'structured_data', 'ai_generated', 'order', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class NovelDraftSerializer(serializers.ModelSerializer):
    settings = DraftSettingSerializer(many=True, read_only=True)

    class Meta:
        model = NovelDraft
        fields = ['id', 'inspiration', 'title', 'genre', 'current_step', 'is_completed', 'converted_project', 'settings', 'created_at', 'updated_at']
        read_only_fields = ['id', 'is_completed', 'converted_project', 'created_at', 'updated_at']
