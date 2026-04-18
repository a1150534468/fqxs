import { describe, expect, test, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import Dashboard from './index';

const mockGetNovels = vi.fn();
const mockGetWorkbenchContext = vi.fn();
const mockGetStatsOverview = vi.fn();

vi.mock('../../api/novels', () => ({
  getNovels: (...args: any[]) => mockGetNovels(...args),
  createDraft: vi.fn(),
  deleteNovel: vi.fn(),
  getWorkbenchContext: (...args: any[]) => mockGetWorkbenchContext(...args),
}));

vi.mock('../../api/stats', () => ({
  getStatsOverview: (...args: any[]) => mockGetStatsOverview(...args),
}));

vi.mock('../../hooks/useChapterStream', () => ({
  useActiveChapterStreams: () => [],
  useChapterStream: () => ({
    state: {},
    start: vi.fn(),
    stop: vi.fn(),
  }),
}));

vi.mock('./HomePage', () => ({
  HomePage: ({ onSelectNovel }: any) => (
    <button type="button" onClick={() => onSelectNovel(7)}>Open Novel</button>
  ),
}));

vi.mock('./WorkspacePage', () => ({
  WorkspacePage: ({ selectedNovel, selectedChapterId }: any) => (
    <div>
      <div data-testid="workspace-novel">{selectedNovel?.title ?? 'none'}</div>
      <div data-testid="workspace-chapter">{selectedChapterId ?? 'none'}</div>
    </div>
  ),
}));

vi.mock('./NewBookWizard', () => ({
  NewBookWizard: () => null,
}));

vi.mock('./LLMConfigModal', () => ({
  LLMConfigModal: () => null,
}));

describe('Dashboard workspace restoration', () => {
  beforeEach(() => {
    mockGetNovels.mockReset();
    mockGetWorkbenchContext.mockReset();
    mockGetStatsOverview.mockReset();

    mockGetNovels.mockResolvedValue({
      results: [
        {
          id: 7,
          title: '测试小说',
          genre: '玄幻',
          current_chapter: 2,
          target_chapters: 10,
        },
      ],
    });
    mockGetWorkbenchContext.mockResolvedValue({
      project: {
        id: 7,
        title: '测试小说',
        genre: '玄幻',
        current_chapter: 2,
        target_chapters: 10,
      },
      chapters: [
        { id: 101, chapter_number: 1, title: '第一章', status: 'draft' },
        { id: 102, chapter_number: 2, title: '第二章', status: 'draft' },
      ],
      stats: {
        total_words: 1000,
        finished_chapters: 2,
        completion_rate: 20,
        average_words: 500,
        last_update: '2026-04-18T00:00:00Z',
      },
      settings: [],
      chapter_summaries: [],
      storylines: [],
      plot_arc_points: [],
      knowledge_facts: [],
      foreshadow_items: [],
      style_profiles: [],
    });
    mockGetStatsOverview.mockResolvedValue({});
  });

  test('restores selected novel and chapter from workspace query params', async () => {
    render(
      <MemoryRouter initialEntries={['/workspace?novelId=7&chapterId=102']}>
        <Routes>
          <Route path="*" element={<Dashboard />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(mockGetWorkbenchContext).toHaveBeenCalledWith(7);
    });

    await waitFor(() => {
      expect(screen.getByTestId('workspace-novel')).toHaveTextContent('测试小说');
      expect(screen.getByTestId('workspace-chapter')).toHaveTextContent('102');
    });
  });

  test('selecting a novel fetches workbench context only once', async () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="*" element={<Dashboard />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(await screen.findByRole('button', { name: 'Open Novel' }));

    await waitFor(() => {
      expect(mockGetWorkbenchContext).toHaveBeenCalledTimes(1);
      expect(mockGetWorkbenchContext).toHaveBeenCalledWith(7);
    });
  });

  test('falls back to first chapter when query chapter is missing after workbench load', async () => {
    render(
      <MemoryRouter initialEntries={['/workspace?novelId=7&chapterId=999']}>
        <Routes>
          <Route path="*" element={<Dashboard />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(mockGetWorkbenchContext).toHaveBeenCalledWith(7);
    });

    await waitFor(() => {
      expect(screen.getByTestId('workspace-chapter')).toHaveTextContent('101');
    });
  });
});
