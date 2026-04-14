import React, { useMemo } from 'react';
import { message } from 'antd';
import { publishChapter } from '../../api/chapters';
import { useChapterStream } from '../../hooks/useChapterStream';
import { ChapterSidebar } from './ChapterSidebar';
import { WritingCenter } from './WritingCenter';
import { SettingsPanel } from './SettingsPanel';
import { formatNumber } from './constants';
import type { Chapter, KnowledgeGraphPayload, Novel, NovelSettingRecord } from './types';

interface WorkspacePageProps {
  selectedNovel: Novel | null;
  selectedChapters: Chapter[];
  selectedChapterId: number | null;
  onSelectChapter: (chapterId: number) => void;
  chapterLoading: boolean;
  aggregatedStats: {
    totalWords: number;
    finishedChapters: number;
    completionRate: number;
    averageWords: number;
    lastUpdate: string;
  };
  settings: NovelSettingRecord[];
  knowledgeGraph?: KnowledgeGraphPayload;
  onChapterSaved?: () => void;
}

export const WorkspacePage: React.FC<WorkspacePageProps> = ({
  selectedNovel,
  selectedChapters,
  selectedChapterId,
  onSelectChapter,
  chapterLoading,
  aggregatedStats,
  settings,
  knowledgeGraph,
  onChapterSaved,
}) => {
  const { state: streamState, start, stop } = useChapterStream(selectedNovel?.id ?? null);

  const handleStart = () => {
    if (!selectedNovel) { message.warning('请先选择一本书'); return; }
    start(selectedNovel.id);
  };

  const handleStop = () => {
    if (!selectedNovel) return;
    stop(selectedNovel.id);
  };

  const handlePublish = async (chapterId: number) => {
    try {
      await publishChapter(chapterId);
      message.success('发布成功');
      onChapterSaved?.();
    } catch {
      message.error('发布失败');
    }
  };

  // Refresh chapter list when a new chapter finishes streaming
  const prevDoneChapter = React.useRef<number | null>(null);
  React.useEffect(() => {
    if (streamState.currentChapter && streamState.currentChapter !== prevDoneChapter.current) {
      prevDoneChapter.current = streamState.currentChapter;
      onChapterSaved?.();
    }
  }, [streamState.currentChapter]);

  const topBarStats = useMemo(() => [
    { label: '总字数', value: formatNumber(aggregatedStats.totalWords) },
    { label: '完成章节', value: `${aggregatedStats.finishedChapters} / ${selectedNovel?.target_chapters ?? '?'}` },
    { label: '完成率', value: `${aggregatedStats.completionRate}%` },
    { label: '均字数', value: formatNumber(aggregatedStats.averageWords) },
    { label: '最近更新', value: aggregatedStats.lastUpdate !== '--' ? aggregatedStats.lastUpdate.slice(0, 10) : '--' },
  ], [aggregatedStats, selectedNovel]);

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Top bar */}
      <div className="flex items-center gap-6 px-6 py-3 bg-white border-b border-gray-200 shadow-sm">
        <span className="font-semibold text-gray-800 text-base">
          {selectedNovel?.title ?? '未选择书目'}
        </span>
        {topBarStats.map((stat) => (
          <div key={stat.label} className="flex flex-col items-center">
            <span className="text-xs text-gray-400">{stat.label}</span>
            <span className="text-sm font-medium text-gray-700">{stat.value}</span>
          </div>
        ))}
      </div>

      {/* 3-column body */}
      <div className="flex flex-1 min-h-0">
        {/* Left: chapter list (240px) */}
        <div className="w-60 flex-shrink-0 bg-white border-r border-gray-200 overflow-y-auto">
          <div className="px-3 py-2 border-b border-gray-100 text-xs font-medium text-gray-500">
            章节列表
          </div>
          <ChapterSidebar
            chapters={selectedChapters}
            selectedChapterId={selectedChapterId}
            loading={chapterLoading}
            onSelect={(c) => onSelectChapter(c.id)}
            onPublish={handlePublish}
          />
        </div>

        {/* Center: writing dispatch (flex-1) */}
        <div className="flex-1 min-w-0 p-4 overflow-hidden flex flex-col">
          <WritingCenter
            novel={selectedNovel}
            streamState={streamState}
            onStart={handleStart}
            onStop={handleStop}
          />
        </div>

        {/* Right: settings + knowledge graph (320px) */}
        <div className="w-80 flex-shrink-0 bg-white border-l border-gray-200 overflow-y-auto p-3">
          <SettingsPanel settings={settings} knowledgeGraph={knowledgeGraph} />
        </div>
      </div>
    </div>
  );
};
