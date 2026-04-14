from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.chapters.models import Chapter
from apps.inspirations.models import Inspiration
from apps.novels.models import NovelProject

User = get_user_model()


class UserModelTest(TestCase):
    def test_create_user(self):
        """Test creating a user with email and password"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('testpass123'))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
    
    def test_user_str_representation(self):
        """Test the string representation of user"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.assertEqual(str(user), 'testuser')


class UserAuthAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='apiuser',
            email='apiuser@example.com',
            password='testpass123',
        )

    def test_login_returns_access_and_refresh_tokens(self):
        response = self.client.post(
            '/api/users/login/',
            {
                'username': 'apiuser',
                'password': 'testpass123',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['id'], self.user.id)
        self.assertEqual(response.data['user']['username'], 'apiuser')
        self.assertEqual(response.data['user']['email'], 'apiuser@example.com')
        self.assertTrue(response.data['user']['is_active'])
        self.assertFalse(response.data['user']['is_staff'])

    def test_login_with_invalid_credentials_returns_401(self):
        response = self.client.post(
            '/api/users/login/',
            {
                'username': 'apiuser',
                'password': 'wrong-password',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('detail', response.data)

    def test_refresh_returns_new_access_token(self):
        login_response = self.client.post(
            '/api/users/login/',
            {
                'username': 'apiuser',
                'password': 'testpass123',
            },
            format='json',
        )
        refresh_token = login_response.data['refresh']

        response = self.client.post(
            '/api/users/refresh/',
            {'refresh': refresh_token},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)


class UserStatsAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='stats-user',
            email='stats@example.com',
            password='testpass123',
        )
        self.other_user = User.objects.create_user(
            username='stats-other',
            email='stats-other@example.com',
            password='testpass123',
        )
        self.stats_url = reverse('user-stats')

        inspiration = Inspiration.objects.create(
            source_url='https://example.com/rank/stats',
            title='Stats Inspiration',
        )

        self.project = NovelProject.objects.create(
            user=self.user,
            inspiration=inspiration,
            title='Stats Project',
            genre='Fantasy',
        )
        self.deleted_project = NovelProject.objects.create(
            user=self.user,
            title='Deleted Project',
            genre='Fantasy',
            is_deleted=True,
        )
        self.other_project = NovelProject.objects.create(
            user=self.other_user,
            title='Other User Project',
            genre='Sci-Fi',
        )

        Chapter.objects.create(project=self.project, chapter_number=1, word_count=1000)
        Chapter.objects.create(project=self.project, chapter_number=2, word_count=1500)
        Chapter.objects.create(project=self.deleted_project, chapter_number=1, word_count=900)
        Chapter.objects.create(project=self.other_project, chapter_number=1, word_count=800)

        self.authenticate(self.user.username)

    def authenticate(self, username):
        login_response = self.client.post(
            reverse('user-login'),
            {
                'username': username,
                'password': 'testpass123',
            },
            format='json',
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")

    def test_stats_returns_current_users_aggregates(self):
        response = self.client.get(self.stats_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['project_count'], 1)
        self.assertEqual(response.data['chapter_count'], 2)
        self.assertEqual(response.data['total_word_count'], 2500)

    def test_stats_requires_authentication(self):
        unauthenticated_client = APIClient()

        response = unauthenticated_client.get(self.stats_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_stats_returns_zero_values_when_user_has_no_data(self):
        empty_user = User.objects.create_user(
            username='empty-stats',
            email='empty@example.com',
            password='testpass123',
        )
        self.authenticate(empty_user.username)

        response = self.client.get(self.stats_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['project_count'], 0)
        self.assertEqual(response.data['chapter_count'], 0)
        self.assertEqual(response.data['total_word_count'], 0)


class CreateAdminCommandTest(TestCase):
    def test_create_admin_command_creates_superuser(self):
        call_command('create_admin')

        admin_user = User.objects.get(username='admin')
        self.assertEqual(admin_user.email, 'admin@example.com')
        self.assertTrue(admin_user.is_superuser)
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.check_password('admin123'))

    def test_create_admin_command_is_idempotent(self):
        call_command('create_admin')
        call_command('create_admin')

        self.assertEqual(User.objects.filter(username='admin').count(), 1)
