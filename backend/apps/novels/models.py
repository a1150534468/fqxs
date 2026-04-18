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
    source = models.CharField(
        max_length=20,
        choices=[
            ('wizard', '向导'),
            ('manual', '手动'),
            ('regenerated', '重新生成'),
            ('imported', '导入'),
        ],
        default='manual',
        verbose_name='来源',
    )
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
    style_preference = models.CharField(max_length=100, blank=True, default='', verbose_name='风格偏好')
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
    source = models.CharField(
        max_length=20,
        choices=NovelSetting._meta.get_field('source').choices,
        default='wizard',
        verbose_name='来源',
    )
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


class Storyline(models.Model):
    """Project-level storyline records."""

    STORYLINE_TYPES = [
        ('main', '主线'),
        ('subplot', '支线'),
        ('character', '角色线'),
        ('world', '世界线'),
    ]
    STATUS_CHOICES = [
        ('planned', '规划中'),
        ('active', '进行中'),
        ('resolved', '已完成'),
        ('paused', '暂停'),
    ]

    project = models.ForeignKey(
        NovelProject,
        on_delete=models.CASCADE,
        related_name='storylines',
        verbose_name='所属项目',
    )
    name = models.CharField(max_length=200, verbose_name='名称')
    storyline_type = models.CharField(
        max_length=20,
        choices=STORYLINE_TYPES,
        default='main',
        verbose_name='故事线类型',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name='状态',
    )
    description = models.TextField(blank=True, verbose_name='描述')
    estimated_chapter_start = models.IntegerField(default=1, verbose_name='预计起始章节')
    estimated_chapter_end = models.IntegerField(default=0, verbose_name='预计结束章节')
    priority = models.IntegerField(default=0, verbose_name='优先级')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'storyline'
        verbose_name = '故事线'
        verbose_name_plural = '故事线'
        ordering = ['-priority', 'estimated_chapter_start', 'created_at']
        indexes = [
            models.Index(fields=['project', 'status']),
        ]

    def __str__(self):
        return f'{self.project.title} - {self.name}'


class PlotArcPoint(models.Model):
    """Key tension or plot milestones mapped to chapter positions."""

    POINT_TYPES = [
        ('opening', '开篇'),
        ('setup', '铺垫'),
        ('turning', '转折'),
        ('climax', '高潮'),
        ('resolution', '收束'),
    ]

    project = models.ForeignKey(
        NovelProject,
        on_delete=models.CASCADE,
        related_name='plot_arc_points',
        verbose_name='所属项目',
    )
    related_storyline = models.ForeignKey(
        Storyline,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='plot_points',
        verbose_name='关联故事线',
    )
    chapter_number = models.IntegerField(default=1, verbose_name='章节号')
    point_type = models.CharField(
        max_length=20,
        choices=POINT_TYPES,
        default='setup',
        verbose_name='节点类型',
    )
    tension_level = models.IntegerField(default=50, verbose_name='张力等级')
    description = models.TextField(blank=True, verbose_name='描述')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'plot_arc_point'
        verbose_name = '情节点'
        verbose_name_plural = '情节点'
        ordering = ['chapter_number', 'created_at']
        indexes = [
            models.Index(fields=['project', 'chapter_number']),
        ]

    def __str__(self):
        return f'{self.project.title} - {self.chapter_number}'


class KnowledgeFact(models.Model):
    """Stable facts extracted from settings or generated chapters."""

    STATUS_CHOICES = [
        ('confirmed', '已确认'),
        ('draft', '待确认'),
        ('conflict', '冲突'),
    ]

    project = models.ForeignKey(
        NovelProject,
        on_delete=models.CASCADE,
        related_name='knowledge_facts',
        verbose_name='所属项目',
    )
    chapter = models.ForeignKey(
        'chapters.Chapter',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='knowledge_facts',
        verbose_name='来源章节',
    )
    subject = models.CharField(max_length=200, verbose_name='主语')
    predicate = models.CharField(max_length=100, verbose_name='谓语')
    object = models.CharField(max_length=255, verbose_name='宾语')
    source_excerpt = models.TextField(blank=True, verbose_name='来源片段')
    confidence = models.FloatField(default=0.7, verbose_name='置信度')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='confirmed',
        verbose_name='状态',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'knowledge_fact'
        verbose_name = '知识事实'
        verbose_name_plural = '知识事实'
        ordering = ['-updated_at', 'subject']
        indexes = [
            models.Index(fields=['project', 'status']),
        ]

    def __str__(self):
        return f'{self.subject} {self.predicate} {self.object}'


class ForeshadowItem(models.Model):
    """Ledger of open story hooks and foreshadow items."""

    STATUS_CHOICES = [
        ('open', '已埋设'),
        ('hinted', '已提示'),
        ('resolved', '已回收'),
        ('abandoned', '已废弃'),
    ]

    project = models.ForeignKey(
        NovelProject,
        on_delete=models.CASCADE,
        related_name='foreshadow_items',
        verbose_name='所属项目',
    )
    introduced_in_chapter = models.ForeignKey(
        'chapters.Chapter',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='introduced_foreshadow_items',
        verbose_name='引入章节',
    )
    title = models.CharField(max_length=200, verbose_name='标题')
    description = models.TextField(blank=True, verbose_name='描述')
    expected_payoff_chapter = models.IntegerField(default=0, verbose_name='预期回收章节')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='open',
        verbose_name='状态',
    )
    related_character = models.CharField(max_length=200, blank=True, verbose_name='关联角色')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'foreshadow_item'
        verbose_name = '伏笔项'
        verbose_name_plural = '伏笔项'
        ordering = ['status', '-updated_at']
        indexes = [
            models.Index(fields=['project', 'status']),
        ]

    def __str__(self):
        return f'{self.project.title} - {self.title}'


class StyleProfile(models.Model):
    """Project-level style baseline and latest analysis output."""

    PROFILE_TYPES = [
        ('project', '项目基线'),
        ('character_voice', '角色声音'),
        ('chapter_analysis', '章节分析'),
    ]

    project = models.ForeignKey(
        NovelProject,
        on_delete=models.CASCADE,
        related_name='style_profiles',
        verbose_name='所属项目',
    )
    profile_type = models.CharField(
        max_length=30,
        choices=PROFILE_TYPES,
        default='project',
        verbose_name='画像类型',
    )
    content = models.TextField(blank=True, verbose_name='画像内容')
    structured_data = models.JSONField(default=dict, blank=True, verbose_name='结构化画像')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'style_profile'
        verbose_name = '风格画像'
        verbose_name_plural = '风格画像'
        ordering = ['profile_type', '-updated_at']
        indexes = [
            models.Index(fields=['project', 'profile_type']),
        ]

    def __str__(self):
        return f'{self.project.title} - {self.profile_type}'
