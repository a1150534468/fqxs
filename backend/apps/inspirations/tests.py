from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.inspirations.models import Inspiration

User = get_user_model()


class InspirationModelTest(TestCase):
    def test_create_inspiration(self):
        """It creates an inspiration with the expected defaults."""
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
        """It renders the title and score in the string representation."""
        inspiration = Inspiration.objects.create(
            source_url='https://example.com/rank/2',
            title='Ranked Story',
            hot_score=Decimal('88.80'),
        )

        self.assertEqual(str(inspiration), 'Ranked Story (88.80)')


class InspirationAPITest(TestCase):
    def setUp(self):
        """Create a test user, authenticate via JWT, and seed one inspiration."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='inspiration-user',
            email='inspiration@example.com',
            password='testpass123',
        )
        self.list_url = reverse('inspiration-list-create')
        self.inspiration = Inspiration.objects.create(
            source_url='https://example.com/rank/api-1',
            title='Existing Inspiration',
            synopsis='Existing synopsis',
            tags=['fantasy'],
            hot_score=Decimal('66.60'),
            rank_type='hot',
        )
        self.detail_url = reverse('inspiration-detail', kwargs={'pk': self.inspiration.pk})
        self.bulk_mark_used_url = reverse('inspiration-bulk-mark-used')
        self.authenticate()

    def authenticate(self):
        """Authenticate the API client using the project's JWT login endpoint."""
        response = self.client.post(
            reverse('user-login'),
            {
                'username': 'inspiration-user',
                'password': 'testpass123',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_list_inspirations(self):
        """It returns the paginated inspiration list for authenticated requests."""
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Existing Inspiration')

    def test_create_inspiration(self):
        """It creates an inspiration through the authenticated API."""
        response = self.client.post(
            self.list_url,
            {
                'source_url': 'https://example.com/rank/api-2',
                'title': 'New Inspiration',
                'synopsis': 'A new idea',
                'tags': ['urban', 'system'],
                'hot_score': '88.80',
                'rank_type': 'new',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'New Inspiration')
        self.assertEqual(response.data['tags'], ['urban', 'system'])
        self.assertFalse(response.data['is_used'])

    def test_retrieve_inspiration(self):
        """It retrieves a single inspiration by primary key."""
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Existing Inspiration')

    def test_update_inspiration(self):
        """It updates an inspiration with a full PUT request."""
        response = self.client.put(
            self.detail_url,
            {
                'source_url': 'https://example.com/rank/api-1-updated',
                'title': 'Updated Inspiration',
                'synopsis': 'Updated synopsis',
                'tags': ['fantasy', 'ranking'],
                'hot_score': '77.70',
                'rank_type': 'weekly',
                'is_used': True,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Inspiration')
        self.assertEqual(response.data['hot_score'], '77.70')
        self.assertEqual(response.data['tags'], ['fantasy', 'ranking'])
        self.assertTrue(response.data['is_used'])

    def test_partial_update_inspiration(self):
        """It supports partial updates through PATCH."""
        response = self.client.patch(
            self.detail_url,
            {
                'title': 'Updated Inspiration',
                'is_used': True,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Inspiration')
        self.assertTrue(response.data['is_used'])

    def test_delete_inspiration(self):
        """It deletes an inspiration through the detail endpoint."""
        response = self.client.delete(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Inspiration.objects.filter(id=self.inspiration.id).exists())

    def test_authentication_required(self):
        """It rejects unauthenticated CRUD requests with HTTP 401."""
        unauthenticated_client = APIClient()

        cases = (
            ('get', self.list_url, None),
            ('post', self.list_url, {'source_url': 'https://example.com/rank/api-3', 'title': 'Blocked'}),
            ('get', self.detail_url, None),
            ('patch', self.detail_url, {'title': 'Blocked'}),
            ('delete', self.detail_url, None),
        )

        for method, url, payload in cases:
            with self.subTest(method=method, url=url):
                response = getattr(unauthenticated_client, method)(url, payload, format='json')
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_inspiration_rejects_negative_hot_score(self):
        """It validates that hot_score cannot be negative."""
        response = self.client.post(
            self.list_url,
            {
                'source_url': 'https://example.com/rank/api-4',
                'title': 'Invalid Inspiration',
                'synopsis': 'Invalid score',
                'tags': ['invalid'],
                'hot_score': '-1.00',
                'rank_type': 'hot',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('hot_score', response.data)

    def test_bulk_mark_used_updates_multiple_inspirations(self):
        """It marks multiple inspirations as used and reports missing IDs."""
        extra = Inspiration.objects.create(
            source_url='https://example.com/rank/api-5',
            title='Second Inspiration',
            hot_score=Decimal('55.50'),
        )

        response = self.client.post(
            self.bulk_mark_used_url,
            {'ids': [self.inspiration.id, extra.id, 999999]},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['requested_count'], 3)
        self.assertEqual(response.data['updated_count'], 2)
        self.assertEqual(response.data['missing_ids'], [999999])
        self.assertTrue(response.data['is_used'])

        self.inspiration.refresh_from_db()
        extra.refresh_from_db()
        self.assertTrue(self.inspiration.is_used)
        self.assertTrue(extra.is_used)

    def test_bulk_mark_used_can_set_false(self):
        """It can mark selected inspirations as unused."""
        self.inspiration.is_used = True
        self.inspiration.save(update_fields=['is_used', 'updated_at'])

        response = self.client.post(
            self.bulk_mark_used_url,
            {'ids': [self.inspiration.id], 'is_used': False},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['updated_count'], 1)
        self.assertFalse(response.data['is_used'])
        self.inspiration.refresh_from_db()
        self.assertFalse(self.inspiration.is_used)

    def test_bulk_mark_used_requires_non_empty_ids(self):
        """It validates the bulk payload."""
        response = self.client.post(
            self.bulk_mark_used_url,
            {'ids': []},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('ids', response.data)

    def test_bulk_mark_used_authentication_required(self):
        """It rejects unauthenticated bulk mark requests."""
        unauthenticated_client = APIClient()

        response = unauthenticated_client.post(
            self.bulk_mark_used_url,
            {'ids': [self.inspiration.id]},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
