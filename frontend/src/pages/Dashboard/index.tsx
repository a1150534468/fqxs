import { useEffect, useMemo, useState } from 'react';
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { Button, message } from 'antd';
import { SettingOutlined } from '@ant-design/icons';
import { getNovels, createDraft, getKnowledgeGraph, getNovelSettings } from '../../api/novels';
import { getChapters } from '../../api/chapters';
import { getStatsOverview } from '../../api/stats';
import { HomePage } from './HomePage';
import { WorkspacePage } from './WorkspacePage';
import { NewBookWizard } from './NewBookWizard';
import { LLMConfigModal } from './LLMConfigModal';
import { useChapterStream } from '../../hooks/useChapterStream';
import type { Chapter, KnowledgeGraphPayload, Novel, NovelSettingRecord } from './types';
import type { StatsOverview } from '../../api/stats';

const pickResults = (response: any) => {
  if (!response) return [];
  if (Array.isArray(response.results)) return response.results;
  if (Array.isArray(response)) return response;
  return [];
};

const Dashboard = () => {
  const navigate = useNavigate();
  const [novels, setNovels] = useState<Novel[]>([]);
  const [chaptersByProject, setChaptersByProject] = useState<Record<number, Chapter[]>>({});
  const [selectedNovelId, setSelectedNovelId] = useState<number | null>(null);
  const [selectedChapterId, setSelectedChapterId] = useState<number | null>(null);
  const [chapterLoading, setChapterLoading] = useState(false);
  const [chatInput, setChatInput] = useState('');
  const [pendingTitle, setPendingTitle] = useState('');
  const [wizardOpen, setWizardOpen] = useState(false);
  const [wizardDraftId, setWizardDraftId] = useState<number | null>(null);
  const [llmModalOpen, setLlmModalOpen] = useState(false);
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
  const { state: activeStreamState } = useChapterStream(selectedNovelId);

  const loadNovels = async () => {
    try {
      const response = await getNovels({ page_size: 100, ordering: '-updated_at' });
      setNovels(pickResults(response));
    } catch (error) { console.error('Failed to fetch novels', error); }
  };

  const fetchChaptersForProject = async (projectId: number) => {
    setChapterLoading(true);
    try {
      const response = await getChapters(projectId, { ordering: 'chapter_number', page_size: 200 });
      const list = pickResults(response);
      setChaptersByProject((prev) => ({ ...prev, [projectId]: list }));
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

  const aggregatedStats = useMemo(() => {
    if (!selectedNovel) return { totalWords: 0, finishedChapters: 0, completionRate: 0, averageWords: 0, lastUpdate: '--' };
    const totalWords = selectedChapters.reduce((sum, c) => sum + (c.word_count || 0), 0);
    const finishedChapters = selectedChapters.filter((c) => ['draft', 'published'].includes(c.status || '')).length;
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
        navigate('/workspace');
      }
    });
  };

  const handleSelectNovel = (novelId: number) => {
    setSelectedNovelId(novelId); setSelectedChapterId(null); navigate('/workspace');
  };

  return (
    <>
      {activeStreamState.isRunning && selectedNovel && (
        <div
          style={{ position: 'fixed', top: 16, right: 64, zIndex: 50 }}
          className="flex items-center gap-1 bg-indigo-600 text-white text-xs px-2 py-1 rounded-full shadow animate-pulse cursor-pointer"
          onClick={() => navigate('/workspace')}
          title={`${selectedNovel.title} 写作中`}
        >
          <span>{selectedNovel.title.slice(0, 6)}</span>
          <span>写作中...</span>
        </div>
      )}
      <Button
        type="default"
        shape="circle"
        size="large"
        icon={<SettingOutlined />}
        onClick={() => setLlmModalOpen(true)}
        title="LLM Provider 管理"
        style={{ position: 'fixed', top: 16, right: 16, zIndex: 50 }}
      />
      <Routes>
        <Route
          path="/"
          element={
            <HomePage
              novels={novels}
              totalStats={totalStats}
              statsOverview={statsOverview}
              chatInput={chatInput}
              setChatInput={setChatInput}
              onCreateProject={handleCreateProject}
              onSelectNovel={handleSelectNovel}
            />
          }
        />
        <Route
          path="/workspace"
          element={
            <WorkspacePage
              selectedNovel={selectedNovel}
              selectedChapters={selectedChapters}
              selectedChapterId={selectedChapterId}
              onSelectChapter={(id) => setSelectedChapterId(id)}
              chapterLoading={chapterLoading}
              aggregatedStats={aggregatedStats}
              settings={selectedNovelId ? settingsByProject[selectedNovelId] || [] : []}
              knowledgeGraph={selectedNovelId ? knowledgeGraphByProject[selectedNovelId] : undefined}
              onChapterSaved={() => { if (selectedNovelId) fetchChaptersForProject(selectedNovelId); }}
            />
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
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
