from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.chapters.models import Chapter
from apps.inspirations.models import Inspiration
from apps.llm_providers.models import LLMProvider
from apps.novels.models import NovelProject

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

    def test_chapter_str(self):
        chapter = Chapter.objects.create(
            project=self.project,
            chapter_number=2,
        )

        self.assertEqual(str(chapter), 'Chapter Novel - 第2章')
