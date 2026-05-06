"""Workflow helpers for chapter post-processing and generation gates."""

from __future__ import annotations

from apps.chapters.models import Chapter, ChapterSummary
from apps.chapters.services.analysis import analyze_chapter_assets
from apps.chapters.services.post_processing import build_chapter_summary_payload

MIN_MANUAL_MODIFICATION_RATE = 15


def refresh_chapter_workflow_assets(project, chapter, content: str) -> dict:
    """Refresh summary and heuristic analysis after chapter content changes."""
    summary_payload = build_chapter_summary_payload(content)
    ChapterSummary.objects.update_or_create(
        project=project,
        chapter=chapter,
        defaults=summary_payload,
    )

    analysis_payload = analyze_chapter_assets(project, chapter, content)
    chapter.summary = summary_payload['summary']
    chapter.open_threads = summary_payload['open_threads']
    chapter.consistency_status = analysis_payload['consistency_status']
    chapter.save(
        update_fields=[
            'summary',
            'open_threads',
            'consistency_status',
            'updated_at',
        ],
    )

    return {
        'summary_payload': summary_payload,
        'analysis_payload': analysis_payload,
    }


def _build_reason(code: str, level: str, title: str, detail: str) -> dict[str, str]:
    return {
        'code': code,
        'level': level,
        'title': title,
        'detail': detail,
    }


def evaluate_generation_workflow_gate(
    project,
    chapter_number: int,
    *,
    block_on_pending: bool = False,
    enforce_modification_rate: bool = False,
) -> dict:
    """Check whether generating the target chapter should be blocked or warned."""
    latest_chapter = (
        Chapter.objects.select_related('review_record')
        .filter(
            project=project,
            is_deleted=False,
            chapter_number__lt=chapter_number,
            status__in=('draft', 'published', 'failed', 'generating'),
        )
        .order_by('-chapter_number')
        .first()
    )

    if latest_chapter is None:
        return {
            'allowed': True,
            'status': 'ok',
            'summary': '当前还没有历史章节，可以直接开始生成。',
            'checked_chapter': None,
            'blocking_reasons': [],
            'warnings': [],
            'minimum_modification_rate': MIN_MANUAL_MODIFICATION_RATE,
        }

    review = getattr(latest_chapter, 'review_record', None)
    blocking_reasons: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if latest_chapter.status == 'generating':
        blocking_reasons.append(_build_reason(
            'chapter_generating',
            'critical',
            '上一章仍在生成中',
            f'第{latest_chapter.chapter_number}章还在生成，当前不应继续推进后续章节。',
        ))

    if review is None:
        reason = _build_reason(
            'review_missing',
            'warning' if not block_on_pending else 'critical',
            '上一章缺少审阅记录',
            f'第{latest_chapter.chapter_number}章还没有正式审阅记录，建议先补审后再继续。',
        )
        if block_on_pending:
            blocking_reasons.append(reason)
        else:
            warnings.append(reason)
    elif review.status == 'revise':
        blocking_reasons.append(_build_reason(
            'review_revise',
            'critical',
            '上一章仍需修订',
            f'第{latest_chapter.chapter_number}章审阅状态为“需修订”，应先处理审阅意见再继续生成。',
        ))
    elif review.status == 'pending':
        reason = _build_reason(
            'review_pending',
            'warning' if not block_on_pending else 'critical',
            '上一章尚未审定',
            f'第{latest_chapter.chapter_number}章还未完成正式审阅，继续生成有承接风险。',
        )
        if block_on_pending:
            blocking_reasons.append(reason)
        else:
            warnings.append(reason)

    if review and enforce_modification_rate and (review.modification_rate or 0) < MIN_MANUAL_MODIFICATION_RATE:
        blocking_reasons.append(_build_reason(
            'low_modification_rate',
            'critical',
            '人工改稿幅度不足',
            (
                f"第{latest_chapter.chapter_number}章当前修改率仅 {review.modification_rate or 0}% ，"
                f"低于 {MIN_MANUAL_MODIFICATION_RATE}% 的流程要求。"
            ),
        ))
    elif review and (review.modification_rate or 0) < MIN_MANUAL_MODIFICATION_RATE:
        warnings.append(_build_reason(
            'low_modification_rate',
            'warning',
            '人工改稿幅度不足',
            (
                f"第{latest_chapter.chapter_number}章当前修改率仅 {review.modification_rate or 0}% ，"
                f"建议先补强人工润色。"
            ),
        ))

    consistency_status = latest_chapter.consistency_status or {}
    quality = consistency_status.get('quality') or {}
    quality_issues = quality.get('issues') or []
    high_quality_issues = [
        issue for issue in quality_issues
        if issue.get('severity') == 'high'
    ]
    if high_quality_issues:
        warnings.append(_build_reason(
            'quality_high_risk',
            'warning',
            '上一章质量诊断风险偏高',
            high_quality_issues[0].get('message') or '上一章仍存在明显质量风险。',
        ))
    elif consistency_status.get('risks'):
        warnings.append(_build_reason(
            'consistency_warning',
            'warning',
            '上一章存在连续性提醒',
            str(consistency_status['risks'][0]),
        ))

    allowed = not blocking_reasons
    status = 'blocked' if not allowed else ('warning' if warnings else 'ok')
    summary = (
        (blocking_reasons[0]['detail'] if blocking_reasons else '')
        or (warnings[0]['detail'] if warnings else '')
        or f'第{latest_chapter.chapter_number}章已满足继续生成条件。'
    )

    return {
        'allowed': allowed,
        'status': status,
        'summary': summary,
        'checked_chapter': {
            'id': latest_chapter.id,
            'chapter_number': latest_chapter.chapter_number,
            'title': latest_chapter.title or f'第{latest_chapter.chapter_number}章',
            'status': latest_chapter.status,
            'review_status': review.status if review else 'missing',
            'modification_rate': review.modification_rate if review else None,
        },
        'blocking_reasons': blocking_reasons,
        'warnings': warnings,
        'minimum_modification_rate': MIN_MANUAL_MODIFICATION_RATE,
    }
