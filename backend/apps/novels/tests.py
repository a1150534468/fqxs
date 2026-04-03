from django.contrib.auth import get_user_model
from django.test import TestCase

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
