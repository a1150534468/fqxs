"""Workbench aggregation helpers."""

from __future__ import annotations

from apps.chapters.models import Chapter, ChapterSummary
from apps.chapters.serializers import ChapterSerializer, ChapterSummarySerializer
from apps.novels.knowledge_graph import build_graph_from_settings
from apps.novels.models import NovelSetting
from apps.novels.services.assets import build_generation_context
from apps.novels.serializers import (
    ForeshadowItemSerializer,
    KnowledgeFactSerializer,
    NovelProjectSerializer,
    NovelSettingSerializer,
    PlotArcPointSerializer,
    StorylineSerializer,
    StyleProfileSerializer,
)


def _build_workbench_stats(project, chapters: list[Chapter]) -> dict:
    total_words = sum(chapter.word_count or 0 for chapter in chapters)
    finished_chapters = sum(
        1 for chapter in chapters if chapter.status in ('draft', 'published')
    )
    average_words = round(total_words / len(chapters)) if chapters else 0

    completion_basis = project.current_chapter or finished_chapters
    completion_rate = 0
    if project.target_chapters:
        completion_rate = min(
            100,
            round((completion_basis / project.target_chapters) * 100),
        )

    last_chapter = chapters[-1] if chapters else None
    last_update = (
        project.last_update_at
        or getattr(last_chapter, 'updated_at', None)
        or getattr(last_chapter, 'created_at', None)
    )

    return {
        'total_words': total_words,
        'finished_chapters': finished_chapters,
        'completion_rate': completion_rate,
        'average_words': average_words,
        'last_update': last_update.isoformat() if last_update else None,
    }


def _build_workbench_highlights(project, chapters: list[Chapter], style_profiles) -> dict:
    focus_chapter_number = project.current_chapter + 1
    if project.target_chapters:
        focus_chapter_number = min(focus_chapter_number, project.target_chapters)
    focus_chapter_number = max(1, focus_chapter_number)

    generation_context = build_generation_context(project, focus_chapter_number)
    latest_chapter = chapters[-1] if chapters else None
    latest_consistency = latest_chapter.consistency_status if latest_chapter else {}
    latest_style = next(
        (item for item in style_profiles if item.profile_type == 'chapter_analysis'),
        None,
    )
    latest_style_data = latest_style.structured_data if latest_style else {}
    project_style = next(
        (item for item in style_profiles if item.profile_type == 'project'),
        None,
    )
    project_style_data = project_style.structured_data if project_style else {}

    due_foreshadow_items = [
        item
        for item in generation_context.get('foreshadow_items', [])
        if (item.get('expected_payoff_chapter') or focus_chapter_number) <= focus_chapter_number + 1
    ]

    return {
        'focus_chapter_number': focus_chapter_number,
        'recommended_focus': generation_context.get('chapter_goal')
        or (generation_context.get('focus_card') or {}).get('mission', ''),
        'active_storyline': (
            generation_context.get('storylines') or [None]
        )[0],
        'nearest_plot_point': (
            generation_context.get('plot_points') or [None]
        )[0],
        'due_foreshadow_items': due_foreshadow_items[:4],
        'continuity_alerts': generation_context.get('continuity_alerts', [])[:4],
        'micro_beats': generation_context.get('micro_beats', [])[:4],
        'focus_card': generation_context.get('focus_card') or {},
        'quality_snapshot': {
            'consistency_status': latest_consistency.get('status') or 'pending',
            'consistency_risks': latest_consistency.get('risks') or [],
            'style_risk': latest_style_data.get('risk_level') or 'unknown',
            'style_tone': latest_style_data.get('tone')
            or project_style_data.get('tone')
            or '',
        },
    }


def build_workbench_context(project) -> dict:
    """Build the workbench context payload for a single project."""
    chapters = list(
        Chapter.objects.select_related('llm_provider')
        .filter(project=project, is_deleted=False)
        .order_by('chapter_number')
    )
    settings_qs = list(NovelSetting.objects.filter(project=project).order_by('order'))
    chapter_summaries = list(
        ChapterSummary.objects.select_related('chapter')
        .filter(project=project)
        .order_by('chapter__chapter_number')
    )
    storylines = list(project.storylines.all().order_by('-priority', 'estimated_chapter_start'))
    plot_arc_points = list(project.plot_arc_points.all().order_by('chapter_number'))
    knowledge_facts = list(project.knowledge_facts.all().order_by('-updated_at')[:30])
    foreshadow_items = list(project.foreshadow_items.all().order_by('status', '-updated_at')[:20])
    style_profiles = list(project.style_profiles.all().order_by('profile_type', '-updated_at'))

    nodes, links = build_graph_from_settings(settings_qs)

    return {
        'project': NovelProjectSerializer(project).data,
        'stats': _build_workbench_stats(project, chapters),
        'chapters': ChapterSerializer(chapters, many=True).data,
        'settings': NovelSettingSerializer(settings_qs, many=True).data,
        'chapter_summaries': ChapterSummarySerializer(chapter_summaries, many=True).data,
        'storylines': StorylineSerializer(storylines, many=True).data,
        'plot_arc_points': PlotArcPointSerializer(plot_arc_points, many=True).data,
        'knowledge_facts': KnowledgeFactSerializer(knowledge_facts, many=True).data,
        'foreshadow_items': ForeshadowItemSerializer(foreshadow_items, many=True).data,
        'style_profiles': StyleProfileSerializer(style_profiles, many=True).data,
        'workbench_highlights': _build_workbench_highlights(project, chapters, style_profiles),
        'knowledge_graph': {
            'project_id': project.id,
            'nodes': nodes,
            'links': links,
            'categories': [
                {'name': 'character'},
                {'name': 'region'},
                {'name': 'faction'},
                {'name': 'plot'},
            ],
        },
    }
