from django.test import TestCase

from apps.tasks.models import Task


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
