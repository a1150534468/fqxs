import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { describe, expect, test, vi } from 'vitest';
import { ChapterSidebar } from './ChapterSidebar';
import type { Chapter } from './types';

const chapters: Chapter[] = [
  {
    id: 101,
    chapter_number: 1,
    title: '凌晨发布',
    word_count: 1800,
    status: 'published',
    review_status: 'approved',
    updated_at: '2026-05-29T11:00:00',
  },
  {
    id: 102,
    chapter_number: 2,
    title: '需求反转',
    word_count: 2200,
    status: 'draft',
    review_status: 'pending',
    updated_at: '2026-05-30T09:30:00',
  },
];

describe('ChapterSidebar', () => {
  test('can transition from loading state to chapter list without hook order errors', async () => {
    const { rerender } = render(
      <ChapterSidebar
        chapters={[]}
        selectedChapterId={null}
        loading
        onSelect={vi.fn()}
        onPublish={vi.fn()}
      />,
    );

    rerender(
      <ChapterSidebar
        chapters={chapters}
        selectedChapterId={101}
        loading={false}
        onSelect={vi.fn()}
        onPublish={vi.fn()}
      />,
    );

    expect(await screen.findByText('第1章 · 凌晨发布')).toBeInTheDocument();
    expect(screen.getByText('第2章 · 需求反转')).toBeInTheDocument();
  });
});
