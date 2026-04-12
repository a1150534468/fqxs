import { useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  Descriptions,
  Divider,
  Empty,
  Input,
  List,
  Modal,
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
import { CloudSyncOutlined, FireOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { getNovels } from '../../api/novels';
import { getChapters } from '../../api/chapters';
import { InsightGraph } from '../../components/charts/InsightGraph';

const { Paragraph, Text } = Typography;
const { Search, TextArea } = Input;

type Mode = 'home' | 'workspace';

interface Novel {
  id: number;
  title: string;
  genre?: string;
  status?: string;
  synopsis?: string;
  target_chapters?: number;
  current_chapter?: number;
  update_frequency?: number;
  last_update_at?: string;
  auto_generation_enabled?: boolean;
  generation_schedule?: string;
}

interface Chapter {
  id: number;
  chapter_number: number;
  title?: string;
  word_count?: number;
  status?: string;
  raw_content?: string;
  final_content?: string;
  created_at?: string;
  updated_at?: string;
}

const wizardSteps = [
  '世界观',
  '人物',
  '地图',
  '故事线',
  '情节弧',
  '开始',
  '维度框架',
  '主要角色',
  '地图系统',
  '主线支线',
  '剧情抽离',
  '进入工作台',
];

const statusColors: Record<string, string> = {
  active: 'green',
  paused: 'orange',
  completed: 'blue',
  abandoned: 'red',
};

const chapterStatusTag: Record<string, { color: string; label: string }> = {
  generating: { color: 'processing', label: '生成中' },
  pending_review: { color: 'warning', label: '待审核' },
  approved: { color: 'green', label: '已审核' },
  published: { color: 'blue', label: '已发布' },
  failed: { color: 'red', label: '失败' },
};

const pickResults = (response: any) => {
  if (!response) return [];
  if (Array.isArray(response.results)) {
    return response.results;
  }
  if (Array.isArray(response)) {
    return response;
  }
  return [];
};

const Dashboard = () => {
  const [mode, setMode] = useState<Mode>('home');
  const [novels, setNovels] = useState<Novel[]>([]);
  const [chaptersByProject, setChaptersByProject] = useState<Record<number, Chapter[]>>({});
  const [chapterProjectMap, setChapterProjectMap] = useState<Record<number, number>>({});
  const [selectedNovelId, setSelectedNovelId] = useState<number | null>(null);
  const [selectedChapterId, setSelectedChapterId] = useState<number | null>(null);
  const [loadingTree, setLoadingTree] = useState(false);
  const [chapterLoading, setChapterLoading] = useState(false);
  const [searchKeyword, setSearchKeyword] = useState('');
  const [chatInput, setChatInput] = useState('');
  const [pendingTitle, setPendingTitle] = useState('');
  const [wizardOpen, setWizardOpen] = useState(false);
  const [wizardStep, setWizardStep] = useState(0);
  const [wizardValues, setWizardValues] = useState<Record<string, string>>({});
  const [wizardOptions, setWizardOptions] = useState<Record<string, WizardOption[]>>({});
  const [wizardLoading, setWizardLoading] = useState(false);
  const [chaptersExpanded, setChaptersExpanded] = useState<React.Key[]>([]);
  const [liveLog, setLiveLog] = useState<string[]>([]);
  const [streamText, setStreamText] = useState('');
  const [streamPointer, setStreamPointer] = useState(0);
  const [isStreaming, setIsStreaming] = useState(true);

  useEffect(() => {
    loadNovels();
  }, []);

  useEffect(() => {
    if (selectedNovelId == null) return;
    if (chaptersByProject[selectedNovelId]) {
      const list = chaptersByProject[selectedNovelId];
      if (!selectedChapterId && list.length) {
        setSelectedChapterId(list[0].id);
      }
      return;
    }
    fetchChaptersForProject(selectedNovelId);
  }, [selectedNovelId]);

  const selectedNovel = novels.find((novel) => novel.id === selectedNovelId) ?? null;
  const selectedChapters = selectedNovel ? chaptersByProject[selectedNovel.id] ?? [] : [];
  const selectedChapter =
    selectedChapters.find((c) => c.id === selectedChapterId) ?? selectedChapters[0] ?? null;

  useEffect(() => {
    if (!selectedChapter) {
      setStreamText('');
      return;
    }
    setStreamPointer(0);
    setStreamText('');
    setIsStreaming(true);
    setLiveLog([
      `${new Date().toLocaleTimeString()} · 打开章节《${selectedChapter.title || `第${selectedChapter.chapter_number}章`}》`,
    ]);
  }, [selectedChapter?.id]);

  useEffect(() => {
    if (!selectedChapter) return;
    const text =
      selectedChapter.final_content ||
      selectedChapter.raw_content ||
      '等待写作引擎输出……';
    if (!isStreaming) {
      setStreamText(text);
      return;
    }
    const interval = setInterval(() => {
      setStreamPointer((prev) => {
        const next = Math.min(text.length, prev + 48);
        setStreamText(text.slice(0, next));
        if (next >= text.length) {
          clearInterval(interval);
          setIsStreaming(false);
        }
        return next;
      });
    }, 300);
    return () => clearInterval(interval);
  }, [isStreaming, selectedChapter]);

  useEffect(() => {
    if (!selectedNovel) return;
    const template = [
      '分析灵感与市场趋势',
      '召回人物设定，更新行为约束',
      '写作引擎排队生成正文',
      'AI 审校标记敏感内容',
      '推送章节至人工审核区',
    ];
    let index = 0;
    const timer = setInterval(() => {
      setLiveLog((prev) => [
        `${new Date().toLocaleTimeString()} · ${template[index % template.length]}`,
        ...prev,
      ].slice(0, 8));
      index += 1;
    }, 4500);
    return () => clearInterval(timer);
  }, [selectedNovel?.id]);

  const loadNovels = async () => {
    setLoadingTree(true);
    try {
      const response = await getNovels({ page_size: 100, ordering: '-updated_at' });
      setNovels(pickResults(response));
    } catch (error) {
      console.error('Failed to fetch novels', error);
    } finally {
      setLoadingTree(false);
    }
  };

  const fetchChaptersForProject = async (projectId: number) => {
    setChapterLoading(true);
    try {
      const response = await getChapters(projectId, { ordering: 'chapter_number', page_size: 200 });
      const list = pickResults(response);
      setChaptersByProject((prev) => ({ ...prev, [projectId]: list }));
      setChapterProjectMap((prev) => {
        const next = { ...prev };
        list.forEach((chapter: Chapter) => {
          next[chapter.id] = projectId;
        });
        return next;
      });
      if (!selectedChapterId && projectId === selectedNovelId && list.length) {
        setSelectedChapterId(list[0].id);
      }
    } catch (error) {
      console.error('Failed to fetch chapters', error);
    } finally {
      setChapterLoading(false);
    }
  };

  const visibleNovels = useMemo(() => {
    const keyword = searchKeyword.trim().toLowerCase();
    if (!keyword) {
      return novels;
    }
    return novels.filter((novel) => novel.title.toLowerCase().includes(keyword));
  }, [novels, searchKeyword]);

  const aggregatedStats = useMemo(() => {
    if (!selectedNovel) {
      return {
        totalWords: 0,
        finishedChapters: 0,
        completionRate: 0,
        averageWords: 0,
        lastUpdate: '--',
      };
    }
    const totalWords = selectedChapters.reduce((sum, chapter) => sum + (chapter.word_count || 0), 0);
    const finishedChapters = selectedChapters.filter((c) =>
      ['approved', 'published'].includes(c.status || '')
    ).length;
    const completionRate = selectedNovel.target_chapters
      ? Math.min(
          100,
          Math.round(
            ((selectedNovel.current_chapter || finishedChapters) / selectedNovel.target_chapters) *
              100,
          ),
        )
      : 0;
    const averageWords =
      selectedChapters.length > 0 ? Math.round(totalWords / selectedChapters.length) : 0;
    const lastUpdate =
      selectedNovel.last_update_at ||
      selectedChapters[selectedChapters.length - 1]?.updated_at ||
      selectedChapters[selectedChapters.length - 1]?.created_at ||
      '--';
    return {
      totalWords,
      finishedChapters,
      completionRate,
      averageWords,
      lastUpdate,
    };
  }, [selectedNovel, selectedChapters]);

  const totalStats = useMemo(() => {
    const chapterTotal = novels.reduce((sum, novel) => sum + (novel.current_chapter || 0), 0);
    const wordTotal = Object.values(chaptersByProject)
      .flat()
      .reduce((sum, chapter) => sum + (chapter.word_count || 0), 0);
    return {
      bookCount: novels.length,
      chapterCount: chapterTotal,
      wordCount: wordTotal,
    };
  }, [novels, chaptersByProject]);

  const treeData: DataNode[] = visibleNovels.map((novel) => ({
    key: `novel-${novel.id}`,
    title: (
      <div className="flex items-center justify-between pr-2 w-full">
        <span className="font-medium text-gray-800">{novel.title}</span>
        <Tag color={statusColors[novel.status || 'active'] || 'default'}>
          {novel.status || 'active'}
        </Tag>
      </div>
    ),
    selectable: true,
    children: (chaptersByProject[novel.id] || []).map((chapter) => ({
      key: `chapter-${chapter.id}`,
      title: (
        <div className="flex items-center justify-between pr-2 w-full text-sm">
          <span>第{chapter.chapter_number}章 {chapter.title || ''}</span>
          <Tag color={chapterStatusTag[chapter.status || 'pending_review']?.color}>
            {chapterStatusTag[chapter.status || 'pending_review']?.label || chapter.status}
          </Tag>
        </div>
      ),
      selectable: true,
    })),
  }));

  const selectedKeys: TreeProps['selectedKeys'] =
    selectedChapterId != null
      ? [`chapter-${selectedChapterId}`]
      : selectedNovelId != null
        ? [`novel-${selectedNovelId}`]
        : [];

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
          items={selectedChapters.slice(0, 5).map((chapter, index) => ({
            title: chapter.title || `第${chapter.chapter_number}章`,
            description:
              (chapter.final_content || chapter.raw_content || '').slice(0, 60) || '等待生成剧情...',
            status: index < statusIndex ? 'finish' : 'wait',
          }))}
        />
      ),
    },
    {
      key: 'setting',
      label: '作品设定',
      children: (
        <div className="space-y-2 text-sm text-gray-600">
          <p>故事设定：{selectedNovel?.synopsis || '尚未填写简介，可从灵感库同步。'}</p>
          <p>世界观：AI 已构建多线世界观，可在知识库中补充细节。</p>
        </div>
      ),
    },
    {
      key: 'knowledge',
      label: '知识库',
      children: (
        <div className="text-sm text-gray-600">
          <p>自动引入：人物设定卡、背景百科、剧情黑板。</p>
          <p>上传采访稿/地图/时间线，AI 写作将自动引用上下文。</p>
        </div>
      ),
    },
  ];

  const handleTreeSelect: TreeProps['onSelect'] = (keys) => {
    const key = keys[0];
    if (!key || typeof key !== 'string') return;
    if (key.startsWith('novel-')) {
      const id = parseInt(key.replace('novel-', ''), 10);
      setSelectedNovelId(id);
      setSelectedChapterId(null);
      setMode('workspace');
    } else if (key.startsWith('chapter-')) {
      const id = parseInt(key.replace('chapter-', ''), 10);
      const projectId = chapterProjectMap[id];
      if (projectId) {
        setSelectedNovelId(projectId);
      }
      setSelectedChapterId(id);
      setMode('workspace');
    }
  };

  const handleTreeExpand: TreeProps['onExpand'] = (keys) => {
    setChaptersExpanded(keys);
    keys.forEach((key) => {
      if (typeof key === 'string' && key.startsWith('novel-')) {
        const id = parseInt(key.replace('novel-', ''), 10);
        if (!chaptersByProject[id]) {
          fetchChaptersForProject(id);
        }
      }
    });
  };

  const handleCreateProject = () => {
    const baseTitle = pendingTitle || chatInput.trim();
    if (!baseTitle) {
      message.warning('先输入一句灵感，再建档哦！');
      return;
    }
    if (!pendingTitle) {
      setPendingTitle(baseTitle);
    }
    setWizardOpen(true);
    setWizardStep(0);
  };

  const handleWizardChange = (value: string) => {
    const key = wizardSteps[wizardStep];
    setWizardValues((prev) => ({ ...prev, [key]: value }));
  };

  const loadWizardOptions = (key: string) => {
    const presets = STEP_PRESETS[key] || [];
    setWizardLoading(true);
    setTimeout(() => {
      setWizardOptions((prev) => ({
        ...prev,
        [key]: presets,
      }));
      setWizardLoading(false);
    }, 300);
  };

  useEffect(() => {
    if (!wizardOpen) return;
    const key = wizardSteps[wizardStep];
    loadWizardOptions(key);
  }, [wizardOpen, wizardStep]);

  const handleWizardNext = () => {
    if (wizardStep < wizardSteps.length - 1) {
      setWizardStep((prev) => prev + 1);
    }
  };

  const handleWizardPrev = () => {
    if (wizardStep > 0) {
      setWizardStep((prev) => prev - 1);
    }
  };

  const handleWizardFinish = () => {
    const newId = Date.now();
    const newNovel: Novel = {
      id: newId,
      title: pendingTitle || `新项目 ${new Date().toLocaleTimeString()}`,
      genre: wizardValues['世界观'] || '未分类',
      status: 'active',
      synopsis: wizardValues['故事线'],
      target_chapters: 100,
      current_chapter: 0,
      update_frequency: 1,
      last_update_at: new Date().toISOString(),
      auto_generation_enabled: true,
    };
    setNovels((prev) => [...prev, newNovel]);
    setSelectedNovelId(newId);
    setMode('workspace');
    setWizardOpen(false);
    setWizardValues({});
    setWizardStep(0);
    setPendingTitle('');
    message.success('已创建新书，进入工作台！');
  };

  const renderHome = () => (
    <div className="space-y-6">
      <div className="rounded-[32px] bg-gradient-to-br from-slate-900 via-purple-800 to-indigo-700 text-white p-8 shadow-2xl flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
        <div>
          <p className="uppercase tracking-[0.6em] text-xs text-indigo-200">PlotPilot Studio</p>
          <h1 className="text-3xl font-semibold mt-3">书稿工作台</h1>
          <p className="text-indigo-100 mt-2">从一句灵感到完稿上架，结构规划与校对一站完成。</p>
        </div>
        <div className="flex gap-4">
          <Button icon={<ThunderboltOutlined />} size="large" ghost>
            快速导入
          </Button>
          <Button type="primary" size="large" onClick={handleCreateProject}>
            建档并进入工作台
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[260px,_minmax(0,1fr)]">
        <div className="space-y-4">
          <Card className="bg-[#1f1f47] text-white border-none shadow-xl">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-indigo-200">林亦苏</p>
                <h3 className="text-xl font-semibold">690 位读者关注</h3>
              </div>
              <Tag color="gold">小封博</Tag>
            </div>
          </Card>

          <Card className="shadow-md">
            <List
              dataSource={[
                { label: '总书籍', value: totalStats.bookCount },
                { label: '总章节', value: totalStats.chapterCount },
                { label: '累计字数', value: `${formatNumber(totalStats.wordCount)} 字` },
              ]}
              renderItem={(item) => (
                <List.Item className="flex justify-between">
                  <span className="text-gray-500 text-sm">{item.label}</span>
                  <span className="text-lg font-semibold text-slate-900">{item.value}</span>
                </List.Item>
              )}
            />
          </Card>

          <Card className="shadow-md">
            <h4 className="text-sm text-gray-500 mb-2">直播通知</h4>
            <p className="text-sm text-gray-700">新人主播，赶粉丝群来交流，来做第一批 PlotPilot 体验官。</p>
          </Card>
        </div>

        <div className="space-y-5">
          <Card className="shadow-xl border-none">
            <div className="flex items-center justify-between mb-3">
              <div>
                <p className="text-sm text-gray-500">新建书目</p>
                <h3 className="text-xl font-semibold text-gray-900">从一句灵感到成书</h3>
              </div>
              <Button type="link" onClick={handleCreateProject}>
                高级设置
              </Button>
            </div>
            <TextArea
              rows={4}
              placeholder="输入一段灵感，例如：想写一部以江湖与AI对抗为背景的权谋恋爱小说..."
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
            />
            <div className="text-right mt-3">
              <Button type="primary" size="large" onClick={handleCreateProject}>
                建档并进入工作台
              </Button>
            </div>
          </Card>

          <Card
            className="shadow-md"
            title="我的书目"
            extra={<Search placeholder="搜索书目..." size="small" />}
          >
            <List
              dataSource={novels}
              locale={{ emptyText: '尚无书目，快建档吧！' }}
              renderItem={(novel) => (
                <List.Item
                  actions={[
                    <Button
                      size="small"
                      type="link"
                      onClick={() => {
                        setSelectedNovelId(novel.id);
                        setSelectedChapterId(null);
                        setMode('workspace');
                      }}
                    >
                      工作台
                    </Button>,
                  ]}
                >
                  <List.Item.Meta
                    title={novel.title}
                    description={`进度 ${novel.current_chapter || 0}/${novel.target_chapters || '--'}`}
                  />
                </List.Item>
              )}
            />
          </Card>
        </div>
      </div>
    </div>
  );

  const workspaceLayout = (
    <div className="space-y-4">
      <div className="rounded-2xl bg-gradient-to-r from-indigo-900 via-purple-700 to-pink-600 text-white p-6 shadow-xl flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4">
        <div>
          <p className="uppercase tracking-[0.35em] text-xs text-indigo-100">PlotPilot Auto-Studio</p>
          <h1 className="text-3xl font-semibold mt-2">番茄 IP 写作指挥舱</h1>
          <p className="text-indigo-100 mt-1">左侧书库、中央写作控制、右侧知识脉络一屏掌控。</p>
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

      <div className="grid gap-4 grid-cols-1 2xl:grid-cols-[280px,_minmax(0,1fr),_360px]">
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
        </div>

        <div className="space-y-4">
          <Card title="故事控制台" className="shadow-sm">
            <Tabs defaultActiveKey="script" size="small" items={knowledgeTabs} />
          </Card>

          <Card title="知识图谱" className="shadow-sm">
            {selectedChapters.length > 0 ? (
              <InsightGraph
                projects={
                  selectedNovel
                    ? [
                        {
                          title: selectedNovel.title,
                          progress: aggregatedStats.completionRate,
                          status: selectedNovel.status,
                        },
                      ]
                    : []
                }
                inspirations={selectedChapters.slice(0, 12).map((chapter) => ({
                  title: chapter.title || `第${chapter.chapter_number}章`,
                  hot_score: chapter.word_count || 0,
                }))}
              />
            ) : (
              <Empty description="暂无章节关系" />
            )}
          </Card>

          <Card title="叙事片场" className="shadow-sm">
            <List
              size="small"
              dataSource={[
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
                  detail: '确保修改率 >=15%，必要时加入本地生活描写以通过平台审核。',
                },
              ]}
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
    </div>
  );

  return (
    <>
      {mode === 'home' ? renderHome() : workspaceLayout}
      <Modal
        open={wizardOpen}
        centered
        width={720}
        title="新书设置向导"
        onCancel={() => setWizardOpen(false)}
        footer={null}
        destroyOnClose
      >
        <Steps current={wizardStep} items={wizardSteps.map((title) => ({ title }))} size="small" className="mb-4" />
        <div className="bg-slate-50 rounded-lg p-3 border border-slate-100 space-y-3">
          <div>
            <p className="text-sm text-gray-600 mb-2">选择一个后端推荐选项</p>
            {wizardLoading ? (
              <Skeleton active paragraph={{ rows: 1 }} />
            ) : (wizardOptions[wizardSteps[wizardStep]] || []).length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {(wizardOptions[wizardSteps[wizardStep]] || []).map((option) => {
                  const isActive = wizardValues[wizardSteps[wizardStep]] === option.title;
                  return (
                    <Button
                      key={option.title}
                      type={isActive ? 'primary' : 'default'}
                      ghost={!isActive}
                      size="small"
                      onClick={() => handleWizardChange(option.title)}
                    >
                      {option.title}
                    </Button>
                  );
                })}
              </div>
            ) : (
              <p className="text-xs text-gray-500">暂无推荐选项，请手动填写。</p>
            )}
          </div>
          <div>
            <p className="text-sm text-gray-600 mb-2">详细描述 / 预览</p>
            <div className="bg-white rounded-lg border border-dashed border-slate-200 p-3 min-h-[160px] text-sm text-gray-600">
              {(() => {
                const currentKey = wizardSteps[wizardStep];
                const currentValue = wizardValues[currentKey];
                const option = (wizardOptions[currentKey] || []).find(
                  (opt) => opt.title === currentValue,
                );
                if (option) {
                  return option.preview;
                }
                if (currentValue) {
                  return currentValue;
                }
                return '请选择推荐项或自定义描述。';
              })()}
            </div>
            <p className="text-sm text-gray-600 mt-3 mb-2">或自定义输入</p>
            <TextArea
              rows={3}
              placeholder={`补充 ${wizardSteps[wizardStep]} 的设定...`}
              value={wizardValues[wizardSteps[wizardStep]] || ''}
              onChange={(e) => handleWizardChange(e.target.value)}
            />
          </div>
        </div>
        <div className="flex justify-between mt-4">
          <Button disabled={wizardStep === 0} onClick={handleWizardPrev}>
            上一步
          </Button>
          {wizardStep < wizardSteps.length - 1 ? (
            <Button
              type="primary"
              onClick={handleWizardNext}
              disabled={!wizardValues[wizardSteps[wizardStep]]}
            >
              下一步
            </Button>
          ) : (
            <Button
              type="primary"
              onClick={handleWizardFinish}
              disabled={!wizardValues[wizardSteps[wizardStep]]}
            >
              完成并进入工作台
            </Button>
          )}
        </div>
      </Modal>
    </>
  );
};

const STEP_PRESETS: Record<string, WizardOption[]> = {
  世界观: [
    { title: '仙侠多宇宙', preview: '古典修真与多宇宙折叠，主角需要在不同宇宙间协调力量。' },
    { title: '赛博朋克华夏', preview: '霓虹与符箓共存的未来都市，AI 神明统治上城。' },
    { title: '末日废土', preview: '尘海覆盖大陆，幸存者依靠巨型机甲与异化植物对抗。' },
    { title: '悬疑都市', preview: '雾城的夜晚永远下雨，超感者必须解开连续失踪案。' },
  ],
  人物: [
    { title: '冷静女主角', preview: '逻辑型女主，擅长情报推演，在关键时刻保持冷静。' },
    { title: '双重身份男主', preview: '表面是音乐家，暗地是影子杀手，内心分裂。' },
    { title: '搞笑搭档', preview: '爱吐槽的副手，总在紧张时刻打破沉默，但关键时刻靠谱。' },
    { title: 'AI 管家', preview: '拥有自我意识的 AI，主角唯一信任的伙伴。' },
  ],
  地图: [
    { title: '主城-云海街区', preview: '浮空城边缘，被撕裂的街区，上层贵族与下层流民壁垒。' },
    { title: '地下迷宫', preview: '废弃避难所改造成的迷宫，布满旧时代机枪与陷阱。' },
    { title: '天空浮岛', preview: '仅凭灵石悬空的岛屿，拥有独立生态与禁空结界。' },
    { title: '三界交汇点', preview: '现实、虚拟、副本三界交错的核心枢纽，故事高潮所在地。' },
  ],
  故事线: [
    { title: '复仇/赎罪双线', preview: '主线追凶，支线是主人公赎罪；两线在真相处汇合。' },
    { title: '成长+破案并行', preview: '每破一案触发成长节点，角色能力与情感同步升级。' },
    { title: '恋爱与权谋', preview: '感情线与权力博弈交织，选择不同阵营影响情感结局。' },
    { title: '师徒羁绊', preview: '师徒身份隐藏巨大阴谋，情感羁绊构成最终抉择。' },
  ],
  情节弧: [
    { title: '从失忆开始', preview: '开局失忆，借助 AI 记录重塑记忆，同时揭露阴谋。' },
    { title: '极限求生', preview: '在不可居住区求生，每章一个致命挑战。' },
    { title: '反派洗白', preview: '前期看似反派，逐章揭露其真实动机并完成洗白。' },
    { title: '黑化救赎', preview: '主角经历黑化高潮，最终靠伙伴拉回正轨。' },
  ],
  开始: [
    { title: '意外穿越', preview: '一次直播事故触发穿越，主角带着观众视角闯新世界。' },
    { title: '任务失败重启', preview: '失败触发时间回溯，掌握未来片段却付出代价。' },
    { title: '神秘信件', preview: '收到已故好友寄出的信，指向隐秘的世界。' },
    { title: 'AI 入侵', preview: '家中助手被未知 AI 接管，逼主角踏上冒险。' },
  ],
  维度框架: [
    { title: '双时空叙事', preview: '现在线与十年前线并行，章节交替揭露真相。' },
    { title: '三条 POV', preview: '主角/反派/旁观者三视角，拼出宏大事件。' },
    { title: '现实幻境交错', preview: '现实穿插幻境，读者需判断哪些是真实。' },
    { title: '梦境/真相对照', preview: '梦境暗示未来，真相需通过梦境碎片拼合。' },
  ],
  主要角色: [
    { title: '主角+搭档+反派', preview: '经典三角，强调立场博弈与情感拉扯。' },
    { title: '双主角阵容', preview: '两位主角在不同阵营，最终走向统一目标。' },
    { title: '家族群像', preview: '以家族为单位展开，每章聚焦不同成员。' },
    { title: '冒险小队', preview: '多职业组合，升级路线与装备系统兼具。' },
  ],
  地图系统: [
    { title: '大世界开放图', preview: '可自由探索的地图，章节以任务点划分。' },
    { title: '章节节点地图', preview: '每章一个节点，完成后解锁下一分支。' },
    { title: '事件轨迹图', preview: '用事件连线展示人物行动路径。' },
    { title: '副本层级地图', preview: '副本式推进，层数越高难度越大。' },
  ],
  主线支线: [
    { title: '权谋+恋爱', preview: '主线是夺权，支线是恋爱成长，互相牵制。' },
    { title: '冒险+谜题', preview: '主线打怪升级，支线解密揭露黑幕。' },
    { title: '成神+救赎', preview: '主线追求力量，支线修复破碎关系。' },
    { title: '黎明计划', preview: '主线抵抗压迫，支线组织民众建立联盟。' },
  ],
  剧情抽离: [
    { title: '保留核心冲突', preview: '删去重复铺垫，突出冲突与转折。' },
    { title: '提炼人物关系', preview: '梳理人物矛盾点，确保主线清晰。' },
    { title: '压缩重复段落', preview: '自动识别雷同情节，建议合并。' },
    { title: '视觉化摘要', preview: '生成图表帮助编辑快速掌握剧情。' },
  ],
};

const formatNumber = (value: number | undefined) => {
  if (!value) return 0;
  return value.toLocaleString('zh-CN');
};

export default Dashboard;
interface WizardOption {
  title: string;
  preview: string;
}
