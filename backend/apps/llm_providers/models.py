from django.conf import settings
from django.db import models
from utils.encryption import encrypt_text, decrypt_text


class LLMProvider(models.Model):
    """LLM service provider configuration"""

    PROVIDER_TYPES = [
        ('openai', 'OpenAI'),
        ('tongyi', '通义千问'),
        ('custom', '自定义'),
    ]

    TASK_TYPES = [
        ('outline', '大纲生成'),
        ('chapter', '章节生成'),
        ('continue', '内容续写'),
        ('setting', '设定生成'),
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
    _api_key_encrypted = models.TextField(verbose_name='API Key (加密)', db_column='api_key', default='')
    model = models.CharField(max_length=100, verbose_name='模型名称', default='gpt-3.5-turbo', help_text='例如: gpt-3.5-turbo, qwen-turbo, qwen-plus')
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

    @property
    def api_key(self) -> str:
        """Decrypt and return API key."""
        if not self._api_key_encrypted:
            return ''
        return decrypt_text(self._api_key_encrypted)

    @api_key.setter
    def api_key(self, value: str):
        """Encrypt and store API key."""
        if value:
            self._api_key_encrypted = encrypt_text(value)
        else:
            self._api_key_encrypted = ''
