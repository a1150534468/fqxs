import { useEffect, useMemo, useState } from 'react';
import { Button, Tag, message } from 'antd';
import { SettingOutlined } from '@ant-design/icons';
import type { DataNode, TreeProps } from 'antd/es/tree';
import { getNovels, createDraft, getKnowledgeGraph, getNovelSettings } from '../../api/novels';
import { getChapters } from '../../api/chapters';
import { getStatsOverview } from '../../api/stats';
import { chapterStatusTag, statusColors } from './constants';
import { HomePage } from './HomePage';
import { WorkspacePage } from './WorkspacePage';
import { NewBookWizard } from './NewBookWizard';
import { LLMConfigModal } from './LLMConfigModal';
import type { Chapter, KnowledgeGraphPayload, Mode, Novel, NovelSettingRecord } from './types';
import type { StatsOverview } from '../../api/stats';

const pickResults = (response: any) => {
  if (!response) return [];
  if (Array.isArray(response.results)) return response.results;
  if (Array.isArray(response)) return response;
  return [];
};

const Dashboard = () => {
  const [mode, setMode] = useState<Mode>('home');
  const [llmModalOpen, setLlmModalOpen] = useState(false);
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
  const [wizardDraftId, setWizardDraftId] = useState<number | null>(null);
  const [chaptersExpanded, setChaptersExpanded] = useState<React.Key[]>([]);
  const [liveLog, setLiveLog] = useState<string[]>([]);
  const [streamText, setStreamText] = useState('');
  const [streamPointer, setStreamPointer] = useState(0);
  const [isStreaming, setIsStreaming] = useState(false);
  const [statsOverview, setStatsOverview] = useState<StatsOverview | null>(null);
  const [settingsByProject, setSettingsByProject] = useState<Record<number, NovelSettingRecord[]>>({});
  const [knowledgeGraphByProject, setKnowledgeGraphByProject] = useState<Record<number, KnowledgeGraphPayload>>({});

  useEffect(() => {
    loadNovels();
    getStatsOverview()
      .then((data) => setStatsOverview(data))
      .catch((err) => console.error('Failed to fetch stats overview', err));
  }, []);

  useEffect(() => {
    if (selectedNovelId == null) return;
    if (!chaptersByProject[selectedNovelId]) {
      fetchChaptersForProject(selectedNovelId);
    } else if (!selectedChapterId) {
      const list = chaptersByProject[selectedNovelId];
      if (list.length) setSelectedChapterId(list[0].id);
    }

    if (!settingsByProject[selectedNovelId]) {
      fetchSettingsForProject(selectedNovelId);
    }
    if (!knowledgeGraphByProject[selectedNovelId]) {
      fetchKnowledgeGraphForProject(selectedNovelId);
    }
  }, [selectedNovelId, chaptersByProject, settingsByProject, knowledgeGraphByProject, selectedChapterId]);

  const selectedNovel = novels.find((n) => n.id === selectedNovelId) ?? null;
  const selectedChapters = selectedNovel ? chaptersByProject[selectedNovel.id] ?? [] : [];
  const selectedChapter = selectedChapters.find((c) => c.id === selectedChapterId) ?? selectedChapters[0] ?? null;

  useEffect(() => {
    if (!selectedChapter) { setStreamText(''); setIsStreaming(false); return; }
    const isGenerating = selectedChapter.status === 'generating';
    setStreamPointer(0);
    setStreamText('');
    setIsStreaming(isGenerating);
    setLiveLog([`${new Date().toLocaleTimeString()} · 打开章节《${selectedChapter.title || `第${selectedChapter.chapter_number}章`}》`]);
  }, [selectedChapter?.id]);

  useEffect(() => {
    if (!selectedChapter || !isStreaming) return;
    const text = selectedChapter.final_content || selectedChapter.raw_content || '';
    if (!text) return;
    const interval = setInterval(() => {
      setStreamPointer((prev) => {
        const next = Math.min(text.length, prev + 48);
        setStreamText(text.slice(0, next));
        if (next >= text.length) { clearInterval(interval); setIsStreaming(false); }
        return next;
      });
    }, 300);
    return () => clearInterval(interval);
  }, [isStreaming, selectedChapter]);

  useEffect(() => {
    if (!selectedNovel) return;
    const template = ['分析灵感与市场趋势', '召回人物设定，更新行为约束', '写作引擎排队生成正文', 'AI 审校标记敏感内容', '推送章节至人工审核区'];
    let index = 0;
    const timer = setInterval(() => {
      setLiveLog((prev) => [`${new Date().toLocaleTimeString()} · ${template[index % template.length]}`, ...prev].slice(0, 8));
      index += 1;
    }, 4500);
    return () => clearInterval(timer);
  }, [selectedNovel?.id]);

  const loadNovels = async () => {
    setLoadingTree(true);
    try {
      const response = await getNovels({ page_size: 100, ordering: '-updated_at' });
      setNovels(pickResults(response));
    } catch (error) { console.error('Failed to fetch novels', error); }
    finally { setLoadingTree(false); }
  };

  const fetchChaptersForProject = async (projectId: number) => {
    setChapterLoading(true);
    try {
      const response = await getChapters(projectId, { ordering: 'chapter_number', page_size: 200 });
      const list = pickResults(response);
      setChaptersByProject((prev) => ({ ...prev, [projectId]: list }));
      setChapterProjectMap((prev) => {
        const next = { ...prev };
        list.forEach((chapter: Chapter) => { next[chapter.id] = projectId; });
        return next;
      });
      if (!selectedChapterId && projectId === selectedNovelId && list.length) setSelectedChapterId(list[0].id);
    } catch (error) { console.error('Failed to fetch chapters', error); }
    finally { setChapterLoading(false); }
  };

  const fetchSettingsForProject = async (projectId: number) => {
    try {
      const response = await getNovelSettings(projectId);
      setSettingsByProject((prev) => ({ ...prev, [projectId]: pickResults(response) }));
    } catch (error) {
      console.error('Failed to fetch settings', error);
    }
  };

  const fetchKnowledgeGraphForProject = async (projectId: number) => {
    try {
      const response = await getKnowledgeGraph(projectId);
      setKnowledgeGraphByProject((prev) => ({ ...prev, [projectId]: response }));
    } catch (error) {
      console.error('Failed to fetch knowledge graph', error);
    }
  };

  const visibleNovels = useMemo(() => {
    const keyword = searchKeyword.trim().toLowerCase();
    if (!keyword) return novels;
    return novels.filter((novel) => novel.title.toLowerCase().includes(keyword));
  }, [novels, searchKeyword]);

  const aggregatedStats = useMemo(() => {
    if (!selectedNovel) return { totalWords: 0, finishedChapters: 0, completionRate: 0, averageWords: 0, lastUpdate: '--' };
    const totalWords = selectedChapters.reduce((sum, c) => sum + (c.word_count || 0), 0);
    const finishedChapters = selectedChapters.filter((c) => ['approved', 'published'].includes(c.status || '')).length;
    const completionRate = selectedNovel.target_chapters ? Math.min(100, Math.round(((selectedNovel.current_chapter || finishedChapters) / selectedNovel.target_chapters) * 100)) : 0;
    const averageWords = selectedChapters.length > 0 ? Math.round(totalWords / selectedChapters.length) : 0;
    const lastUpdate = selectedNovel.last_update_at || selectedChapters[selectedChapters.length - 1]?.updated_at || selectedChapters[selectedChapters.length - 1]?.created_at || '--';
    return { totalWords, finishedChapters, completionRate, averageWords, lastUpdate };
  }, [selectedNovel, selectedChapters]);

  const totalStats = useMemo(() => {
    const chapterTotal = novels.reduce((sum, n) => sum + (n.current_chapter || 0), 0);
    const wordTotal = Object.values(chaptersByProject).flat().reduce((sum, c) => sum + (c.word_count || 0), 0);
    return { bookCount: novels.length, chapterCount: chapterTotal, wordCount: wordTotal };
  }, [novels, chaptersByProject]);

  const treeData: DataNode[] = visibleNovels.map((novel) => ({
    key: `novel-${novel.id}`,
    title: (
      <div className="flex items-center justify-between pr-2 w-full">
        <span className="font-medium text-gray-800">{novel.title}</span>
        <Tag color={statusColors[novel.status || 'active'] || 'default'}>{novel.status || 'active'}</Tag>
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
    selectedChapterId != null ? [`chapter-${selectedChapterId}`] : selectedNovelId != null ? [`novel-${selectedNovelId}`] : [];

  const handleTreeSelect: TreeProps['onSelect'] = (keys) => {
    const key = keys[0];
    if (!key || typeof key !== 'string') return;
    if (key.startsWith('novel-')) {
      const id = parseInt(key.replace('novel-', ''), 10);
      setSelectedNovelId(id); setSelectedChapterId(null); setMode('workspace');
    } else if (key.startsWith('chapter-')) {
      const id = parseInt(key.replace('chapter-', ''), 10);
      const projectId = chapterProjectMap[id];
      if (projectId) setSelectedNovelId(projectId);
      setSelectedChapterId(id); setMode('workspace');
    }
  };

  const handleTreeExpand: TreeProps['onExpand'] = (keys) => {
    setChaptersExpanded(keys);
    keys.forEach((key) => {
      if (typeof key === 'string' && key.startsWith('novel-')) {
        const id = parseInt(key.replace('novel-', ''), 10);
        if (!chaptersByProject[id]) fetchChaptersForProject(id);
      }
    });
  };

  const handleCreateProject = async () => {
    const inspiration = pendingTitle || chatInput.trim();
    if (!inspiration) { message.warning('先输入一句灵感，再建档哦！'); return; }
    if (!pendingTitle) setPendingTitle(inspiration);
    try {
      const draft = await createDraft({ inspiration });
      setWizardDraftId(draft.id);
      setWizardOpen(true);
    } catch (err: any) {
      console.error(err);
      message.error(err?.response?.data?.detail || '创建草稿失败');
    }
  };

  const handleWizardFinished = (newProjectId?: number) => {
    setWizardOpen(false);
    setWizardDraftId(null);
    setPendingTitle('');
    loadNovels().then(() => {
      if (newProjectId) {
        setSelectedNovelId(newProjectId);
        setMode('workspace');
      }
    });
  };

  const handleSelectNovel = (novelId: number) => {
    setSelectedNovelId(novelId); setSelectedChapterId(null); setMode('workspace');
  };

  return (
    <>
      <Button
        type="default"
        shape="circle"
        size="large"
        icon={<SettingOutlined />}
        onClick={() => setLlmModalOpen(true)}
        title="LLM Provider 管理"
        style={{ position: 'fixed', top: 16, right: 16, zIndex: 50 }}
      />
      {mode === 'home' ? (
        <HomePage
          novels={novels}
          totalStats={totalStats}
          statsOverview={statsOverview}
          chatInput={chatInput}
          setChatInput={setChatInput}
          onCreateProject={handleCreateProject}
          onSelectNovel={handleSelectNovel}
        />
      ) : (
        <WorkspacePage
          novels={novels}
          visibleNovels={visibleNovels}
          selectedNovel={selectedNovel}
          selectedChapters={selectedChapters}
          selectedChapter={selectedChapter}
          chaptersByProject={chaptersByProject}
          aggregatedStats={aggregatedStats}
          statsOverview={statsOverview}
          searchKeyword={searchKeyword}
          setSearchKeyword={setSearchKeyword}
          loadingTree={loadingTree}
          chapterLoading={chapterLoading}
          chaptersExpanded={chaptersExpanded}
          treeData={treeData}
          selectedKeys={selectedKeys}
          handleTreeSelect={handleTreeSelect}
          handleTreeExpand={handleTreeExpand}
          streamText={streamText}
          streamPointer={streamPointer}
          isStreaming={isStreaming}
          setIsStreaming={setIsStreaming}
          liveLog={liveLog}
          setLiveLog={setLiveLog}
          setMode={setMode}
          onChapterSaved={() => { if (selectedNovelId) fetchChaptersForProject(selectedNovelId); }}
          settings={selectedNovelId ? settingsByProject[selectedNovelId] || [] : []}
          knowledgeGraph={selectedNovelId ? knowledgeGraphByProject[selectedNovelId] : undefined}
        />
      )}
      <NewBookWizard
        open={wizardOpen}
        onClose={() => setWizardOpen(false)}
        draftId={wizardDraftId}
        pendingTitle={pendingTitle}
        onFinished={handleWizardFinished}
      />
      <LLMConfigModal open={llmModalOpen} onClose={() => setLlmModalOpen(false)} />
    </>
  );
};

export default Dashboard;
