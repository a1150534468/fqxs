"""Asset initialization and generation-context helpers for creative workflow."""

from __future__ import annotations

import json
import re
from typing import Any

from apps.chapters.services.analysis import derive_chapter_asset_snapshot
from apps.chapters.services.workflow import evaluate_generation_workflow_gate
from apps.chapters.models import ChapterSummary
from django.db.models import Q
from apps.novels.models import (
    ForeshadowItem,
    KnowledgeFact,
    NovelSetting,
    PlotArcPoint,
    Storyline,
    StyleProfile,
)

TOKEN_RE = re.compile(r'[A-Za-z0-9_]+|[\u4e00-\u9fff]+')


def _trim(value: Any, limit: int = 240) -> str:
    text = str(value or '').strip()
    if len(text) <= limit:
        return text
    return f'{text[:limit - 1]}…'


def _safe_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _compact_json(value: Any) -> str:
    if not value:
        return ''
    return _trim(json.dumps(value, ensure_ascii=False, sort_keys=True), 320)


def _tokenize(value: Any) -> list[str]:
    tokens: list[str] = []
    for chunk in TOKEN_RE.findall(str(value or '').lower()):
        if re.fullmatch(r'[\u4e00-\u9fff]+', chunk):
            if len(chunk) <= 4:
                tokens.append(chunk)
            tokens.extend(chunk[index:index + 2] for index in range(max(len(chunk) - 1, 0)))
        elif len(chunk) > 1:
            tokens.append(chunk)
    return tokens


def _score_text(value: Any, query_tokens: list[str]) -> float:
    text = str(value or '').lower()
    if not text:
        return 0

    candidate_tokens = set(_tokenize(text))
    overlap_score = sum(2 for token in query_tokens if token in candidate_tokens)
    substring_score = sum(3 for token in set(query_tokens) if len(token) >= 2 and token in text)
    return overlap_score + substring_score


def _rank_items(
    items: list[dict[str, Any]],
    query_texts: list[str],
    text_builder,
    *,
    limit: int,
    bonus_builder=None,
) -> list[dict[str, Any]]:
    query_tokens = _tokenize(' '.join(filter(None, query_texts)))
    decorated: list[tuple[float, int, dict[str, Any]]] = []

    for index, item in enumerate(items):
        score = _score_text(text_builder(item), query_tokens)
        if bonus_builder is not None:
            score += float(bonus_builder(item) or 0)
        decorated.append((score, index, item))

    decorated.sort(key=lambda item: (-item[0], item[1]))
    return [item for _, _, item in decorated[:limit]]


def _setting_map(project) -> dict[str, NovelSetting]:
    return {
        setting.setting_type: setting
        for setting in project.settings.all().order_by('order')
    }


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        text = str(value or '').strip()
        if not text or text in seen:
            continue
        seen.add(text)
        unique_values.append(text)
    return unique_values


def _simplify_quality_issues(quality: dict[str, Any]) -> list[dict[str, str]]:
    issues = _safe_list((quality or {}).get('issues'))
    simplified: list[dict[str, str]] = []
    for item in issues[:5]:
        if not isinstance(item, dict):
            continue
        simplified.append({
            'code': _trim(item.get('code'), 60),
            'severity': _trim(item.get('severity'), 30),
            'message': _trim(item.get('message'), 120),
            'suggestion': _trim(item.get('suggestion'), 160),
        })
    return simplified


def build_chapter_asset_payload(project, chapter, summary_record: ChapterSummary | None = None) -> dict[str, list[dict[str, Any]]]:
    """Return persisted chapter assets, or derive a read-only fallback for legacy/manual chapters."""
    persisted_assets = ((chapter.consistency_status or {}).get('chapter_assets') or {})
    key_events = _safe_list(summary_record.key_events if summary_record else [])
    open_threads = _safe_list(summary_record.open_threads if summary_record else [])
    source_text = '\n'.join(filter(None, [
        chapter.final_content,
        chapter.raw_content,
        chapter.summary,
        summary_record.summary if summary_record else '',
        *key_events,
        *(chapter.open_threads or []),
        *open_threads,
    ]))
    derived_assets = derive_chapter_asset_snapshot(project, source_text) if source_text else {}

    event_cards = _safe_list(persisted_assets.get('event_cards'))
    if not event_cards:
        event_cards = _safe_list(derived_assets.get('event_cards'))
    if not event_cards:
        event_cards = [
            {
                'label': _trim(event, 48),
                'event_type': 'progress',
                'tension_level': 'medium',
                'actors': [],
                'locations': [],
                'evidence': _trim(event, 180),
            }
            for event in key_events[:4]
            if str(event or '').strip()
        ]
    if not event_cards and chapter.summary:
        event_cards = [{
            'label': _trim(chapter.summary, 48),
            'event_type': 'progress',
            'tension_level': 'medium',
            'actors': [],
            'locations': [],
            'evidence': _trim(chapter.summary, 180),
        }]

    character_mentions = _safe_list(persisted_assets.get('character_mentions'))
    if not character_mentions:
        character_mentions = _safe_list(derived_assets.get('character_mentions'))

    location_mentions = _safe_list(persisted_assets.get('location_mentions'))
    if not location_mentions:
        location_mentions = _safe_list(derived_assets.get('location_mentions'))

    return {
        'event_cards': event_cards[:4],
        'character_mentions': character_mentions[:8],
        'location_mentions': location_mentions[:8],
    }


def _serialize_summary_payload(summary_record: ChapterSummary) -> dict[str, Any]:
    return {
        'chapter_number': summary_record.chapter.chapter_number,
        'summary': _trim(summary_record.summary, 220),
        'open_threads': _safe_list(summary_record.open_threads)[:5],
    }


def _build_related_chapter_recalls(
    project,
    chapter_number: int,
    query_texts: list[str],
    chapter_summaries: list[ChapterSummary],
) -> list[dict[str, Any]]:
    summary_by_chapter_id = {
        summary.chapter_id: summary
        for summary in chapter_summaries
    }
    query_tokens = _tokenize(' '.join(filter(None, query_texts)))
    query_token_set = set(query_tokens)

    target_chapter = (
        project.chapters.filter(is_deleted=False, chapter_number=chapter_number)
        .first()
    )
    target_summary = summary_by_chapter_id.get(target_chapter.id) if target_chapter else None
    target_assets = (
        build_chapter_asset_payload(project, target_chapter, target_summary)
        if target_chapter else {'event_cards': [], 'character_mentions': [], 'location_mentions': []}
    )
    target_characters = {
        str(item.get('name') or '').strip()
        for item in _safe_list(target_assets.get('character_mentions'))
        if str(item.get('name') or '').strip()
    }
    target_locations = {
        str(item.get('name') or '').strip()
        for item in _safe_list(target_assets.get('location_mentions'))
        if str(item.get('name') or '').strip()
    }

    candidate_chapters = list(
        project.chapters.select_related('review_record')
        .filter(is_deleted=False, chapter_number__lt=chapter_number)
        .order_by('-chapter_number')[:12]
    )

    decorated: list[tuple[float, int, int, dict[str, Any]]] = []
    for chapter in candidate_chapters:
        summary_record = summary_by_chapter_id.get(chapter.id)
        chapter_assets = build_chapter_asset_payload(project, chapter, summary_record)
        key_events = _safe_list(summary_record.key_events if summary_record else [])[:4]
        open_threads = _dedupe_keep_order([
            *(_safe_list(chapter.open_threads)),
            *(_safe_list(summary_record.open_threads if summary_record else [])),
        ])[:4]
        summary_text = _trim(
            (summary_record.summary if summary_record else chapter.summary) or '',
            220,
        )
        event_labels = [
            str(item.get('label') or item.get('evidence') or '').strip()
            for item in _safe_list(chapter_assets.get('event_cards'))
            if isinstance(item, dict)
        ][:4]
        character_names = {
            str(item.get('name') or '').strip()
            for item in _safe_list(chapter_assets.get('character_mentions'))
            if str(item.get('name') or '').strip()
        }
        location_names = {
            str(item.get('name') or '').strip()
            for item in _safe_list(chapter_assets.get('location_mentions'))
            if str(item.get('name') or '').strip()
        }

        candidate_text = ' '.join(filter(None, [
            chapter.title,
            chapter.summary,
            summary_text,
            *key_events,
            *open_threads,
            *event_labels,
        ]))
        if not candidate_text.strip():
            continue

        gap = max(chapter_number - chapter.chapter_number, 1)
        score = float(_score_text(candidate_text, query_tokens))
        score += max(0, 12 - gap)

        thread_overlap = len(set(_tokenize(' '.join(open_threads))) & query_token_set)
        if thread_overlap:
            score += min(thread_overlap, 5) * 1.5

        shared_characters = sorted(target_characters & character_names)
        if shared_characters:
            score += min(len(shared_characters), 3) * 3

        shared_locations = sorted(target_locations & location_names)
        if shared_locations:
            score += min(len(shared_locations), 2) * 2

        chapter_review = getattr(chapter, 'review_record', None)
        if chapter_review and chapter_review.status in {'pending', 'revise'}:
            score += 1.5

        reasons: list[str] = []
        if gap == 1:
            reasons.append('直接前章承接')
        if thread_overlap:
            reasons.append('线索与当前任务重合')
        if shared_characters:
            reasons.append(f"关联角色：{'、'.join(shared_characters[:2])}")
        if shared_locations:
            reasons.append(f"关联地点：{'、'.join(shared_locations[:2])}")
        if chapter_review and chapter_review.status in {'pending', 'revise'}:
            reasons.append(f"审阅状态：{chapter_review.status}")
        if not reasons:
            reasons.append('语义上与当前章节更接近')

        decorated.append((
            score,
            gap,
            -chapter.chapter_number,
            {
                'chapter_number': chapter.chapter_number,
                'title': chapter.title or f'第{chapter.chapter_number}章',
                'summary': summary_text,
                'key_events': key_events,
                'open_threads': open_threads,
                'review_status': chapter_review.status if chapter_review else 'missing',
                'relevance_score': round(score, 2),
                'why_selected': reasons[:3],
            },
        ))

    decorated.sort(key=lambda item: (-item[0], item[1], item[2]))
    return [item for _, _, _, item in decorated[:4]]


def _build_target_chapter_context(project, chapter_number: int) -> dict[str, Any]:
    target_chapter = (
        project.chapters.select_related('review_record')
        .filter(chapter_number=chapter_number, is_deleted=False)
        .order_by('-updated_at')
        .first()
    )
    if not target_chapter:
        return {
            'exists': False,
            'chapter_number': chapter_number,
        }

    summary_record = (
        ChapterSummary.objects
        .filter(project=project, chapter=target_chapter)
        .first()
    )
    review = getattr(target_chapter, 'review_record', None)
    consistency = target_chapter.consistency_status or {}
    quality = consistency.get('quality') or {}
    chapter_assets = build_chapter_asset_payload(project, target_chapter, summary_record)
    open_threads = _dedupe_keep_order([
        *(_safe_list(target_chapter.open_threads)),
        *(_safe_list(summary_record.open_threads if summary_record else [])),
    ])

    return {
        'exists': True,
        'chapter_id': target_chapter.id,
        'chapter_number': target_chapter.chapter_number,
        'title': target_chapter.title or f'第{target_chapter.chapter_number}章',
        'status': target_chapter.status,
        'summary': _trim(
            (summary_record.summary if summary_record else target_chapter.summary) or '',
            260,
        ),
        'key_events': _safe_list(summary_record.key_events if summary_record else [])[:5],
        'open_threads': open_threads[:5],
        'review': {
            'status': review.status if review else 'missing',
            'review_notes': _trim(review.review_notes if review else '', 220),
            'ai_review': _trim(review.ai_review if review else '', 220),
            'ai_action_items': _safe_list(review.ai_action_items if review else [])[:5],
            'modification_rate': review.modification_rate if review else None,
        },
        'consistency_risks': _safe_list(consistency.get('risks'))[:5],
        'chapter_assets': {
            'event_cards': _safe_list(chapter_assets.get('event_cards'))[:4],
            'character_mentions': _safe_list(chapter_assets.get('character_mentions'))[:6],
            'location_mentions': _safe_list(chapter_assets.get('location_mentions'))[:6],
        },
        'quality': {
            'score': quality.get('score'),
            'tension_score': quality.get('tension_score'),
            'rhythm_status': quality.get('rhythm_status'),
            'style_risk': quality.get('style_risk'),
            'issues': _simplify_quality_issues(quality),
        },
    }


def _join_values(values: list[str], limit: int = 3) -> str:
    selected = _dedupe_keep_order(values)[:limit]
    return '、'.join(selected)


def _extract_setting_anchor(setting: NovelSetting | None) -> str:
    if not setting:
        return ''

    structured = setting.structured_data or {}

    if setting.setting_type == 'worldview':
        return _join_values([
            structured.get('time_setting', ''),
            structured.get('place_setting', ''),
            structured.get('power_system', ''),
            structured.get('natural_laws', ''),
        ]) or _trim(setting.content, 180)

    if setting.setting_type == 'characters':
        characters = [
            f"{item.get('name', '')}（{item.get('role', '角色')}）"
            for item in _safe_list(structured.get('characters'))[:5]
            if item.get('name')
        ]
        return _join_values(characters, 5) or _trim(setting.content, 180)

    if setting.setting_type == 'map':
        regions = [
            f"{item.get('name', '')}（{item.get('type', '地点')}）"
            for item in _safe_list(structured.get('regions'))[:5]
            if item.get('name')
        ]
        return _join_values(regions, 5) or _trim(setting.content, 180)

    if setting.setting_type == 'storyline':
        return _join_values([
            structured.get('premise', ''),
            structured.get('central_conflict', ''),
            structured.get('stakes', ''),
        ]) or _trim(setting.content, 180)

    if setting.setting_type == 'plot_arc':
        acts = [
            item.get('description') or item.get('name') or ''
            for item in _safe_list(structured.get('acts'))[:4]
        ]
        return _join_values(acts, 4) or _trim(setting.content, 180)

    if setting.setting_type == 'opening':
        return _join_values([
            structured.get('scene', ''),
            structured.get('hook', ''),
            structured.get('first_chapter_goal', ''),
        ]) or _trim(setting.content, 180)

    return _trim(setting.content, 180)


def _classify_scene_kind(*texts: str) -> str:
    merged = ' '.join(texts).lower()

    keyword_groups = (
        ('battle', ('战斗', '打斗', '对决', '追杀', '追击', '围攻', '突袭', '搏杀')),
        ('reveal', ('真相', '发现', '揭露', '秘密', '档案', '线索', '证据')),
        ('emotion', ('告白', '诀别', '背叛', '和解', '悲伤', '心结', '情绪')),
        ('investigation', ('调查', '追查', '试探', '潜入', '搜查', '推理')),
        ('conflict', ('争吵', '冲突', '质问', '对峙', '谈判', '对抗')),
    )

    for scene_kind, keywords in keyword_groups:
        if any(keyword in merged for keyword in keywords):
            return scene_kind

    return 'transition'


def _build_micro_beats(
    chapter_number: int,
    chapter_goal: str,
    focus_card: dict[str, Any],
    open_threads: list[str],
) -> list[dict[str, Any]]:
    total_words = 2800 if chapter_number <= 3 else 3200
    scene_kind = _classify_scene_kind(
        chapter_goal,
        focus_card.get('conflict', ''),
        focus_card.get('key_turn', ''),
    )

    beat_templates: dict[str, list[dict[str, Any]]] = {
        'battle': [
            {'label': '开场压迫', 'focus': 'sensory', 'objective': '先让环境、敌我距离与危险信号落地。', 'ratio': 0.18},
            {'label': '试探交锋', 'focus': 'action', 'objective': '通过第一轮动作试探暴露双方优势与缺口。', 'ratio': 0.26},
            {'label': '代价升级', 'focus': 'emotion', 'objective': '把受伤、失手或代价写实，让角色做出更难选择。', 'ratio': 0.31},
            {'label': '余波挂钩', 'focus': 'dialogue', 'objective': '用结果和余波抛出下一轮更大的威胁。', 'ratio': 0.25},
        ],
        'reveal': [
            {'label': '线索落点', 'focus': 'sensory', 'objective': '先把线索出现的场景、媒介和异常感写清。', 'ratio': 0.2},
            {'label': '推理拼接', 'focus': 'dialogue', 'objective': '让角色通过对话或观察逐步拼起事实。', 'ratio': 0.28},
            {'label': '真相翻面', 'focus': 'emotion', 'objective': '揭露关键信息，并体现认知被改写后的情绪冲击。', 'ratio': 0.3},
            {'label': '新任务抛出', 'focus': 'action', 'objective': '让真相直接转化成下一章必须执行的新任务。', 'ratio': 0.22},
        ],
        'emotion': [
            {'label': '情绪铺底', 'focus': 'sensory', 'objective': '先用场景与细节把压抑、亲近或决裂氛围立住。', 'ratio': 0.2},
            {'label': '关系碰撞', 'focus': 'dialogue', 'objective': '通过对话推进关系，不要只写感受总结。', 'ratio': 0.3},
            {'label': '内心翻转', 'focus': 'emotion', 'objective': '把人物态度变化写成具体心理决断。', 'ratio': 0.28},
            {'label': '结果留痕', 'focus': 'action', 'objective': '让情绪变化落到具体行动或下一步承诺上。', 'ratio': 0.22},
        ],
        'investigation': [
            {'label': '目标锁定', 'focus': 'sensory', 'objective': '明确调查对象、现场信息与行动切入口。', 'ratio': 0.2},
            {'label': '取证推进', 'focus': 'action', 'objective': '让调查通过试探、潜入或搜查不断推进。', 'ratio': 0.3},
            {'label': '误判反咬', 'focus': 'emotion', 'objective': '加入一次误判或反制，抬高查证成本。', 'ratio': 0.27},
            {'label': '锁定下个线头', 'focus': 'dialogue', 'objective': '保留未解部分，但明确下一步调查方向。', 'ratio': 0.23},
        ],
        'conflict': [
            {'label': '气氛拉满', 'focus': 'sensory', 'objective': '先写紧绷氛围与双方隐性情绪。', 'ratio': 0.18},
            {'label': '正面交锋', 'focus': 'dialogue', 'objective': '把冲突写进对话和动作，不要只概括。', 'ratio': 0.32},
            {'label': '底牌翻出', 'focus': 'emotion', 'objective': '在冲突中暴露真正诉求、伤口或代价。', 'ratio': 0.28},
            {'label': '后果扩散', 'focus': 'action', 'objective': '冲突后必须留下新的局面变化。', 'ratio': 0.22},
        ],
        'transition': [
            {'label': '场景落位', 'focus': 'sensory', 'objective': '用环境与人物状态快速完成开场定位。', 'ratio': 0.2},
            {'label': '主任务推进', 'focus': 'dialogue', 'objective': '围绕本章目标推进一个核心事件。', 'ratio': 0.32},
            {'label': '阻力显形', 'focus': 'action', 'objective': '中段必须出现阻力、误差或新的压力源。', 'ratio': 0.26},
            {'label': '钩子收尾', 'focus': 'emotion', 'objective': '在章节尾部留下下一步行动或悬念。', 'ratio': 0.22},
        ],
    }

    templates = beat_templates.get(scene_kind, beat_templates['transition'])
    ending_hook = focus_card.get('ending_hook', '')
    conflict = focus_card.get('conflict', '')

    beats: list[dict[str, Any]] = []
    for index, template in enumerate(templates, start=1):
        objective = template['objective']
        if index == 2 and conflict:
            objective = f"{objective} 当前冲突核心：{_trim(conflict, 80)}"
        if index == len(templates) and ending_hook:
            objective = f"{objective} 收尾时把“{_trim(ending_hook, 48)}”挂出来。"
        if index == len(templates) - 1 and open_threads:
            objective = f"{objective} 记得触碰已有线索：{_trim(open_threads[0], 48)}。"

        beats.append({
            'index': index,
            'label': template['label'],
            'focus': template['focus'],
            'objective': objective,
            'target_words': max(240, round(total_words * template['ratio'])),
        })

    return beats


def _build_continuity_alerts(
    chapter_number: int,
    active_storyline: dict[str, Any] | None,
    recent_open_threads: list[str],
    due_foreshadow_items: list[dict[str, Any]],
    knowledge_facts: list[dict[str, Any]],
    review_feedback: list[dict[str, Any]],
) -> list[dict[str, str]]:
    alerts: list[dict[str, str]] = []

    if due_foreshadow_items:
        titles = '；'.join(item['title'] for item in due_foreshadow_items[:3])
        alerts.append({
            'level': 'warning',
            'title': '伏笔接近回收窗口',
            'detail': f'第{chapter_number}章附近应优先处理：{titles}',
        })

    if len(recent_open_threads) >= 5:
        alerts.append({
            'level': 'warning',
            'title': '开放线索偏多',
            'detail': '近期未收束线索已经堆积，本章更适合回收或聚焦，而不是继续扩坑。',
        })

    if active_storyline and active_storyline.get('estimated_chapter_end'):
        estimated_end = active_storyline['estimated_chapter_end']
        if estimated_end and chapter_number > estimated_end:
            alerts.append({
                'level': 'critical',
                'title': '主线进度落后',
                'detail': f"{active_storyline.get('name', '当前主线')}预计应在第{estimated_end}章前后收束，当前节奏需要加压。",
            })

    if not knowledge_facts:
        alerts.append({
            'level': 'info',
            'title': '稳定事实较少',
            'detail': '本章写作时尽量复用既有设定锚点，避免一次性引入太多新世界规则。',
        })

    if review_feedback:
        latest_feedback = review_feedback[0]
        latest_status = latest_feedback.get('status')
        latest_chapter = latest_feedback.get('chapter_number')
        if latest_status == 'revise':
            alerts.append({
                'level': 'critical',
                'title': '上一章仍需修订',
                'detail': f"第{latest_chapter}章审阅状态为“需修订”，应先处理：{_trim(latest_feedback.get('review_notes') or latest_feedback.get('ai_review') or '补齐审阅意见', 72)}",
            })
        elif latest_status == 'pending':
            alerts.append({
                'level': 'warning',
                'title': '上一章尚未审定',
                'detail': f'第{latest_chapter}章还未完成正式审阅，继续生成时要特别注意承接风险。',
            })
        if (latest_feedback.get('modification_rate') or 0) < 15:
            alerts.append({
                'level': 'warning',
                'title': '人工改稿幅度偏低',
                'detail': f"第{latest_chapter}章当前预估修改率仅 {latest_feedback.get('modification_rate') or 0}% ，后续章节容易继承原稿问题。",
            })

    return alerts


def initialize_project_assets(project) -> dict[str, int]:
    """Create the minimum storyline/facts/foreshadow/style assets after wizard completion."""
    settings = _setting_map(project)
    storyline_setting = settings.get('storyline')
    plot_arc_setting = settings.get('plot_arc')
    opening_setting = settings.get('opening')
    characters_setting = settings.get('characters')
    map_setting = settings.get('map')
    worldview_setting = settings.get('worldview')

    created_counts = {
        'storylines': 0,
        'plot_arc_points': 0,
        'knowledge_facts': 0,
        'foreshadow_items': 0,
        'style_profiles': 0,
    }

    if storyline_setting and not project.storylines.exists():
        structured = storyline_setting.structured_data or {}
        description = '\n'.join(filter(None, [
            _trim(structured.get('premise')),
            _trim(structured.get('central_conflict')),
            _trim(structured.get('stakes')),
        ]))
        storyline = Storyline.objects.create(
            project=project,
            name=storyline_setting.title or '主线故事线',
            storyline_type='main',
            status='active',
            description=description or _trim(storyline_setting.content),
            estimated_chapter_start=1,
            estimated_chapter_end=project.target_chapters or 0,
            priority=100,
        )
        created_counts['storylines'] += 1
    else:
        storyline = project.storylines.order_by('-priority', 'id').first()

    if plot_arc_setting and not project.plot_arc_points.exists():
        structured = plot_arc_setting.structured_data or {}
        acts = _safe_list(structured.get('acts'))
        count = max(len(acts), 1)
        for index, act in enumerate(acts or [{'name': '第一幕', 'description': _trim(plot_arc_setting.content), 'key_events': []}], start=1):
            estimated_chapter = max(1, round((project.target_chapters or 1) * index / count))
            point_type = 'setup'
            if index == 1:
                point_type = 'opening'
            elif index == count:
                point_type = 'climax'
            PlotArcPoint.objects.create(
                project=project,
                related_storyline=storyline,
                chapter_number=estimated_chapter,
                point_type=point_type,
                tension_level=min(100, 35 + index * 15),
                description=_trim(act.get('description') or act.get('name')),
            )
            created_counts['plot_arc_points'] += 1

    if characters_setting:
        for character in _safe_list((characters_setting.structured_data or {}).get('characters'))[:12]:
            defaults = {
                'source_excerpt': _trim(character.get('brief')),
                'confidence': 0.9,
                'status': 'confirmed',
            }
            _, created = KnowledgeFact.objects.get_or_create(
                project=project,
                chapter=None,
                subject=character.get('name') or '角色',
                predicate='角色定位',
                object=character.get('role') or _trim(character.get('brief') or '未设定'),
                defaults=defaults,
            )
            created_counts['knowledge_facts'] += int(created)

    if map_setting:
        for region in _safe_list((map_setting.structured_data or {}).get('regions'))[:12]:
            _, created = KnowledgeFact.objects.get_or_create(
                project=project,
                chapter=None,
                subject=region.get('name') or '地点',
                predicate='地理类型',
                object=region.get('type') or '区域',
                defaults={
                    'source_excerpt': _trim(region.get('description')),
                    'confidence': 0.85,
                    'status': 'confirmed',
                },
            )
            created_counts['knowledge_facts'] += int(created)

    if worldview_setting:
        worldview_data = worldview_setting.structured_data or {}
        for key, label in (
            ('time_setting', '时代设定'),
            ('place_setting', '空间格局'),
            ('power_system', '力量体系'),
            ('natural_laws', '世界法则'),
        ):
            value = worldview_data.get(key)
            if not value:
                continue
            _, created = KnowledgeFact.objects.get_or_create(
                project=project,
                chapter=None,
                subject=project.title,
                predicate=label,
                object=_trim(value, 120),
                defaults={
                    'source_excerpt': _trim(value),
                    'confidence': 0.8,
                    'status': 'confirmed',
                },
            )
            created_counts['knowledge_facts'] += int(created)

    if opening_setting and not project.foreshadow_items.exists():
        hook = (opening_setting.structured_data or {}).get('hook')
        if hook:
            ForeshadowItem.objects.create(
                project=project,
                title=_trim(hook, 80),
                description=_trim(opening_setting.content),
                expected_payoff_chapter=max(3, min(project.target_chapters or 3, 12)),
                status='open',
                related_character=(opening_setting.structured_data or {}).get('pov_character', ''),
            )
            created_counts['foreshadow_items'] += 1

    if not project.style_profiles.filter(profile_type='project').exists():
        opening_data = opening_setting.structured_data if opening_setting else {}
        StyleProfile.objects.create(
            project=project,
            profile_type='project',
            content=_trim(opening_setting.content if opening_setting else project.synopsis or project.outline or ''),
            structured_data={
                'genre': project.genre,
                'tone': opening_data.get('tone', ''),
                'themes': _safe_list((storyline_setting.structured_data if storyline_setting else {}).get('themes')),
            },
        )
        created_counts['style_profiles'] += 1

    return created_counts


def build_generation_context(project, chapter_number: int) -> dict[str, Any]:
    """Assemble the default generation context payload for writing a chapter."""
    workflow_gate = evaluate_generation_workflow_gate(
        project,
        chapter_number,
        block_on_pending=False,
        enforce_modification_rate=False,
    )
    target_chapter_context = _build_target_chapter_context(project, chapter_number)
    recent_summary_records = list(
        project.chapter_summaries.select_related('chapter')
        .filter(chapter__chapter_number__lt=chapter_number)
        .order_by('-chapter__chapter_number')[:12]
    )
    recent_summaries = [
        _serialize_summary_payload(summary)
        for summary in recent_summary_records[:5]
    ]

    settings = _setting_map(project)
    selected_settings = []
    for setting_type in ('worldview', 'characters', 'map', 'storyline', 'plot_arc', 'opening'):
        setting = settings.get(setting_type)
        if not setting:
            continue
        selected_settings.append({
            'setting_type': setting.setting_type,
            'title': setting.title or setting.get_setting_type_display(),
            'content': _trim(setting.content, 320),
            'structured_data': setting.structured_data or {},
        })

    storylines = [
        {
            'id': item.id,
            'name': item.name,
            'description': _trim(item.description, 180),
            'status': item.status,
            'storyline_type': item.storyline_type,
            'estimated_chapter_start': item.estimated_chapter_start,
            'estimated_chapter_end': item.estimated_chapter_end,
            'priority': item.priority,
        }
        for item in project.storylines.order_by('-priority', 'estimated_chapter_start')[:5]
    ]

    plot_points = [
        {
            'id': item.id,
            'chapter_number': item.chapter_number,
            'point_type': item.point_type,
            'tension_level': item.tension_level,
            'description': _trim(item.description, 160),
            'related_storyline': item.related_storyline_id,
            'related_storyline_name': item.related_storyline.name if item.related_storyline_id else '',
        }
        for item in project.plot_arc_points.order_by('chapter_number')[:8]
    ]

    chapter_goal = ''
    for point in plot_points:
        if point['chapter_number'] >= chapter_number:
            chapter_goal = point['description']
            break
    if not chapter_goal and plot_points:
        chapter_goal = plot_points[-1]['description']

    active_storyline = next(
        (
            item for item in storylines
            if item['status'] == 'active'
            and (item.get('estimated_chapter_start') or 1) <= chapter_number
            and (
                not item.get('estimated_chapter_end')
                or chapter_number <= item['estimated_chapter_end']
            )
        ),
        storylines[0] if storylines else None,
    )
    current_plot_point = next(
        (item for item in plot_points if item['chapter_number'] >= chapter_number),
        plot_points[-1] if plot_points else None,
    )

    knowledge_facts = [
        {
            'subject': item.subject,
            'predicate': item.predicate,
            'object': item.object,
            'chapter_number': item.chapter.chapter_number if item.chapter_id else None,
            'source_excerpt': _trim(item.source_excerpt, 180),
        }
        for item in (
            project.knowledge_facts.filter(status='confirmed')
            .filter(Q(chapter__isnull=True) | Q(chapter__chapter_number__lt=chapter_number))
            .order_by('-updated_at')[:24]
        )
    ]

    foreshadow_items = [
        {
            'id': item.id,
            'title': item.title,
            'description': _trim(item.description, 120),
            'status': item.status,
            'expected_payoff_chapter': item.expected_payoff_chapter,
            'related_character': item.related_character,
        }
        for item in (
            project.foreshadow_items.exclude(status='resolved')
            .filter(
                Q(introduced_in_chapter__isnull=True)
                | Q(introduced_in_chapter__chapter_number__lt=chapter_number)
            )
            .order_by('expected_payoff_chapter', '-updated_at')[:20]
        )
    ]

    style_profile = project.style_profiles.filter(profile_type='project').order_by('-updated_at').first()
    review_feedback = [
        {
            'chapter_number': item.chapter.chapter_number,
            'status': item.status,
            'review_notes': _trim(item.review_notes, 180),
            'ai_review': _trim(item.ai_review, 180),
            'ai_action_items': _safe_list(item.ai_action_items)[:4],
            'modification_rate': item.modification_rate,
        }
        for item in (
            project.chapter_reviews.select_related('chapter')
            .filter(chapter__chapter_number__lt=chapter_number)
            .exclude(status='approved', review_notes='', ai_review='')
            .order_by('-chapter__chapter_number')[:4]
        )
    ]

    nearby_plot_points = [
        point for point in plot_points
        if abs((point.get('chapter_number') or chapter_number) - chapter_number) <= 3
    ]
    query_texts = [
        project.title,
        project.genre,
        project.synopsis or '',
        chapter_goal,
        target_chapter_context.get('summary') or '',
        *((target_chapter_context.get('key_events') or [])[:3]),
        (
            ((target_chapter_context.get('review') or {}).get('review_notes'))
            or ((target_chapter_context.get('review') or {}).get('ai_review'))
            or ''
        ),
        *(point.get('description') or '' for point in nearby_plot_points[:3]),
        *(item.get('summary') or '' for item in recent_summaries[:3]),
        *(item.get('review_notes') or item.get('ai_review') or '' for item in review_feedback[:2]),
    ]

    selected_settings = _rank_items(
        selected_settings,
        query_texts,
        lambda item: ' '.join([
            item.get('setting_type', ''),
            item.get('title', ''),
            item.get('content', ''),
            _compact_json(item.get('structured_data')),
        ]),
        limit=6,
    )
    storylines = _rank_items(
        storylines,
        query_texts,
        lambda item: ' '.join([item.get('name', ''), item.get('description', '')]),
        limit=5,
        bonus_builder=lambda item: (
            (item.get('priority') or 0) / 20
            + (8 if item.get('status') == 'active' else 0)
            + (
                10
                if (
                    (item.get('estimated_chapter_start') or 0) <= chapter_number
                    and (
                        not item.get('estimated_chapter_end')
                        or chapter_number <= item.get('estimated_chapter_end')
                    )
                )
                else 0
            )
        ),
    )
    plot_points = _rank_items(
        plot_points,
        query_texts,
        lambda item: item.get('description', ''),
        limit=8,
        bonus_builder=lambda item: max(0, 12 - abs((item.get('chapter_number') or 0) - chapter_number) * 4),
    )
    knowledge_facts = _rank_items(
        knowledge_facts,
        query_texts,
        lambda item: ' '.join([
            item.get('subject', ''),
            item.get('predicate', ''),
            item.get('object', ''),
            item.get('source_excerpt', ''),
        ]),
        limit=12,
        bonus_builder=lambda item: (
            max(0, 6 - abs((item.get('chapter_number') or chapter_number) - chapter_number) * 2)
            if item.get('chapter_number') is not None
            else 2
        ),
    )
    foreshadow_items = _rank_items(
        foreshadow_items,
        query_texts,
        lambda item: ' '.join([item.get('title', ''), item.get('description', '')]),
        limit=8,
        bonus_builder=lambda item: (
            max(0, 10 - abs((item.get('expected_payoff_chapter') or chapter_number) - chapter_number))
            + (4 if item.get('status') in {'open', 'hinted'} else 0)
        ),
    )
    retrieved_chapters = _build_related_chapter_recalls(
        project=project,
        chapter_number=chapter_number,
        query_texts=[
            *query_texts,
            *(item.get('title') or '' for item in foreshadow_items[:4]),
            *(item.get('subject') or '' for item in knowledge_facts[:4]),
            *(item.get('object') or '' for item in knowledge_facts[:4]),
        ],
        chapter_summaries=recent_summary_records,
    )

    recent_open_threads = _dedupe_keep_order([
        thread
        for summary in recent_summaries
        for thread in summary.get('open_threads', [])
    ])
    due_foreshadow_items = [
        item for item in foreshadow_items
        if (item.get('expected_payoff_chapter') or chapter_number) <= chapter_number + 1
    ][:4]
    target_review = target_chapter_context.get('review') or {}
    target_assets = target_chapter_context.get('chapter_assets') or {}
    review_actions = _dedupe_keep_order([
        *[
            action
            for action in _safe_list(target_review.get('ai_action_items'))
            if str(action or '').strip()
        ],
        target_review.get('review_notes') or target_review.get('ai_review') or '',
        *[
            issue.get('suggestion') or issue.get('message') or ''
            for issue in _safe_list((target_chapter_context.get('quality') or {}).get('issues'))
            if isinstance(issue, dict)
        ],
        *[
            str(item.get('label') or '')
            for item in _safe_list(target_assets.get('event_cards'))
            if isinstance(item, dict) and item.get('label')
        ],
        *[
            action
            for item in review_feedback[:2]
            for action in _safe_list(item.get('ai_action_items'))
            if str(action or '').strip()
        ],
        *[
            item.get('review_notes') or item.get('ai_review') or ''
            for item in review_feedback[:2]
        ],
    ])[:4]

    style_tone = ''
    style_themes: list[str] = []
    if style_profile:
        style_tone = _trim((style_profile.structured_data or {}).get('tone') or style_profile.content, 120)
        style_themes = _safe_list((style_profile.structured_data or {}).get('themes'))

    storyline_setting = settings.get('storyline')
    storyline_data = storyline_setting.structured_data if storyline_setting else {}

    focus_card = {
        'chapter_number': chapter_number,
        'mission': chapter_goal or (
            active_storyline.get('description') if active_storyline else ''
        ) or _extract_setting_anchor(storyline_setting) or '推进主线，并在本章留下明确的新压力。',
        'conflict': (
            storyline_data.get('central_conflict')
            or (current_plot_point or {}).get('description')
            or '让角色在推进目标时必须付出代价。'
        ),
        'key_turn': (
            (current_plot_point or {}).get('description')
            or '在章节后半段给出足以改变下一步行动的转折。'
        ),
        'emotional_note': style_tone or '情绪推进要贴着动作和对话走，不要空转抒情。',
        'ending_hook': (
            recent_open_threads[0]
            if recent_open_threads
            else (due_foreshadow_items[0]['title'] if due_foreshadow_items else '')
        ) or ((current_plot_point or {}).get('description') or '让下一章目标自然浮出水面。'),
        'must_keep': _dedupe_keep_order([
            f"{item.get('subject')} {item.get('predicate')} {item.get('object')}"
            for item in knowledge_facts[:4]
        ])[:4],
        'must_payoff': [
            item['title']
            for item in due_foreshadow_items[:3]
        ],
        'must_fix': review_actions[:3],
        'avoid': _dedupe_keep_order([
            '不要一次性解决所有开放线索',
            '不要引入未经铺垫的新设定替代现有冲突',
            '不要让角色动机与前文已确认事实脱节',
            '不要用总结性旁白替代具体场景推进',
        ])[:4],
    }

    micro_beats = _build_micro_beats(
        chapter_number=chapter_number,
        chapter_goal=chapter_goal,
        focus_card=focus_card,
        open_threads=recent_open_threads,
    )
    continuity_alerts = _build_continuity_alerts(
        chapter_number=chapter_number,
        active_storyline=active_storyline,
        recent_open_threads=recent_open_threads,
        due_foreshadow_items=due_foreshadow_items,
        knowledge_facts=knowledge_facts,
        review_feedback=review_feedback,
    )

    context_layers = {
        'foundation': _dedupe_keep_order([
            f"世界底层：{_extract_setting_anchor(settings.get('worldview'))}",
            f"角色阵列：{_extract_setting_anchor(settings.get('characters'))}",
            f"地理舞台：{_extract_setting_anchor(settings.get('map'))}",
            f"主线前提：{_extract_setting_anchor(storyline_setting)}",
            f"开篇承诺：{_extract_setting_anchor(settings.get('opening'))}",
            f"风格基调：{_join_values(style_themes, 4) if style_themes else style_tone}",
        ]),
        'continuity': _dedupe_keep_order([
            (
                f"当前章底稿摘要：{target_chapter_context.get('summary')}"
                if target_chapter_context.get('exists') and target_chapter_context.get('summary')
                else ''
            ),
            (
                f"当前章关键事件：{'；'.join(_safe_list(target_chapter_context.get('key_events'))[:4])}"
                if target_chapter_context.get('exists') and target_chapter_context.get('key_events')
                else ''
            ),
            (
                "当前章事件卡："
                + '；'.join(
                    _trim(item.get('label') or item.get('evidence') or '', 72)
                    for item in _safe_list(target_assets.get('event_cards'))[:4]
                    if isinstance(item, dict)
                )
                if target_chapter_context.get('exists') and target_assets.get('event_cards')
                else ''
            ),
            *[
                f"第{item['chapter_number']}章摘要：{item['summary']}"
                for item in recent_summaries[:3]
                if item.get('summary')
            ],
            *[
                (
                    f"关联章节：第{item['chapter_number']}章 {item.get('title', '')}。"
                    f"{item.get('summary', '')}"
                    f" 命中原因：{'；'.join(_safe_list(item.get('why_selected'))[:2])}"
                )
                for item in retrieved_chapters[:3]
                if item.get('summary')
            ],
            *[
                f"稳定事实：{item['subject']} {item['predicate']} {item['object']}"
                for item in knowledge_facts[:5]
            ],
            (
                f"开放线索：{'；'.join(recent_open_threads[:4])}"
                if recent_open_threads
                else ''
            ),
            (
                f"待回收伏笔：{'；'.join(item['title'] for item in due_foreshadow_items[:3])}"
                if due_foreshadow_items
                else ''
            ),
            *[
                f"第{item['chapter_number']}章审阅：{item['review_notes'] or item['ai_review']}"
                for item in review_feedback[:2]
                if item.get('review_notes') or item.get('ai_review')
            ],
            (
                f"当前章审阅：{target_review.get('review_notes') or target_review.get('ai_review')}"
                if target_chapter_context.get('exists')
                and (target_review.get('review_notes') or target_review.get('ai_review'))
                else ''
            ),
        ]),
        'tactical': _dedupe_keep_order([
            f"本章任务：{focus_card['mission']}",
            f"当前冲突：{focus_card['conflict']}",
            f"关键转折：{focus_card['key_turn']}",
            f"收尾钩子：{focus_card['ending_hook']}",
            (
                f"推进故事线：{active_storyline['name']}"
                if active_storyline
                else '推进故事线：优先让主线获得新的确定性信息'
            ),
            (
                f"优先修复：{'；'.join(review_actions[:3])}"
                if review_actions
                else ''
            ),
        ]),
    }

    return {
        'project': {
            'id': project.id,
            'title': project.title,
            'genre': project.genre,
            'synopsis': _trim(project.synopsis, 240),
            'outline': _trim(project.outline, 300),
        },
        'chapter_number': chapter_number,
        'chapter_goal': chapter_goal,
        'recent_summaries': recent_summaries,
        'selected_settings': selected_settings,
        'storylines': storylines,
        'plot_points': plot_points,
        'knowledge_facts': knowledge_facts,
        'foreshadow_items': foreshadow_items,
        'review_feedback': review_feedback,
        'target_chapter_context': target_chapter_context,
        'style_profile': {
            'content': _trim(style_profile.content, 220) if style_profile else '',
            'structured_data': style_profile.structured_data if style_profile else {},
        },
        'retrieved_chapters': retrieved_chapters,
        'workflow_gate': workflow_gate,
        'context_layers': context_layers,
        'focus_card': focus_card,
        'micro_beats': micro_beats,
        'continuity_alerts': continuity_alerts,
    }
