import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Divider,
  Empty,
  Input,
  List,
  Progress,
  Skeleton,
  Steps,
  Tabs,
  Tag,
  Tree,
  Typography,
  message,
} from 'antd';
import type { DataNode, TreeProps } from 'antd/es/tree';
import { CloudSyncOutlined, EditOutlined, FireOutlined, ThunderboltOutlined } from '@ant-design/icons';
import MDEditor from '@uiw/react-md-editor';
import { InsightGraph } from '../../components/charts/InsightGraph';
import { updateChapter } from '../../api/chapters';
import { chapterStatusTag, formatNumber, statusColors } from './constants';
import { SettingEditDrawer } from './SettingEditDrawer';
import type { Chapter, KnowledgeGraphPayload, Novel, NovelSettingRecord } from './types';
import type { StatsOverview } from '../../api/stats';

const { Paragraph, Text } = Typography;
const { Search } = Input;

interface WorkspacePageProps {
  novels: Novel[];
  visibleNovels: Novel[];
  selectedNovel: Novel | null;
  selectedChapters: Chapter[];
  selectedChapter: Chapter | null;
  chaptersByProject: Record<number, Chapter[]>;
  aggregatedStats: {
    totalWords: number;
    finishedChapters: number;
    completionRate: number;
    averageWords: number;
    lastUpdate: string;
  };
  statsOverview: StatsOverview | null;
  searchKeyword: string;
  setSearchKeyword: (value: string) => void;
  loadingTree: boolean;
  chapterLoading: boolean;
  chaptersExpanded: React.Key[];
  treeData: DataNode[];
  selectedKeys: TreeProps['selectedKeys'];
  handleTreeSelect: TreeProps['onSelect'];
  handleTreeExpand: TreeProps['onExpand'];
  streamText: string;
  streamPointer: number;
  isStreaming: boolean;
  setIsStreaming: (value: boolean) => void;
  liveLog: string[];
  setLiveLog: React.Dispatch<React.SetStateAction<string[]>>;
  setMode: (mode: 'home' | 'workspace') => void;
  onChapterSaved?: () => void;
  settings: NovelSettingRecord[];
  knowledgeGraph?: KnowledgeGraphPayload;
}

export const WorkspacePage = ({
  selectedNovel,
  selectedChapters,
  selectedChapter,
  visibleNovels,
  aggregatedStats,
  statsOverview,
  searchKeyword,
  setSearchKeyword,
  loadingTree,
  chapterLoading,
  chaptersExpanded,
  treeData,
  selectedKeys,
  handleTreeSelect,
  handleTreeExpand,
  streamText,
  streamPointer,
  isStreaming,
  setIsStreaming,
  liveLog,
  setLiveLog,
  setMode,
  onChapterSaved,
  settings,
  knowledgeGraph,
}: WorkspacePageProps) => {
  const [editContent, setEditContent] = useState('');
  const [editSaving, setEditSaving] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerSetting, setDrawerSetting] = useState<NovelSettingRecord | null>(null);
  const [localSettings, setLocalSettings] = useState<NovelSettingRecord[]>(settings);

  useEffect(() => {
    setLocalSettings(settings);
  }, [settings]);

  const settingsMap = useMemo(() => {
    const map: Record<string, NovelSettingRecord> = {};
    localSettings.forEach((item) => {
      map[item.setting_type] = item;
    });
    return map;
  }, [localSettings]);

  const openSettingDrawer = (setting_type: string) => {
    const existing =
      settingsMap[setting_type] ||
      ({ setting_type, title: '', content: '', structured_data: {} } as NovelSettingRecord);
    setDrawerSetting(existing);
    setDrawerOpen(true);
  };

  const handleDrawerSaved = (updated: NovelSettingRecord) => {
    setLocalSettings((prev) => {
      const idx = prev.findIndex((s) => s.setting_type === updated.setting_type);
      if (idx === -1) return [...prev, updated];
      const next = [...prev];
      next[idx] = updated;
      return next;
    });
  };

  useEffect(() => {
    if (selectedChapter) {
      setEditContent(selectedChapter.final_content || selectedChapter.raw_content || '');
    } else {
      setEditContent('');
    }
  }, [selectedChapter?.id]);

  const rawLen = selectedChapter?.raw_content?.length || 0;
  const editedLen = editContent.length;
  const editRatio = rawLen > 0 ? Math.abs(editedLen - rawLen) / rawLen : 0;
  const editRatioPct = Math.round(editRatio * 100);
  const editRatioOk = editRatio >= 0.15;

  const handleSaveChapter = async (status: 'draft' | 'approved') => {
    if (!selectedChapter) return;
    setEditSaving(true);
    try {
      await updateChapter(selectedChapter.id, {
        final_content: editContent,
        publish_status: status,
      });
      message.success(status === 'approved' ? '已标记为已审核' : '草稿已保存');
      onChapterSaved?.();
    } catch {
      message.error('保存失败');
    } finally {
      setEditSaving(false);
    }
  };

  const showStreaming = isStreaming || !!streamText;
  const showEditor = !showStreaming && !!selectedChapter;

  const stageItems = [
    { key: 'outline', title: '剧情规划' },
    { key: 'writing', title: 'AI 写作' },
    { key: 'review', title: '人工审核' },
    { key: 'publish', title: '发布' },
  ];

  const statusIndex = (() => {
    const status = selectedChapter?.status || 'generating';
    if (status === 'generating') return 1;
    if (status === 'pending_review') return 2;
    if (status === 'approved') return 3;
    if (status === 'published') return 4;
    return 1;
  })();

  const streamingPlaceholder =
    selectedChapter?.final_content || selectedChapter?.raw_content || '等待写作输出...';

  const worldviewDimensions = useMemo(() => {
    const w = settingsMap.worldview?.structured_data || {};
    return [
      { label: '时间设定', value: w.time_setting || '待补充' },
      { label: '地点设定', value: w.place_setting || '待补充' },
      { label: '社会结构', value: w.social_structure || '待补充' },
      { label: '文化背景', value: w.cultural_background || '待补充' },
      { label: '科技水平', value: w.tech_level || '待补充' },
      { label: '力量体系', value: w.power_system || '待补充' },
      { label: '历史背景', value: w.history || '待补充' },
      { label: '自然法则', value: w.natural_laws || '待补充' },
    ];
  }, [settingsMap]);

  const storylineActs = useMemo(() => {
    const acts = settingsMap.plot_arc?.structured_data?.acts;
    if (Array.isArray(acts)) return acts;
    return [];
  }, [settingsMap]);

  const mapRegions = useMemo(() => {
    const regions = settingsMap.map?.structured_data?.regions;
    if (Array.isArray(regions)) return regions.slice(0, 4);
    return [];
  }, [settingsMap]);

  const knowledgeGraphProjects = useMemo(() => {
    if (knowledgeGraph?.nodes) {
      const plotNodes = knowledgeGraph.nodes.filter((node) => node.category === 'plot');
      if (plotNodes.length) {
        return plotNodes.map((node) => ({
          title: node.name,
          progress: aggregatedStats.completionRate,
          status: node.category,
        }));
      }
    }
    return selectedNovel
      ? [
          {
            title: selectedNovel.title,
            progress: aggregatedStats.completionRate,
            status: selectedNovel.status,
          },
        ]
      : [];
  }, [knowledgeGraph, aggregatedStats, selectedNovel]);

  const knowledgeGraphInspirations = useMemo(() => {
    if (knowledgeGraph?.nodes) {
      const characterNodes = knowledgeGraph.nodes.filter((node) => node.category === 'character');
      if (characterNodes.length) {
        return characterNodes.map((node) => ({
          title: node.name,
          hot_score: Number(node.info?.influence) || 0,
        }));
      }
    }
    return selectedChapters.slice(0, 12).map((chapter) => ({
      title: chapter.title || `第${chapter.chapter_number}章`,
      hot_score: chapter.word_count || 0,
    }));
  }, [knowledgeGraph, selectedChapters]);

  const knowledgeTabs = [
    {
      key: 'script',
      label: '剧本计件',
      children: (
        <List
          size="small"
          dataSource={selectedChapters.slice(0, 5)}
          locale={{ emptyText: '暂无章节任务' }}
          renderItem={(chapter) => (
            <List.Item>
              <div>
                <div className="font-medium">{chapter.title || `第${chapter.chapter_number}章`}</div>
                <div className="text-xs text-gray-500">
                  字数 {chapter.word_count || 0}，状态{' '}
                  {chapterStatusTag[chapter.status || 'pending_review']?.label || chapter.status}
                </div>
              </div>
            </List.Item>
          )}
        />
      ),
    },
    {
      key: 'plot',
      label: '叙事脉络',
      children: (
        <Steps
          direction="vertical"
          items={
            storylineActs.length
              ? storylineActs.map((act: any, index: number) => ({
                  title: act.name || `情节段 ${index + 1}`,
                  description: (act.key_events || []).slice(0, 2).join(' · ') || '等待补全关键节点',
                  status: index < statusIndex ? 'finish' : 'wait',
                }))
              : selectedChapters.slice(0, 5).map((chapter, index) => ({
                  title: chapter.title || `第${chapter.chapter_number}章`,
                  description:
                    (chapter.final_content || chapter.raw_content || '').slice(0, 60) || '等待生成剧情...',
                  status: index < statusIndex ? 'finish' : 'wait',
                }))
          }
        />
      ),
    },
    {
      key: 'setting',
      label: '作品设定',
      children: (
        <List
          size="small"
          dataSource={localSettings.slice(0, 5)}
          locale={{ emptyText: '暂无设定，先通过向导完成设定。' }}
          renderItem={(item) => (
            <List.Item
              className="cursor-pointer hover:bg-slate-50"
              onClick={() => openSettingDrawer(item.setting_type)}
            >
              <div>
                <div className="font-medium text-gray-800">{item.title || item.setting_type}</div>
                <div className="text-xs text-gray-500 max-h-10 overflow-hidden">
                  {(item.content || '').replace(/\s+/g, ' ').slice(0, 120) || '等待完善详细内容'}
                </div>
              </div>
            </List.Item>
          )}
        />
      ),
    },
    {
      key: 'knowledge',
      label: '知识库',
      children: (
        <div className="text-sm text-gray-600 leading-relaxed">
          <p>自动引入：人物设定卡、背景百科、剧情黑板。</p>
          <p>上传采访稿 / 面访记录 / 地图 / 时间线，AI 写作将自动引用上下文。</p>
        </div>
      ),
    },
  ];

  const heroSummary = statsOverview
    ? `今日新增 ${statsOverview.today_new_chapters} 章 · 全站累计 ${formatNumber(statsOverview.total_words)} 字`
    : '左侧书库、中央写作控制、右侧知识脉络一屏掌控';

  return (
    <div className="space-y-4">
      <div className="rounded-3xl bg-gradient-to-r from-indigo-900 via-purple-700 to-pink-600 text-white p-6 shadow-xl flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4">
        <div>
          <p className="uppercase tracking-[0.35em] text-xs text-indigo-100">PlotPilot Auto-Studio</p>
          <h1 className="text-3xl font-semibold mt-2">番茄 IP 写作指挥舱</h1>
          <p className="text-indigo-100 mt-1">{heroSummary}</p>
        </div>
        <div className="flex gap-3">
          <Button icon={<ThunderboltOutlined />} size="large">
            导入书目
          </Button>
          <Button type="primary" size="large" icon={<FireOutlined />} onClick={() => setMode('home')}>
            返回聊天
          </Button>
        </div>
      </div>

      <div className="grid gap-4 grid-cols-1 xl:grid-cols-[280px,_minmax(0,1fr),_360px]">
        <div className="space-y-4">
          <Card
            title="书库检索"
            extra={<Tag icon={<CloudSyncOutlined />} color="purple">实时同步</Tag>}
            className="shadow-sm"
          >
            <Search
              placeholder="输入书名快速定位"
              allowClear
              value={searchKeyword}
              onChange={(e) => setSearchKeyword(e.target.value)}
              className="mb-3"
            />
            {loadingTree ? (
              <Skeleton active />
            ) : visibleNovels.length ? (
              <Tree
                showLine
                blockNode
                onSelect={handleTreeSelect}
                onExpand={handleTreeExpand}
                expandedKeys={chaptersExpanded}
                selectedKeys={selectedKeys}
                treeData={treeData}
                height={420}
              />
            ) : (
              <Empty description="暂无匹配书目" />
            )}
          </Card>

          <Card title="书目概览" className="shadow-sm">
            <div className="grid grid-cols-2 gap-4 text-center">
              <div>
                <p className="text-xs text-gray-500">总字数</p>
                <p className="text-xl font-semibold text-slate-800">
                  {formatNumber(aggregatedStats.totalWords)}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">完成章节</p>
                <p className="text-xl font-semibold text-slate-800">
                  {aggregatedStats.finishedChapters}/{selectedNovel?.target_chapters || '--'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">完成率</p>
                <p className="text-xl font-semibold text-slate-800">
                  {aggregatedStats.completionRate}%
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">平均字数/章</p>
                <p className="text-xl font-semibold text-slate-800">
                  {formatNumber(aggregatedStats.averageWords)}
                </p>
              </div>
            </div>
            <Divider />
            <p className="text-xs text-gray-500">最后更新</p>
            <p className="text-sm text-gray-800">{aggregatedStats.lastUpdate || '--'}</p>
          </Card>

          <Card title="章节预览" className="shadow-sm" loading={chapterLoading}>
            {selectedChapter ? (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold">
                    {selectedChapter.title || `第${selectedChapter.chapter_number}章`}
                  </span>
                  <Tag color={chapterStatusTag[selectedChapter.status || 'pending_review']?.color}>
                    {chapterStatusTag[selectedChapter.status || 'pending_review']?.label ||
                      selectedChapter.status}
                  </Tag>
                </div>
                <Paragraph className="text-sm text-gray-600" ellipsis={{ rows: 6, expandable: true }}>
                  {selectedChapter.final_content ||
                    selectedChapter.raw_content ||
                    '暂未产出内容，等待写作生成。'}
                </Paragraph>
              </div>
            ) : (
              <Empty description="选择一本书以查看章节" />
            )}
          </Card>
        </div>

        <div className="space-y-4">
          <Card title="全书态势" className="shadow-sm">
            {selectedNovel ? (
              <div className="space-y-4">
                <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-2">
                  <div>
                    <p className="text-xs text-gray-400 uppercase tracking-[0.3em]">当前项目</p>
                    <h2 className="text-2xl font-semibold text-gray-900">{selectedNovel.title}</h2>
                  </div>
                  <div className="flex gap-2">
                    <Tag color={statusColors[selectedNovel.status || 'active'] || 'default'}>
                      {selectedNovel.status || 'active'}
                    </Tag>
                    {selectedNovel.auto_generation_enabled && <Tag color="blue">托管写作中</Tag>}
                  </div>
                </div>
                <Progress
                  percent={aggregatedStats.completionRate}
                  status={aggregatedStats.completionRate >= 80 ? 'success' : 'active'}
                  strokeColor={{ from: '#8b5cf6', to: '#6366f1' }}
                />
                <Descriptions column={3} size="small">
                  <Descriptions.Item label="题材">{selectedNovel.genre || '--'}</Descriptions.Item>
                  <Descriptions.Item label="目标章节">
                    {selectedNovel.target_chapters || '--'}
                  </Descriptions.Item>
                  <Descriptions.Item label="更新频率">
                    每日 {selectedNovel.update_frequency || 1} 章
                  </Descriptions.Item>
                  <Descriptions.Item label="托管计划">
                    {selectedNovel.generation_schedule || '每日'}
                  </Descriptions.Item>
                  <Descriptions.Item label="当前章节">
                    {selectedNovel.current_chapter || aggregatedStats.finishedChapters}
                  </Descriptions.Item>
                  <Descriptions.Item label="最后更新时间">
                    {aggregatedStats.lastUpdate}
                  </Descriptions.Item>
                </Descriptions>
              </div>
            ) : (
              <Empty description="暂无书目" />
            )}
          </Card>

          <Card title="写作调度中心" className="shadow-sm">
            {selectedChapter ? (
              <div className="grid gap-4 lg:grid-cols-2">
                <div className="space-y-3">
                  <div className="flex items-center justify-center">
                    <Progress
                      type="dashboard"
                      percent={Math.min(
                        100,
                        Math.round((streamPointer / (streamingPlaceholder.length || 1)) * 100),
                      )}
                      status={isStreaming ? 'active' : 'success'}
                    />
                  </div>
                  <div>
                    <p className="font-semibold">
                      {selectedChapter.title || `第${selectedChapter.chapter_number}章`}
                    </p>
                    <p className="text-xs text-gray-500 mb-2">实时阶段追踪</p>
                    <Steps
                      current={Math.min(stageItems.length, statusIndex)}
                      items={stageItems.map((item) => ({ title: item.title }))}
                      size="small"
                    />
                  </div>
                </div>
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm font-semibold">实时日志</p>
                    <Button size="small" onClick={() => setLiveLog([])}>
                      清空
                    </Button>
                  </div>
                  {liveLog.length > 0 ? (
                    <List
                      size="small"
                      dataSource={liveLog}
                      renderItem={(item) => (
                        <List.Item className="text-xs text-gray-500">{item}</List.Item>
                      )}
                      className="max-h-48 overflow-auto"
                    />
                  ) : (
                    <Empty description="暂无日志" />
                  )}
                </div>
              </div>
            ) : (
              <Empty description="选择章节以查看进度" />
            )}
          </Card>

          {showStreaming ? (
            <Card
              title="实时写作输出"
              className="shadow-sm"
              extra={
                <Button danger ghost onClick={() => setIsStreaming(false)}>
                  停止写作
                </Button>
              }
            >
              <div className="font-mono text-sm bg-slate-900 text-green-200 rounded-lg p-4 h-72 overflow-auto whitespace-pre-wrap">
                {streamText || streamingPlaceholder}
              </div>
            </Card>
          ) : showEditor ? (
            <Card
              title={`章节编辑 - ${selectedChapter.title || `第${selectedChapter.chapter_number}章`}`}
              className="shadow-sm"
              extra={
                <span className="text-xs text-gray-500">
                  {editContent.replace(/[#*`_[\]()]/g, '').replace(/\s+/g, '').length} 字
                </span>
              }
            >
              <Alert
                message="人工审核规则"
                description={
                  <span>
                    AI 生成内容须人工修改 &ge;15% 方可发布。当前编辑比例：
                    <strong className={editRatioOk ? 'text-green-600' : 'text-red-500'}>
                      {editRatioPct}%
                    </strong>
                    {editRatioOk ? ' (已达标)' : ' (未达标)'}
                  </span>
                }
                type="warning"
                showIcon
                className="mb-4"
              />
              <div data-color-mode="light">
                <MDEditor
                  value={editContent}
                  onChange={(val) => setEditContent(val || '')}
                  height={400}
                  previewOptions={{ disallowedElements: ['style'] }}
                />
              </div>
              <div className="flex items-center justify-end gap-3 mt-4">
                <Button
                  loading={editSaving}
                  onClick={() => handleSaveChapter('draft')}
                >
                  保存草稿
                </Button>
                <Button
                  type="primary"
                  loading={editSaving}
                  onClick={() => handleSaveChapter('approved')}
                >
                  标记已审核
                </Button>
              </div>
            </Card>
          ) : (
            <Card className="shadow-sm">
              <Empty
                image={<EditOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />}
                description="请在左侧选择章节，或触发 AI 生成"
              />
            </Card>
          )}
        </div>

        <div className="space-y-4">
          <Card title="知识库控制台" className="shadow-sm">
            <Tabs defaultActiveKey="script" size="small" items={knowledgeTabs} />
          </Card>

          <Card title="世界观 · 八个维度" className="shadow-sm">
            <div className="grid grid-cols-2 gap-3">
              {worldviewDimensions.map((dim) => (
                <div
                  key={dim.label}
                  className="bg-slate-50 rounded-2xl p-3 cursor-pointer hover:bg-indigo-50 transition-colors"
                  onClick={() => openSettingDrawer('worldview')}
                >
                  <p className="text-[11px] text-gray-500">{dim.label}</p>
                  <p className="text-xs text-gray-800 mt-1 max-h-12 overflow-hidden">{dim.value}</p>
                </div>
              ))}
            </div>
          </Card>

          <Card title="知识图谱" className="shadow-sm">
            {knowledgeGraphProjects.length || knowledgeGraphInspirations.length ? (
              <InsightGraph projects={knowledgeGraphProjects} inspirations={knowledgeGraphInspirations} />
            ) : (
              <Empty description="暂无知识图谱" />
            )}
          </Card>

          <Card title="叙事片场" className="shadow-sm">
            <List
              size="small"
              dataSource={
                mapRegions.length
                  ? mapRegions.map((region: any) => ({
                      stage: region.name,
                      detail: region.description || '等待补充场景描述',
                    }))
                  : [
                      {
                        stage: '情绪轨道',
                        detail: '保持高张力，人物冲突需在 500 字内爆发。',
                      },
                      {
                        stage: '镜头语言',
                        detail: '多用动态动词与感官描写，控制句长 15 中文字符左右。',
                      },
                      {
                        stage: '人工审核提示',
                        detail: '确保修改率 ≥15%，必要时加入本地生活描写以通过平台审核。',
                      },
                    ]
              }
              renderItem={(item) => (
                <List.Item>
                  <div>
                    <Text strong>{item.stage}</Text>
                    <p className="text-xs text-gray-500">{item.detail}</p>
                  </div>
                </List.Item>
              )}
            />
          </Card>
        </div>
      </div>
      <SettingEditDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        novelId={selectedNovel?.id ?? null}
        novelTitle={selectedNovel?.title || ''}
        setting={drawerSetting}
        onSaved={handleDrawerSaved}
      />
    </div>
  );
};
