from django.db import models


class Stats(models.Model):
    """Daily statistics"""

    METRIC_TYPES = [
        ('generation', '生成统计'),
        ('cost', '成本统计'),
        ('performance', '性能统计'),
    ]

    date = models.DateField(verbose_name='日期')
    metric_type = models.CharField(max_length=20, choices=METRIC_TYPES, verbose_name='指标类型')
    metric_data = models.JSONField(default=dict, verbose_name='指标数据')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'stats'
        verbose_name = '统计数据'
        verbose_name_plural = '统计数据'
        unique_together = [['date', 'metric_type']]
        ordering = ['-date', 'metric_type']

    def __str__(self):
        return f'{self.date} - {self.metric_type}'
