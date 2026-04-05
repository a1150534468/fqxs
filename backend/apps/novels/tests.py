from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.inspirations.models import Inspiration
from apps.novels.models import NovelProject

User = get_user_model()


class NovelProjectModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='novel-user',
            email='novel@example.com',
            password='testpass123',
        )
        self.inspiration = Inspiration.objects.create(
            source_url='https://example.com/rank/novel',
            title='Idea Source',
        )

    def test_create_novel_project(self):
        project = NovelProject.objects.create(
            user=self.user,
            inspiration=self.inspiration,
            title='My Novel',
            genre='Fantasy',
            update_frequency=1,
        )

        self.assertEqual(project.user, self.user)
        self.assertEqual(project.inspiration, self.inspiration)
        self.assertEqual(project.status, 'active')

    def test_novel_project_str(self):
        project = NovelProject.objects.create(
            user=self.user,
            title='String Novel',
            genre='Sci-Fi',
        )

        self.assertEqual(str(project), 'String Novel')


class NovelProjectAPITest(TestCase):
    def setUp(self):
        """Create authenticated clients and seed projects for ownership checks."""
        self.client = APIClient()
        self.other_client = APIClient()
        self.user = User.objects.create_user(
            username='project-owner',
            email='owner@example.com',
            password='testpass123',
        )
        self.other_user = User.objects.create_user(
            username='other-owner',
            email='other@example.com',
            password='testpass123',
        )
        self.inspiration = Inspiration.objects.create(
            source_url='https://example.com/rank/api-project',
            title='Project Idea Source',
        )
        self.project = NovelProject.objects.create(
            user=self.user,
            inspiration=self.inspiration,
            title='Owner Project',
            genre='Fantasy',
            synopsis='Owner synopsis',
            target_chapters=120,
            current_chapter=12,
            update_frequency=1,
        )
        self.paused_project = NovelProject.objects.create(
            user=self.user,
            title='Mystery Casebook',
            genre='Mystery',
            status='paused',
            synopsis='Detective themed project',
            target_chapters=80,
            current_chapter=20,
            update_frequency=1,
        )
        self.completed_project = NovelProject.objects.create(
            user=self.user,
            title='Historical Saga',
            genre='History',
            status='completed',
            target_chapters=60,
            current_chapter=60,
            update_frequency=1,
        )
        self.other_project = NovelProject.objects.create(
            user=self.other_user,
            title='Other Project',
            genre='Sci-Fi',
        )
        now = timezone.now()
        NovelProject.objects.filter(pk=self.project.pk).update(created_at=now - timedelta(days=7))
        NovelProject.objects.filter(pk=self.paused_project.pk).update(created_at=now - timedelta(days=2))
        NovelProject.objects.filter(pk=self.completed_project.pk).update(created_at=now - timedelta(days=15))
        self.list_url = reverse('novelproject-list')
        self.detail_url = reverse('novelproject-detail', kwargs={'pk': self.project.pk})
        self.other_detail_url = reverse('novelproject-detail', kwargs={'pk': self.other_project.pk})
        self.authenticate(self.client, 'project-owner')
        self.authenticate(self.other_client, 'other-owner')

    def authenticate(self, client, username):
        """Authenticate an API client using the JWT login endpoint."""
        response = client.post(
            reverse('user-login'),
            {
                'username': username,
                'password': 'testpass123',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_list_only_returns_current_users_projects(self):
        """It limits the paginated list response to the current user's projects."""
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
        returned_titles = {item['title'] for item in response.data['results']}
        self.assertSetEqual(returned_titles, {'Owner Project', 'Mystery Casebook', 'Historical Saga'})

    def test_create_project_assigns_authenticated_user(self):
        """It ignores any submitted user value and binds the project to request.user."""
        response = self.client.post(
            self.list_url,
            {
                'user': self.other_user.pk,
                'inspiration': self.inspiration.pk,
                'title': 'New Project',
                'genre': 'Urban',
                'synopsis': 'Generated synopsis',
                'outline': 'Outline',
                'ai_prompt_template': 'Prompt',
                'status': 'active',
                'target_chapters': 50,
                'current_chapter': 0,
                'update_frequency': 1,
                'tomato_book_id': 'book-123',
                'is_deleted': False,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'New Project')
        self.assertEqual(response.data['user'], self.user.pk)
        self.assertEqual(NovelProject.objects.get(id=response.data['id']).user, self.user)

    def test_retrieve_project(self):
        """It retrieves a single project owned by the authenticated user."""
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Owner Project')
        self.assertEqual(response.data['user'], self.user.pk)

    def test_update_project(self):
        """It updates a project owned by the authenticated user."""
        response = self.client.put(
            self.detail_url,
            {
                'inspiration': self.inspiration.pk,
                'title': 'Updated Project',
                'genre': 'Fantasy',
                'synopsis': 'Updated synopsis',
                'outline': 'Updated outline',
                'ai_prompt_template': 'Updated prompt',
                'status': 'paused',
                'target_chapters': 130,
                'current_chapter': 13,
                'update_frequency': 1,
                'tomato_book_id': 'book-456',
                'is_deleted': False,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Project')
        self.assertEqual(response.data['status'], 'paused')

    def test_partial_update_project(self):
        """It supports partial updates for owned projects."""
        response = self.client.patch(
            self.detail_url,
            {
                'title': 'Patched Project',
                'current_chapter': 15,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Patched Project')
        self.assertEqual(response.data['current_chapter'], 15)

    def test_delete_project_soft_deletes_and_hides_it(self):
        """It soft deletes owned projects and removes them from the visible queryset."""
        response = self.client.delete(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.project.refresh_from_db()
        self.assertTrue(self.project.is_deleted)
        self.assertEqual(self.client.get(self.detail_url).status_code, status.HTTP_404_NOT_FOUND)

    def test_authentication_required(self):
        """It rejects unauthenticated CRUD requests with HTTP 401."""
        unauthenticated_client = APIClient()

        cases = (
            ('get', self.list_url, None),
            ('post', self.list_url, {'title': 'Blocked', 'genre': 'Fantasy', 'target_chapters': 10, 'current_chapter': 0, 'update_frequency': 1}),
            ('get', self.detail_url, None),
            ('patch', self.detail_url, {'title': 'Blocked'}),
            ('delete', self.detail_url, None),
        )

        for method, url, payload in cases:
            with self.subTest(method=method, url=url):
                response = getattr(unauthenticated_client, method)(url, payload, format='json')
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_cannot_access_another_users_project(self):
        """It returns 404 when a user tries to access someone else's project."""
        response = self.client.get(self.other_detail_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_project_rejects_invalid_chapter_counts(self):
        """It validates chapter-related numeric constraints."""
        response = self.client.post(
            self.list_url,
            {
                'title': 'Invalid Project',
                'genre': 'Fantasy',
                'target_chapters': 5,
                'current_chapter': 6,
                'update_frequency': 1,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('current_chapter', response.data)

    def test_list_filters_by_status(self):
        """It filters projects by one or more status values."""
        response = self.client.get(self.list_url, {'status': 'paused,completed'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_titles = {item['title'] for item in response.data['results']}
        self.assertSetEqual(returned_titles, {'Mystery Casebook', 'Historical Saga'})

    def test_list_filters_by_type_alias(self):
        """It treats `type` as a genre filter for compatibility."""
        response = self.client.get(self.list_url, {'type': 'mystery'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Mystery Casebook')

    def test_list_supports_keyword_search(self):
        """It searches title, genre, synopsis, and outline fields."""
        response = self.client.get(self.list_url, {'search': 'detective'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Mystery Casebook')

    def test_list_filters_by_created_time_range(self):
        """It filters by created_after and created_before query params."""
        start = (timezone.now() - timedelta(days=3)).isoformat()
        end = (timezone.now() - timedelta(days=1)).isoformat()

        response = self.client.get(
            self.list_url,
            {'created_after': start, 'created_before': end},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Mystery Casebook')

    def test_list_rejects_invalid_created_time(self):
        """It returns HTTP 400 when created time params are malformed."""
        response = self.client.get(self.list_url, {'created_after': 'not-a-date'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('created_after', response.data)
