"""Heuristic helpers for chapter review workflows."""

from __future__ import annotations

import re

from django.utils import timezone

from apps.chapters.models import ChapterReview
from apps.chapters.services.analysis import build_quality_diagnostics

SENTENCE_RE = re.compile(r'(?<=[。！？?!])')


def _compact_text(content: str) -> str:
    return ''.join((content or '').split())


def estimate_modification_rate(raw_content: str | None, final_content: str | None) -> int:
    """Estimate how much the reviewed draft diverges from the raw AI output."""
    original = _compact_text(raw_content or '')
    revised = _compact_text(final_content or '')

    if not original:
        return 100 if revised else 0

    compare_length = min(len(original), len(revised))
    same_count = 0
    for index in range(compare_length):
        if original[index] == revised[index]:
            same_count += 1

    denominator = max(len(original), len(revised), 1)
    return max(0, round((1 - (same_count / denominator)) * 100))


def build_ai_review_payload(chapter) -> dict:
    """Build an AI-style review suggestion without another model call."""
    content = chapter.final_content or chapter.raw_content or ''
    sentences = [part.strip() for part in SENTENCE_RE.split(content) if part.strip()]
    summary = chapter.summary or ''.join(sentences[:2])[:160]
    open_threads = [str(item).strip() for item in (chapter.open_threads or []) if str(item).strip()]
    consistency_risks = [
        str(item).strip()
        for item in (chapter.consistency_status or {}).get('risks', [])
        if str(item).strip()
    ]
    quality = (chapter.consistency_status or {}).get('quality') or build_quality_diagnostics(content)
    quality_issues = quality.get('issues') or []
    modification_rate = estimate_modification_rate(chapter.raw_content, chapter.final_content)

    strengths: list[str] = []
    if summary:
        strengths.append('本章主事件已经可被快速复述')
    if open_threads:
        strengths.append('章节结尾保留了后续推进空间')
    if chapter.word_count >= 1200:
        strengths.append('篇幅基本支撑起单章节奏')
    if (quality.get('score') or 0) >= 75:
        strengths.append('节奏和信息组织基本稳定')
    if quality.get('ending_hook'):
        strengths.append('章节收尾具备追读钩子')

    action_items: list[str] = []
    if modification_rate < 15:
        action_items.append('人工改稿幅度偏低，发布前需要继续强化措辞、节奏和细节。')
    if chapter.word_count < 800:
        action_items.append('章节字数偏少，建议补足场景铺垫或关键反应。')
    if not open_threads:
        action_items.append('当前章节缺少明显钩子，建议补一个未解问题或下一步压力。')
    for issue in quality_issues[:3]:
        suggestion = str(issue.get('suggestion') or issue.get('message') or '').strip()
        if suggestion:
            action_items.append(suggestion)
    for risk in consistency_risks[:3]:
        action_items.append(f'一致性复核：{risk}')
    if not action_items:
        action_items.append('结构和信息密度基本达标，建议重点做语句润色和错字复查。')

    review_sections = []
    if summary:
        review_sections.append(f'本章概述：{summary}')
    if strengths:
        review_sections.append(f"优点：{'；'.join(strengths[:3])}")
    review_sections.append(
        f"诊断：质量分 {quality.get('score') or 0} /100；张力 {quality.get('tension_score') or 0}；"
        f"节奏 {quality.get('rhythm_status') or 'unknown'}；风格风险 {quality.get('style_risk') or 'unknown'}"
    )
    if action_items:
        review_sections.append(f"建议：{'；'.join(action_items[:4])}")

    has_high_quality_issue = any(issue.get('severity') == 'high' for issue in quality_issues)

    return {
        'ai_review': '\n'.join(review_sections),
        'ai_action_items': action_items[:5],
        'modification_rate': modification_rate,
        'suggested_status': (
            'revise'
            if modification_rate < 15 or consistency_risks or has_high_quality_issue
            else 'approved'
        ),
    }


def sync_chapter_review(
    chapter,
    *,
    reviewer=None,
    refresh_ai: bool = False,
    reset_status: bool = False,
):
    """Create or refresh the chapter review record after content changes."""
    payload = build_ai_review_payload(chapter)
    review, created = ChapterReview.objects.get_or_create(
        project=chapter.project,
        chapter=chapter,
        defaults={
            'reviewer': reviewer,
            'status': 'pending',
        },
    )

    if reviewer and review.reviewer_id is None:
        review.reviewer = reviewer

    review.modification_rate = payload['modification_rate']

    if created or refresh_ai or not review.ai_review:
        review.ai_review = payload['ai_review']
        review.ai_action_items = payload['ai_action_items']
        review.ai_generated_at = timezone.now()

    if reset_status and review.status in ('approved', 'revise'):
        review.status = 'pending'

    review.save()

    if reset_status and chapter.reviewed_at is not None:
        chapter.reviewed_at = None
        chapter.save(update_fields=['reviewed_at', 'updated_at'])

    return review
