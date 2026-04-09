"""
Celery periodic task configuration for inspiration generation.

Add this to your celery beat schedule to automate inspiration generation.
"""

from celery.schedules import crontab

# In your celery.py or settings.py, add to CELERY_BEAT_SCHEDULE:

CELERY_BEAT_SCHEDULE = {
    # Generate inspirations from trends every day at 2 AM
    'generate-daily-inspirations': {
        'task': 'celery_tasks.ai_tasks.generate_inspiration_from_trends',
        'schedule': crontab(hour=2, minute=0),
        'options': {
            'expires': 3600,  # Task expires after 1 hour if not executed
        }
    },
}

# Manual task execution examples:

# 1. Generate inspirations immediately
from celery_tasks.ai_tasks import generate_inspiration_from_trends
result = generate_inspiration_from_trends.delay()
print(f"Task ID: {result.id}")

# 2. Start project from inspiration
from celery_tasks.ai_tasks import start_novel_project_from_inspiration
result = start_novel_project_from_inspiration.delay(
    user_id=1,
    inspiration_id=5,
    title="都市修仙传说",
    genre="都市",
    target_chapters=100
)
print(f"Task ID: {result.id}")

# 3. With task tracking
from apps.tasks.models import Task
task_record = Task.objects.create(
    task_type='generate_inspiration',
    status='pending',
    params={'source': 'manual'}
)
result = generate_inspiration_from_trends.delay(task_record_id=task_record.id)

# Check task status
task_record.refresh_from_db()
print(f"Status: {task_record.status}")
print(f"Result: {task_record.result}")
