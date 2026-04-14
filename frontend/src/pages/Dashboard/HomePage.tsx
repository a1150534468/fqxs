import { useMemo, useState } from 'react';
import { Button } from 'antd';
import dayjs from 'dayjs';
import { SidebarOverview } from './components/SidebarOverview';
import { NewBookCard, type ChatMessage } from './components/NewBookCard';
import { BookGrid } from './components/BookGrid';
import type { Novel } from './types';
import type { StatsOverview } from '../../api/stats';

interface HomePageProps {
  novels: Novel[];
  totalStats: {
    bookCount: number;
    chapterCount: number;
    wordCount: number;
  };
  statsOverview: StatsOverview | null;
  chatInput: string;
  setChatInput: (value: string) => void;
  onCreateProject: () => void;
  onSelectNovel: (novelId: number) => void;
}

export const HomePage = ({
  novels,
  totalStats,
  statsOverview,
  chatInput,
  setChatInput,
  onCreateProject,
  onSelectNovel,
}: HomePageProps) => {
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([
    {
      id: 'init-user',
      role: 'user',
      text: '想写一部赛博江湖题材，突出快节奏爱情线，可以吗？',
      timestamp: dayjs().subtract(2, 'minute').format('HH:mm'),
    },
    {
      id: 'init-ai',
      role: 'ai',
      text: '已根据热点题材准备灵感模板，输入一句话即可拉起 6 步设定向导。',
      timestamp: dayjs().subtract(2, 'minute').format('HH:mm'),
    },
  ]);

  const metrics = useMemo(() => {
    if (!statsOverview) {
      return [
        { label: '总书籍', value: totalStats.bookCount },
        { label: '总章节', value: totalStats.chapterCount },
        { label: '累计字数', value: `${totalStats.wordCount.toLocaleString()} 字` },
      ];
    }
    return [
      { label: '总书籍', value: statsOverview.total_books },
      { label: '总章节', value: statsOverview.total_chapters },
      { label: '累计字数', value: `${statsOverview.total_words.toLocaleString()} 字` },
      { label: '今日新增章节', value: statsOverview.today_new_chapters },
    ];
  }, [statsOverview, totalStats]);

  const handleChatSend = (text: string) => {
    if (!text.trim()) return;
    const id = `${Date.now()}`;
    setChatHistory((prev) => [
      ...prev,
      { id, role: 'user', text, timestamp: dayjs().format('HH:mm') },
      {
        id: `${id}-ai`,
        role: 'ai',
        text: '灵感已收录，PlotPilot 会在向导中逐步展开世界观、角色与剧情。',
        timestamp: dayjs().format('HH:mm'),
      },
    ]);
  };

  return (
    <div className="flex flex-col lg:flex-row gap-6 min-h-[calc(100vh-120px)]">
      <aside className="lg:w-72 xl:w-80 flex-shrink-0">
        <SidebarOverview stats={metrics} onCreateProject={onCreateProject} />
      </aside>
      <main className="flex-1 space-y-6">
        <div className="rounded-[28px] bg-gradient-to-br from-[#1b1344] via-[#3b1f7a] to-[#5b21b6] text-white p-8 shadow-xl flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div>
            <p className="uppercase tracking-[0.55em] text-xs text-indigo-200">PlotPilot Studio</p>
            <h1 className="text-3xl font-semibold mt-3">书稿工作台</h1>
            <p className="text-indigo-100 mt-2">从一句灵感到上架完稿，左侧导航随时召唤 6 步写作引擎。</p>
          </div>
          <div className="flex gap-4">
            
            <Button type="primary" size="large" onClick={onCreateProject}>
              建档并进入工作台
            </Button>
            
          </div>
        </div>

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr),_minmax(0,0.9fr)]">
          <NewBookCard
            chatInput={chatInput}
            setChatInput={setChatInput}
            onCreateProject={() => {
              handleChatSend(chatInput);
              onCreateProject();
            }}
            history={chatHistory}
          />

          <div className="space-y-5">
            <BookGrid novels={novels} onSelectNovel={onSelectNovel} />
            
          </div>
        </div>
      </main>
    </div>
  );
};
