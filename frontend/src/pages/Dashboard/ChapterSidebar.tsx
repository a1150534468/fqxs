import React from 'react';
import { Button, Empty, Spin, Tag } from 'antd';
import { chapterStatusTag } from './constants';
import type { Chapter } from './types';

interface ChapterSidebarProps {
  chapters: Chapter[];
  selectedChapterId: number | null;
  loading: boolean;
  onSelect: (chapter: Chapter) => void;
  onPublish: (chapterId: number) => void;
}

export const ChapterSidebar: React.FC<ChapterSidebarProps> = ({
  chapters,
  selectedChapterId,
  loading,
  onSelect,
  onPublish,
}) => {
  if (loading) return <Spin className="flex justify-center mt-8" />;

  if (!chapters.length) {
    return (
      <div className="flex h-full items-center justify-center px-4">
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="暂无章节，点击启动写作生成第一章"
        />
      </div>
    );
  }

  const getConsistencyColor = (status?: string) => {
    if (status === 'ok') return 'green';
    if (status === 'warning') return 'orange';
    if (status === 'error') return 'red';
    return 'default';
  };

  const getDisplayTitle = (chapter: Chapter) => {
    const rawTitle = chapter.title?.trim() || '';
    if (!rawTitle) return '';

    const normalizedTitle = rawTitle.replace(/[\s:：]/g, '');
    const normalizedFallback = `第${chapter.chapter_number}章`.replace(/[\s:：]/g, '');

    return normalizedTitle === normalizedFallback ? '' : rawTitle;
  };

  return (
    <div className="space-y-2">
      {chapters.map((chapter) => {
        const tag = chapterStatusTag[chapter.status || 'draft'] ?? chapterStatusTag.draft;
        const isSelected = chapter.id === selectedChapterId;
        const consistencyStatus = String(chapter.consistency_status?.status || '');
        const displayTitle = getDisplayTitle(chapter);
        const metaText = [
          `${chapter.word_count || 0} 字`,
          `${chapter.open_threads?.length || 0} 线索`,
          chapter.updated_at ? chapter.updated_at.slice(5, 16).replace('T', ' ') : '刚创建',
        ].join(' · ');

        return (
          <div
            key={chapter.id}
            role="button"
            tabIndex={0}
            className={`w-full rounded-2xl border px-3 py-2.5 text-left transition-all ${
              isSelected
                ? 'border-sky-200 bg-sky-50 shadow-sm'
                : 'border-transparent bg-white hover:border-slate-200 hover:bg-slate-50'
            }`}
            onClick={() => onSelect(chapter)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                onSelect(chapter);
              }
            }}
          >
            <div className="w-full">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-semibold text-slate-800">
                    第{chapter.chapter_number}章
                    {displayTitle ? ` · ${displayTitle}` : ''}
                  </div>
                  <div className="mt-1 truncate text-[11px] text-slate-400">
                    {metaText}
                  </div>
                </div>
                <div className="flex flex-shrink-0 items-center gap-1">
                  <Tag color={tag.color} className="mr-0 text-[11px]">
                    {tag.label}
                  </Tag>
                  {consistencyStatus && (
                    <Tag color={getConsistencyColor(consistencyStatus)} className="mr-0 text-[11px]">
                      {consistencyStatus}
                    </Tag>
                  )}
                </div>
              </div>

              {isSelected && chapter.summary && (
                <div className="mt-2 line-clamp-2 text-xs leading-5 text-slate-500">
                  {chapter.summary}
                </div>
              )}

              <div className="mt-2 flex items-center justify-end">
                {chapter.status === 'draft' && (
                  <Button
                    size="small"
                    type="primary"
                    ghost
                    className="h-6 rounded-lg px-2 text-[11px]"
                    onClick={(e) => { e.stopPropagation(); onPublish(chapter.id); }}
                  >
                    发布
                  </Button>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};
