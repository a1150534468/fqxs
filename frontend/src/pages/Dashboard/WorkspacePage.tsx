import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { message, Button, Progress, Tag, Alert } from 'antd';
import {
  ArrowLeftOutlined,
  DeploymentUnitOutlined,
  PartitionOutlined,
  RadarChartOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { publishChapter, saveChapterReview, updateChapter } from '../../api/chapters';
import { useChapterStream } from '../../hooks/useChapterStream';
import { ChapterSidebar } from './ChapterSidebar';
import { WritingCenter } from './WritingCenter';
import { SettingsPanel } from './SettingsPanel';
import { formatNumber } from './constants';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import type {
  ChapterAssetSnapshot,
  Chapter,
  ChapterReviewRecord,
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

type WorkspaceSurface = 'cockpit' | 'dashboard' | 'intelligence';
type SurfaceTone = 'default' | 'warning' | 'danger' | 'accent';

const WORKSPACE_SURFACES: Array<{
  id: WorkspaceSurface;
  label: string;
  short: string;
  description: string;
}> = [
  {
    id: 'cockpit',
    label: '写作主航道',
    short: '驾驶舱',
    description: '正文推进、流式写作与审阅协同',
  },
  {
    id: 'dashboard',
    label: '项目脉冲',
    short: '仪表盘',
    description: '先看进度、主线与风险，再决定下一步',
  },
  {
    id: 'intelligence',
    label: '设定与情报',
    short: '情报库',
    description: '把设定、审阅、伏笔和章节资产放大查看',
  },
];

const toneClassMap: Record<SurfaceTone, string> = {
  default: 'border-[var(--app-border)] bg-[var(--app-surface)]',
  warning: 'border-amber-200 bg-[linear-gradient(180deg,#fffdf7_0%,#ffffff_100%)]',
  danger: 'border-rose-200 bg-[linear-gradient(180deg,#fff8f8_0%,#ffffff_100%)]',
  accent: 'border-sky-200 bg-[linear-gradient(180deg,#f8fcff_0%,#ffffff_100%)]',
};

const formatWorkflowStatus = (status?: string) => {
  if (status === 'blocked') return '阻塞';
  if (status === 'warning') return '提醒';
  if (status === 'ok') return '通过';
  return '待判定';
};

const formatReviewStatus = (status?: 'pending' | 'approved' | 'revise') => {
  if (status === 'approved') return '已定稿';
  if (status === 'revise') return '需修订';
  return '待审';
};


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
  chapterReviews: ChapterReviewRecord[];
  storylines: StorylineRecord[];
  plotArcPoints: PlotArcPointRecord[];
  knowledgeFacts: KnowledgeFactRecord[];
  foreshadowItems: ForeshadowItemRecord[];
  chapterAssetIndex?: Record<string, ChapterAssetSnapshot>;
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
  chapterReviews,
  storylines,
  plotArcPoints,
  knowledgeFacts,
  foreshadowItems,
  chapterAssetIndex,
  styleProfiles,
  knowledgeGraph,
  workbenchHighlights,
  onChapterSaved,
}) => {
  const { state: streamState, start, stop } = useChapterStream(selectedNovel?.id ?? null);
  const navigate = useNavigate();
  const [activeSurface, setActiveSurface] = useState<WorkspaceSurface>('cockpit');
  const selectedChapter = selectedChapters.find((chapter) => chapter.id === selectedChapterId) ?? null;
  const selectedChapterIndex = selectedChapters.findIndex((chapter) => chapter.id === selectedChapterId);
  const nextChapterNumber = (selectedNovel?.current_chapter ?? 0) + 1;
  const workflowGate = workbenchHighlights?.workflow_gate;

  const missingBookTitle = selectedNovel && (!selectedNovel.title || selectedNovel.title.trim() === '');

  useEffect(() => {
    if (missingBookTitle) {
      message.warning({
        content: '该项目尚未设置书名，建议先设置书名以获得更好的 AI 生成效果',
        duration: 5,
      });
    }
  }, [missingBookTitle]);

  const handleStartContinuous = (targetChapter: number) => {
    if (!selectedNovel) {
      message.warning('请先选择一本书');
      return;
    }
    if (workflowGate && !workflowGate.allowed) {
      message.warning(workflowGate.summary || '当前工作流闸门未通过，暂时不能持续迭代');
      return;
    }
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
    if (!selectedNovel) {
      message.warning('请先选择一本书');
      return;
    }
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

  const handleSaveChapterContent = async (
    chapterId: number,
    content: string,
    options?: { silent?: boolean },
  ) => {
    try {
      await updateChapter(chapterId, {
        final_content: content,
        publish_status: 'draft',
      });
      if (!options?.silent) {
        message.success('正文已保存');
      }
      onChapterSaved?.();
    } catch {
      if (!options?.silent) {
        message.error('保存正文失败');
      }
      throw new Error('save chapter content failed');
    }
  };

  const handleSaveChapterReview = async (
    chapterId: number,
    payload: {
      status?: 'pending' | 'approved' | 'revise';
      review_notes?: string;
      generate_ai?: boolean;
      apply_ai_to_notes?: boolean;
    },
    options?: { silent?: boolean },
  ) => {
    try {
      const response = await saveChapterReview(chapterId, payload);
      if (!options?.silent) {
        message.success(payload.generate_ai ? 'AI 审读建议已生成' : '审阅记录已保存');
      }
      onChapterSaved?.();
      return response;
    } catch {
      if (!options?.silent) {
        message.error(payload.generate_ai ? '生成 AI 审读建议失败' : '保存审阅记录失败');
      }
      throw new Error('save chapter review failed');
    }
  };

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

  const selectedReviewLabel = formatReviewStatus(selectedChapter?.review_status);
  const displayTitle = selectedNovel?.title?.trim() || '未命名项目';
  const heroDescription = selectedNovel?.synopsis?.trim()
    || workbenchHighlights?.focus_card?.mission
    || workbenchHighlights?.recommended_focus
    || '当前还没有项目摘要，可以从章节推进与情报信号开始判断下一步。';

  const topBarStats = useMemo(() => [
    { label: '总字数', value: formatNumber(aggregatedStats.totalWords), tip: '累计写作体量' },
    { label: '完成章节', value: `${aggregatedStats.finishedChapters} / ${selectedNovel?.target_chapters ?? '?'}`, tip: '章节推进' },
    { label: '完成率', value: `${aggregatedStats.completionRate}%`, tip: '项目节奏' },
    { label: '均字数', value: formatNumber(aggregatedStats.averageWords), tip: '章节密度' },
    { label: '最近更新', value: aggregatedStats.lastUpdate !== '--' ? aggregatedStats.lastUpdate.slice(0, 10) : '--', tip: '最近动作' },
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

  const focusSignals = useMemo<Array<{
    key: string;
    title: string;
    value: string;
    detail: string;
    tone: SurfaceTone;
    icon: React.ReactNode;
  }>>(() => {
    const focusChapterNumber = workbenchHighlights?.focus_chapter_number ?? nextChapterNumber;
    const dueForeshadowCount = workbenchHighlights?.due_foreshadow_items.length ?? 0;
    const continuityAlertCount = workbenchHighlights?.continuity_alerts.length ?? 0;
    const focusTone: SurfaceTone = continuityAlertCount ? 'warning' : 'accent';
    const workflowTone: SurfaceTone = workflowGate?.status === 'blocked'
      ? 'danger'
      : workflowGate?.status === 'warning'
        ? 'warning'
        : 'default';

    return [
      {
        key: 'focus',
        title: '当前焦点',
        value: `第 ${focusChapterNumber} 章`,
        detail: workbenchHighlights?.focus_card?.mission
          || workbenchHighlights?.recommended_focus
          || '优先稳定本章节奏，再进入下一段剧情推进。',
        tone: focusTone,
        icon: <RadarChartOutlined />,
      },
      {
        key: 'workflow',
        title: '工作流闸门',
        value: workflowGate ? formatWorkflowStatus(workflowGate.status) : '待判定',
        detail: workflowGate?.summary || '当前没有闸门阻塞，写作与审阅都可以继续推进。',
        tone: workflowTone,
        icon: <WarningOutlined />,
      },
      {
        key: 'storyline',
        title: '主线状态',
        value: workbenchHighlights?.active_storyline?.name || '主线建立中',
        detail: workbenchHighlights?.active_storyline?.description
          || '生成更多章节后，这里会持续显示当前主线与情节压力。',
        tone: 'default',
        icon: <DeploymentUnitOutlined />,
      },
      {
        key: 'ledger',
        title: '账本提醒',
        value: dueForeshadowCount ? `${dueForeshadowCount} 条待回收` : `${continuityAlertCount} 条连续性提醒`,
        detail: dueForeshadowCount
          ? (workbenchHighlights?.due_foreshadow_items[0]?.title || '优先处理即将到期的伏笔回收项')
          : continuityAlertCount
            ? (workbenchHighlights?.continuity_alerts[0]?.detail || '建议先处理连续性风险，再继续写作。')
            : '当前没有高优先级账本风险，可以继续正文推进。',
        tone: dueForeshadowCount || continuityAlertCount ? 'warning' : 'default',
        icon: <PartitionOutlined />,
      },
    ];
  }, [nextChapterNumber, workbenchHighlights, workflowGate]);

  const secondarySurfaceCards = useMemo(() => ([
    {
      key: 'project',
      label: '当前项目',
      value: displayTitle,
      detail: selectedNovel?.genre || '未分类',
    },
    {
      key: 'chapter',
      label: '当前章节',
      value: selectedChapter ? `第 ${selectedChapter.chapter_number} 章` : `第 ${nextChapterNumber} 章`,
      detail: selectedChapter?.title || '当前未锁定具体章节',
    },
    {
      key: 'workflow',
      label: '工作流',
      value: workflowGate ? formatWorkflowStatus(workflowGate.status) : '待判定',
      detail: workflowGate?.summary || `审阅状态：${selectedReviewLabel}`,
    },
  ]), [
    displayTitle,
    nextChapterNumber,
    selectedChapter,
    selectedNovel?.genre,
    selectedReviewLabel,
    workflowGate,
  ]);
  const dashboardPulse = useMemo(() => {
    const latestChapters = [...selectedChapters]
      .sort((a, b) => (b.chapter_number || 0) - (a.chapter_number || 0))
      .slice(0, 4);
    const nextMilestones = plotArcPoints
      .filter((item) => item.chapter_number >= nextChapterNumber)
      .sort((a, b) => a.chapter_number - b.chapter_number)
      .slice(0, 4);
    const activeStorylines = storylines
      .filter((item) => item.status === 'active')
      .slice(0, 4);
    const openForeshadow = foreshadowItems
      .filter((item) => item.status !== 'resolved')
      .sort((a, b) => (a.expected_payoff_chapter || 10_000) - (b.expected_payoff_chapter || 10_000))
      .slice(0, 4);

    return {
      latestChapters,
      nextMilestones,
      activeStorylines,
      openForeshadow,
    };
  }, [foreshadowItems, nextChapterNumber, plotArcPoints, selectedChapters, storylines]);

  const chapterRail = (
    <aside
      aria-label="章节导航"
      className="flex min-h-0 w-full flex-col overflow-hidden rounded-[18px] border border-[var(--app-border)] bg-[color:var(--app-surface)] shadow-[var(--app-shadow-sm)]"
    >
      <div className="border-b border-[var(--plotpilot-split-border)] bg-[color:var(--app-surface)] px-4 py-3">
        <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[color:var(--app-text-muted)]">
          书目列表
        </div>
        <div className="mt-3 rounded-[14px] border border-[var(--app-border)] bg-[color:var(--app-shell)] px-3 py-3">
          <div className="truncate text-sm font-semibold text-[color:var(--app-text-primary)]">
            {displayTitle}
          </div>
          <div className="mt-1 text-xs text-[color:var(--app-text-muted)]">
            {selectedNovel?.id ? `novel-${selectedNovel.id}` : 'novel-未选择'}
          </div>
          <div className="mt-3 text-xs leading-5 text-[color:var(--app-text-muted)]">
            {workflowGate?.summary || heroDescription}
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <div className="rounded-[12px] border border-[var(--app-border)] bg-white px-3 py-2">
              <div className="text-[10px] uppercase tracking-[0.12em] text-[color:var(--app-text-muted)]">当前章节</div>
              <div className="mt-1 text-sm font-semibold text-[color:var(--app-text-primary)]">
                {selectedChapter ? `第 ${selectedChapter.chapter_number} 章` : `第 ${nextChapterNumber} 章`}
              </div>
            </div>
            <div className="rounded-[12px] border border-[var(--app-border)] bg-white px-3 py-2">
              <div className="text-[10px] uppercase tracking-[0.12em] text-[color:var(--app-text-muted)]">状态</div>
              <div className="mt-1 text-sm font-semibold text-[color:var(--app-text-primary)]">
                {streamState.isRunning ? '运行中' : '待命'}
              </div>
            </div>
          </div>
          <div className="mt-3 grid grid-cols-3 gap-2 text-center">
            <div className="rounded-[12px] bg-white px-2 py-2">
              <div className="text-[10px] text-[color:var(--app-text-muted)]">已发布</div>
              <div className="mt-1 text-sm font-semibold text-[color:var(--app-text-primary)]">{sidebarStats.published}</div>
            </div>
            <div className="rounded-[12px] bg-white px-2 py-2">
              <div className="text-[10px] text-[color:var(--app-text-muted)]">草稿</div>
              <div className="mt-1 text-sm font-semibold text-[color:var(--app-text-primary)]">{sidebarStats.draft}</div>
            </div>
            <div className="rounded-[12px] bg-white px-2 py-2">
              <div className="text-[10px] text-[color:var(--app-text-muted)]">待检</div>
              <div className="mt-1 text-sm font-semibold text-[color:var(--app-text-primary)]">{sidebarStats.flagged}</div>
            </div>
          </div>
        </div>
      </div>
      <div className="border-b border-[var(--plotpilot-split-border)] bg-[color:var(--app-surface)] px-4 py-3 text-xs font-medium text-[color:var(--app-text-muted)]">
        树形视图
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto bg-[color:var(--app-shell)] px-2 py-2">
        <ChapterSidebar
          chapters={selectedChapters}
          selectedChapterId={selectedChapterId}
          loading={chapterLoading}
          onSelect={(chapter) => onSelectChapter(chapter.id)}
          onPublish={handlePublish}
        />
      </div>
    </aside>
  );

  const writingCenterPanel = (
    <main
      aria-label="正文工作区"
      className="min-w-0 overflow-hidden rounded-[18px] border border-[var(--app-border)] bg-[color:var(--app-surface)] shadow-[var(--app-shadow-sm)]"
    >
      <WritingCenter
        surface={activeSurface}
        novel={selectedNovel}
        selectedChapter={selectedChapter}
        streamState={streamState}
        highlights={workbenchHighlights}
        canPrevChapter={selectedChapterIndex > 0}
        canNextChapter={selectedChapterIndex >= 0 && selectedChapterIndex < selectedChapters.length - 1}
        onPrevChapter={() => {
          if (selectedChapterIndex > 0) {
            onSelectChapter(selectedChapters[selectedChapterIndex - 1].id);
          }
        }}
        onNextChapter={() => {
          if (selectedChapterIndex >= 0 && selectedChapterIndex < selectedChapters.length - 1) {
            onSelectChapter(selectedChapters[selectedChapterIndex + 1].id);
          }
        }}
        onStartContinuous={handleStartContinuous}
        onGenerateNext={handleGenerateNext}
        onContinueCurrent={handleContinueCurrent}
        onRegenerateCurrent={handleRegenerateCurrent}
        onSaveChapterContent={handleSaveChapterContent}
        onStop={handleStop}
      />
    </main>
  );

  const intelligencePanel = (
    <aside
      aria-label="右侧情报区"
      className="min-h-0 overflow-hidden rounded-[18px] border border-[var(--app-border)] bg-[color:var(--app-surface)] shadow-[var(--app-shadow-sm)]"
    >
      <SettingsPanel
        settings={settings}
        chapter={selectedChapter}
        chapterSummaries={chapterSummaries}
        chapterReviews={chapterReviews}
        storylines={storylines}
        plotArcPoints={plotArcPoints}
        knowledgeFacts={knowledgeFacts}
        foreshadowItems={foreshadowItems}
        chapterAssetIndex={chapterAssetIndex}
        styleProfiles={styleProfiles}
        onSaveChapterReview={handleSaveChapterReview}
        workbenchHighlights={workbenchHighlights}
        knowledgeGraph={knowledgeGraph}
      />
    </aside>
  );
  const dashboardPanel = (
    <main
      aria-label="项目脉冲面板"
      className="min-w-0 overflow-y-auto rounded-[var(--app-radius-shell)] border border-[var(--app-border)] bg-[color:var(--app-surface)] p-4 shadow-[var(--app-shadow-sm)]"
    >
      <div className="space-y-4">
        <section className="rounded-[18px] border border-[var(--app-border)] bg-[color:var(--app-shell)] p-4">
          <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--app-text-muted)]">项目脉冲</div>
          <div className="mt-2 text-lg font-semibold text-[color:var(--app-text-primary)]">
            {workbenchHighlights?.recommended_focus || '当前优先任务还未形成，建议先锁定本章目标。'}
          </div>
          <div className="mt-2 grid gap-3 md:grid-cols-3">
            <div className="rounded-[16px] bg-white px-4 py-3 shadow-[var(--app-shadow-sm)]">
              <div className="text-[11px] uppercase tracking-[0.14em] text-[color:var(--app-text-muted)]">工作流</div>
              <div className="mt-1 text-sm font-semibold text-[color:var(--app-text-primary)]">
                {workflowGate ? formatWorkflowStatus(workflowGate.status) : '待判定'}
              </div>
              <div className="mt-2 text-xs leading-5 text-[color:var(--app-text-muted)]">
                {workflowGate?.summary || '当前无阻塞，可继续推进正文或审阅。'}
              </div>
            </div>
            <div className="rounded-[16px] bg-white px-4 py-3 shadow-[var(--app-shadow-sm)]">
              <div className="text-[11px] uppercase tracking-[0.14em] text-[color:var(--app-text-muted)]">当前主线</div>
              <div className="mt-1 text-sm font-semibold text-[color:var(--app-text-primary)]">
                {workbenchHighlights?.active_storyline?.name || '主线建立中'}
              </div>
              <div className="mt-2 text-xs leading-5 text-[color:var(--app-text-muted)]">
                {workbenchHighlights?.active_storyline?.description || '继续生成与整理后，这里会显示当前主线压力。'}
              </div>
            </div>
            <div className="rounded-[16px] bg-white px-4 py-3 shadow-[var(--app-shadow-sm)]">
              <div className="text-[11px] uppercase tracking-[0.14em] text-[color:var(--app-text-muted)]">下一行动</div>
              <div className="mt-1 text-sm font-semibold text-[color:var(--app-text-primary)]">
                {selectedChapter ? `处理第 ${selectedChapter.chapter_number} 章` : `准备第 ${nextChapterNumber} 章`}
              </div>
              <div className="mt-2 text-xs leading-5 text-[color:var(--app-text-muted)]">
                {workbenchHighlights?.focus_card?.mission || '没有锁定章节时，优先确定当前推进目标。'}
              </div>
            </div>
          </div>
        </section>

        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(18rem,22rem)]">
          <section className="space-y-4">
            <div className="rounded-[18px] border border-[var(--app-border)] bg-white p-4 shadow-[var(--app-shadow-sm)]">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--app-text-muted)]">最近章节</div>
                  <div className="mt-1 text-sm font-semibold text-[color:var(--app-text-primary)]">最近推进与章节状态</div>
                </div>
                <Tag color="blue" className="mr-0">{dashboardPulse.latestChapters.length} 章</Tag>
              </div>
              <div className="mt-3 space-y-3">
                {dashboardPulse.latestChapters.length ? dashboardPulse.latestChapters.map((chapter) => (
                  <div key={chapter.id} className="rounded-[16px] border border-[var(--app-border)] bg-[color:var(--app-shell)] px-4 py-3">
                    <div className="flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-semibold text-[color:var(--app-text-primary)]">
                          第 {chapter.chapter_number} 章 {chapter.title || ''}
                        </div>
                        <div className="mt-1 text-xs text-[color:var(--app-text-muted)]">
                          {chapter.word_count || 0} 字 · {chapter.review_status === 'approved' ? '已定稿' : chapter.review_status === 'revise' ? '需修订' : '待审'}
                        </div>
                      </div>
                      <Tag color={chapter.consistency_status?.status === 'ok' ? 'green' : chapter.consistency_status?.status ? 'orange' : 'default'} className="mr-0">
                        {chapter.consistency_status?.status || '未检'}
                      </Tag>
                    </div>
                    {chapter.summary ? (
                      <div className="mt-2 line-clamp-2 text-xs leading-5 text-[color:var(--app-text-muted)]">
                        {chapter.summary}
                      </div>
                    ) : null}
                  </div>
                )) : (
                  <div className="text-sm text-[color:var(--app-text-muted)]">暂无章节数据。</div>
                )}
              </div>
            </div>

            <div className="rounded-[18px] border border-[var(--app-border)] bg-white p-4 shadow-[var(--app-shadow-sm)]">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--app-text-muted)]">主线与情节点</div>
                  <div className="mt-1 text-sm font-semibold text-[color:var(--app-text-primary)]">后续推进窗口</div>
                </div>
              </div>
              <div className="mt-3 grid gap-3 lg:grid-cols-2">
                <div className="space-y-3">
                  {(dashboardPulse.activeStorylines.length ? dashboardPulse.activeStorylines : storylines.slice(0, 3)).map((item) => (
                    <div key={item.id} className="rounded-[16px] bg-[color:var(--app-shell)] px-4 py-3">
                      <div className="flex items-center justify-between gap-2">
                        <div className="font-medium text-[color:var(--app-text-primary)]">{item.name}</div>
                        <Tag color={item.status === 'active' ? 'green' : 'default'} className="mr-0">
                          {item.status}
                        </Tag>
                      </div>
                      <div className="mt-2 text-xs leading-5 text-[color:var(--app-text-muted)]">
                        {item.description || '暂无主线描述'}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="space-y-3">
                  {dashboardPulse.nextMilestones.length ? dashboardPulse.nextMilestones.map((point) => (
                    <div key={point.id} className="rounded-[16px] border border-[var(--app-border)] px-4 py-3">
                      <div className="flex items-center justify-between gap-3">
                        <div className="text-sm font-medium text-[color:var(--app-text-primary)]">
                          第 {point.chapter_number} 章
                        </div>
                        <Tag color="purple" className="mr-0">
                          张力 {point.tension_level}
                        </Tag>
                      </div>
                      <div className="mt-2 text-xs leading-5 text-[color:var(--app-text-muted)]">
                        {point.description}
                      </div>
                    </div>
                  )) : (
                    <div className="rounded-[16px] bg-[color:var(--app-shell)] px-4 py-3 text-sm text-[color:var(--app-text-muted)]">
                      暂无后续情节点，建议先补主线推进与情节弧。
                    </div>
                  )}
                </div>
              </div>
            </div>
          </section>

          <aside className="space-y-4">
            <div className="rounded-[18px] border border-[var(--app-border)] bg-white p-4 shadow-[var(--app-shadow-sm)]">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--app-text-muted)]">风险队列</div>
              <div className="mt-3 space-y-3">
                {workbenchHighlights?.continuity_alerts?.length ? workbenchHighlights.continuity_alerts.slice(0, 4).map((item) => (
                  <div key={`${item.level}-${item.title}`} className="rounded-[16px] border border-[var(--app-border)] px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Tag color={item.level === 'critical' ? 'red' : item.level === 'warning' ? 'orange' : 'blue'} className="mr-0">
                        {item.level}
                      </Tag>
                      <div className="text-sm font-medium text-[color:var(--app-text-primary)]">{item.title}</div>
                    </div>
                    <div className="mt-2 text-xs leading-5 text-[color:var(--app-text-muted)]">{item.detail}</div>
                  </div>
                )) : (
                  <div className="rounded-[16px] bg-[color:var(--app-shell)] px-4 py-3 text-sm text-[color:var(--app-text-muted)]">
                    暂无连续性风险。
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-[18px] border border-[var(--app-border)] bg-white p-4 shadow-[var(--app-shadow-sm)]">
              <div className="text-[11px] uppercase tracking-[0.18em] text-[color:var(--app-text-muted)]">伏笔回收</div>
              <div className="mt-3 space-y-3">
                {dashboardPulse.openForeshadow.length ? dashboardPulse.openForeshadow.map((item) => (
                  <div key={item.id} className="rounded-[16px] bg-[color:var(--app-shell)] px-4 py-3">
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-sm font-medium text-[color:var(--app-text-primary)]">{item.title}</div>
                      <Tag color="gold" className="mr-0">
                        {item.expected_payoff_chapter || '--'} 章
                      </Tag>
                    </div>
                    <div className="mt-2 text-xs leading-5 text-[color:var(--app-text-muted)]">
                      {item.description || '暂无描述'}
                    </div>
                  </div>
                )) : (
                  <div className="rounded-[16px] bg-[color:var(--app-shell)] px-4 py-3 text-sm text-[color:var(--app-text-muted)]">
                    当前没有待回收伏笔。
                  </div>
                )}
              </div>
            </div>
          </aside>
        </div>
      </div>
    </main>
  );

  return (
    <div className="flex h-screen flex-col bg-[color:var(--app-page-bg)] text-[color:var(--app-text-primary)]">
      {missingBookTitle && (
        <Alert
          title="该项目尚未设置书名"
          description="建议先设置书名以获得更好的 AI 生成效果。书名会影响 AI 对故事风格和主题的理解。"
          type="warning"
          showIcon
          closable
          action={
            <Button size="small" type="primary" ghost onClick={() => navigate('/')}>
              返回首页
            </Button>
          }
          className="rounded-none border-x-0 border-t-0"
        />
      )}

      <header className="workspace-topbar px-4 sm:px-6">
        <div className="mx-auto flex h-full w-full max-w-[1800px] items-center gap-4">
          {/* Left: back button + title */}
          <div className="flex shrink-0 items-center gap-3">
            <Button
              type="text"
              icon={<ArrowLeftOutlined />}
              size="small"
              onClick={() => navigate('/')}
              style={{ color: 'rgba(255,255,255,0.7)' }}
              className="hover:!bg-white/10 hover:!text-white"
            />
            <div className="h-4 w-px bg-white/20" />
            <div className="min-w-0">
              <div className="max-w-[180px] truncate text-sm font-semibold text-white">
                {displayTitle}
              </div>
              <div className="max-w-[180px] truncate text-[10px] text-white/50">
                {selectedNovel?.genre || '未分类'}
              </div>
            </div>
          </div>

          {/* Center: stats pills */}
          <div className="flex flex-1 items-center justify-center gap-2 overflow-x-auto">
            {topBarStats.map((stat) => (
              <div
                key={stat.label}
                title={stat.tip}
                className="flex shrink-0 items-center gap-2 rounded-[10px] border border-white/10 bg-white/10 px-3 py-1"
              >
                <span className="text-[10px] uppercase tracking-[0.12em] text-white/50">
                  {stat.label}
                </span>
                <span className="text-sm font-semibold text-white">{stat.value}</span>
              </div>
            ))}
          </div>

          {/* Right: surface switcher */}
          <div className="flex shrink-0 items-center gap-0.5 rounded-[12px] border border-white/10 bg-white/10 p-1">
            {WORKSPACE_SURFACES.map((surface) => {
              const active = surface.id === activeSurface;
              return (
                <button
                  key={surface.id}
                  type="button"
                  title={surface.description}
                  onClick={() => setActiveSurface(surface.id)}
                  className={`rounded-[8px] px-3 py-1 text-sm font-medium transition-all duration-150 ${
                    active
                      ? 'bg-white/15 text-white shadow-sm'
                      : 'text-white/55 hover:text-white/85'
                  }`}
                >
                  {surface.short}
                </button>
              );
            })}
          </div>
        </div>
      </header>

      <div className="min-h-0 flex-1 px-4 py-4 sm:px-6 sm:py-4">
        <div className="mx-auto flex h-full w-full max-w-[1800px] min-h-0">
          <PanelGroup direction="horizontal" className="min-h-0 w-full gap-0">
            {/* Left: chapter rail */}
            <Panel defaultSize={16} minSize={12} maxSize={28} className="min-h-0">
              {chapterRail}
            </Panel>

            <PanelResizeHandle className="workspace-resize-handle mx-1" />

            {/* Center panel */}
            <Panel defaultSize={55} minSize={35} className="min-h-0">
              {activeSurface === 'dashboard'
                ? dashboardPanel
                : activeSurface === 'intelligence'
                  ? intelligencePanel
                  : writingCenterPanel}
            </Panel>

            <PanelResizeHandle className="workspace-resize-handle mx-1" />

            {/* Right panel */}
            <Panel defaultSize={29} minSize={20} maxSize={40} className="min-h-0">
              {activeSurface === 'intelligence' ? writingCenterPanel : intelligencePanel}
            </Panel>
          </PanelGroup>
        </div>
      </div>
    </div>
  );
};
