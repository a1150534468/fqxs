import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { MemoryRouter, useLocation } from 'react-router-dom';
import Dashboard from './index';
import type { WorkbenchContext } from './types';

const mocks = vi.hoisted(() => ({
  getNovelsMock: vi.fn(),
  getWorkbenchContextMock: vi.fn(),
  getStatsOverviewMock: vi.fn(),
}));

vi.mock('../../api/novels', () => ({
  getNovels: (...args: unknown[]) => mocks.getNovelsMock(...args),
  getWorkbenchContext: (...args: unknown[]) => mocks.getWorkbenchContextMock(...args),
  createDraft: vi.fn(),
  deleteNovel: vi.fn(),
}));

vi.mock('../../api/stats', () => ({
  getStatsOverview: (...args: unknown[]) => mocks.getStatsOverviewMock(...args),
}));

vi.mock('../../hooks/useChapterStream', () => ({
  useActiveChapterStreams: () => [],
}));

vi.mock('./HomePage', () => ({
  HomePage: ({
    novels,
    onSelectNovel,
  }: {
    novels: Array<{ id: number; title: string }>;
    onSelectNovel: (novelId: number) => void;
  }) => (
    <div>
      <div>home-page</div>
      {novels.map((novel) => (
        <button key={novel.id} type="button" onClick={() => onSelectNovel(novel.id)}>
          打开 {novel.title}
        </button>
      ))}
    </div>
  ),
}));

vi.mock('./WorkspacePage', () => ({
  WorkspacePage: ({
    selectedNovel,
    selectedChapters,
    selectedChapterId,
    onSelectChapter,
  }: {
    selectedNovel: { id: number; title: string } | null;
    selectedChapters: Array<{ id: number; title?: string }>;
    selectedChapterId: number | null;
    onSelectChapter: (chapterId: number) => void;
  }) => (
    <div>
      <div data-testid="workspace-state">
        novel:{selectedNovel?.id ?? 'none'} chapter:{selectedChapterId ?? 'none'}
      </div>
      {selectedChapters.map((chapter) => (
        <button key={chapter.id} type="button" onClick={() => onSelectChapter(chapter.id)}>
          选择章节 {chapter.id}
        </button>
      ))}
    </div>
  ),
}));

vi.mock('./NewBookWizard', () => ({
  NewBookWizard: () => null,
}));

vi.mock('./LLMConfigModal', () => ({
  LLMConfigModal: () => null,
}));

const novelsResponse = {
  results: [
    {
      id: 1,
      title: '程序员夜航',
      genre: '都市',
      synopsis: '现代程序员的趣事小说',
      current_chapter: 2,
      target_chapters: 12,
    },
  ],
};

const workbenchContext: WorkbenchContext = {
  project: {
    id: 1,
    title: '程序员夜航',
    genre: '都市',
    synopsis: '现代程序员的趣事小说',
    current_chapter: 2,
    target_chapters: 12,
  },
  chapters: [
    {
      id: 101,
      chapter_number: 1,
      title: '凌晨发布',
      status: 'published',
    },
    {
      id: 102,
      chapter_number: 2,
      title: '需求反转',
      status: 'draft',
    },
  ],
  stats: {
    total_words: 4200,
    finished_chapters: 1,
    completion_rate: 8,
    average_words: 2100,
    last_update: '2026-05-30T10:00:00',
  },
  settings: [],
  chapter_summaries: [],
  chapter_reviews: [],
  storylines: [],
  plot_arc_points: [],
  knowledge_facts: [],
  foreshadow_items: [],
  style_profiles: [],
  knowledge_graph: {
    nodes: [],
    links: [],
    categories: [],
    project_id: 1,
  },
  workbench_highlights: {
    focus_chapter_number: 2,
    recommended_focus: '推进程序员主角的团队冲突',
    due_foreshadow_items: [],
    continuity_alerts: [],
    micro_beats: [],
    quality_snapshot: {
      consistency_status: 'ok',
      consistency_risks: [],
      style_risk: 'low',
      style_tone: 'stable',
    },
  },
};

const statsOverview = {
  total_books: 1,
  total_chapters: 2,
  total_words: 4200,
  status_counts: {},
  today_new_chapters: 0,
};

const LocationProbe = () => {
  const location = useLocation();
  return <div data-testid="location-probe">{`${location.pathname}${location.search}`}</div>;
};

const renderDashboard = (initialEntry = '/') => render(
  <MemoryRouter initialEntries={[initialEntry]}>
    <LocationProbe />
    <Dashboard />
  </MemoryRouter>,
);

describe('Dashboard workspace routing', () => {
  beforeEach(() => {
    mocks.getNovelsMock.mockReset();
    mocks.getWorkbenchContextMock.mockReset();
    mocks.getStatsOverviewMock.mockReset();

    mocks.getNovelsMock.mockResolvedValue(novelsResponse);
    mocks.getWorkbenchContextMock.mockResolvedValue(workbenchContext);
    mocks.getStatsOverviewMock.mockResolvedValue(statsOverview);
  });

  test('direct workspace URL restores the current novel and defaults to the first chapter', async () => {
    renderDashboard('/workspace/1');

    await waitFor(() => {
      expect(screen.getByTestId('workspace-state')).toHaveTextContent('novel:1 chapter:101');
    });

    expect(screen.getByTestId('location-probe')).toHaveTextContent('/workspace/1?chapter=101');
    expect(mocks.getWorkbenchContextMock).toHaveBeenCalledWith(1);
  });

  test('workspace URL preserves the chapter query on refresh-like entry', async () => {
    renderDashboard('/workspace/1?chapter=102');

    await waitFor(() => {
      expect(screen.getByTestId('workspace-state')).toHaveTextContent('novel:1 chapter:102');
    });

    expect(screen.getByTestId('location-probe')).toHaveTextContent('/workspace/1?chapter=102');
  });

  test('selecting a novel from homepage navigates with novel id and chapter query', async () => {
    renderDashboard('/');

    fireEvent.click(await screen.findByRole('button', { name: '打开 程序员夜航' }));

    await waitFor(() => {
      expect(screen.getByTestId('workspace-state')).toHaveTextContent('novel:1 chapter:101');
    });

    expect(screen.getByTestId('location-probe')).toHaveTextContent('/workspace/1?chapter=101');
  });

  test('changing chapter updates the chapter query in the URL', async () => {
    renderDashboard('/workspace/1');

    await waitFor(() => {
      expect(screen.getByTestId('workspace-state')).toHaveTextContent('novel:1 chapter:101');
    });

    fireEvent.click(screen.getByRole('button', { name: '选择章节 102' }));

    await waitFor(() => {
      expect(screen.getByTestId('workspace-state')).toHaveTextContent('novel:1 chapter:102');
    });

    expect(screen.getByTestId('location-probe')).toHaveTextContent('/workspace/1?chapter=102');
  });
});
