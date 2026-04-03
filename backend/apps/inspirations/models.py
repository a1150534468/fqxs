from django.db import models


class Inspiration(models.Model):
    """Creative inspiration from novel ranking lists"""

    source_url = models.URLField(max_length=500, verbose_name='来源链接')
    title = models.CharField(max_length=200, verbose_name='书名')
    synopsis = models.TextField(blank=True, null=True, verbose_name='简介')
    tags = models.JSONField(default=list, verbose_name='标签')
    hot_score = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='热度分数')
    rank_type = models.CharField(max_length=50, blank=True, null=True, verbose_name='榜单类型')
    collected_at = models.DateTimeField(auto_now_add=True, verbose_name='采集时间')
    is_used = models.BooleanField(default=False, verbose_name='是否已使用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'inspiration'
        verbose_name = '创意'
        verbose_name_plural = '创意'
        indexes = [
            models.Index(fields=['is_used', '-hot_score']),
            models.Index(fields=['-collected_at']),
        ]
        ordering = ['-hot_score', '-collected_at']

    def __str__(self):
        return f'{self.title} ({self.hot_score})'
