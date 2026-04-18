from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.chapters.models import Chapter
from apps.novels.models import NovelProject
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
        self.project = NovelProject.objects.create(
            user=self.user,
            title='Task Project',
            genre='Fantasy',
        )
        self.authenticate()

        self.task = Task.objects.create(
            task_type='generate_chapter',
            status='running',
            celery_task_id='celery-task-123',
            related_type='project',
            related_id=self.project.id,
            params={'project_id': self.project.id},
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


class TaskListScopeAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='task-owner',
            email='task-owner@example.com',
            password='testpass123',
        )
        self.other_user = User.objects.create_user(
            username='task-other',
            email='task-other@example.com',
            password='testpass123',
        )

        self.project = NovelProject.objects.create(
            user=self.user,
            title='Scoped Project',
            genre='Fantasy',
        )
        self.chapter = Chapter.objects.create(
            project=self.project,
            chapter_number=1,
            title='第1章',
            status='draft',
        )
        self.other_project = NovelProject.objects.create(
            user=self.other_user,
            title='Other Project',
            genre='Sci-Fi',
        )
        self.other_chapter = Chapter.objects.create(
            project=self.other_project,
            chapter_number=1,
            title='第1章',
            status='draft',
        )

        self.project_task = Task.objects.create(
            task_type='generate_chapter',
            related_type='project',
            related_id=self.project.id,
            status='pending',
            params={'project_id': self.project.id},
            celery_task_id='owned-project-task',
        )
        self.chapter_task = Task.objects.create(
            task_type='publish_chapter',
            related_type='chapter',
            related_id=self.chapter.id,
            status='running',
            params={'chapter_id': self.chapter.id},
            celery_task_id='owned-chapter-task',
        )
        self.params_only_task = Task.objects.create(
            task_type='generate_chapter',
            related_type='',
            related_id=None,
            status='success',
            params={'project_id': self.project.id},
            celery_task_id='owned-params-task',
        )
        self.other_task = Task.objects.create(
            task_type='generate_chapter',
            related_type='project',
            related_id=self.other_project.id,
            status='pending',
            params={'project_id': self.other_project.id},
            celery_task_id='other-task',
        )
        self.other_chapter_task = Task.objects.create(
            task_type='publish_chapter',
            related_type='chapter',
            related_id=self.other_chapter.id,
            status='running',
            params={'chapter_id': self.other_chapter.id},
            celery_task_id='other-chapter-task',
        )

        self.list_url = reverse('task-list')
        self.authenticate()

    def authenticate(self):
        response = self.client.post(
            reverse('user-login'),
            {'username': 'task-owner', 'password': 'testpass123'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_task_list_only_returns_current_users_records(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
        returned_ids = {item['id'] for item in response.data['results']}
        self.assertSetEqual(
            returned_ids,
            {self.project_task.id, self.chapter_task.id, self.params_only_task.id},
        )

    def test_task_status_rejects_other_users_task(self):
        response = self.client.get(
            reverse('task-status', kwargs={'task_id': self.other_task.celery_task_id})
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
