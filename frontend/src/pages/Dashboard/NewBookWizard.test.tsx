import { render, screen, fireEvent, within } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { describe, expect, test, vi } from 'vitest';
import { NewBookWizard } from './NewBookWizard';

vi.mock('../../api/novels', () => ({
  getDraftSettings: vi.fn(() => Promise.resolve([])),
  saveDraftStep: vi.fn(() => Promise.resolve({})),
  completeDraft: vi.fn(() => Promise.resolve({ id: 1 })),
}));

vi.mock('../../hooks/useSettingStream', () => ({
  useSettingStream: () => ({
    streamingText: '# 一个非常长的标题 '.repeat(20),
    statusMessage: 'streaming',
    isStreaming: true,
    error: '',
    generate: vi.fn(),
    stop: vi.fn(),
  }),
}));

vi.mock('echarts-for-react', () => ({
  default: () => <div data-testid="echarts" />,
}));

describe('NewBookWizard streaming preview', () => {
  test('keeps the streaming markdown panel constrained to the section width', async () => {
    render(
      <NewBookWizard
        open
        onClose={() => {}}
        draftId={1}
        pendingTitle="测试书名"
        onFinished={() => {}}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: /人物/ }));

    const heading = await screen.findByText('AI 实时输出');
    const previewSection = heading.closest('div')?.parentElement?.parentElement;
    expect(previewSection).toBeTruthy();

    const previewPanel = previewSection
      ? within(previewSection).getByText(/一个非常长的标题/).closest('[data-color-mode="light"]')
      : null;

    expect(previewPanel).toBeTruthy();
    expect(previewPanel).toHaveClass('min-w-0');
  });
});
