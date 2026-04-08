from django.db import models
from apps.chapters.models import Chapter
from utils.encryption import encrypt_text, decrypt_text


class PublishConfig(models.Model):
    """Tomato Fiction publishing configuration."""

    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='publish_configs')
    platform_username = models.CharField(max_length=100, verbose_name='平台用户名')
    _platform_password_encrypted = models.TextField(verbose_name='平台密码（加密）', db_column='platform_password', default='')
    novel_id = models.CharField(max_length=100, verbose_name='小说ID', help_text='番茄小说平台的小说ID')
    project = models.ForeignKey('novels.NovelProject', on_delete=models.CASCADE, related_name='publish_configs')
    is_active = models.BooleanField(default=True, verbose_name='启用')
    proxy_list = models.TextField(blank=True, verbose_name='代理IP列表', help_text='每行一个代理，格式：http://ip:port')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'publish_config'
        verbose_name = '发布配置'
        verbose_name_plural = verbose_name
        unique_together = [['user', 'project']]

    def __str__(self):
        return f'{self.user.username} - {self.project.title}'

    @property
    def platform_password(self) -> str:
        """Decrypt and return password."""
        if not self._platform_password_encrypted:
            return ''
        return decrypt_text(self._platform_password_encrypted)

    @platform_password.setter
    def platform_password(self, value: str):
        """Encrypt and store password."""
        if value:
            self._platform_password_encrypted = encrypt_text(value)
        else:
            self._platform_password_encrypted = ''

    def get_proxy_list(self) -> list:
        """Parse proxy list from text field."""
        if not self.proxy_list:
            return []
        return [line.strip() for line in self.proxy_list.split('\n') if line.strip()]


class PublishRecord(models.Model):
    """Record of chapter publishing attempts."""

    STATUS_CHOICES = [
        ('pending', '待发布'),
        ('publishing', '发布中'),
        ('success', '成功'),
        ('failed', '失败'),
    ]

    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='publish_records')
    config = models.ForeignKey(PublishConfig, on_delete=models.CASCADE, related_name='publish_records')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    platform_chapter_id = models.CharField(max_length=100, blank=True, verbose_name='平台章节ID')
    error_message = models.TextField(blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'publish_record'
        verbose_name = '发布记录'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.chapter.title} - {self.status}'

