import React from 'react';
import { Button, List, Spin, Tag } from 'antd';
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

  const getConsistencyColor = (status?: string) => {
    if (status === 'ok') return 'green';
    if (status === 'warning') return 'orange';
    if (status === 'error') return 'red';
    return 'default';
  };

  return (
    <List
      size="small"
      dataSource={chapters}
      locale={{ emptyText: '暂无章节，点击启动写作生成第一章' }}
      renderItem={(chapter) => {
        const tag = chapterStatusTag[chapter.status || 'draft'] ?? chapterStatusTag.draft;
        const isSelected = chapter.id === selectedChapterId;
        const consistencyStatus = String(chapter.consistency_status?.status || '');
        return (
          <List.Item
            key={chapter.id}
            className={`cursor-pointer rounded-2xl border px-3 py-3 transition-all ${
              isSelected
                ? 'border-sky-200 bg-sky-50 shadow-sm'
                : 'border-transparent bg-white hover:border-slate-200 hover:bg-slate-50'
            }`}
            onClick={() => onSelect(chapter)}
          >
            <div className="w-full min-w-0">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 text-[11px] font-medium text-slate-400">
                    <span>第 {chapter.chapter_number} 章</span>
                    <span>·</span>
                    <span>{chapter.word_count || 0} 字</span>
                  </div>
                  <div className="mt-1 truncate text-sm font-medium text-slate-800">
                    {chapter.title || `未命名章节`}
                  </div>
                </div>
                <div className="flex items-center gap-1 pl-2">
                  <Tag color={tag.color} className="mr-0 text-[11px]">{tag.label}</Tag>
                  {consistencyStatus && (
                    <Tag color={getConsistencyColor(consistencyStatus)} className="mr-0 text-[11px]">
                      {consistencyStatus}
                    </Tag>
                  )}
                </div>
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-400">
                <span>{chapter.open_threads?.length || 0} 线索</span>
                <span>{chapter.summary ? '有摘要' : '未摘要'}</span>
                <span>{chapter.updated_at ? chapter.updated_at.slice(5, 16).replace('T', ' ') : '刚创建'}</span>
              </div>
              {chapter.summary && (
                <div className="mt-2 line-clamp-2 text-xs leading-5 text-slate-500">
                  {chapter.summary}
                </div>
              )}
              {chapter.status === 'draft' && (
                <div className="mt-3 flex justify-end">
                  <Button
                    size="small"
                    type="primary"
                    ghost
                    onClick={(e) => { e.stopPropagation(); onPublish(chapter.id); }}
                  >
                    发布
                  </Button>
                </div>
              )}
            </div>
          </List.Item>
        );
      }}
    />
  );
};
