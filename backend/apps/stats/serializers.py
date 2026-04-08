from rest_framework import serializers

from apps.stats.models import Stats


class StatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stats
        fields = ('id', 'date', 'metric_type', 'metric_data', 'created_at')
        read_only_fields = ('id', 'created_at')
