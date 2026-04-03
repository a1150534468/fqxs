from django.conf import settings
from django.db import models


class LLMProvider(models.Model):
    """LLM service provider configuration"""

    PROVIDER_TYPES = [
        ('openai', 'OpenAI'),
        ('qwen', '通义千问'),
        ('custom', '自定义'),
    ]

    TASK_TYPES = [
        ('idea_generation', '创意生成'),
        ('chapter_writing', '章节写作'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='llm_providers',
        verbose_name='用户',
    )
    name = models.CharField(max_length=100, verbose_name='服务名称')
    provider_type = models.CharField(max_length=20, choices=PROVIDER_TYPES, verbose_name='服务类型')
    api_url = models.URLField(max_length=255, verbose_name='API 地址')
    api_key = models.CharField(max_length=255, verbose_name='API Key')
    task_type = models.CharField(max_length=20, choices=TASK_TYPES, verbose_name='任务类型')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    priority = models.IntegerField(default=0, verbose_name='优先级')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'llm_provider'
        verbose_name = 'LLM 服务提供商'
        verbose_name_plural = 'LLM 服务提供商'
        indexes = [
            models.Index(fields=['task_type', 'priority', 'is_active']),
        ]
        ordering = ['-priority', 'created_at']

    def __str__(self):
        return f'{self.name} ({self.provider_type})'
