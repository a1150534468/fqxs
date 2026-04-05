from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.tasks.models import Task

User = get_user_model()


class TaskModelTest(TestCase):
    def test_create_task(self):
        task = Task.objects.create(
            task_type='generate_chapter',
            related_type='chapter',
            related_id=1,
            params={'chapter_number': 1},
        )

        self.assertEqual(task.status, 'pending')
        self.assertEqual(task.params['chapter_number'], 1)
        self.assertEqual(task.retry_count, 0)

    def test_task_str(self):
        task = Task.objects.create(
            task_type='publish_chapter',
            status='running',
        )

        self.assertEqual(str(task), 'publish_chapter - running')


class TaskStatusAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='task-user',
            email='task-user@example.com',
            password='testpass123',
        )
        self.authenticate()

        self.task = Task.objects.create(
            task_type='generate_chapter',
            status='running',
            celery_task_id='celery-task-123',
            params={'project_id': 1},
        )
        self.status_url = reverse('task-status', kwargs={'task_id': self.task.celery_task_id})

    def authenticate(self):
        response = self.client.post(
            reverse('user-login'),
            {'username': 'task-user', 'password': 'testpass123'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    @patch('apps.tasks.views.AsyncResult')
    def test_task_status_returns_celery_state_and_task_record(self, mock_async_result):
        fake_result = SimpleNamespace(status='SUCCESS', result={'ok': True})
        fake_result.ready = lambda: True
        mock_async_result.return_value = fake_result

        response = self.client.get(self.status_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['task_id'], self.task.celery_task_id)
        self.assertEqual(response.data['status'], 'SUCCESS')
        self.assertEqual(response.data['result'], {'ok': True})
        self.assertEqual(response.data['task_record']['id'], self.task.id)
        self.assertEqual(response.data['task_record']['task_type'], 'generate_chapter')

    @patch('apps.tasks.views.AsyncResult')
    def test_task_status_hides_result_when_not_ready(self, mock_async_result):
        fake_result = SimpleNamespace(status='PENDING', result={'ok': False})
        fake_result.ready = lambda: False
        mock_async_result.return_value = fake_result

        response = self.client.get(self.status_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'PENDING')
        self.assertIsNone(response.data['result'])

    def test_task_status_requires_authentication(self):
        unauthenticated_client = APIClient()

        response = unauthenticated_client.get(self.status_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
