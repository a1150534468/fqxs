import React, { useMemo } from 'react';
import { Collapse, Empty, Tag } from 'antd';
import { CaretRightOutlined } from '@ant-design/icons';
import MDEditor from '@uiw/react-md-editor';
import { InsightGraph } from '../../components/charts/InsightGraph';
import type {
  Chapter,
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

const renderTagList = (
  items: string[] | undefined,
  color: string,
  emptyText: string,
) => (items?.length ? (
  <div className="mt-2 min-w-0 flex flex-wrap gap-2">
    {items.map((item, index) => (
      <Tag key={`${item}-${index}`} color={color} className="mr-0 whitespace-normal break-words">{item}</Tag>
    ))}
  </div>
) : <span className="text-slate-300">{emptyText}</span>);

interface SettingsPanelProps {
  settings: NovelSettingRecord[];
  chapter: Chapter | null;
  chapterSummaries: ChapterSummaryRecord[];
  storylines: StorylineRecord[];
  plotArcPoints: PlotArcPointRecord[];
  knowledgeFacts: KnowledgeFactRecord[];
  foreshadowItems: ForeshadowItemRecord[];
  styleProfiles: StyleProfileRecord[];
  workbenchHighlights?: WorkbenchHighlights;
  knowledgeGraph?: KnowledgeGraphPayload;
}

const styleRiskColor: Record<string, string> = {
  low: 'green',
  medium: 'orange',
  high: 'red',
  unknown: 'default',
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
  <div className="rounded-[24px] border border-slate-200 bg-white p-4 shadow-sm">
    <div className="mb-3 text-xs font-medium uppercase tracking-[0.22em] text-slate-400">{title}</div>
    {children}
  </div>
);

export const SettingsPanel: React.FC<SettingsPanelProps> = ({
  settings,
  chapter,
  chapterSummaries,
  storylines,
  plotArcPoints,
  knowledgeFacts,
  foreshadowItems,
  workbenchHighlights,
  knowledgeGraph,
}) => {
  const settingsMap = useMemo(() => {
    const map: Record<string, NovelSettingRecord> = {};
    settings.forEach((item) => {
      map[item.setting_type] = item;
    });
    return map;
  }, [settings]);

  const settingsSections = useMemo(() => WIZARD_STEP_TYPES
    .map((type) => ({
      key: type,
      label: STEP_LABELS[type] || type,
      content: settingsMap[type]?.content || '',
    }))
    .filter((section) => section.content), [settingsMap]);

  const selectedSummary = useMemo(() => {
    if (!chapter) return chapterSummaries[chapterSummaries.length - 1];
    return chapterSummaries.find((item) => item.chapter === chapter.id)
      || chapterSummaries.find((item) => item.chapter_number === chapter.chapter_number)
      || chapterSummaries[chapterSummaries.length - 1];
  }, [chapter, chapterSummaries]);



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



  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="border-b border-slate-100 px-5 py-4">
        <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Intelligence Panels</div>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <h3 className="text-lg font-semibold text-slate-800">写作情报</h3>
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
        <div className="mt-2 text-sm text-slate-500">
          只保留当前写作最常用的信息，其余内容折叠查看。
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        <div className="space-y-4">
          <PanelCard title="当前聚焦">
            <div className="space-y-4 text-sm">
              <div>
                <div className="text-xs text-slate-400">推荐焦点</div>
                <div className="mt-1 font-medium leading-6 text-slate-800">
                  {workbenchHighlights?.recommended_focus || '围绕当前主线推进章节。'}
                </div>
              </div>
              {focusCard?.mission ? (
                <div className="rounded-2xl bg-slate-50 px-4 py-3">
                  <div className="text-xs text-slate-400">本章任务</div>
                  <div className="mt-1 font-medium text-slate-800">{focusCard.mission}</div>
                  {focusCard.conflict ? (
                    <div className="mt-2 text-xs leading-5 text-slate-500">冲突：{focusCard.conflict}</div>
                  ) : null}
                  {focusCard.ending_hook ? (
                    <div className="mt-1 text-xs leading-5 text-slate-500">钩子：{focusCard.ending_hook}</div>
                  ) : null}
                </div>
              ) : (
                <Empty description="生成章节后自动补充本章任务" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
              {microBeats.length ? (
                <div>
                  <div className="text-xs text-slate-400">节拍拆分</div>
                  <div className="mt-2 space-y-2">
                    {microBeats.slice(0, 4).map((beat) => (
                      <div key={`${beat.index}-${beat.label}`} className="rounded-2xl bg-slate-50 px-4 py-3">
                        <div className="flex items-center justify-between gap-3">
                          <div className="min-w-0 truncate text-sm font-medium text-slate-800">
                            {beat.index}. {beat.label}
                          </div>
                          <Tag color="blue" className="mr-0 shrink-0">{beat.target_words} 字</Tag>
                        </div>
                        <div className="mt-1 text-xs text-slate-500">{beat.objective}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          </PanelCard>

          <PanelCard title="章节摘要">
            {selectedSummary ? (
              <div className="space-y-4 text-sm">
                <div>
                  <div className="text-xs text-slate-400">摘要</div>
                  <div className="mt-1 leading-6 text-slate-700">{selectedSummary.summary || '暂无摘要'}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-400">关键事件</div>
                  {renderTagList(selectedSummary.key_events, 'blue', '暂无关键事件')}
                </div>
                <div>
                  <div className="text-xs text-slate-400">开放线索</div>
                  {renderTagList(selectedSummary.open_threads, 'gold', '暂无开放线索')}
                </div>
              </div>
            ) : (
              <Empty description="暂无章节摘要" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </PanelCard>

          <Collapse
            defaultActiveKey={['continuity']}
            expandIcon={({ isActive }) => (
              <CaretRightOutlined rotate={isActive ? 90 : 0} className="text-slate-400" />
            )}
            className="writing-hints-collapse"
            items={[
              {
                key: 'continuity',
                label: <span className="text-xs font-medium uppercase tracking-[0.22em] text-slate-500">连续性与风险</span>,
                children: continuityAlerts.length || chapter?.consistency_status ? (
                  <div className="space-y-3">
                    {continuityAlerts.length ? continuityAlerts.map((alert) => (
                      <div key={`${alert.level}-${alert.title}`} className="rounded-2xl border border-slate-100 px-4 py-3">
                        <div className="flex items-center gap-2 min-w-0">
                          <Tag color={alertColorMap[alert.level]} className="mr-0 shrink-0">{alert.level}</Tag>
                          <div className="min-w-0 truncate text-sm font-medium text-slate-800">{alert.title}</div>
                        </div>
                        <div className="mt-2 text-sm leading-6 text-slate-600">{alert.detail}</div>
                      </div>
                    )) : null}
                    {chapter?.consistency_status && Object.keys(chapter.consistency_status).length ? (
                      <div className="rounded-2xl bg-slate-50 px-4 py-3">
                        <div className="flex items-center justify-between gap-3">
                          <span className="font-medium text-slate-800">当前章节一致性</span>
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
                    ) : null}
                    {!continuityAlerts.length && !(chapter?.consistency_status && Object.keys(chapter.consistency_status).length) ? (
                      <Empty description="暂无连续性提醒" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                    ) : null}
                  </div>
                ) : (
                  <Empty description="暂无连续性提醒" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                ),
              },
              {
                key: 'assets',
                label: <span className="text-xs font-medium uppercase tracking-[0.22em] text-slate-500">世界设定与资产</span>,
                children: (
                  <div className="space-y-4">
                    <div>
                      <div className="mb-2 text-xs text-slate-400">核心设定</div>
                      {settingsSections.length ? (
                        <div className="space-y-3">
                          {settingsSections.slice(0, 4).map((section) => (
                            <div key={section.key} className="rounded-2xl bg-slate-50 px-4 py-3">
                              <div className="text-sm font-medium text-slate-800">{section.label}</div>
                              <div className="mt-2 line-clamp-4 text-sm leading-6 text-slate-600">
                                <MDEditor.Markdown source={section.content} style={{ background: 'transparent' }} />
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <Empty description="暂未生成设定" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                      )}
                    </div>
                    <div>
                      <div className="mb-2 text-xs text-slate-400">主线与情节点</div>
                      {storylines.length || plotArcPoints.length ? (
                        <div className="space-y-2">
                          {storylines.slice(0, 3).map((item) => (
                            <div key={item.id} className="rounded-2xl bg-slate-50 px-4 py-3">
                              <div className="flex items-center justify-between gap-2">
                                <div className="font-medium text-slate-800">{item.name}</div>
                                <Tag color={item.status === 'active' ? 'green' : 'default'} className="mr-0">{item.status}</Tag>
                              </div>
                              <div className="mt-1 text-sm leading-6 text-slate-600">{item.description || '暂无描述'}</div>
                            </div>
                          ))}
                          {plotArcPoints.slice(0, 4).map((item) => (
                            <div key={item.id} className="rounded-2xl border border-slate-100 px-4 py-3 text-sm text-slate-600">
                              第 {item.chapter_number} 章 · {item.description}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <Empty description="暂无故事资产" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                      )}
                    </div>
                  </div>
                ),
              },
              {
                key: 'facts',
                label: <span className="text-xs font-medium uppercase tracking-[0.22em] text-slate-500">事实 / 伏笔 / 图谱</span>,
                children: (
                  <div className="space-y-4">
                    <div>
                      <div className="mb-2 text-xs text-slate-400">知识事实</div>
                      {knowledgeFacts.length ? (
                        <div className="space-y-2">
                          {knowledgeFacts.slice(0, 5).map((fact) => (
                            <div key={fact.id} className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
                              <div className="text-slate-800">{fact.subject} {fact.predicate} {fact.object}</div>
                              <div className="mt-1 text-[11px] text-slate-400">置信度 {Math.round((fact.confidence || 0) * 100)}%</div>
                            </div>
                          ))}
                        </div>
                      ) : <div className="text-sm text-slate-300">暂无知识事实</div>}
                    </div>
                    <div>
                      <div className="mb-2 text-xs text-slate-400">伏笔账本</div>
                      {foreshadowItems.length ? (
                        <div className="space-y-2">
                          {foreshadowItems.slice(0, 5).map((item) => (
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
                              <div className="mt-2 text-xs text-slate-400">预期回收章节 {item.expected_payoff_chapter || '--'}</div>
                            </div>
                          ))}
                        </div>
                      ) : <div className="text-sm text-slate-300">暂无伏笔项</div>}
                    </div>
                    <div>
                      <div className="mb-2 text-xs text-slate-400">知识图谱</div>
                      {graphProjects.length || graphInspirations.length ? (
                        <InsightGraph projects={graphProjects} inspirations={graphInspirations} />
                      ) : (
                        <Empty description="暂无图谱数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                      )}
                    </div>
                  </div>
                ),
              },
            ]}
          />
        </div>
      </div>
    </div>
  );
};
