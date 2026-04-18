"""Heuristic analysis helpers used to backfill creative assets after generation."""

from __future__ import annotations

import re

from apps.novels.models import ForeshadowItem, KnowledgeFact, StyleProfile

SENTENCE_RE = re.compile(r'(?<=[。！？?!])')


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


def analyze_chapter_assets(project, chapter, content: str) -> dict:
    """Extract knowledge facts, foreshadow items, and style/consistency status."""
    sentences = _split_sentences(content)
    characters, regions = _known_names(project)

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

    sentence_lengths = [len(sentence) for sentence in sentences] or [0]
    average_sentence_length = round(sum(sentence_lengths) / len(sentence_lengths), 2)
    dialogue_density = round(content.count('“') / max(len(sentences), 1), 2)
    exclamation_density = round((content.count('！') + content.count('!')) / max(len(sentences), 1), 2)

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
        'average_sentence_length': average_sentence_length,
        'dialogue_density': dialogue_density,
        'exclamation_density': exclamation_density,
        'risk_level': 'medium' if exclamation_density > 0.6 else 'low',
    }
    baseline.save(update_fields=['content', 'structured_data', 'updated_at'])

    risk_items = []
    if chapter.word_count < 500:
        risk_items.append('章节字数偏低，可能影响节奏展开')
    if characters and not any(name in content for name in characters[:3]):
        risk_items.append('本章未触达主要角色，可能与主线推进脱节')
    if regions and not any(name in content for name in regions[:3]):
        risk_items.append('本章未引用核心地点信息，世界感可能偏弱')

    consistency_status = {
        'status': 'warning' if risk_items else 'ok',
        'conflicts': [],
        'risks': risk_items,
        'checked_entities': characters[:5] + regions[:5],
    }

    return {
        'facts_created': created_facts,
        'foreshadow_created': created_foreshadow,
        'style_profile_id': baseline.id,
        'consistency_status': consistency_status,
    }
