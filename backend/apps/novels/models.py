from django.conf import settings
from django.db import models


class NovelProject(models.Model):
    """Novel project"""

    STATUS_CHOICES = [
        ('active', '活跃'),
        ('paused', '暂停'),
        ('completed', '完结'),
        ('abandoned', '废弃'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='novels',
        verbose_name='用户',
    )
    inspiration = models.ForeignKey(
        'inspirations.Inspiration',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='novels',
        verbose_name='创意来源',
    )
    title = models.CharField(max_length=200, verbose_name='书名')
    genre = models.CharField(max_length=50, verbose_name='分类')
    synopsis = models.TextField(blank=True, null=True, verbose_name='简介')
    outline = models.TextField(blank=True, null=True, verbose_name='大纲')
    ai_prompt_template = models.TextField(blank=True, null=True, verbose_name='章节生成 Prompt 模板')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='状态')
    target_chapters = models.IntegerField(default=100, verbose_name='目标章节数')
    current_chapter = models.IntegerField(default=0, verbose_name='当前章节数')
    update_frequency = models.IntegerField(default=1, verbose_name='每日更新章节数')
    last_update_at = models.DateTimeField(null=True, blank=True, verbose_name='最后更新时间')
    tomato_book_id = models.CharField(max_length=100, blank=True, null=True, verbose_name='番茄小说书籍 ID')
    wizard_completed = models.BooleanField(default=False, verbose_name='向导是否完成')
    wizard_step = models.IntegerField(default=0, verbose_name='向导当前步骤')
    auto_generation_enabled = models.BooleanField(default=False, verbose_name='是否启用自动生成')
    generation_schedule = models.CharField(
        max_length=20,
        choices=[
            ('daily', '每天'),
            ('every_2_days', '每2天'),
            ('weekly', '每周'),
        ],
        default='daily',
        verbose_name='生成计划',
    )
    next_generation_time = models.DateTimeField(null=True, blank=True, verbose_name='下次生成时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_deleted = models.BooleanField(default=False, verbose_name='是否删除')

    class Meta:
        db_table = 'novel_project'
        verbose_name = '小说项目'
        verbose_name_plural = '小说项目'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'last_update_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class NovelSetting(models.Model):
    """Novel project setting (worldview, characters, map, etc.)"""

    SETTING_TYPES = [
        ('worldview', '世界观'),
        ('characters', '人物'),
        ('map', '地图'),
        ('storyline', '故事线'),
        ('plot_arc', '情节弧'),
        ('opening', '开始'),
    ]

    project = models.ForeignKey(
        NovelProject,
        on_delete=models.CASCADE,
        related_name='settings',
        verbose_name='所属项目',
    )
    setting_type = models.CharField(max_length=30, choices=SETTING_TYPES, verbose_name='设定类型')
    title = models.CharField(max_length=200, blank=True, verbose_name='标题')
    content = models.TextField(blank=True, verbose_name='详细内容')
    structured_data = models.JSONField(default=dict, blank=True, verbose_name='结构化数据')
    ai_generated = models.BooleanField(default=False, verbose_name='是否 AI 生成')
    order = models.IntegerField(default=0, verbose_name='排序')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'novel_setting'
        verbose_name = '小说设定'
        verbose_name_plural = '小说设定'
        unique_together = [['project', 'setting_type']]
        ordering = ['order']

    def __str__(self):
        return f'{self.project.title} - {self.get_setting_type_display()}'


class NovelDraft(models.Model):
    """12 步向导草稿，走完才转为 NovelProject"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='drafts',
        verbose_name='用户',
    )
    inspiration = models.TextField(verbose_name='灵感输入')
    title = models.CharField(max_length=200, blank=True, verbose_name='暂定书名')
    genre = models.CharField(max_length=50, blank=True, default='未分类', verbose_name='分类')
    current_step = models.IntegerField(default=0, verbose_name='当前步骤')
    is_completed = models.BooleanField(default=False, verbose_name='是否已完成转化')
    converted_project = models.ForeignKey(
        'NovelProject', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='source_draft',
        verbose_name='转化后的项目',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'novel_draft'
        verbose_name = '小说草稿'
        verbose_name_plural = '小说草稿'
        ordering = ['-updated_at']

    def __str__(self):
        return f'草稿: {self.title or self.inspiration[:30]}'


class DraftSetting(models.Model):
    """草稿阶段的设定，结构同 NovelSetting"""
    SETTING_TYPES = NovelSetting.SETTING_TYPES

    draft = models.ForeignKey(
        NovelDraft, on_delete=models.CASCADE,
        related_name='settings', verbose_name='所属草稿',
    )
    setting_type = models.CharField(max_length=30, choices=NovelSetting.SETTING_TYPES, verbose_name='设定类型')
    title = models.CharField(max_length=200, blank=True, verbose_name='标题')
    content = models.TextField(blank=True, verbose_name='详细内容')
    structured_data = models.JSONField(default=dict, blank=True, verbose_name='结构化数据')
    ai_generated = models.BooleanField(default=False, verbose_name='是否 AI 生成')
    order = models.IntegerField(default=0, verbose_name='排序')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'novel_draft_setting'
        verbose_name = '草稿设定'
        verbose_name_plural = '草稿设定'
        unique_together = [['draft', 'setting_type']]
        ordering = ['order']

    def __str__(self):
        return f'{self.draft} - {self.get_setting_type_display()}'
