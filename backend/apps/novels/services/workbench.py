"""Workbench aggregation helpers."""

from __future__ import annotations

import re

from apps.chapters.models import Chapter, ChapterReview, ChapterSummary
from apps.chapters.serializers import ChapterReviewSerializer, ChapterSerializer, ChapterSummarySerializer
from apps.novels.knowledge_graph import build_graph_from_settings
from apps.novels.models import NovelSetting
from apps.novels.services.assets import build_chapter_asset_payload, build_generation_context
from apps.novels.serializers import (
    ForeshadowItemSerializer,
    KnowledgeFactSerializer,
    NovelProjectSerializer,
    NovelSettingSerializer,
    PlotArcPointSerializer,
    StorylineSerializer,
    StyleProfileSerializer,
)

TOKEN_RE = re.compile(r'[A-Za-z0-9_]+|[\u4e00-\u9fff]+')


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
        'workflow_gate': generation_context.get('workflow_gate') or {},
    }


def _tokenize(value) -> set[str]:
    tokens: set[str] = set()
    for chunk in TOKEN_RE.findall(str(value or '').lower()):
        if re.fullmatch(r'[\u4e00-\u9fff]+', chunk):
            if len(chunk) <= 4:
                tokens.add(chunk)
            tokens.update(chunk[index:index + 2] for index in range(max(len(chunk) - 1, 0)))
        elif len(chunk) > 1:
            tokens.add(chunk)
    return tokens


def _extract_setting_elements(settings_qs: list[NovelSetting]) -> dict[str, list[dict[str, str]]]:
    character_elements: list[dict[str, str]] = []
    location_elements: list[dict[str, str]] = []

    for setting in settings_qs:
        structured = setting.structured_data or {}

        if setting.setting_type == 'characters':
            for item in structured.get('characters', []) or []:
                name = str(item.get('name') or '').strip()
                if not name:
                    continue
                character_elements.append({
                    'name': name,
                    'role': str(item.get('role') or item.get('identity') or '').strip(),
                    'note': str(item.get('summary') or item.get('goal') or item.get('description') or '').strip(),
                })

        if setting.setting_type == 'map':
            for item in structured.get('regions', []) or []:
                name = str(item.get('name') or '').strip()
                if not name:
                    continue
                location_elements.append({
                    'name': name,
                    'type': str(item.get('type') or item.get('region_type') or '').strip(),
                    'note': str(item.get('description') or item.get('function') or '').strip(),
                })

    return {
        'characters': character_elements,
        'locations': location_elements,
    }


def _build_chapter_asset_index(
    chapters: list[Chapter],
    chapter_summaries: list[ChapterSummary],
    settings_qs: list[NovelSetting],
    knowledge_facts_all,
    foreshadow_items_all,
    review_by_chapter_id: dict[int, ChapterReview],
) -> dict[str, dict]:
    summary_by_chapter_id = {
        summary.chapter_id: summary
        for summary in chapter_summaries
    }
    facts_by_chapter_id: dict[int, list] = {}
    introduced_foreshadow_by_chapter_id: dict[int, list] = {}

    for fact in knowledge_facts_all:
        if fact.chapter_id:
            facts_by_chapter_id.setdefault(fact.chapter_id, []).append(fact)

    for item in foreshadow_items_all:
        if item.introduced_in_chapter_id:
            introduced_foreshadow_by_chapter_id.setdefault(item.introduced_in_chapter_id, []).append(item)

    setting_elements = _extract_setting_elements(settings_qs)
    chapter_asset_index: dict[str, dict] = {}

    for chapter in chapters:
        summary_record = summary_by_chapter_id.get(chapter.id)
        chapter_facts = facts_by_chapter_id.get(chapter.id, [])
        introduced_foreshadow_items = introduced_foreshadow_by_chapter_id.get(chapter.id, [])
        chapter_asset_payload = build_chapter_asset_payload(project=chapter.project, chapter=chapter, summary_record=summary_record)
        quality_payload = (chapter.consistency_status or {}).get('quality') or {}
        chapter_review = review_by_chapter_id.get(chapter.id)
        chapter_body = ' '.join(filter(None, [
            chapter.title,
            chapter.summary,
            getattr(summary_record, 'summary', ''),
            chapter.final_content,
            chapter.raw_content,
        ]))

        keyword_payload = [
            chapter.title,
            chapter.summary,
            *(chapter.open_threads or []),
            getattr(summary_record, 'summary', ''),
            *(getattr(summary_record, 'key_events', []) or []),
            *(getattr(summary_record, 'open_threads', []) or []),
            *[
                ' '.join(filter(None, [fact.subject, fact.predicate, fact.object]))
                for fact in chapter_facts
            ],
        ]
        chapter_keywords = _tokenize(' '.join(filter(None, keyword_payload)))
        chapter_text = ' '.join(filter(None, [chapter.title, chapter.summary, getattr(summary_record, 'summary', '')]))

        matched_characters = [
            item for item in setting_elements['characters']
            if item['name'] in chapter_body
        ][:8]
        matched_locations = [
            item for item in setting_elements['locations']
            if item['name'] in chapter_body
        ][:8]

        scored_recommendations: list[tuple[float, int, object]] = []
        for item in foreshadow_items_all:
            if item.status not in ('open', 'hinted'):
                continue

            introduced_chapter = getattr(item.introduced_in_chapter, 'chapter_number', None)
            if introduced_chapter and introduced_chapter >= chapter.chapter_number:
                continue

            score = 0.0
            if item.expected_payoff_chapter:
                if item.expected_payoff_chapter <= chapter.chapter_number + 1:
                    score += 6.0
                elif item.expected_payoff_chapter <= chapter.chapter_number + 3:
                    score += 2.5

            item_tokens = _tokenize(' '.join(filter(None, [
                item.title,
                item.description,
                item.related_character,
            ])))
            overlap = len(chapter_keywords & item_tokens)
            score += min(overlap, 4) * 1.5

            if item.related_character and item.related_character in chapter_text:
                score += 2.0

            if score <= 0:
                continue

            expected_payoff = item.expected_payoff_chapter or 10 ** 6
            scored_recommendations.append((score, expected_payoff, item))

        scored_recommendations.sort(key=lambda value: (-value[0], value[1], value[2].id))
        recommended_items = [item for _, _, item in scored_recommendations[:4]]

        character_mentions = chapter_asset_payload.get('character_mentions') or []
        location_mentions = chapter_asset_payload.get('location_mentions') or []
        event_cards = chapter_asset_payload.get('event_cards') or []
        repair_actions = []
        if chapter_review is not None:
            repair_actions.extend(chapter_review.ai_action_items or [])
            if chapter_review.review_notes:
                repair_actions.append(chapter_review.review_notes)
        repair_actions = [str(item).strip() for item in repair_actions if str(item).strip()][:4]

        chapter_asset_index[str(chapter.chapter_number)] = {
            'knowledge_facts': KnowledgeFactSerializer(chapter_facts[:8], many=True).data,
            'introduced_foreshadow_items': ForeshadowItemSerializer(introduced_foreshadow_items[:6], many=True).data,
            'recommended_foreshadow_items': ForeshadowItemSerializer(recommended_items, many=True).data,
            'character_elements': (
                [
                    {
                        'name': str(item.get('name') or ''),
                        'role': (
                            next(
                                (
                                    candidate.get('role', '')
                                    for candidate in matched_characters
                                    if candidate.get('name') == item.get('name')
                                ),
                                '',
                            )
                        ),
                        'note': str(item.get('evidence') or ''),
                    }
                    for item in character_mentions
                    if item.get('name')
                ]
                or matched_characters
            ),
            'location_elements': (
                [
                    {
                        'name': str(item.get('name') or ''),
                        'type': (
                            next(
                                (
                                    candidate.get('type', '')
                                    for candidate in matched_locations
                                    if candidate.get('name') == item.get('name')
                                ),
                                '',
                            )
                        ),
                        'note': str(item.get('evidence') or ''),
                    }
                    for item in location_mentions
                    if item.get('name')
                ]
                or matched_locations
            ),
            'event_cards': event_cards[:4],
            'quality_issues': (quality_payload.get('issues') or [])[:4],
            'repair_actions': repair_actions,
        }

    return chapter_asset_index


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
    chapter_reviews = list(
        ChapterReview.objects.select_related('chapter', 'reviewer')
        .filter(project=project)
        .order_by('chapter__chapter_number')
    )
    review_by_chapter_id = {
        item.chapter_id: item
        for item in chapter_reviews
    }
    storylines = list(project.storylines.all().order_by('-priority', 'estimated_chapter_start'))
    plot_arc_points = list(project.plot_arc_points.all().order_by('chapter_number'))
    knowledge_facts = list(project.knowledge_facts.all().order_by('-updated_at')[:30])
    foreshadow_items = list(project.foreshadow_items.all().order_by('status', '-updated_at')[:20])
    knowledge_facts_all = list(project.knowledge_facts.select_related('chapter').all())
    foreshadow_items_all = list(
        project.foreshadow_items.select_related('introduced_in_chapter').all()
    )
    style_profiles = list(project.style_profiles.all().order_by('profile_type', '-updated_at'))

    nodes, links = build_graph_from_settings(settings_qs)

    return {
        'project': NovelProjectSerializer(project).data,
        'stats': _build_workbench_stats(project, chapters),
        'chapters': ChapterSerializer(chapters, many=True).data,
        'settings': NovelSettingSerializer(settings_qs, many=True).data,
        'chapter_summaries': ChapterSummarySerializer(chapter_summaries, many=True).data,
        'chapter_reviews': ChapterReviewSerializer(chapter_reviews, many=True).data,
        'storylines': StorylineSerializer(storylines, many=True).data,
        'plot_arc_points': PlotArcPointSerializer(plot_arc_points, many=True).data,
        'knowledge_facts': KnowledgeFactSerializer(knowledge_facts, many=True).data,
        'foreshadow_items': ForeshadowItemSerializer(foreshadow_items, many=True).data,
        'chapter_asset_index': _build_chapter_asset_index(
            chapters,
            chapter_summaries,
            settings_qs,
            knowledge_facts_all,
            foreshadow_items_all,
            review_by_chapter_id,
        ),
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
