import React, { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { message, Button, Progress, Tag } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { publishChapter } from '../../api/chapters';
import { useChapterStream } from '../../hooks/useChapterStream';
import { ChapterSidebar } from './ChapterSidebar';
import { WritingCenter } from './WritingCenter';
import { SettingsPanel } from './SettingsPanel';
import { formatNumber } from './constants';
import type {
  Chapter,
  ChapterSummaryRecord,
  ForeshadowItemRecord,
  KnowledgeFactRecord,
  KnowledgeGraphPayload,
  Novel,
  NovelSettingRecord,
  PlotArcPointRecord,
  StorylineRecord,
  StyleProfileRecord,
  WorkbenchHighlights,
} from './types';

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
  chapterSummaries: ChapterSummaryRecord[];
  storylines: StorylineRecord[];
  plotArcPoints: PlotArcPointRecord[];
  knowledgeFacts: KnowledgeFactRecord[];
  foreshadowItems: ForeshadowItemRecord[];
  styleProfiles: StyleProfileRecord[];
  knowledgeGraph?: KnowledgeGraphPayload;
  workbenchHighlights?: WorkbenchHighlights;
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
  chapterSummaries,
  storylines,
  plotArcPoints,
  knowledgeFacts,
  foreshadowItems,
  styleProfiles,
  knowledgeGraph,
  workbenchHighlights,
  onChapterSaved,
}) => {
  const { state: streamState, start, stop } = useChapterStream(selectedNovel?.id ?? null);
  const navigate = useNavigate();
  const selectedChapter = selectedChapters.find((chapter) => chapter.id === selectedChapterId) ?? null;
  const nextChapterNumber = (selectedNovel?.current_chapter ?? 0) + 1;

  const handleStartContinuous = (targetChapter: number) => {
    if (!selectedNovel) { message.warning('请先选择一本书'); return; }
    if (targetChapter < nextChapterNumber) {
      message.warning(`目标章节不能小于第 ${nextChapterNumber} 章`);
      return;
    }
    start(selectedNovel.id, {
      mode: 'generate',
      runMode: 'continuous',
      chapterNumber: nextChapterNumber,
      targetChapter,
    });
  };

  const handleGenerateNext = () => {
    if (!selectedNovel) { message.warning('请先选择一本书'); return; }
    start(selectedNovel.id, {
      mode: 'generate',
      runMode: 'single',
      chapterNumber: nextChapterNumber,
    });
  };

  const handleContinueCurrent = () => {
    if (!selectedNovel || !selectedChapter) {
      message.warning('请先选择一个章节');
      return;
    }
    const currentContent = selectedChapter.final_content || selectedChapter.raw_content || '';
    if (!currentContent) {
      message.warning('当前章节还没有可续写的正文');
      return;
    }
    start(selectedNovel.id, {
      mode: 'continue',
      chapterNumber: selectedChapter.chapter_number,
      chapterTitle: selectedChapter.title || `第${selectedChapter.chapter_number}章`,
      currentContent,
      continueLength: 1200,
    });
  };

  const handleRegenerateCurrent = () => {
    if (!selectedNovel || !selectedChapter) {
      message.warning('请先选择一个章节');
      return;
    }
    start(selectedNovel.id, {
      mode: 'regenerate',
      chapterNumber: selectedChapter.chapter_number,
      chapterTitle: selectedChapter.title || `第${selectedChapter.chapter_number}章`,
    });
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

  // Refresh chapter list whenever a chapter is saved during streaming
  const prevSavedEvent = React.useRef<string | null>(null);
  React.useEffect(() => {
    if (
      streamState.lastSavedEventId
      && streamState.lastSavedEventId !== prevSavedEvent.current
    ) {
      prevSavedEvent.current = streamState.lastSavedEventId;
      if (streamState.lastSavedChapterId) {
        onSelectChapter(streamState.lastSavedChapterId);
      }
      onChapterSaved?.();
    }
  }, [
    onChapterSaved,
    onSelectChapter,
    streamState.lastSavedChapterId,
    streamState.lastSavedEventId,
  ]);

  const topBarStats = useMemo(() => [
    { label: '总字数', value: formatNumber(aggregatedStats.totalWords) },
    { label: '完成章节', value: `${aggregatedStats.finishedChapters} / ${selectedNovel?.target_chapters ?? '?'}` },
    { label: '完成率', value: `${aggregatedStats.completionRate}%` },
    { label: '均字数', value: formatNumber(aggregatedStats.averageWords) },
    { label: '最近更新', value: aggregatedStats.lastUpdate !== '--' ? aggregatedStats.lastUpdate.slice(0, 10) : '--' },
  ], [aggregatedStats, selectedNovel]);

  const sidebarStats = useMemo(() => {
    const published = selectedChapters.filter((chapter) => chapter.status === 'published').length;
    const draft = selectedChapters.filter((chapter) => chapter.status === 'draft').length;
    const flagged = selectedChapters.filter((chapter) => {
      const status = chapter.consistency_status?.status;
      return status && status !== 'ok';
    }).length;

    return { published, draft, flagged };
  }, [selectedChapters]);

  return (
    <div className="flex h-screen flex-col bg-[#eef2f7]">
      <div className="border-b border-slate-200 bg-white shadow-sm">
        <div className="mx-auto flex w-full max-w-[1780px] flex-col gap-4 px-4 py-3 sm:px-6 xl:flex-row xl:items-center">
          <Button
            type="text"
            icon={<ArrowLeftOutlined />}
            size="small"
            onClick={() => navigate('/')}
            className="text-slate-500"
          />
          <div className="flex min-w-0 flex-1 flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
            <div className="min-w-0 xl:max-w-[21rem]">
              <div className="truncate text-base font-semibold text-slate-800">
                {selectedNovel?.title ?? '未选择书目'}
              </div>
              <div className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-slate-400">
                <span>{selectedNovel?.genre || '未分类'}</span>
                {workbenchHighlights?.active_storyline?.name && (
                  <Tag color="cyan" className="mr-0">
                    {workbenchHighlights.active_storyline.name}
                  </Tag>
                )}
              </div>
            </div>

            <div className="min-w-0 flex-1 rounded-[22px] border border-slate-200 bg-slate-50 px-4 py-3 xl:max-w-[34rem]">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div className="min-w-0 flex-1">
                  <div className="text-[11px] font-medium uppercase tracking-[0.2em] text-slate-400">
                    项目总览
                  </div>
                  <div className="mt-1 truncate text-sm font-medium text-slate-800">
                    当前焦点：第 {workbenchHighlights?.focus_chapter_number ?? selectedNovel?.current_chapter ?? 1} 章
                  </div>
                  <div className="mt-1 line-clamp-1 text-xs text-slate-500">
                    {workbenchHighlights?.focus_card?.mission || workbenchHighlights?.recommended_focus || '优先完成当前章节，再进入下一章的情节推进。'}
                  </div>
                </div>
                <div className="w-full md:max-w-[11rem]">
                  <div className="mb-1 flex items-center justify-between text-[11px] text-slate-400">
                    <span>总进度</span>
                    <span>{aggregatedStats.completionRate}%</span>
                  </div>
                  <Progress
                    percent={aggregatedStats.completionRate}
                    showInfo={false}
                    strokeColor="#0ea5e9"
                    trailColor="#e2e8f0"
                  />
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <div className="rounded-xl bg-white px-2.5 py-1 text-[11px] text-slate-500">
                  已发布 <span className="ml-1 font-semibold text-slate-800">{sidebarStats.published}</span>
                </div>
                <div className="rounded-xl bg-amber-50 px-2.5 py-1 text-[11px] text-amber-600">
                  草稿 <span className="ml-1 font-semibold text-amber-700">{sidebarStats.draft}</span>
                </div>
                <div className="rounded-xl bg-rose-50 px-2.5 py-1 text-[11px] text-rose-600">
                  待检查 <span className="ml-1 font-semibold text-rose-700">{sidebarStats.flagged}</span>
                </div>
              </div>
            </div>

            <div className="grid gap-2 sm:grid-cols-2 xl:w-[30rem] xl:grid-cols-4">
              {topBarStats.map((stat) => (
                <div key={stat.label} className="rounded-[18px] border border-slate-200 bg-slate-50 px-3 py-2.5">
                  <div className="text-[11px] text-slate-400">{stat.label}</div>
                  <div className="mt-1 text-sm font-semibold text-slate-800">{stat.value}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="flex flex-1 min-h-0 px-4 pb-4 pt-4 sm:px-6">
        <div className="mx-auto flex h-full w-full max-w-[1780px] min-h-0 flex-col gap-4 xl:flex-row">
          <aside className="flex min-h-0 w-full flex-col xl:w-[16.5rem] xl:flex-shrink-0">
            <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-sm">
              <div className="border-b border-slate-100 px-4 py-3 text-xs font-medium text-slate-500">
                章节导航
              </div>
              <div className="min-h-0 flex-1 overflow-y-auto px-2 py-2">
                <ChapterSidebar
                  chapters={selectedChapters}
                  selectedChapterId={selectedChapterId}
                  loading={chapterLoading}
                  onSelect={(c) => onSelectChapter(c.id)}
                  onPublish={handlePublish}
                />
              </div>
            </div>
          </aside>

          <main className="min-w-0 flex-1 overflow-hidden rounded-[32px] border border-slate-200 bg-white shadow-sm xl:flex-[1.25]">
            <WritingCenter
              novel={selectedNovel}
              selectedChapter={selectedChapter}
              streamState={streamState}
              highlights={workbenchHighlights}
              onStartContinuous={handleStartContinuous}
              onGenerateNext={handleGenerateNext}
              onContinueCurrent={handleContinueCurrent}
              onRegenerateCurrent={handleRegenerateCurrent}
              onStop={handleStop}
            />
          </main>

          <aside className="min-h-0 w-full overflow-hidden rounded-[32px] border border-slate-200 bg-white shadow-sm xl:w-[25rem] xl:flex-shrink-0">
            <SettingsPanel
              settings={settings}
              chapter={selectedChapter}
              chapterSummaries={chapterSummaries}
              storylines={storylines}
              plotArcPoints={plotArcPoints}
              knowledgeFacts={knowledgeFacts}
              foreshadowItems={foreshadowItems}
              styleProfiles={styleProfiles}
              workbenchHighlights={workbenchHighlights}
              knowledgeGraph={knowledgeGraph}
            />
          </aside>
        </div>
      </div>
    </div>
  );
};
