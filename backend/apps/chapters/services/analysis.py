"""Heuristic analysis helpers used to backfill creative assets after generation."""

from __future__ import annotations

import re
from collections import Counter

from apps.novels.models import ForeshadowItem, KnowledgeFact, StyleProfile

SENTENCE_RE = re.compile(r'(?<=[。！？?!])')
NON_WHITESPACE_RE = re.compile(r'\S')
CHINESE_PHRASE_RE = re.compile(r'[\u4e00-\u9fff]{4,8}')
DIALOGUE_MARKER_RE = re.compile(r'[“”「」『』"]')
ACTION_HINT_RE = re.compile(
    r'(发现|进入|离开|追查|追踪|质问|决定|揭开|暴露|潜入|逃离|收到|确认|锁定|怀疑|救下|袭击|反击|调查|谈判|搜查|交手|对峙|得知|看见|看到)'
)
TENSION_KEYWORDS = (
    '危险', '危机', '威胁', '真相', '秘密', '追击', '追杀', '冲突', '对峙',
    '失控', '崩塌', '血', '杀', '爆炸', '质问', '怀疑', '异常', '反击', '暴露',
)
Cliche_Snippets = (
    '嘴角微微上扬',
    '倒吸了一口凉气',
    '瞳孔骤缩',
    '心头一震',
    '不由得',
    '空气仿佛凝固',
    '时间仿佛静止',
    '深吸一口气',
    '头皮发麻',
)
EVENT_KIND_KEYWORDS = (
    ('action', ('追', '打', '杀', '战', '交手', '突袭', '反击', '冲出', '逃离')),
    ('reveal', ('发现', '真相', '秘密', '揭开', '得知', '暴露', '线索')),
    ('investigation', ('调查', '追查', '搜查', '试探', '潜入', '锁定', '怀疑')),
    ('conflict', ('质问', '对峙', '争吵', '谈判', '冲突', '逼问')),
    ('emotion', ('心头', '沉默', '犹豫', '悲伤', '愤怒', '和解', '告白')),
)


def _split_sentences(content: str) -> list[str]:
    return [part.strip() for part in SENTENCE_RE.split(content or '') if part.strip()]


def _known_names(project) -> tuple[list[str], list[str]]:
    characters: list[str] = []
    regions: list[str] = []
    for setting in project.settings.all():
        structured = setting.structured_data or {}
        if setting.setting_type == 'characters':
            characters.extend([
                item.get('name', '').strip()
                for item in structured.get('characters', [])
                if item.get('name')
            ])
        elif setting.setting_type == 'map':
            regions.extend([
                item.get('name', '').strip()
                for item in structured.get('regions', [])
                if item.get('name')
            ])
    return characters[:20], regions[:20]


def _collect_repeated_phrases(content: str) -> list[str]:
    normalized = ''.join(str(content or '').split())
    if len(normalized) < 24:
        return []

    phrase_counter: Counter[str] = Counter()
    for match in CHINESE_PHRASE_RE.finditer(normalized):
        phrase = match.group(0)
        if len(set(phrase)) <= 2:
            continue
        phrase_counter[phrase] += 1

    repeated = [
        phrase
        for phrase, count in phrase_counter.most_common(8)
        if count >= 3
    ]
    return repeated[:5]


def _detect_cliches(content: str) -> list[str]:
    text = str(content or '')
    return [snippet for snippet in Cliche_Snippets if snippet in text][:5]


def _extract_entity_mentions(
    sentences: list[str],
    names: list[str],
    *,
    kind: str,
) -> list[dict[str, str | int]]:
    mentions: list[dict[str, str | int]] = []
    for name in names:
        matched_sentences = [sentence for sentence in sentences if name in sentence]
        if not matched_sentences:
            continue
        mentions.append({
            'name': name,
            'kind': kind,
            'count': len(matched_sentences),
            'evidence': matched_sentences[0][:180],
        })
    mentions.sort(key=lambda item: (-int(item['count']), str(item['name'])))
    return mentions[:8]


def _classify_event_kind(sentence: str) -> str:
    lowered = str(sentence or '').lower()
    for event_kind, keywords in EVENT_KIND_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            return event_kind
    return 'progress'


def _build_event_cards(
    sentences: list[str],
    characters: list[str],
    regions: list[str],
) -> list[dict[str, object]]:
    scored: list[tuple[int, int, dict[str, object]]] = []
    for index, sentence in enumerate(sentences):
        text = sentence.strip()
        if len(text) < 12:
            continue

        actors = [name for name in characters if name in text][:3]
        locations = [name for name in regions if name in text][:2]
        score = 0
        if ACTION_HINT_RE.search(text):
            score += 3
        if actors:
            score += min(len(actors), 2) * 2
        if locations:
            score += 1
        if '？' in text or '?' in text:
            score += 2
        if any(keyword in text for keyword in TENSION_KEYWORDS):
            score += 2
        if any(marker in text for marker in ('但', '却', '然而', '忽然', '最终', '没想到')):
            score += 1
        if score <= 0:
            continue

        event_kind = _classify_event_kind(text)
        tension_level = 'high' if score >= 6 else 'medium' if score >= 3 else 'low'
        event_label = text[:32] + ('…' if len(text) > 32 else '')
        scored.append((
            score,
            -index,
            {
                'label': event_label,
                'event_type': event_kind,
                'tension_level': tension_level,
                'actors': actors,
                'locations': locations,
                'evidence': text[:180],
            },
        ))

    scored.sort(key=lambda item: (-item[0], item[1]))
    cards: list[dict[str, object]] = []
    seen_labels: set[str] = set()
    for _score, _index, card in scored:
        label = str(card['label'])
        if label in seen_labels:
            continue
        seen_labels.add(label)
        cards.append(card)
        if len(cards) >= 4:
            break
    return cards


def derive_chapter_asset_snapshot(project, content: str) -> dict[str, list[dict[str, object]]]:
    """Derive lightweight chapter assets from content without writing to the database."""
    sentences = _split_sentences(content)
    characters, regions = _known_names(project)
    return {
        'character_mentions': _extract_entity_mentions(sentences, characters, kind='character'),
        'location_mentions': _extract_entity_mentions(sentences, regions, kind='location'),
        'event_cards': _build_event_cards(sentences, characters, regions),
    }


def build_quality_diagnostics(content: str) -> dict:
    """Produce lightweight rhythm/tension/repetition diagnostics for a chapter."""
    normalized = str(content or '')
    sentences = _split_sentences(normalized)
    paragraphs = [
        part.strip()
        for part in re.split(r'\n{1,}', normalized)
        if part.strip()
    ]
    word_count = len(NON_WHITESPACE_RE.findall(normalized))
    sentence_lengths = [len(sentence) for sentence in sentences] or [0]
    average_sentence_length = round(sum(sentence_lengths) / len(sentence_lengths), 2)
    long_sentence_count = sum(1 for length in sentence_lengths if length >= 38)
    question_count = normalized.count('？') + normalized.count('?')
    exclamation_count = normalized.count('！') + normalized.count('!')
    dialogue_sentence_count = sum(
        1 for sentence in sentences if DIALOGUE_MARKER_RE.search(sentence)
    )
    dialogue_ratio = round(dialogue_sentence_count / max(len(sentences), 1), 2)
    duplicate_sentence_count = sum(
        count - 1
        for sentence, count in Counter(sentences).items()
        if len(sentence) >= 12 and count > 1
    )
    repeated_phrases = _collect_repeated_phrases(normalized)
    cliche_hits = _detect_cliches(normalized)

    ending_window = ''.join(sentences[-2:]) if sentences else normalized[-120:]
    has_ending_hook = any(marker in ending_window for marker in ('？', '?', '！', '!', '却', '然而', '没想到'))

    tension_hits = sum(normalized.count(keyword) for keyword in TENSION_KEYWORDS)
    tension_score = min(
        100,
        round(
            min(word_count / 18, 28)
            + question_count * 7
            + exclamation_count * 4
            + min(tension_hits * 5, 35)
            + (12 if has_ending_hook else 0)
        ),
    )

    issues: list[dict[str, str]] = []
    if word_count < 800:
        issues.append({
            'code': 'low_word_count',
            'severity': 'high',
            'message': '章节偏短，情节推进和场景展开可能不足。',
            'suggestion': '补足动作反应、环境细节或人物决策链，避免只给结论。',
        })
    if len(paragraphs) <= 1 and word_count >= 500:
        issues.append({
            'code': 'flat_paragraphs',
            'severity': 'medium',
            'message': '段落切分过少，阅读节奏偏闷。',
            'suggestion': '按动作、对话和情绪转折拆段，给读者留出呼吸点。',
        })
    if average_sentence_length >= 38 and long_sentence_count / max(len(sentence_lengths), 1) >= 0.35:
        issues.append({
            'code': 'long_sentences',
            'severity': 'medium',
            'message': '长句占比偏高，叙述容易拖慢节奏。',
            'suggestion': '把关键动作和判断拆成短句，减少多层并列信息堆叠。',
        })
    if dialogue_ratio < 0.08 and word_count >= 1000:
        issues.append({
            'code': 'low_dialogue_density',
            'severity': 'medium',
            'message': '对话密度偏低，人物关系和冲突不够具象。',
            'suggestion': '让冲突落到对话、试探和反问中，不要只写旁白总结。',
        })
    if duplicate_sentence_count >= 2 or repeated_phrases:
        issues.append({
            'code': 'repetition_risk',
            'severity': 'high' if duplicate_sentence_count >= 3 else 'medium',
            'message': '存在重复表达，章节语言可能显得机械。',
            'suggestion': '替换高频短语，压缩重复句式，让信息推进而不是原地复述。',
        })
    if len(cliche_hits) >= 2:
        issues.append({
            'code': 'cliche_risk',
            'severity': 'medium',
            'message': '套话痕迹偏明显，文风辨识度不足。',
            'suggestion': '优先改写套话句，换成角色专属反应和更具体的感官细节。',
        })
    if not has_ending_hook and len(sentences) >= 3:
        issues.append({
            'code': 'weak_ending_hook',
            'severity': 'medium',
            'message': '收尾钩子偏弱，读者继续追更的驱动力不够。',
            'suggestion': '结尾留一个未解问题、代价升级，或明确抛出下一步压力。',
        })

    score = 100
    for issue in issues:
        score -= {
            'high': 18,
            'medium': 10,
            'low': 6,
        }.get(issue['severity'], 6)
    score = max(18, score)

    if score >= 80:
        rhythm_status = 'steady'
    elif score >= 60:
        rhythm_status = 'needs_tune'
    else:
        rhythm_status = 'unstable'

    style_risk = 'low'
    if any(issue['severity'] == 'high' for issue in issues):
        style_risk = 'high'
    elif issues:
        style_risk = 'medium'

    return {
        'score': score,
        'tension_score': tension_score,
        'rhythm_status': rhythm_status,
        'style_risk': style_risk,
        'ending_hook': has_ending_hook,
        'repeated_phrases': repeated_phrases,
        'cliche_hits': cliche_hits,
        'issues': issues,
        'metrics': {
            'word_count': word_count,
            'paragraph_count': len(paragraphs),
            'sentence_count': len(sentences),
            'average_sentence_length': average_sentence_length,
            'dialogue_ratio': dialogue_ratio,
            'question_count': question_count,
            'exclamation_count': exclamation_count,
            'duplicate_sentence_count': duplicate_sentence_count,
        },
    }


def analyze_chapter_assets(project, chapter, content: str) -> dict:
    """Extract knowledge facts, foreshadow items, and style/consistency status."""
    sentences = _split_sentences(content)
    characters, regions = _known_names(project)
    quality = build_quality_diagnostics(content)
    asset_snapshot = derive_chapter_asset_snapshot(project, content)
    character_mentions = asset_snapshot['character_mentions']
    location_mentions = asset_snapshot['location_mentions']
    event_cards = asset_snapshot['event_cards']

    facts = []
    for name in characters:
        matching = next((sentence for sentence in sentences if name in sentence), '')
        if matching:
            facts.append({
                'subject': name,
                'predicate': '本章动向',
                'object': f'第{chapter.chapter_number}章出现',
                'source_excerpt': matching[:240],
                'confidence': 0.78,
                'status': 'confirmed',
            })

    for name in regions:
        matching = next((sentence for sentence in sentences if name in sentence), '')
        if matching:
            facts.append({
                'subject': name,
                'predicate': '章节地点',
                'object': f'第{chapter.chapter_number}章涉及',
                'source_excerpt': matching[:240],
                'confidence': 0.74,
                'status': 'confirmed',
            })

    if not facts and sentences:
        facts.append({
            'subject': f'第{chapter.chapter_number}章',
            'predicate': '关键事件',
            'object': sentences[0][:80],
            'source_excerpt': sentences[0][:240],
            'confidence': 0.68,
            'status': 'confirmed',
        })

    created_facts = 0
    for fact in facts[:10]:
        _, created = KnowledgeFact.objects.get_or_create(
            project=project,
            chapter=chapter,
            subject=fact['subject'],
            predicate=fact['predicate'],
            object=fact['object'],
            defaults={
                'source_excerpt': fact['source_excerpt'],
                'confidence': fact['confidence'],
                'status': fact['status'],
            },
        )
        created_facts += int(created)

    foreshadow_items = []
    for sentence in sentences:
        if '？' in sentence or '?' in sentence:
            foreshadow_items.append({
                'title': sentence[:80],
                'description': sentence[:220],
                'status': 'open',
            })

    created_foreshadow = 0
    for item in foreshadow_items[:5]:
        _, created = ForeshadowItem.objects.get_or_create(
            project=project,
            introduced_in_chapter=chapter,
            title=item['title'],
            defaults={
                'description': item['description'],
                'status': item['status'],
                'expected_payoff_chapter': chapter.chapter_number + 3,
                'related_character': '',
            },
        )
        created_foreshadow += int(created)

    baseline, _created = StyleProfile.objects.get_or_create(
        project=project,
        profile_type='chapter_analysis',
        defaults={
            'content': f'第{chapter.chapter_number}章风格分析',
            'structured_data': {},
        },
    )
    baseline.content = f'第{chapter.chapter_number}章风格分析'
    baseline.structured_data = {
        'chapter_number': chapter.chapter_number,
        'average_sentence_length': quality['metrics']['average_sentence_length'],
        'dialogue_density': quality['metrics']['dialogue_ratio'],
        'exclamation_density': round(
            quality['metrics']['exclamation_count'] / max(quality['metrics']['sentence_count'], 1),
            2,
        ),
        'tension_score': quality['tension_score'],
        'rhythm_status': quality['rhythm_status'],
        'risk_level': quality['style_risk'],
        'quality_score': quality['score'],
        'event_types': [str(item.get('event_type')) for item in event_cards[:4]],
    }
    baseline.save(update_fields=['content', 'structured_data', 'updated_at'])

    risk_items = []
    if chapter.word_count < 500:
        risk_items.append('章节字数偏低，可能影响节奏展开')
    if characters and not any(name in content for name in characters[:3]):
        risk_items.append('本章未触达主要角色，可能与主线推进脱节')
    if regions and not any(name in content for name in regions[:3]):
        risk_items.append('本章未引用核心地点信息，世界感可能偏弱')
    risk_items.extend(issue['message'] for issue in quality['issues'][:4])

    consistency_status = {
        'status': 'warning' if risk_items else 'ok',
        'conflicts': [],
        'risks': risk_items[:6],
        'checked_entities': characters[:5] + regions[:5],
        'quality': quality,
        'chapter_assets': {
            'event_cards': event_cards,
            'character_mentions': character_mentions,
            'location_mentions': location_mentions,
        },
    }

    return {
        'facts_created': created_facts,
        'foreshadow_created': created_foreshadow,
        'style_profile_id': baseline.id,
        'quality': quality,
        'consistency_status': consistency_status,
    }
