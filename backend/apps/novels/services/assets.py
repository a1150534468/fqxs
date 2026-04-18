"""Asset initialization and generation-context helpers for creative workflow."""

from __future__ import annotations

import json
import re
from typing import Any

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
    recent_summaries = [
        {
            'chapter_number': summary.chapter.chapter_number,
            'summary': _trim(summary.summary, 220),
            'open_threads': summary.open_threads[:5],
        }
        for summary in project.chapter_summaries.select_related('chapter').order_by('-chapter__chapter_number')[:5]
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
        for item in project.knowledge_facts.filter(status='confirmed').order_by('-updated_at')[:12]
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
        for item in project.foreshadow_items.exclude(status='resolved').order_by('expected_payoff_chapter', '-updated_at')[:8]
    ]

    style_profile = project.style_profiles.filter(profile_type='project').order_by('-updated_at').first()

    nearby_plot_points = [
        point for point in plot_points
        if abs((point.get('chapter_number') or chapter_number) - chapter_number) <= 3
    ]
    query_texts = [
        project.title,
        project.genre,
        project.synopsis or '',
        chapter_goal,
        *(point.get('description') or '' for point in nearby_plot_points[:3]),
        *(item.get('summary') or '' for item in recent_summaries[:3]),
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

    recent_open_threads = _dedupe_keep_order([
        thread
        for summary in recent_summaries
        for thread in summary.get('open_threads', [])
    ])
    due_foreshadow_items = [
        item for item in foreshadow_items
        if (item.get('expected_payoff_chapter') or chapter_number) <= chapter_number + 1
    ][:4]

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
            *[
                f"第{item['chapter_number']}章摘要：{item['summary']}"
                for item in recent_summaries[:3]
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
        'style_profile': {
            'content': _trim(style_profile.content, 220) if style_profile else '',
            'structured_data': style_profile.structured_data if style_profile else {},
        },
        'context_layers': context_layers,
        'focus_card': focus_card,
        'micro_beats': micro_beats,
        'continuity_alerts': continuity_alerts,
    }
