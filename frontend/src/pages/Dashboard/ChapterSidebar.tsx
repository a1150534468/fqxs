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

  return (
    <List
      size="small"
      dataSource={chapters}
      locale={{ emptyText: '暂无章节，点击启动写作生成第一章' }}
      renderItem={(chapter) => {
        const tag = chapterStatusTag[chapter.status || 'draft'] ?? chapterStatusTag.draft;
        const isSelected = chapter.id === selectedChapterId;
        return (
          <List.Item
            className={`cursor-pointer px-2 rounded transition-colors ${isSelected ? 'bg-indigo-50' : 'hover:bg-gray-50'}`}
            onClick={() => onSelect(chapter)}
          >
            <div className="w-full">
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400">第{chapter.chapter_number}章</span>
                <Tag color={tag.color} className="text-xs">{tag.label}</Tag>
              </div>
              <div className="text-sm text-gray-800 truncate mt-0.5">
                {chapter.title || `第${chapter.chapter_number}章`}
              </div>
              <div className="flex items-center justify-between mt-1">
                <span className="text-xs text-gray-400">{chapter.word_count || 0} 字</span>
                {chapter.status === 'draft' && (
                  <Button
                    size="small"
                    type="primary"
                    ghost
                    onClick={(e) => { e.stopPropagation(); onPublish(chapter.id); }}
                  >
                    发布
                  </Button>
                )}
              </div>
            </div>
          </List.Item>
        );
      }}
    />
  );
};
