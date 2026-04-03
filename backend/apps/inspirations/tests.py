from decimal import Decimal

from django.test import TestCase

from apps.inspirations.models import Inspiration


class InspirationModelTest(TestCase):
    def test_create_inspiration(self):
        inspiration = Inspiration.objects.create(
            source_url='https://example.com/rank/1',
            title='Hot Novel',
            synopsis='A popular story idea',
            tags=['urban', 'system'],
            hot_score=Decimal('95.50'),
            rank_type='hot',
        )

        self.assertEqual(inspiration.title, 'Hot Novel')
        self.assertEqual(inspiration.tags, ['urban', 'system'])
        self.assertFalse(inspiration.is_used)

    def test_inspiration_str(self):
        inspiration = Inspiration.objects.create(
            source_url='https://example.com/rank/2',
            title='Ranked Story',
            hot_score=Decimal('88.80'),
        )

        self.assertEqual(str(inspiration), 'Ranked Story (88.80)')
