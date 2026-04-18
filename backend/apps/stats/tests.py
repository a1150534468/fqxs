from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.chapters.models import Chapter
from apps.novels.models import NovelProject
from apps.stats.models import Stats
from apps.tasks.models import Task

User = get_user_model()


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


class DashboardStatsAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='stats-user',
            email='stats-user@example.com',
            password='testpass123',
        )
        self.other_user = User.objects.create_user(
            username='stats-other',
            email='stats-other@example.com',
            password='testpass123',
        )
        self.authenticate()

        self.active_project = NovelProject.objects.create(
            user=self.user,
            title='Realtime Project',
            genre='Fantasy',
            status='active',
        )
        self.paused_project = NovelProject.objects.create(
            user=self.user,
            title='Paused Project',
            genre='Mystery',
            status='paused',
        )
        self.other_project = NovelProject.objects.create(
            user=self.other_user,
            title='Other Project',
            genre='Sci-Fi',
            status='active',
        )

        Chapter.objects.create(
            project=self.active_project,
            chapter_number=1,
            title='第1章',
            word_count=1800,
            status='draft',
            generation_meta={
                'input_tokens': 120,
                'output_tokens': 380,
                'latency_ms': 1500,
                'estimated_cost': 0.03,
            },
            consistency_status={'status': 'ok', 'risks': []},
        )
        Chapter.objects.create(
            project=self.active_project,
            chapter_number=2,
            title='第2章',
            word_count=2200,
            status='published',
            generation_meta={
                'input_tokens': 150,
                'output_tokens': 450,
                'latency_ms': 2500,
                'estimated_cost': 0.05,
            },
            consistency_status={'status': 'warning', 'risks': ['设定冲突风险']},
        )
        Chapter.objects.create(
            project=self.other_project,
            chapter_number=1,
            title='第1章',
            word_count=5000,
            status='published',
            generation_meta={
                'input_tokens': 999,
                'output_tokens': 999,
                'latency_ms': 9999,
                'estimated_cost': 9.99,
            },
            consistency_status={'status': 'ok', 'risks': []},
        )

        Task.objects.create(
            task_type='generate_chapter',
            related_type='project',
            related_id=self.active_project.id,
            status='pending',
            params={'project_id': self.active_project.id},
        )
        Task.objects.create(
            task_type='publish_chapter',
            related_type='project',
            related_id=self.other_project.id,
            status='running',
            params={'project_id': self.other_project.id},
        )

        self.dashboard_url = '/api/stats/dashboard/'

    def authenticate(self):
        response = self.client.post(
            reverse('user-login'),
            {'username': 'stats-user', 'password': 'testpass123'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_dashboard_stats_returns_expected_shape_and_scoped_values(self):
        response = self.client.get(self.dashboard_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['generation']['total_chapters'], 2)
        self.assertEqual(response.data['generation']['avg_word_count'], 2000)
        self.assertEqual(response.data['generation']['success_rate'], 100.0)
        self.assertEqual(response.data['cost']['total_api_calls'], 2)
        self.assertEqual(response.data['cost']['total_tokens'], 1100)
        self.assertEqual(response.data['cost']['estimated_cost'], 0.08)
        self.assertEqual(response.data['performance']['avg_generation_time'], 2.0)
        self.assertEqual(response.data['performance']['current_queue'], 1)
        self.assertEqual(response.data['novels']['active_count'], 1)
        self.assertEqual(response.data['novels']['total_chapters_published'], 1)
        self.assertEqual(response.data['quality']['warning_count'], 1)
        self.assertEqual(response.data['quality']['chapters_with_risk'], 1)
