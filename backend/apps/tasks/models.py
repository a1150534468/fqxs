from django.db import models


class Task(models.Model):
    """Async task tracking"""

    TASK_TYPES = [
        ('crawl_ideas', '采集创意'),
        ('generate_outline', '生成大纲'),
        ('generate_chapter', '生成章节'),
        ('publish_chapter', '发布章节'),
    ]

    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('running', '运行中'),
        ('success', '成功'),
        ('failed', '失败'),
        ('retry', '重试中'),
    ]

    task_type = models.CharField(max_length=50, choices=TASK_TYPES, verbose_name='任务类型')
    related_type = models.CharField(max_length=50, blank=True, null=True, verbose_name='关联对象类型')
    related_id = models.IntegerField(null=True, blank=True, verbose_name='关联对象 ID')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    celery_task_id = models.CharField(max_length=255, blank=True, null=True, verbose_name='Celery 任务 ID')
    params = models.JSONField(default=dict, verbose_name='任务参数')
    result = models.JSONField(default=dict, blank=True, null=True, verbose_name='任务结果')
    error_message = models.TextField(blank=True, null=True, verbose_name='错误信息')
    retry_count = models.IntegerField(default=0, verbose_name='重试次数')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'task'
        verbose_name = '任务'
        verbose_name_plural = '任务'
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['celery_task_id']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.task_type} - {self.status}'
