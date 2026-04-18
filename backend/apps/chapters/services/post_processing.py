"""Lightweight post-processing helpers for generated chapters."""

from __future__ import annotations

import re

SENTENCE_SPLIT_RE = re.compile(r'(?<=[。！？?!])')


def _normalize_text(content: str) -> str:
    return ' '.join((content or '').split())


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

    summary_parts: list[str] = []
    for sentence in sentences:
        if sum(len(part) for part in summary_parts) + len(sentence) > 180 and summary_parts:
            break
        summary_parts.append(sentence)

    open_threads = [
        sentence for sentence in sentences if '？' in sentence or '?' in sentence
    ][:5]

    return {
        'summary': ''.join(summary_parts)[:220],
        'key_events': sentences[:3],
        'open_threads': open_threads,
    }
