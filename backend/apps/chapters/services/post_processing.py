"""Lightweight post-processing helpers for generated chapters."""

from __future__ import annotations

import re

SENTENCE_SPLIT_RE = re.compile(r'(?<=[。！？?!])')
ACTION_HINT_RE = re.compile(
    r'(发现|得知|看到|进入|离开|追查|追踪|质问|交手|对峙|决定|揭开|暴露|潜入|逃离|收到|确认|锁定|怀疑|救下|袭击|反击|谈判|搜查|击退)'
)


def _normalize_text(content: str) -> str:
    return ' '.join((content or '').split())


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or '').strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _build_key_events(sentences: list[str]) -> list[str]:
    scored: list[tuple[int, int, str]] = []
    for index, sentence in enumerate(sentences):
        text = sentence.strip()
        if len(text) < 10:
            continue
        score = 0
        if ACTION_HINT_RE.search(text):
            score += 3
        if '？' in text or '?' in text:
            score += 2
        if any(marker in text for marker in ('但', '却', '然而', '忽然', '没想到', '最终')):
            score += 2
        if 14 <= len(text) <= 60:
            score += 1
        scored.append((score, -index, text[:180]))

    scored.sort(key=lambda item: (-item[0], -item[1]))
    selected = [item[2] for item in scored if item[0] > 0][:4]
    if not selected:
        selected = [sentence[:180] for sentence in sentences[:3]]
    return _dedupe_keep_order(selected)[:4]


def build_chapter_summary_payload(content: str) -> dict:
    """Create a lightweight summary payload without requiring another LLM call."""
    normalized = _normalize_text(content)
    if not normalized:
        return {
            'summary': '',
            'key_events': [],
            'open_threads': [],
        }

    sentences = [part.strip() for part in SENTENCE_SPLIT_RE.split(normalized) if part.strip()]
    if not sentences:
        sentences = [normalized]

    key_events = _build_key_events(sentences)

    summary_parts: list[str] = []
    for sentence in key_events + sentences:
        if sum(len(part) for part in summary_parts) + len(sentence) > 180 and summary_parts:
            break
        summary_parts.append(sentence)

    open_threads = _dedupe_keep_order([
        sentence for sentence in sentences if '？' in sentence or '?' in sentence
    ])[:5]

    return {
        'summary': ''.join(summary_parts)[:220],
        'key_events': key_events,
        'open_threads': open_threads,
    }
