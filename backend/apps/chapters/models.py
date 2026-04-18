from django.db import models


class Chapter(models.Model):
    """Individual chapter"""

    STATUS_CHOICES = [
        ('generating', '生成中'),
        ('draft', '草稿'),
        ('published', '已发布'),
        ('failed', '生成失败'),
    ]

    project = models.ForeignKey(
        'novels.NovelProject',
        on_delete=models.CASCADE,
        related_name='chapters',
        verbose_name='所属项目',
    )
    chapter_number = models.IntegerField(verbose_name='章节序号')
    title = models.CharField(max_length=200, blank=True, null=True, verbose_name='章节标题')
    raw_content = models.TextField(blank=True, null=True, verbose_name='AI 原始内容')
    final_content = models.TextField(blank=True, null=True, verbose_name='人工审核后内容')
    word_count = models.IntegerField(default=0, verbose_name='字数')
    generation_prompt = models.TextField(blank=True, null=True, verbose_name='生成 Prompt')
    generation_meta = models.JSONField(default=dict, blank=True, verbose_name='生成元数据')
    context_snapshot = models.JSONField(default=dict, blank=True, verbose_name='生成时上下文快照')
    summary = models.TextField(blank=True, null=True, verbose_name='章节摘要')
    open_threads = models.JSONField(default=list, blank=True, verbose_name='开放线索')
    consistency_status = models.JSONField(default=dict, blank=True, verbose_name='一致性状态')
    llm_provider = models.ForeignKey(
        'llm_providers.LLMProvider',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chapters',
        verbose_name='使用的 LLM 服务',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='generating', verbose_name='状态')
    generated_at = models.DateTimeField(null=True, blank=True, verbose_name='生成时间')
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='审核时间')
    published_at = models.DateTimeField(null=True, blank=True, verbose_name='发布时间')
    tomato_chapter_id = models.CharField(max_length=100, blank=True, null=True, verbose_name='番茄小说章节 ID')
    read_count = models.IntegerField(default=0, verbose_name='阅读量')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_deleted = models.BooleanField(default=False, verbose_name='是否删除')

    class Meta:
        db_table = 'chapter'
        verbose_name = '章节'
        verbose_name_plural = '章节'
        unique_together = [['project', 'chapter_number']]
        indexes = [
            models.Index(fields=['status', '-generated_at']),
        ]
        ordering = ['project', 'chapter_number']

    def __str__(self):
        return f'{self.project.title} - 第{self.chapter_number}章'


class ChapterSummary(models.Model):
    """Structured summary asset generated from a chapter."""

    project = models.ForeignKey(
        'novels.NovelProject',
        on_delete=models.CASCADE,
        related_name='chapter_summaries',
        verbose_name='所属项目',
    )
    chapter = models.OneToOneField(
        Chapter,
        on_delete=models.CASCADE,
        related_name='summary_record',
        verbose_name='所属章节',
    )
    summary = models.TextField(blank=True, verbose_name='摘要')
    key_events = models.JSONField(default=list, blank=True, verbose_name='关键事件')
    open_threads = models.JSONField(default=list, blank=True, verbose_name='开放线索')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'chapter_summary'
        verbose_name = '章节摘要'
        verbose_name_plural = '章节摘要'
        ordering = ['chapter__chapter_number']
        indexes = [
            models.Index(fields=['project', 'updated_at']),
        ]

    def __str__(self):
        return f'{self.project.title} - 第{self.chapter.chapter_number}章摘要'
