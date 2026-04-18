import { useEffect, useMemo, useState } from 'react';
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { Button, message } from 'antd';
import { SettingOutlined } from '@ant-design/icons';
import { getNovels, createDraft, deleteNovel, getWorkbenchContext } from '../../api/novels';
import { getStatsOverview } from '../../api/stats';
import { HomePage } from './HomePage';
import { WorkspacePage } from './WorkspacePage';
import { NewBookWizard } from './NewBookWizard';
import { LLMConfigModal } from './LLMConfigModal';
import { useActiveChapterStreams } from '../../hooks/useChapterStream';
import type { Novel, WorkbenchContext } from './types';
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
  const [workbenchByProject, setWorkbenchByProject] = useState<Record<number, WorkbenchContext>>({});
  const [selectedNovelId, setSelectedNovelId] = useState<number | null>(null);
  const [selectedChapterId, setSelectedChapterId] = useState<number | null>(null);
  const [chapterLoading, setChapterLoading] = useState(false);
  const [chatInput, setChatInput] = useState('');
  const [pendingTitle, setPendingTitle] = useState('');
  const [wizardOpen, setWizardOpen] = useState(false);
  const [wizardDraftId, setWizardDraftId] = useState<number | null>(null);
  const [llmModalOpen, setLlmModalOpen] = useState(false);
  const [statsOverview, setStatsOverview] = useState<StatsOverview | null>(null);

  useEffect(() => {
    loadNovels();
    getStatsOverview()
      .then((data) => setStatsOverview(data))
      .catch((err) => console.error('Failed to fetch stats overview', err));
  }, []);

  useEffect(() => {
    if (selectedNovelId == null) return;
    if (!workbenchByProject[selectedNovelId]) {
      fetchWorkbenchContextForProject(selectedNovelId);
    } else if (!selectedChapterId) {
      const list = workbenchByProject[selectedNovelId]?.chapters ?? [];
      if (list.length) setSelectedChapterId(list[0].id);
    }
  }, [selectedNovelId, workbenchByProject, selectedChapterId]);

  const selectedWorkbench = selectedNovelId != null ? workbenchByProject[selectedNovelId] ?? null : null;
  const selectedNovel = selectedWorkbench?.project ?? novels.find((n) => n.id === selectedNovelId) ?? null;
  const selectedChapters = selectedWorkbench?.chapters ?? [];
  const activeStreams = useActiveChapterStreams();

  const loadNovels = async () => {
    try {
      const response = await getNovels({ page_size: 100, ordering: '-updated_at' });
      setNovels(pickResults(response));
    } catch (error) { console.error('Failed to fetch novels', error); }
  };

  const fetchWorkbenchContextForProject = async (projectId: number) => {
    setChapterLoading(true);
    try {
      const response = await getWorkbenchContext(projectId);
      setWorkbenchByProject((prev) => ({ ...prev, [projectId]: response }));
      setNovels((prev) => prev.map((novel) => (
        novel.id === projectId ? { ...novel, ...response.project } : novel
      )));

      if (projectId === selectedNovelId) {
        const list = response.chapters ?? [];
        if (!list.some((chapter: { id: number }) => chapter.id === selectedChapterId)) {
          setSelectedChapterId(list[0]?.id ?? null);
        }
      }
    } catch (error) { console.error('Failed to fetch workbench context', error); }
    finally { setChapterLoading(false); }
  };

  const aggregatedStats = useMemo(() => {
    if (!selectedWorkbench) {
      return {
        totalWords: 0,
        finishedChapters: 0,
        completionRate: 0,
        averageWords: 0,
        lastUpdate: '--',
      };
    }

    return {
      totalWords: selectedWorkbench.stats.total_words,
      finishedChapters: selectedWorkbench.stats.finished_chapters,
      completionRate: selectedWorkbench.stats.completion_rate,
      averageWords: selectedWorkbench.stats.average_words,
      lastUpdate: selectedWorkbench.stats.last_update || '--',
    };
  }, [selectedWorkbench]);

  const totalStats = useMemo(() => {
    const chapterTotal = novels.reduce((sum, n) => sum + (n.current_chapter || 0), 0);
    const wordTotal = Object.values(workbenchByProject).reduce(
      (sum, context) => sum + (context.stats.total_words || 0),
      0,
    );
    return { bookCount: novels.length, chapterCount: chapterTotal, wordCount: wordTotal };
  }, [novels, workbenchByProject]);

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
    setSelectedNovelId(novelId);
    setSelectedChapterId(null);
    fetchWorkbenchContextForProject(novelId);
    navigate('/workspace');
  };

  const handleDeleteNovel = async (novelId: number) => {
    try {
      await deleteNovel(novelId);
      setNovels((prev) => prev.filter((novel) => novel.id !== novelId));
      setWorkbenchByProject((prev) => {
        const next = { ...prev };
        delete next[novelId];
        return next;
      });

      if (selectedNovelId === novelId) {
        setSelectedNovelId(null);
        setSelectedChapterId(null);
      }

      message.success('书目已删除');
    } catch (error) {
      console.error('Failed to delete novel', error);
      message.error('删除书目失败');
    }
  };

  return (
    <>
      {activeStreams.length > 0 && (
        <div style={{ position: 'fixed', top: 16, right: 64, zIndex: 50 }} className="flex flex-col gap-2">
          {activeStreams.map(({ projectId, state }) => {
            const novel = workbenchByProject[projectId]?.project
              || novels.find((item) => item.id === projectId);
            const title = novel?.title || `项目 ${projectId}`;
            return (
              <div
                key={projectId}
                className="flex items-center gap-1 bg-indigo-600 text-white text-xs px-2 py-1 rounded-full shadow animate-pulse cursor-pointer"
                onClick={() => {
                  setSelectedNovelId(projectId);
                  setSelectedChapterId(null);
                  fetchWorkbenchContextForProject(projectId);
                  navigate('/workspace');
                }}
                title={`${title} ${state.runMode === 'continuous' ? 'continuous' : state.mode || 'generate'} 中`}
              >
                <span>{title.slice(0, 6)}</span>
                <span>
                  {state.runMode === 'continuous'
                    ? `迭代 ${state.currentChapter ?? '?'} / ${state.targetChapter ?? '?'}`
                    : state.mode === 'continue'
                      ? '续写中'
                      : state.mode === 'regenerate'
                        ? '重写中'
                        : '写作中'}
                </span>
              </div>
            );
          })}
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
              onDeleteNovel={handleDeleteNovel}
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
              settings={selectedWorkbench?.settings || []}
              chapterSummaries={selectedWorkbench?.chapter_summaries || []}
              storylines={selectedWorkbench?.storylines || []}
              plotArcPoints={selectedWorkbench?.plot_arc_points || []}
              knowledgeFacts={selectedWorkbench?.knowledge_facts || []}
              foreshadowItems={selectedWorkbench?.foreshadow_items || []}
              styleProfiles={selectedWorkbench?.style_profiles || []}
              workbenchHighlights={selectedWorkbench?.workbench_highlights}
              knowledgeGraph={selectedWorkbench?.knowledge_graph}
              onChapterSaved={() => {
                if (selectedNovelId) {
                  fetchWorkbenchContextForProject(selectedNovelId);
                  loadNovels();
                }
              }}
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
