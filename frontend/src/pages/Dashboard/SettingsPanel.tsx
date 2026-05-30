import React, { useEffect, useMemo, useState } from 'react';
import { Button, Empty, Input, Progress, Segmented, Tabs, Tag } from 'antd';
import MDEditor from '@uiw/react-md-editor';
import { InsightGraph } from '../../components/charts/InsightGraph';
import type {
  ChapterAssetSnapshot,
  Chapter,
  ChapterReviewRecord,
  ChapterSummaryRecord,
  ContinuityAlertRecord,
  FocusCardRecord,
  ForeshadowItemRecord,
  KnowledgeFactRecord,
  KnowledgeGraphPayload,
  MicroBeatRecord,
  NovelSettingRecord,
  PlotArcPointRecord,
  StorylineRecord,
  StyleProfileRecord,
  WorkbenchHighlights,
} from './types';
import { WIZARD_STEP_TYPES } from './constants';

const STEP_LABELS: Record<string, string> = {
  worldview: '世界观',
  characters: '角色',
  map: '地图',
  storyline: '故事线',
  plot_arc: '情节弧',
  opening: '开篇',
};

interface SettingsPanelProps {
  settings: NovelSettingRecord[];
  chapter: Chapter | null;
  chapterSummaries: ChapterSummaryRecord[];
  chapterReviews: ChapterReviewRecord[];
  storylines: StorylineRecord[];
  plotArcPoints: PlotArcPointRecord[];
  knowledgeFacts: KnowledgeFactRecord[];
  foreshadowItems: ForeshadowItemRecord[];
  chapterAssetIndex?: Record<string, ChapterAssetSnapshot>;
  styleProfiles: StyleProfileRecord[];
  onSaveChapterReview?: (
    chapterId: number,
    payload: {
      status?: 'pending' | 'approved' | 'revise';
      review_notes?: string;
      generate_ai?: boolean;
      apply_ai_to_notes?: boolean;
    },
    options?: { silent?: boolean },
  ) => Promise<ChapterReviewRecord>;
  workbenchHighlights?: WorkbenchHighlights;
  knowledgeGraph?: KnowledgeGraphPayload;
  focusSignals?: Array<{
    key: string;
    title: string;
    value: string;
    detail: string;
    tone: string;
    icon: React.ReactNode;
  }>;
  dashboardPulse?: {
    latestChapters: Chapter[];
    nextMilestones: PlotArcPointRecord[];
    activeStorylines: StorylineRecord[];
    openForeshadow: ForeshadowItemRecord[];
  };
  aggregatedStats?: {
    totalWords: number;
    finishedChapters: number;
    completionRate: number;
    averageWords: number;
    lastUpdate: string;
  };
}

const styleRiskColor: Record<string, string> = {
  low: 'green',
  medium: 'orange',
  high: 'red',
  unknown: 'default',
};

const toneClassMap: Record<string, string> = {
  default: 'border-[var(--app-border)] bg-[var(--app-surface)]',
  warning: 'border-amber-200 bg-[linear-gradient(180deg,#fffdf7_0%,#ffffff_100%)]',
  danger: 'border-rose-200 bg-[linear-gradient(180deg,#fff8f8_0%,#ffffff_100%)]',
  accent: 'border-sky-200 bg-[linear-gradient(180deg,#f8fcff_0%,#ffffff_100%)]',
};

const alertColorMap: Record<ContinuityAlertRecord['level'], string> = {
  info: 'blue',
  warning: 'orange',
  critical: 'red',
};

const isSnapshotShape = (
  value: unknown,
): value is {
  focus_card?: FocusCardRecord;
  micro_beats?: MicroBeatRecord[];
  continuity_alerts?: ContinuityAlertRecord[];
} => typeof value === 'object' && value !== null;

const PanelCard: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <div className="rounded-[18px] border border-[var(--app-border)] bg-[color:var(--app-surface)] p-4 shadow-[var(--app-shadow-sm)]">
    <div className="mb-3 text-[11px] font-medium uppercase tracking-[0.2em] text-slate-400">{title}</div>
    {children}
  </div>
);

export const SettingsPanel: React.FC<SettingsPanelProps> = ({
  settings,
  chapter,
  chapterSummaries,
  chapterReviews,
  storylines,
  plotArcPoints,
  knowledgeFacts,
  foreshadowItems,
  chapterAssetIndex,
  styleProfiles,
  onSaveChapterReview,
  workbenchHighlights,
  knowledgeGraph,
  focusSignals,
  dashboardPulse,
  aggregatedStats,
}) => {
  const [reviewStatusDraft, setReviewStatusDraft] = useState<'pending' | 'approved' | 'revise'>('pending');
  const [reviewNotesDraft, setReviewNotesDraft] = useState('');
  const [aiReviewDraft, setAiReviewDraft] = useState('');
  const [aiActionItemsDraft, setAiActionItemsDraft] = useState<string[]>([]);
  const [savingReview, setSavingReview] = useState(false);
  const [generatingReview, setGeneratingReview] = useState(false);

  const settingsMap = useMemo(() => {
    const map: Record<string, NovelSettingRecord> = {};
    settings.forEach((item) => {
      map[item.setting_type] = item;
    });
    return map;
  }, [settings]);

  const selectedSummary = useMemo(() => {
    if (!chapter) return chapterSummaries[chapterSummaries.length - 1];
    return chapterSummaries.find((item) => item.chapter === chapter.id)
      || chapterSummaries.find((item) => item.chapter_number === chapter.chapter_number)
      || chapterSummaries[chapterSummaries.length - 1];
  }, [chapter, chapterSummaries]);

  const matchedChapterSummary = useMemo(() => {
    if (!chapter) return null;
    return chapterSummaries.find((item) => item.chapter === chapter.id)
      || chapterSummaries.find((item) => item.chapter_number === chapter.chapter_number)
      || null;
  }, [chapter, chapterSummaries]);

  const latestStyleAnalysis = useMemo(
    () => styleProfiles.find((item) => item.profile_type === 'chapter_analysis'),
    [styleProfiles],
  );

  const currentChapterReview = useMemo(() => {
    if (!chapter) return null;
    return chapterReviews.find((item) => item.chapter === chapter.id)
      || chapterReviews.find((item) => item.chapter_number === chapter.chapter_number)
      || null;
  }, [chapter, chapterReviews]);

  const chapterAssetSnapshot = useMemo<ChapterAssetSnapshot | null>(() => {
    if (!chapter || !chapterAssetIndex) return null;
    return chapterAssetIndex[String(chapter.chapter_number)] || null;
  }, [chapter, chapterAssetIndex]);

  const graphProjects = useMemo(() => {
    if (!knowledgeGraph?.nodes) return [];
    const plotNodes = knowledgeGraph.nodes.filter((node) => node.category === 'plot');
    return plotNodes.map((node) => ({ title: node.name, status: node.category }));
  }, [knowledgeGraph]);

  const graphInspirations = useMemo(() => {
    if (!knowledgeGraph?.nodes) return [];
    const characterNodes = knowledgeGraph.nodes.filter((node) => node.category === 'character');
    return characterNodes.map((node) => ({
      title: node.name,
      hot_score: Number(node.info?.influence) || 0,
    }));
  }, [knowledgeGraph]);

  const snapshot = useMemo(
    () => (isSnapshotShape(chapter?.context_snapshot) ? chapter?.context_snapshot : undefined),
    [chapter?.context_snapshot],
  );

  const focusCard = useMemo<FocusCardRecord | null>(
    () => snapshot?.focus_card || workbenchHighlights?.focus_card || null,
    [snapshot?.focus_card, workbenchHighlights?.focus_card],
  );

  const microBeats = useMemo<MicroBeatRecord[]>(
    () => snapshot?.micro_beats || workbenchHighlights?.micro_beats || [],
    [snapshot?.micro_beats, workbenchHighlights?.micro_beats],
  );

  const continuityAlerts = useMemo<ContinuityAlertRecord[]>(
    () => snapshot?.continuity_alerts || workbenchHighlights?.continuity_alerts || [],
    [snapshot?.continuity_alerts, workbenchHighlights?.continuity_alerts],
  );

  const chapterSummaryText = useMemo(
    () => matchedChapterSummary?.summary || chapter?.summary || '',
    [chapter?.summary, matchedChapterSummary?.summary],
  );

  const chapterKeyEvents = useMemo(
    () => (matchedChapterSummary?.key_events || []).filter(Boolean),
    [matchedChapterSummary?.key_events],
  );

  const chapterOpenThreads = useMemo(() => {
    const values = [
      ...(chapter?.open_threads || []),
      ...(matchedChapterSummary?.open_threads || []),
    ]
      .map((item) => String(item || '').trim())
      .filter(Boolean);
    return Array.from(new Set(values));
  }, [chapter?.open_threads, matchedChapterSummary?.open_threads]);

  const chapterKnowledgeFacts = useMemo(() => {
    if (!chapter) return [];
    if (chapterAssetSnapshot?.knowledge_facts?.length) return chapterAssetSnapshot.knowledge_facts;
    return knowledgeFacts.filter((item) => (
      item.chapter === chapter.id || item.chapter_number === chapter.chapter_number
    )).slice(0, 8);
  }, [chapter, chapterAssetSnapshot?.knowledge_facts, knowledgeFacts]);

  const introducedForeshadowItems = useMemo(() => {
    if (!chapter) return [];
    if (chapterAssetSnapshot?.introduced_foreshadow_items?.length) {
      return chapterAssetSnapshot.introduced_foreshadow_items;
    }
    return foreshadowItems.filter(
      (item) => item.introduced_in_chapter_number === chapter.chapter_number,
    ).slice(0, 6);
  }, [chapter, chapterAssetSnapshot?.introduced_foreshadow_items, foreshadowItems]);

  const recommendedForeshadowItems = useMemo(() => {
    if (!chapter) return [];
    if (chapterAssetSnapshot?.recommended_foreshadow_items?.length) {
      return chapterAssetSnapshot.recommended_foreshadow_items;
    }
    return foreshadowItems.filter((item) => (
      item.status !== 'resolved'
      && item.introduced_in_chapter_number
      && item.introduced_in_chapter_number < chapter.chapter_number
      && (item.expected_payoff_chapter || chapter.chapter_number + 2) <= chapter.chapter_number + 1
    )).slice(0, 4);
  }, [chapter, chapterAssetSnapshot?.recommended_foreshadow_items, foreshadowItems]);

  const chapterConsistencyRisks = useMemo(() => {
    const risks = chapter?.consistency_status?.risks;
    if (!Array.isArray(risks)) return [];
    return risks.map((item) => String(item || '').trim()).filter(Boolean);
  }, [chapter?.consistency_status?.risks]);

  const chapterCheckedEntities = useMemo(() => {
    const entities = chapter?.consistency_status?.checked_entities;
    if (!Array.isArray(entities)) return [];
    return entities.map((item) => String(item || '').trim()).filter(Boolean);
  }, [chapter?.consistency_status?.checked_entities]);

  const chapterCharacters = useMemo(
    () => chapterAssetSnapshot?.character_elements || [],
    [chapterAssetSnapshot?.character_elements],
  );

  const chapterLocations = useMemo(
    () => chapterAssetSnapshot?.location_elements || [],
    [chapterAssetSnapshot?.location_elements],
  );

  const chapterEventCards = useMemo(
    () => chapterAssetSnapshot?.event_cards || [],
    [chapterAssetSnapshot?.event_cards],
  );

  const chapterQualityIssues = useMemo(
    () => chapterAssetSnapshot?.quality_issues || [],
    [chapterAssetSnapshot?.quality_issues],
  );

  const chapterRepairActions = useMemo(
    () => chapterAssetSnapshot?.repair_actions || [],
    [chapterAssetSnapshot?.repair_actions],
  );
  const tacticalTabLabel = (
    <div className="flex items-center gap-2">
      <span>作品设定</span>
      {(focusCard?.must_fix?.length || continuityAlerts.length) ? (
        <Tag color={(focusCard?.must_fix?.length || continuityAlerts.some((item) => item.level === 'critical')) ? 'red' : 'orange'} className="mr-0">
          {(focusCard?.must_fix?.length || 0) + continuityAlerts.length}
        </Tag>
      ) : null}
    </div>
  );
  const chapterTabLabel = (
    <div className="flex items-center gap-2">
      <span>手稿道具</span>
      {chapter ? (
        <Tag color="blue" className="mr-0">
          第 {chapter.chapter_number} 章
        </Tag>
      ) : null}
    </div>
  );
  const reviewTabLabel = (
    <div className="flex items-center gap-2">
      <span>故事演进</span>
      {currentChapterReview?.status && currentChapterReview.status !== 'pending' ? (
        <Tag color={currentChapterReview.status === 'approved' ? 'green' : 'orange'} className="mr-0">
          {currentChapterReview.status === 'approved' ? '已定稿' : '需修订'}
        </Tag>
      ) : null}
    </div>
  );

  const estimatedReviewModificationRate = useMemo(() => {
    if (typeof currentChapterReview?.modification_rate === 'number') {
      return currentChapterReview.modification_rate;
    }

    const original = (chapter?.raw_content || '').replace(/\s/g, '');
    const revised = ((chapter?.final_content || chapter?.raw_content || '')).replace(/\s/g, '');
    if (!original) return revised ? 100 : 0;
    const compareLength = Math.min(original.length, revised.length);
    let sameCount = 0;
    for (let index = 0; index < compareLength; index += 1) {
      if (original[index] === revised[index]) sameCount += 1;
    }
    const denominator = Math.max(original.length, revised.length, 1);
    return Math.max(0, Math.round((1 - (sameCount / denominator)) * 100));
  }, [chapter?.final_content, chapter?.raw_content, currentChapterReview?.modification_rate]);

  useEffect(() => {
    setReviewStatusDraft(currentChapterReview?.status || chapter?.review_status || 'pending');
    setReviewNotesDraft(currentChapterReview?.review_notes || '');
    setAiReviewDraft(currentChapterReview?.ai_review || '');
    setAiActionItemsDraft(currentChapterReview?.ai_action_items || []);
  }, [
    chapter?.id,
    chapter?.review_status,
    currentChapterReview?.ai_action_items,
    currentChapterReview?.ai_review,
    currentChapterReview?.review_notes,
    currentChapterReview?.status,
  ]);

  const handleGenerateAiReview = async () => {
    if (!chapter || !onSaveChapterReview) return;
    setGeneratingReview(true);
    try {
      const review = await onSaveChapterReview(chapter.id, { generate_ai: true });
      setReviewStatusDraft(review.status);
      setAiReviewDraft(review.ai_review || '');
      setAiActionItemsDraft(review.ai_action_items || []);
      if (!reviewNotesDraft.trim() && review.ai_review) {
        setReviewNotesDraft(review.ai_review);
      }
    } catch {
      // WorkspacePage already surfaces the error message.
    } finally {
      setGeneratingReview(false);
    }
  };

  const handleSaveReview = async () => {
    if (!chapter || !onSaveChapterReview) return;
    setSavingReview(true);
    try {
      const review = await onSaveChapterReview(chapter.id, {
        status: reviewStatusDraft,
        review_notes: reviewNotesDraft,
      });
      setReviewStatusDraft(review.status);
      setReviewNotesDraft(review.review_notes || '');
      setAiReviewDraft(review.ai_review || '');
      setAiActionItemsDraft(review.ai_action_items || []);
    } catch {
      // WorkspacePage already surfaces the error message.
    } finally {
      setSavingReview(false);
    }
  };

  const settingsTabItems = WIZARD_STEP_TYPES.map((type) => ({
    key: type,
    label: STEP_LABELS[type] || type,
    children: settingsMap[type] ? (
      <div className="overflow-y-auto" style={{ maxHeight: 280 }}>
        <MDEditor.Markdown source={settingsMap[type].content || '暂无内容'} style={{ background: 'transparent' }} />
      </div>
    ) : (
      <Empty description="暂未生成，请先完成向导设定" image={Empty.PRESENTED_IMAGE_SIMPLE} />
    ),
  }));
  const scrollPaneStyle = { maxHeight: 'calc(100vh - 14rem)' };

  return (
    <div className="flex h-full flex-col bg-[color:var(--app-shell)]">
      <div className="border-b border-[var(--app-divider)] bg-[color:var(--app-surface)] px-5 py-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-[1.05rem] font-semibold text-slate-800">作品设定</h3>
              <Tag color="purple" className="mr-0">Story Bible</Tag>
            </div>
            <div className="mt-2 max-w-[34rem] text-xs leading-6 text-slate-500">
              梗概锁定、写作公约、世界观与角色关系在这里汇总。右栏负责“这本书是什么”，不抢中间正文主航道。
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {workbenchHighlights?.quality_snapshot && (
              <Tag color={styleRiskColor[workbenchHighlights.quality_snapshot.style_risk || 'unknown']}>
                风格风险 {workbenchHighlights.quality_snapshot.style_risk || 'unknown'}
              </Tag>
            )}
            {workbenchHighlights?.quality_snapshot?.consistency_status && (
              <Tag color={workbenchHighlights.quality_snapshot.consistency_status === 'ok' ? 'green' : 'orange'}>
                一致性 {workbenchHighlights.quality_snapshot.consistency_status}
              </Tag>
            )}
          </div>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-hidden p-4">
        <Tabs
          className="workspace-tabs workspace-tabs--panel h-full rounded-[18px] border border-[var(--app-border)] bg-[color:var(--app-surface)] px-4 pt-2 shadow-[var(--app-shadow-sm)]"
          items={[
            {
              key: 'tactical',
              label: tacticalTabLabel,
              children: (
                <div className="overflow-y-auto overflow-x-hidden pr-1 pb-4" style={scrollPaneStyle}>
                  <PanelCard title="本书锁定">
                    {focusCard?.mission || workbenchHighlights?.recommended_focus ? (
                      <div className="space-y-4 text-sm">
                        <div>
                          <div className="text-xs text-slate-400">梗概锁定</div>
                          <div className="mt-1 font-medium leading-6 text-slate-800">
                            {focusCard?.mission || workbenchHighlights?.recommended_focus}
                          </div>
                        </div>
                        {focusCard?.conflict ? (
                          <div>
                            <div className="text-xs text-slate-400">核心冲突</div>
                            <div className="mt-1 leading-6 text-slate-600">{focusCard.conflict}</div>
                          </div>
                        ) : null}
                        {focusCard?.ending_hook ? (
                          <div>
                            <div className="text-xs text-slate-400">写作公约</div>
                            <div className="mt-1 leading-6 text-slate-600">{focusCard.ending_hook}</div>
                          </div>
                        ) : null}
                        {focusCard?.must_keep?.length ? (
                          <div>
                            <div className="text-xs text-slate-400">必须保持</div>
                            <div className="mt-2 min-w-0 flex flex-wrap gap-2">
                              {focusCard.must_keep.map((item) => (
                                <Tag key={item} color="blue" className="mr-0 whitespace-normal break-words">{item}</Tag>
                              ))}
                            </div>
                          </div>
                        ) : null}
                      </div>
                    ) : (
                      <Empty description="生成章节后自动形成当前写作焦点" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                    )}
                  </PanelCard>

                  <PanelCard title="资料分工">
                    {microBeats.length ? (
                      <div className="space-y-3">
                        <div className="grid gap-3 sm:grid-cols-2">
                          <div className="rounded-2xl border border-indigo-100 bg-indigo-50/60 px-4 py-3">
                            <div className="text-xs font-medium text-indigo-500">梗概锁定</div>
                            <div className="mt-2 text-sm font-semibold text-slate-800">主线与不可违背设定</div>
                            <div className="mt-1 text-xs leading-5 text-slate-500">此处维护全书上下文，不让剧情跑偏。</div>
                          </div>
                          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                            <div className="text-xs font-medium text-slate-500">世界观构建</div>
                            <div className="mt-2 text-sm font-semibold text-slate-800">世界观 Tab</div>
                            <div className="mt-1 text-xs leading-5 text-slate-500">承接更细的世界规则和框架。</div>
                          </div>
                          <div className="rounded-2xl border border-indigo-100 bg-indigo-50/60 px-4 py-3">
                            <div className="text-xs font-medium text-indigo-500">写作风格</div>
                            <div className="mt-2 text-sm font-semibold text-slate-800">本书锁定的文风公约</div>
                            <div className="mt-1 text-xs leading-5 text-slate-500">控制“怎么写”，保持全书语气稳定。</div>
                          </div>
                          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                            <div className="text-xs font-medium text-slate-500">角色与地点</div>
                            <div className="mt-2 text-sm font-semibold text-slate-800">知识库与图谱</div>
                            <div className="mt-1 text-xs leading-5 text-slate-500">查看三元组关系和章节资产。</div>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <Empty description="暂无设定分工信息" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                    )}
                  </PanelCard>

                  <PanelCard title="写作风险与回收">
                    <div className="space-y-4 text-sm">
                      <div>
                        <div className="text-xs text-slate-400">连续性提醒</div>
                        <div className="mt-2 space-y-2">
                          {continuityAlerts.length ? continuityAlerts.slice(0, 3).map((alert) => (
                            <div key={`${alert.level}-${alert.title}`} className="rounded-2xl border border-slate-100 px-4 py-3">
                              <div className="flex items-center gap-2 min-w-0">
                                <Tag color={alertColorMap[alert.level]} className="mr-0 shrink-0">
                                  {alert.level}
                                </Tag>
                                <div className="font-medium text-slate-800 text-sm min-w-0 truncate">{alert.title}</div>
                              </div>
                              <div className="mt-2 text-sm leading-6 text-slate-600">{alert.detail}</div>
                            </div>
                          )) : <div className="text-slate-300">暂无连续性警报</div>}
                        </div>
                      </div>

                      <div>
                        <div className="text-xs text-slate-400">优先回收</div>
                        <div className="mt-2 min-w-0 flex flex-wrap gap-2">
                          {workbenchHighlights?.due_foreshadow_items?.length
                            ? workbenchHighlights.due_foreshadow_items.slice(0, 4).map((item) => (
                              <Tag key={item.id} color="gold" className="mr-0 whitespace-normal break-words">
                                {item.title}
                              </Tag>
                            ))
                            : <span className="text-slate-300">暂无紧迫伏笔</span>}
                        </div>
                      </div>
                    </div>
                  </PanelCard>
                </div>
              ),
            },
            {
              key: 'review',
              label: reviewTabLabel,
              children: chapter ? (
                <div className="space-y-4 overflow-y-auto overflow-x-hidden pr-1 pb-4" style={scrollPaneStyle}>
                  <PanelCard title="审阅状态">
                    <div className="space-y-4">
                      <div className="flex flex-wrap items-center gap-2">
                        <Tag color={reviewStatusDraft === 'approved' ? 'green' : reviewStatusDraft === 'revise' ? 'orange' : 'default'} className="mr-0">
                          {reviewStatusDraft === 'approved' ? '已定稿' : reviewStatusDraft === 'revise' ? '需修订' : '待阅'}
                        </Tag>
                        <Tag color={estimatedReviewModificationRate >= 15 ? 'blue' : 'red'} className="mr-0">
                          修改率 {estimatedReviewModificationRate}%
                        </Tag>
                        {currentChapterReview?.reviewer_username ? (
                          <Tag color="cyan" className="mr-0">
                            {currentChapterReview.reviewer_username}
                          </Tag>
                        ) : null}
                      </div>

                      <Segmented
                        block
                        value={reviewStatusDraft}
                        onChange={(value) => setReviewStatusDraft(value as 'pending' | 'approved' | 'revise')}
                        options={[
                          { label: '待阅', value: 'pending' },
                          { label: '已定稿', value: 'approved' },
                          { label: '需修订', value: 'revise' },
                        ]}
                      />

                      <div>
                        <div className="mb-2 text-xs text-slate-400">审阅意见</div>
                        <Input.TextArea
                          value={reviewNotesDraft}
                          onChange={(event) => setReviewNotesDraft(event.target.value)}
                          rows={8}
                          placeholder="记录人工审稿结论、问题位置和修改建议。"
                        />
                      </div>

                      <div className="flex flex-wrap gap-2">
                        <Button
                          onClick={() => setReviewNotesDraft(aiReviewDraft || reviewNotesDraft)}
                          disabled={!aiReviewDraft}
                        >
                          写入 AI 建议
                        </Button>
                        <Button
                          onClick={handleGenerateAiReview}
                          loading={generatingReview}
                        >
                          生成 AI 审读建议
                        </Button>
                        <Button
                          type="primary"
                          onClick={handleSaveReview}
                          loading={savingReview}
                        >
                          保存审阅
                        </Button>
                      </div>
                    </div>
                  </PanelCard>

                  <PanelCard title="AI 审读建议">
                    {aiReviewDraft ? (
                      <div className="space-y-4 text-sm">
                        <div className="rounded-2xl bg-slate-50 px-4 py-3 leading-6 text-slate-700 whitespace-pre-wrap">
                          {aiReviewDraft}
                        </div>
                        <div>
                          <div className="mb-2 text-xs text-slate-400">动作清单</div>
                          <div className="min-w-0 flex flex-wrap gap-2">
                            {aiActionItemsDraft.length
                              ? aiActionItemsDraft.map((item, index) => (
                                <Tag key={`${item}-${index}`} color="blue" className="mr-0 whitespace-normal break-words">
                                  {item}
                                </Tag>
                              ))
                              : <span className="text-slate-300">暂无动作建议</span>}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <Empty description="还没有 AI 审读建议" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                    )}
                  </PanelCard>
                </div>
              ) : (
                <div className="flex h-full items-center justify-center">
                  <Empty description="请选择一个章节后开始审阅" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                </div>
              ),
            },
            {
              key: 'chapter',
              label: chapterTabLabel,
              children: chapter ? (
                <div className="space-y-4 overflow-y-auto overflow-x-hidden pr-1 pb-4" style={scrollPaneStyle}>
                  <PanelCard title="当前章节">
                    <div className="space-y-4 text-sm">
                      <div>
                        <div className="flex items-center justify-between gap-3">
                          <div className="min-w-0">
                            <div className="truncate font-medium text-slate-800">
                              第 {chapter.chapter_number} 章
                              {chapter.title ? ` · ${chapter.title}` : ''}
                            </div>
                            <div className="mt-1 text-xs text-slate-400">
                              更新时间 {chapter.updated_at ? chapter.updated_at.slice(5, 16).replace('T', ' ') : '--'}
                            </div>
                          </div>
                          <Tag color={chapter.status === 'published' ? 'blue' : chapter.status === 'draft' ? 'gold' : 'default'} className="mr-0">
                            {chapter.status || 'draft'}
                          </Tag>
                        </div>
                        <div className="mt-3 flex flex-wrap gap-2">
                          <Tag color="cyan" className="mr-0">{chapter.word_count || 0} 字</Tag>
                          {chapterConsistencyRisks.length ? (
                            <Tag color="orange" className="mr-0">{chapterConsistencyRisks.length} 项风险</Tag>
                          ) : (
                            <Tag color="green" className="mr-0">一致性正常</Tag>
                          )}
                          {recommendedForeshadowItems.length ? (
                            <Tag color="gold" className="mr-0">{recommendedForeshadowItems.length} 条待回收</Tag>
                          ) : null}
                        </div>
                      </div>

                      <div>
                        <div className="text-xs text-slate-400">本章摘要</div>
                        <div className="mt-1 leading-6 text-slate-700">
                          {chapterSummaryText || '暂无摘要'}
                        </div>
                      </div>
                    </div>
                  </PanelCard>

                  <PanelCard title="关键事件与线索">
                    <div className="space-y-4 text-sm">
                      <div>
                        <div className="text-xs text-slate-400">关键事件</div>
                        <div className="mt-2 min-w-0 flex flex-wrap gap-2">
                          {chapterKeyEvents.length
                            ? chapterKeyEvents.map((item, index) => (
                              <Tag key={`${item}-${index}`} color="blue" className="mr-0 whitespace-normal break-words">
                                {item}
                              </Tag>
                            ))
                            : <span className="text-slate-300">暂无关键事件</span>}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-slate-400">开放线索</div>
                        <div className="mt-2 min-w-0 flex flex-wrap gap-2">
                          {chapterOpenThreads.length
                            ? chapterOpenThreads.map((item, index) => (
                              <Tag key={`${item}-${index}`} color="gold" className="mr-0 whitespace-normal break-words">
                                {item}
                              </Tag>
                            ))
                            : <span className="text-slate-300">暂无开放线索</span>}
                        </div>
                      </div>
                    </div>
                  </PanelCard>

                  <PanelCard title="事件卡">
                    {chapterEventCards.length ? (
                      <div className="space-y-3 text-sm">
                        {chapterEventCards.map((item, index) => (
                          <div key={`${item.label}-${index}`} className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3">
                            <div className="flex flex-wrap items-center gap-2">
                              <Tag color={item.tension_level === 'high' ? 'red' : item.tension_level === 'medium' ? 'orange' : 'blue'} className="mr-0">
                                {item.tension_level}
                              </Tag>
                              <Tag color="purple" className="mr-0">{item.event_type}</Tag>
                              <div className="font-medium text-slate-800">{item.label}</div>
                            </div>
                            <div className="mt-2 text-xs leading-5 text-slate-500">{item.evidence}</div>
                            <div className="mt-2 flex flex-wrap gap-2">
                              {item.actors?.map((actor) => (
                                <Tag key={`${item.label}-${actor}`} color="blue" className="mr-0 whitespace-normal break-words">
                                  {actor}
                                </Tag>
                              ))}
                              {item.locations?.map((location) => (
                                <Tag key={`${item.label}-${location}`} color="cyan" className="mr-0 whitespace-normal break-words">
                                  {location}
                                </Tag>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <Empty description="本章暂未提取出事件卡" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                    )}
                  </PanelCard>

                  <PanelCard title="关联事实">
                    {chapterKnowledgeFacts.length ? (
                      <div className="space-y-2">
                        {chapterKnowledgeFacts.map((fact) => (
                          <div key={fact.id} className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
                            <div className="text-slate-800">
                              {fact.subject} {fact.predicate} {fact.object}
                            </div>
                            <div className="mt-1 text-[11px] text-slate-400">
                              置信度 {Math.round((fact.confidence || 0) * 100)}%
                              {fact.source_excerpt ? ` · ${fact.source_excerpt.slice(0, 36)}` : ''}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <Empty description="本章暂无关联事实" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                    )}
                  </PanelCard>

                  <PanelCard title="章节元素">
                    <div className="space-y-4 text-sm">
                      <div>
                        <div className="text-xs text-slate-400">人物</div>
                        {chapterCharacters.length ? (
                          <div className="mt-2 space-y-2">
                            {chapterCharacters.map((item) => (
                              <div key={`character-${item.name}`} className="rounded-2xl bg-slate-50 px-4 py-3">
                                <div className="flex items-center gap-2">
                                  <Tag color="blue" className="mr-0">角色</Tag>
                                  <div className="font-medium text-slate-800">{item.name}</div>
                                  {item.role ? (
                                    <span className="text-xs text-slate-400">{item.role}</span>
                                  ) : null}
                                </div>
                                {item.note ? (
                                  <div className="mt-2 text-xs leading-5 text-slate-500">{item.note}</div>
                                ) : null}
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="mt-2 text-slate-300">本章暂无命中的角色设定</div>
                        )}
                      </div>

                      <div>
                        <div className="text-xs text-slate-400">地点</div>
                        {chapterLocations.length ? (
                          <div className="mt-2 space-y-2">
                            {chapterLocations.map((item) => (
                              <div key={`location-${item.name}`} className="rounded-2xl bg-slate-50 px-4 py-3">
                                <div className="flex items-center gap-2">
                                  <Tag color="cyan" className="mr-0">地点</Tag>
                                  <div className="font-medium text-slate-800">{item.name}</div>
                                  {item.type ? (
                                    <span className="text-xs text-slate-400">{item.type}</span>
                                  ) : null}
                                </div>
                                {item.note ? (
                                  <div className="mt-2 text-xs leading-5 text-slate-500">{item.note}</div>
                                ) : null}
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="mt-2 text-slate-300">本章暂无命中的地点设定</div>
                        )}
                      </div>
                    </div>
                  </PanelCard>

                  <PanelCard title="伏笔与回收建议">
                    <div className="space-y-4 text-sm">
                      <div>
                        <div className="text-xs text-slate-400">本章新埋设</div>
                        {introducedForeshadowItems.length ? (
                          <div className="mt-2 space-y-2">
                            {introducedForeshadowItems.map((item) => (
                              <div key={item.id} className="rounded-2xl bg-slate-50 px-4 py-3">
                                <div className="flex items-center justify-between gap-3">
                                  <div className="font-medium text-slate-800">{item.title}</div>
                                  <Tag color="gold" className="mr-0">{item.status}</Tag>
                                </div>
                                <div className="mt-2 text-xs leading-5 text-slate-500">
                                  {item.description || '暂无描述'}
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="mt-2 text-slate-300">本章暂无新伏笔</div>
                        )}
                      </div>

                      <div>
                        <div className="text-xs text-slate-400">建议优先回收</div>
                        {recommendedForeshadowItems.length ? (
                          <div className="mt-2 space-y-2">
                            {recommendedForeshadowItems.map((item) => (
                              <div key={item.id} className="rounded-2xl border border-amber-100 bg-amber-50/70 px-4 py-3">
                                <div className="flex items-center justify-between gap-3">
                                  <div className="font-medium text-slate-800">{item.title}</div>
                                  <Tag color="orange" className="mr-0">
                                    目标 {item.expected_payoff_chapter || '--'} 章
                                  </Tag>
                                </div>
                                <div className="mt-2 text-xs leading-5 text-slate-600">
                                  {item.description || '暂无描述'}
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="mt-2 text-slate-300">当前没有紧迫的伏笔回收项</div>
                        )}
                      </div>
                    </div>
                  </PanelCard>

                  <PanelCard title="一致性雷达">
                    <div className="space-y-4 text-sm">
                      <div>
                        <div className="text-xs text-slate-400">风险结论</div>
                        <div className="mt-2 min-w-0 flex flex-wrap gap-2">
                          {chapterConsistencyRisks.length
                            ? chapterConsistencyRisks.map((item, index) => (
                              <Tag key={`${item}-${index}`} color="orange" className="mr-0 whitespace-normal break-words">
                                {item}
                              </Tag>
                            ))
                            : <span className="text-slate-300">暂无明显风险</span>}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-slate-400">检查实体</div>
                        <div className="mt-2 min-w-0 flex flex-wrap gap-2">
                          {chapterCheckedEntities.length
                            ? chapterCheckedEntities.map((item) => (
                              <Tag key={item} color="blue" className="mr-0 whitespace-normal break-words">{item}</Tag>
                            ))
                            : <span className="text-slate-300">暂无实体检查记录</span>}
                        </div>
                      </div>
                    </div>
                  </PanelCard>

                  <PanelCard title="修订闭环">
                    <div className="space-y-4 text-sm">
                      <div>
                        <div className="text-xs text-slate-400">质量问题</div>
                        <div className="mt-2 space-y-2">
                          {chapterQualityIssues.length ? chapterQualityIssues.map((item, index) => (
                            <div key={`${item.code}-${index}`} className="rounded-2xl bg-slate-50 px-4 py-3">
                              <div className="flex items-center gap-2">
                                <Tag color={item.severity === 'high' ? 'red' : item.severity === 'medium' ? 'orange' : 'default'} className="mr-0">
                                  {item.severity}
                                </Tag>
                                <div className="font-medium text-slate-800">{item.message}</div>
                              </div>
                              {item.suggestion ? (
                                <div className="mt-2 text-xs leading-5 text-slate-500">{item.suggestion}</div>
                              ) : null}
                            </div>
                          )) : <div className="text-slate-300">暂无结构化质量问题</div>}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-slate-400">建议先改</div>
                        <div className="mt-2 min-w-0 flex flex-wrap gap-2">
                          {chapterRepairActions.length
                            ? chapterRepairActions.map((item, index) => (
                              <Tag key={`${item}-${index}`} color="red" className="mr-0 whitespace-normal break-words">
                                {item}
                              </Tag>
                            ))
                            : <span className="text-slate-300">暂无修订动作</span>}
                        </div>
                      </div>
                    </div>
                  </PanelCard>
                </div>
              ) : (
                <div className="flex h-full items-center justify-center">
                  <Empty description="请选择一个章节后查看章节资产" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                </div>
              ),
            },
            {
              key: 'settings',
              label: '世界观',
              children: (
                <div className="space-y-4 overflow-y-auto overflow-x-hidden pr-1 pb-4" style={scrollPaneStyle}>
                  <PanelCard title="设定总览">
                    <Tabs size="small" items={settingsTabItems} />
                  </PanelCard>
                  <PanelCard title="当前主线">
                    {workbenchHighlights?.active_storyline ? (
                      <div className="rounded-2xl bg-slate-50 px-4 py-3">
                        <div className="flex items-center justify-between gap-3">
                          <div className="font-medium text-slate-800">
                            {workbenchHighlights.active_storyline.name}
                          </div>
                          <Tag color={workbenchHighlights.active_storyline.status === 'active' ? 'green' : 'default'}>
                            {workbenchHighlights.active_storyline.status}
                          </Tag>
                        </div>
                        <div className="mt-2 text-sm leading-6 text-slate-600">
                          {workbenchHighlights.active_storyline.description || '暂无描述'}
                        </div>
                      </div>
                    ) : (
                      <Empty description="暂无主线信息" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                    )}
                  </PanelCard>
                </div>
              ),
            },
            {
              key: 'assets',
              label: '知识库',
              children: (
                <div className="space-y-4 overflow-y-auto overflow-x-hidden pr-1 pb-4" style={scrollPaneStyle}>
                  <PanelCard title="章节摘要">
                    {selectedSummary ? (
                      <div className="space-y-3 text-sm">
                        <div>
                          <div className="text-xs text-slate-400">摘要</div>
                          <div className="mt-1 leading-6 text-slate-700">{selectedSummary.summary || '暂无摘要'}</div>
                        </div>
                        <div>
                          <div className="text-xs text-slate-400">关键事件</div>
                          <div className="mt-2 min-w-0 flex flex-wrap gap-2">
                            {selectedSummary.key_events?.length
                              ? selectedSummary.key_events.map((event, index) => (
                                <Tag key={`${event}-${index}`} color="blue" className="mr-0 whitespace-normal break-words">{event}</Tag>
                              ))
                              : <span className="text-slate-300">暂无关键事件</span>}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-slate-400">开放线索</div>
                          <div className="mt-2 min-w-0 flex flex-wrap gap-2">
                            {selectedSummary.open_threads?.length
                              ? selectedSummary.open_threads.map((item, index) => (
                                <Tag key={`${item}-${index}`} color="gold" className="mr-0 whitespace-normal break-words">{item}</Tag>
                              ))
                              : <span className="text-slate-300">暂无开放线索</span>}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <Empty description="暂无章节摘要" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                    )}
                  </PanelCard>

                  <PanelCard title="故事线与情节点">
                    {storylines.length || plotArcPoints.length ? (
                      <div className="space-y-3">
                        {storylines.slice(0, 4).map((item) => (
                          <div key={item.id} className="rounded-2xl bg-slate-50 px-4 py-3">
                            <div className="flex items-center justify-between gap-2">
                              <div className="font-medium text-slate-800">{item.name}</div>
                              <Tag color={item.status === 'active' ? 'green' : 'default'} className="mr-0">
                                {item.status}
                              </Tag>
                            </div>
                            <div className="mt-2 text-sm leading-6 text-slate-600">{item.description || '暂无描述'}</div>
                          </div>
                        ))}
                        {plotArcPoints.slice(0, 6).map((item) => (
                          <div key={item.id} className="flex items-start justify-between gap-3 rounded-2xl border border-slate-100 px-4 py-3">
                            <div>
                              <div className="text-sm font-medium text-slate-800">
                                第 {item.chapter_number} 章 · {item.description}
                              </div>
                              <div className="mt-1 text-xs text-slate-400">
                                {item.related_storyline_name || item.point_type}
                              </div>
                            </div>
                            <Tag color="purple" className="mr-0">
                              张力 {item.tension_level}
                            </Tag>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <Empty description="暂无故事资产" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                    )}
                  </PanelCard>

                  <PanelCard title="事实与伏笔">
                    <div className="space-y-4">
                      <div>
                        <div className="mb-2 text-xs text-slate-400">知识事实</div>
                        {knowledgeFacts.length ? (
                          <div className="space-y-2">
                            {knowledgeFacts.slice(0, 6).map((fact) => (
                              <div key={fact.id} className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
                                <div className="text-slate-800">{fact.subject} {fact.predicate} {fact.object}</div>
                                <div className="mt-1 text-[11px] text-slate-400">
                                  置信度 {Math.round((fact.confidence || 0) * 100)}%
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-sm text-slate-300">暂无知识事实</div>
                        )}
                      </div>

                      <div>
                        <div className="mb-2 text-xs text-slate-400">伏笔账本</div>
                        {foreshadowItems.length ? (
                          <div className="space-y-2">
                            {foreshadowItems.slice(0, 6).map((item) => (
                              <div key={item.id} className="rounded-2xl bg-slate-50 px-4 py-3 text-sm">
                                <div className="flex items-center justify-between gap-3">
                                  <div className="font-medium text-slate-800">{item.title}</div>
                                  <Tag
                                    color={item.status === 'open' ? 'gold' : item.status === 'resolved' ? 'green' : 'default'}
                                    className="mr-0"
                                  >
                                    {item.status}
                                  </Tag>
                                </div>
                                <div className="mt-2 text-xs text-slate-400">
                                  预期回收章节 {item.expected_payoff_chapter || '--'}
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-sm text-slate-300">暂无伏笔项</div>
                        )}
                      </div>
                    </div>
                  </PanelCard>
                </div>
              ),
            },
            {
              key: 'quality',
              label: '角色锚点',
              children: (
                <div className="space-y-4 overflow-y-auto overflow-x-hidden pr-1 pb-4" style={scrollPaneStyle}>
                  <PanelCard title="连续性警报">
                    {workbenchHighlights?.continuity_alerts?.length ? (
                      <div className="space-y-3">
                        {workbenchHighlights.continuity_alerts.map((item) => (
                          <div key={`${item.level}-${item.title}`} className="rounded-2xl border border-slate-100 px-4 py-3">
                            <div className="flex items-center gap-2">
                              <Tag color={item.level === 'critical' ? 'red' : item.level === 'warning' ? 'orange' : 'blue'} className="mr-0">
                                {item.level}
                              </Tag>
                              <div className="font-medium text-slate-800">{item.title}</div>
                            </div>
                            <div className="mt-2 text-sm leading-6 text-slate-600">{item.detail}</div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <Empty description="暂无连续性警报" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                    )}
                  </PanelCard>

                  <PanelCard title="风格与一致性">
                    <div className="space-y-4 text-sm">
                      <div>
                        <div className="text-xs text-slate-400">最新风格分析</div>
                        {latestStyleAnalysis ? (
                          <div className="mt-2 rounded-2xl bg-slate-50 px-4 py-3">
                            <div className="flex items-center justify-between gap-3">
                              <span className="font-medium text-slate-800">
                                第 {latestStyleAnalysis.structured_data?.chapter_number || '--'} 章
                              </span>
                              <Tag color={styleRiskColor[latestStyleAnalysis.structured_data?.risk_level || 'unknown']} className="mr-0">
                                {latestStyleAnalysis.structured_data?.risk_level || 'unknown'}
                              </Tag>
                            </div>
                            <div className="mt-2 text-xs text-slate-500">
                              平均句长 {latestStyleAnalysis.structured_data?.average_sentence_length || '--'}
                              {' · '}
                              对话密度 {latestStyleAnalysis.structured_data?.dialogue_density || '--'}
                            </div>
                          </div>
                        ) : (
                          <div className="mt-2 text-slate-300">暂无风格分析</div>
                        )}
                      </div>

                      <div>
                        <div className="text-xs text-slate-400">当前章节一致性</div>
                        {chapter?.consistency_status && Object.keys(chapter.consistency_status).length ? (
                          <div className="mt-2 rounded-2xl bg-slate-50 px-4 py-3">
                            <div className="flex items-center justify-between gap-3">
                              <span className="font-medium text-slate-800">状态</span>
                              <Tag color={chapter.consistency_status.status === 'ok' ? 'green' : 'orange'} className="mr-0">
                                {chapter.consistency_status.status}
                              </Tag>
                            </div>
                            <div className="mt-2 text-sm leading-6 text-slate-600">
                              {(chapter.consistency_status.risks || []).length
                                ? (chapter.consistency_status.risks || []).join('；')
                                : '暂无明显风险'}
                            </div>
                          </div>
                        ) : (
                          <div className="mt-2 text-slate-300">暂无一致性检查结果</div>
                        )}
                      </div>

                      <div>
                        <div className="text-xs text-slate-400">待优先回收</div>
                        <div className="mt-2 min-w-0 flex flex-wrap gap-2">
                          {workbenchHighlights?.due_foreshadow_items?.length
                            ? workbenchHighlights.due_foreshadow_items.map((item) => (
                              <Tag key={item.id} color="gold" className="mr-0 whitespace-normal break-words">
                                {item.title}
                              </Tag>
                            ))
                            : <span className="text-slate-300">暂无紧迫伏笔</span>}
                        </div>
                      </div>
                    </div>
                  </PanelCard>
                </div>
              ),
            },
            {
              key: 'graph',
              label: '伏笔账本',
              children: (
                <div className="space-y-4 overflow-y-auto overflow-x-hidden pr-1 pb-4" style={{ maxHeight: 'calc(100vh - 16rem)' }}>
                  <PanelCard title="工作焦点">
                    <div className="space-y-3 text-sm">
                      <div>
                        <div className="text-xs text-slate-400">推荐焦点</div>
                        <div className="mt-1 font-medium text-slate-800">
                          {workbenchHighlights?.recommended_focus || '围绕当前主线推进章节。'}
                        </div>
                      </div>
                      {workbenchHighlights?.focus_card?.must_keep?.length ? (
                        <div>
                          <div className="text-xs text-slate-400">必须保持</div>
                          <div className="mt-2 min-w-0 flex flex-wrap gap-2">
                            {workbenchHighlights.focus_card.must_keep.map((item) => (
                              <Tag key={item} color="blue" className="mr-0 whitespace-normal break-words">{item}</Tag>
                            ))}
                          </div>
                        </div>
                      ) : null}
                      {workbenchHighlights?.nearest_plot_point && (
                        <div className="rounded-2xl bg-slate-50 px-4 py-3">
                          <div className="font-medium text-slate-800">
                            第 {workbenchHighlights.nearest_plot_point.chapter_number} 章情节点
                          </div>
                          <div className="mt-2 text-sm leading-6 text-slate-600">
                            {workbenchHighlights.nearest_plot_point.description}
                          </div>
                        </div>
                      )}
                    </div>
                  </PanelCard>

                  <PanelCard title="知识图谱">
                    {graphProjects.length || graphInspirations.length ? (
                      <InsightGraph projects={graphProjects} inspirations={graphInspirations} />
                    ) : (
                      <Empty description="暂无图谱数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                    )}
                  </PanelCard>
                </div>
              ),
            },
            {
              key: 'pulse',
              label: '项目脉冲',
              children: (
                <div className="overflow-y-auto overflow-x-hidden pr-1 pb-4" style={scrollPaneStyle}>
                  {aggregatedStats && (
                    <PanelCard title="总进度">
                      <div className="space-y-3">
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-slate-500">完成率</span>
                          <span className="font-semibold text-slate-800">{aggregatedStats.completionRate}%</span>
                        </div>
                        <Progress percent={aggregatedStats.completionRate} showInfo={false} strokeColor="#2563eb" trailColor="#e5e7eb" />
                        <div className="grid grid-cols-2 gap-2 text-xs text-slate-500">
                          <span>总字数 <span className="font-semibold text-slate-700">{aggregatedStats.totalWords.toLocaleString()}</span></span>
                          <span>完成章节 <span className="font-semibold text-slate-700">{aggregatedStats.finishedChapters}</span></span>
                          <span>均字数 <span className="font-semibold text-slate-700">{aggregatedStats.averageWords.toLocaleString()}</span></span>
                          <span>最近更新 <span className="font-semibold text-slate-700">{aggregatedStats.lastUpdate.slice(0, 10)}</span></span>
                        </div>
                      </div>
                    </PanelCard>
                  )}

                  {focusSignals?.length ? (
                    <PanelCard title="焦点信号">
                      <div className="grid gap-2 sm:grid-cols-2">
                        {focusSignals.map((item) => (
                          <div
                            key={item.key}
                            className={`rounded-[14px] border px-3 py-2.5 ${toneClassMap[item.tone] || toneClassMap.default}`}
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div className="min-w-0">
                                <div className="text-[10px] uppercase tracking-[0.14em] text-[color:var(--app-text-muted)]">{item.title}</div>
                                <div className="mt-1 text-sm font-semibold text-[color:var(--app-text-primary)]">{item.value}</div>
                              </div>
                              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[8px] bg-[color:var(--app-surface-subtle)] text-[color:var(--app-text-secondary)]">
                                {item.icon}
                              </div>
                            </div>
                            <div className="mt-1.5 text-xs leading-5 text-[color:var(--app-text-muted)]">{item.detail}</div>
                          </div>
                        ))}
                      </div>
                    </PanelCard>
                  ) : null}

                  {dashboardPulse?.latestChapters.length ? (
                    <PanelCard title="最近章节">
                      <div className="space-y-2">
                        {dashboardPulse.latestChapters.map((ch) => (
                          <div key={ch.id} className="rounded-[14px] border border-[var(--app-border)] bg-[color:var(--app-shell)] px-3 py-2.5">
                            <div className="flex items-center justify-between gap-2">
                              <div className="min-w-0">
                                <div className="truncate text-sm font-semibold text-[color:var(--app-text-primary)]">
                                  第 {ch.chapter_number} 章 {ch.title || ''}
                                </div>
                                <div className="mt-0.5 text-xs text-[color:var(--app-text-muted)]">
                                  {ch.word_count || 0} 字 · {ch.review_status === 'approved' ? '已定稿' : ch.review_status === 'revise' ? '需修订' : '待审'}
                                </div>
                              </div>
                              <Tag color={ch.consistency_status?.status === 'ok' ? 'green' : ch.consistency_status?.status ? 'orange' : 'default'} className="mr-0 shrink-0">
                                {ch.consistency_status?.status || '未检'}
                              </Tag>
                            </div>
                          </div>
                        ))}
                      </div>
                    </PanelCard>
                  ) : null}

                  {(dashboardPulse?.activeStorylines.length || dashboardPulse?.nextMilestones.length) ? (
                    <PanelCard title="主线与情节点">
                      <div className="space-y-2">
                        {dashboardPulse?.activeStorylines.map((item) => (
                          <div key={item.id} className="rounded-[14px] bg-[color:var(--app-shell)] px-3 py-2.5">
                            <div className="flex items-center justify-between gap-2">
                              <div className="text-sm font-medium text-[color:var(--app-text-primary)]">{item.name}</div>
                              <Tag color={item.status === 'active' ? 'green' : 'default'} className="mr-0 shrink-0">{item.status}</Tag>
                            </div>
                            {item.description ? (
                              <div className="mt-1 text-xs leading-5 text-[color:var(--app-text-muted)]">{item.description}</div>
                            ) : null}
                          </div>
                        ))}
                        {dashboardPulse?.nextMilestones.map((point) => (
                          <div key={point.id} className="rounded-[14px] border border-[var(--app-border)] px-3 py-2.5">
                            <div className="flex items-center justify-between gap-2">
                              <div className="text-sm font-medium text-[color:var(--app-text-primary)]">第 {point.chapter_number} 章</div>
                              <Tag color="purple" className="mr-0 shrink-0">张力 {point.tension_level}</Tag>
                            </div>
                            <div className="mt-1 text-xs leading-5 text-[color:var(--app-text-muted)]">{point.description}</div>
                          </div>
                        ))}
                      </div>
                    </PanelCard>
                  ) : null}

                  {dashboardPulse?.openForeshadow.length ? (
                    <PanelCard title="伏笔回收">
                      <div className="space-y-2">
                        {dashboardPulse.openForeshadow.map((item) => (
                          <div key={item.id} className="rounded-[14px] bg-[color:var(--app-shell)] px-3 py-2.5">
                            <div className="flex items-center justify-between gap-2">
                              <div className="text-sm font-medium text-[color:var(--app-text-primary)]">{item.title}</div>
                              <Tag color="gold" className="mr-0 shrink-0">{item.expected_payoff_chapter || '--'} 章</Tag>
                            </div>
                            {item.description ? (
                              <div className="mt-1 text-xs leading-5 text-[color:var(--app-text-muted)]">{item.description}</div>
                            ) : null}
                          </div>
                        ))}
                      </div>
                    </PanelCard>
                  ) : null}
                </div>
              ),
            },
          ]}
        />
      </div>
    </div>
  );
};
