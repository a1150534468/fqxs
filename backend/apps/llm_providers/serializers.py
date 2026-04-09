from rest_framework import serializers

from apps.llm_providers.models import LLMProvider


class LLMProviderSerializer(serializers.ModelSerializer):
    api_key = serializers.CharField(write_only=True, required=True, max_length=255)
    api_key_masked = serializers.SerializerMethodField()

    class Meta:
        model = LLMProvider
        fields = (
            'id',
            'name',
            'provider_type',
            'api_url',
            'api_key',
            'api_key_masked',
            'model',
            'task_type',
            'is_active',
            'priority',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'api_key_masked', 'created_at', 'updated_at')

    def get_api_key_masked(self, obj):
        if not obj.api_key:
            return ''
        if len(obj.api_key) <= 8:
            return '****'
        return obj.api_key[:4] + '****' + obj.api_key[-4:]

    def create(self, validated_data):
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'api_key' in validated_data:
            api_key = validated_data.pop('api_key')
            instance.api_key = api_key
        return super().update(instance, validated_data)
