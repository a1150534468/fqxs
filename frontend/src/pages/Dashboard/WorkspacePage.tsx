import React, { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { message, Button, Progress, Tag } from 'antd';
import { ArrowLeftOutlined, BookOutlined, FileTextOutlined, WarningOutlined } from '@ant-design/icons';
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

  const navigationStats = useMemo(() => [
    {
      key: 'all',
      label: '章节总数',
      value: selectedChapters.length,
      icon: <BookOutlined className="text-slate-400" />,
      tone: 'bg-slate-50 text-slate-700',
    },
    {
      key: 'draft',
      label: '草稿',
      value: sidebarStats.draft,
      icon: <FileTextOutlined className="text-amber-500" />,
      tone: 'bg-amber-50 text-amber-700',
    },
    {
      key: 'flagged',
      label: '待检查',
      value: sidebarStats.flagged,
      icon: <WarningOutlined className="text-rose-500" />,
      tone: 'bg-rose-50 text-rose-700',
    },
  ], [selectedChapters.length, sidebarStats.draft, sidebarStats.flagged]);

  return (
    <div className="flex h-screen flex-col bg-[#eef2f7]">
      <div className="flex items-center gap-6 border-b border-slate-200 bg-white px-6 py-3 shadow-sm">
        <Button
          type="text"
          icon={<ArrowLeftOutlined />}
          size="small"
          onClick={() => navigate('/')}
          className="text-slate-500"
        />
        <div className="min-w-0">
          <div className="truncate text-base font-semibold text-slate-800">
            {selectedNovel?.title ?? '未选择书目'}
          </div>
          <div className="mt-0.5 flex items-center gap-2 text-xs text-slate-400">
            <span>{selectedNovel?.genre || '未分类'}</span>
            {workbenchHighlights?.active_storyline?.name && (
              <Tag color="cyan" className="mr-0">
                {workbenchHighlights.active_storyline.name}
              </Tag>
            )}
          </div>
        </div>
        <div className="ml-auto flex items-center gap-5">
          {topBarStats.map((stat) => (
            <div key={stat.label} className="flex min-w-[70px] flex-col items-center">
              <span className="text-[11px] text-slate-400">{stat.label}</span>
              <span className="text-sm font-medium text-slate-700">{stat.value}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="flex flex-1 min-h-0 p-4">
        <div className="mx-auto flex h-full w-full max-w-[1780px] min-h-0 flex-col gap-4 xl:flex-row">
          <aside className="flex w-full flex-col gap-4 xl:w-[19.5rem] xl:flex-shrink-0">
            <div className="rounded-[28px] border border-slate-200 bg-white p-4 shadow-sm">
              <div className="text-xs font-medium uppercase tracking-[0.24em] text-slate-400">
                项目总览
              </div>
              <div className="mt-3 text-lg font-semibold text-slate-800">
                {selectedNovel?.title ?? '未选择书目'}
              </div>
              <div className="mt-2 text-sm leading-6 text-slate-500">
                {workbenchHighlights?.recommended_focus || '优先完成当前章节，再进入下一章的情节推进。'}
              </div>
              <div className="mt-4">
                <div className="mb-2 flex items-center justify-between text-xs text-slate-400">
                  <span>总进度</span>
                  <span>{aggregatedStats.completionRate}%</span>
                </div>
                <Progress percent={aggregatedStats.completionRate} showInfo={false} strokeColor="#0ea5e9" />
              </div>
              <div className="mt-4 grid grid-cols-3 gap-2">
                <div className="rounded-2xl bg-slate-50 px-3 py-2">
                  <div className="text-[11px] text-slate-400">已发布</div>
                  <div className="mt-1 text-base font-semibold text-slate-800">{sidebarStats.published}</div>
                </div>
                <div className="rounded-2xl bg-amber-50 px-3 py-2">
                  <div className="text-[11px] text-amber-500">草稿</div>
                  <div className="mt-1 text-base font-semibold text-amber-700">{sidebarStats.draft}</div>
                </div>
                <div className="rounded-2xl bg-rose-50 px-3 py-2">
                  <div className="text-[11px] text-rose-500">待检查</div>
                  <div className="mt-1 text-base font-semibold text-rose-700">{sidebarStats.flagged}</div>
                </div>
              </div>
              <div className="mt-4 rounded-2xl bg-[#0f172a] px-4 py-3 text-slate-200">
                <div className="text-[11px] uppercase tracking-[0.2em] text-slate-400">当前焦点</div>
                <div className="mt-2 text-sm font-medium">
                  第 {workbenchHighlights?.focus_chapter_number ?? selectedNovel?.current_chapter ?? 1} 章
                </div>
                <div className="mt-2 text-xs leading-5 text-slate-300">
                  {workbenchHighlights?.focus_card?.mission || '围绕当前主线推进，并在章节尾部留下下一步钩子。'}
                </div>
              </div>
            </div>

            <div className="min-h-0 flex flex-1 flex-col overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-sm">
              <div className="border-b border-slate-100 px-4 py-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-xs font-medium text-slate-500">章节导航</div>
                    <div className="mt-1 text-[11px] text-slate-400">选章、检查状态、快速发布都放在这里</div>
                  </div>
                  <Tag color="blue" className="mr-0">{selectedChapters.length} 章</Tag>
                </div>
                <div className="mt-3 grid grid-cols-3 gap-2">
                  {navigationStats.map((stat) => (
                    <div key={stat.key} className={`rounded-2xl px-3 py-2 ${stat.tone}`}>
                      <div className="flex items-center gap-1 text-[11px]">
                        {stat.icon}
                        <span>{stat.label}</span>
                      </div>
                      <div className="mt-1 text-base font-semibold">{stat.value}</div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="min-h-0 flex-1 overflow-y-auto px-2 py-2" data-testid="chapter-sidebar-scroll">
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
            <div className="flex h-full min-h-0 flex-col bg-slate-50/40">
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
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
};
