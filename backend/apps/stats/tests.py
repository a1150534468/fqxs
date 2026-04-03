from datetime import date

from django.test import TestCase

from apps.stats.models import Stats


class StatsModelTest(TestCase):
    def test_create_stats(self):
        stats = Stats.objects.create(
            date=date(2026, 4, 3),
            metric_type='generation',
            metric_data={'chapters': 3},
        )

        self.assertEqual(stats.metric_type, 'generation')
        self.assertEqual(stats.metric_data['chapters'], 3)

    def test_stats_str(self):
        stats = Stats.objects.create(
            date=date(2026, 4, 4),
            metric_type='cost',
            metric_data={'amount': 12.5},
        )

        self.assertEqual(str(stats), '2026-04-04 - cost')
