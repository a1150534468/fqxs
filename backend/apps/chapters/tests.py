from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.chapters.models import Chapter
from apps.inspirations.models import Inspiration
from apps.llm_providers.models import LLMProvider
from apps.novels.models import NovelProject
from apps.tasks.models import Task

User = get_user_model()


class ChapterModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='chapter-user',
            email='chapter@example.com',
            password='testpass123',
        )
        self.inspiration = Inspiration.objects.create(
            source_url='https://example.com/rank/chapter',
            title='Chapter Idea',
        )
        self.project = NovelProject.objects.create(
            user=self.user,
            inspiration=self.inspiration,
            title='Chapter Novel',
            genre='Urban',
        )
        self.provider = LLMProvider.objects.create(
            user=self.user,
            name='Writer Provider',
            provider_type='openai',
            api_url='https://api.openai.com/v1',
            api_key='secret-key',
            task_type='chapter_writing',
        )

    def test_create_chapter(self):
        chapter = Chapter.objects.create(
            project=self.project,
            chapter_number=1,
            title='Chapter One',
            raw_content='raw',
            final_content='final',
            word_count=1234,
            llm_provider=self.provider,
            status='pending_review',
        )

        self.assertEqual(chapter.project, self.project)
        self.assertEqual(chapter.llm_provider, self.provider)
        self.assertEqual(chapter.word_count, 1234)
        self.assertFalse(chapter.is_deleted)

    def test_chapter_str(self):
        chapter = Chapter.objects.create(
            project=self.project,
            chapter_number=2,
        )

        self.assertEqual(str(chapter), 'Chapter Novel - 第2章')


class ChapterAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.other_client = APIClient()
        self.user = User.objects.create_user(
            username='chapter-owner',
            email='chapter-owner@example.com',
            password='testpass123',
        )
        self.other_user = User.objects.create_user(
            username='chapter-other',
            email='chapter-other@example.com',
            password='testpass123',
        )

        inspiration = Inspiration.objects.create(
            source_url='https://example.com/rank/chapter-api',
            title='Chapter API Inspiration',
        )

        self.project = NovelProject.objects.create(
            user=self.user,
            inspiration=inspiration,
            title='Owner Novel',
            genre='Fantasy',
        )
        self.other_project = NovelProject.objects.create(
            user=self.other_user,
            title='Other Novel',
            genre='Sci-Fi',
        )

        self.chapter_draft = Chapter.objects.create(
            project=self.project,
            chapter_number=1,
            title='Draft Intro',
            final_content='draft content',
            word_count=11,
            status='pending_review',
        )
        self.chapter_published = Chapter.objects.create(
            project=self.project,
            chapter_number=2,
            title='Published Arc',
            final_content='published content',
            word_count=16,
            status='published',
        )
        self.chapter_failed = Chapter.objects.create(
            project=self.project,
            chapter_number=3,
            title='Failed Attempt',
            final_content='failed content',
            word_count=13,
            status='failed',
        )
        self.deleted_chapter = Chapter.objects.create(
            project=self.project,
            chapter_number=4,
            title='Deleted Chapter',
            status='published',
            is_deleted=True,
        )
        self.other_chapter = Chapter.objects.create(
            project=self.other_project,
            chapter_number=1,
            title='Other Chapter',
            status='published',
        )

        now = timezone.now()
        Chapter.objects.filter(pk=self.chapter_draft.pk).update(created_at=now - timedelta(days=5))
        Chapter.objects.filter(pk=self.chapter_published.pk).update(created_at=now - timedelta(days=2))
        Chapter.objects.filter(pk=self.chapter_failed.pk).update(created_at=now - timedelta(days=1))

        self.list_url = reverse('chapter-list')
        self.detail_url = reverse('chapter-detail', kwargs={'pk': self.chapter_draft.pk})
        self.other_detail_url = reverse('chapter-detail', kwargs={'pk': self.other_chapter.pk})
        self.generate_async_url = reverse('chapter-generate-async')

        self.authenticate(self.client, 'chapter-owner')
        self.authenticate(self.other_client, 'chapter-other')

    def authenticate(self, client, username):
        response = client.post(
            reverse('user-login'),
            {'username': username, 'password': 'testpass123'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_list_returns_only_current_users_non_deleted_chapters(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
        returned_ids = {item['id'] for item in response.data['results']}
        self.assertSetEqual(
            returned_ids,
            {self.chapter_draft.id, self.chapter_published.id, self.chapter_failed.id},
        )

    def test_create_chapter_success_and_auto_word_count(self):
        response = self.client.post(
            self.list_url,
            {
                'project_id': self.project.id,
                'chapter_number': 5,
                'title': 'New Chapter',
                'final_content': 'abc de\nf',
                'publish_status': 'draft',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['project'], self.project.id)
        self.assertEqual(response.data['word_count'], 6)
        self.assertEqual(response.data['publish_status'], 'draft')
        self.assertEqual(response.data['status'], 'pending_review')

    def test_create_chapter_requires_project_id(self):
        response = self.client.post(
            self.list_url,
            {
                'chapter_number': 6,
                'title': 'Missing Project',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('project_id', response.data)

    def test_create_chapter_rejects_other_users_project(self):
        response = self.client.post(
            self.list_url,
            {
                'project_id': self.other_project.id,
                'chapter_number': 6,
                'title': 'Blocked',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('project_id', response.data)

    def test_create_chapter_rejects_duplicate_chapter_number(self):
        response = self.client.post(
            self.list_url,
            {
                'project_id': self.project.id,
                'chapter_number': self.chapter_draft.chapter_number,
                'title': 'Duplicate Number',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_chapter_rejects_non_positive_chapter_number(self):
        response = self.client.post(
            self.list_url,
            {
                'project_id': self.project.id,
                'chapter_number': 0,
                'title': 'Invalid Number',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('chapter_number', response.data)

    def test_retrieve_chapter(self):
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.chapter_draft.id)
        self.assertEqual(response.data['publish_status'], 'draft')

    def test_patch_chapter_updates_word_count_and_publish_status(self):
        response = self.client.patch(
            self.detail_url,
            {
                'final_content': 'x y z',
                'publish_status': 'published',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['word_count'], 3)
        self.assertEqual(response.data['status'], 'published')
        self.assertEqual(response.data['publish_status'], 'published')

    def test_delete_chapter_soft_deletes_and_hides_resource(self):
        response = self.client.delete(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.chapter_draft.refresh_from_db()
        self.assertTrue(self.chapter_draft.is_deleted)
        self.assertEqual(
            self.client.get(self.detail_url).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_user_cannot_access_another_users_chapter(self):
        response = self.client.get(self.other_detail_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_authentication_required(self):
        unauthenticated_client = APIClient()

        cases = (
            ('get', self.list_url, None),
            (
                'post',
                self.list_url,
                {'project_id': self.project.id, 'chapter_number': 9, 'title': 'Blocked'},
            ),
            (
                'post',
                self.generate_async_url,
                {'project_id': self.project.id, 'chapter_number': 9, 'chapter_title': 'Blocked'},
            ),
            ('get', self.detail_url, None),
            ('patch', self.detail_url, {'title': 'Blocked'}),
            ('delete', self.detail_url, None),
        )

        for method, url, payload in cases:
            with self.subTest(method=method, url=url):
                response = getattr(unauthenticated_client, method)(
                    url,
                    payload,
                    format='json',
                )
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_filter_by_project_id(self):
        response = self.client.get(self.list_url, {'project_id': self.project.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)

    def test_filter_by_publish_status(self):
        response = self.client.get(self.list_url, {'publish_status': 'published,failed'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item['id'] for item in response.data['results']}
        self.assertSetEqual(returned_ids, {self.chapter_published.id, self.chapter_failed.id})

    def test_search_by_title(self):
        response = self.client.get(self.list_url, {'search': 'Arc'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.chapter_published.id)

    def test_filter_by_created_time_range(self):
        start = (timezone.now() - timedelta(days=3)).isoformat()
        end = (timezone.now() - timedelta(days=1, hours=12)).isoformat()
        response = self.client.get(
            self.list_url,
            {'created_after': start, 'created_before': end},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.chapter_published.id)

    def test_filter_rejects_invalid_publish_status(self):
        response = self.client.get(self.list_url, {'publish_status': 'unknown'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('publish_status', response.data)

    def test_filter_rejects_invalid_project_id(self):
        response = self.client.get(self.list_url, {'project_id': 'abc'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('project_id', response.data)

    def test_filter_rejects_invalid_created_time(self):
        response = self.client.get(self.list_url, {'created_after': 'not-a-date'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('created_after', response.data)

    @patch('apps.chapters.views.generate_chapter_async.delay')
    def test_generate_async_returns_task_id(self, mock_delay):
        mock_delay.return_value = SimpleNamespace(id='celery-task-1')

        response = self.client.post(
            self.generate_async_url,
            {
                'project_id': self.project.id,
                'chapter_number': 9,
                'chapter_title': 'Async Chapter',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data['task_id'], 'celery-task-1')
        task_record = Task.objects.get(id=response.data['task_record_id'])
        self.assertEqual(task_record.celery_task_id, 'celery-task-1')
        self.assertEqual(task_record.status, 'pending')
        self.assertEqual(task_record.task_type, 'generate_chapter')
        mock_delay.assert_called_once()

    @patch('apps.chapters.views.generate_chapter_async.delay')
    def test_generate_async_requires_owned_project(self, mock_delay):
        response = self.client.post(
            self.generate_async_url,
            {
                'project_id': self.other_project.id,
                'chapter_number': 9,
                'chapter_title': 'Blocked',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        mock_delay.assert_not_called()

    @patch('apps.chapters.views.generate_chapter_async.delay')
    def test_generate_async_validates_payload(self, mock_delay):
        response = self.client.post(
            self.generate_async_url,
            {
                'project_id': self.project.id,
                'chapter_number': 0,
                'chapter_title': '',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('chapter_number', response.data)
        self.assertIn('chapter_title', response.data)
        mock_delay.assert_not_called()
