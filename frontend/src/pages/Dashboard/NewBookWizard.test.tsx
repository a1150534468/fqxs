import { render, screen, fireEvent, within } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { describe, expect, test, vi } from 'vitest';
import { NewBookWizard } from './NewBookWizard';

const mockStreamState = {
  streamingText: '# 一个非常长的标题 '.repeat(20),
  statusMessage: 'streaming',
  isStreaming: true,
  error: '',
  generate: vi.fn(),
  stop: vi.fn(),
};

vi.mock('../../api/novels', () => ({
  getDraft: vi.fn(() => Promise.resolve({ id: 1, title: '', current_step: 1 })),
  getDraftSettings: vi.fn(() => Promise.resolve([
    {
      setting_type: 'worldview',
      title: '世界观',
      content: '',
      structured_data: {},
    },
  ])),
  saveDraftStep: vi.fn(() => Promise.resolve({})),
  completeDraft: vi.fn(() => Promise.resolve({ id: 1 })),
  generateDraftTitles: vi.fn(() => Promise.resolve({ titles: ['测试书名甲', '测试书名乙'] })),
  updateDraft: vi.fn(() => Promise.resolve({ id: 1, title: '测试书名甲' })),
}));

vi.mock('../../hooks/useSettingStream', () => ({
  useSettingStream: () => mockStreamState,
}));

vi.mock('echarts-for-react', () => ({
  default: () => <div data-testid="echarts" />,
}));

describe('NewBookWizard streaming preview', () => {
  test('keeps the streaming markdown panel constrained to the section width', async () => {
    Object.assign(mockStreamState, {
      streamingText: '# 一个非常长的标题 '.repeat(20),
      statusMessage: 'streaming',
      isStreaming: true,
      error: '',
    });

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
    expect(previewPanel).toHaveClass('w-full');
    expect(previewPanel).not.toHaveClass('w-0');
  });

  test('locks future steps before previous steps are completed', async () => {
    Object.assign(mockStreamState, {
      streamingText: '',
      statusMessage: '',
      isStreaming: false,
      error: '',
    });

    render(
      <NewBookWizard
        open
        onClose={() => {}}
        draftId={1}
        pendingTitle="测试书名"
        onFinished={() => {}}
      />,
    );

    const nextStepButton = await screen.findByRole('button', { name: /人物/ });
    expect(nextStepButton).toBeDisabled();
  });
});
