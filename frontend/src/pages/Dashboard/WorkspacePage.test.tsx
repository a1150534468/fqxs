import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { WorkspacePage } from './WorkspacePage';
import type {
  Chapter,
  ChapterReviewRecord,
  ChapterSummaryRecord,
  ForeshadowItemRecord,
  KnowledgeFactRecord,
  Novel,
  NovelSettingRecord,
  PlotArcPointRecord,
  StorylineRecord,
  StyleProfileRecord,
  WorkbenchHighlights,
} from './types';

const mockRefs = vi.hoisted(() => ({
  streamStartMock: vi.fn(),
  streamStopMock: vi.fn(),
  updateChapterMock: vi.fn(),
  publishChapterMock: vi.fn(),
  saveChapterReviewMock: vi.fn(),
  messageSuccessMock: vi.fn(),
  messageWarningMock: vi.fn(),
  messageErrorMock: vi.fn(),
  navigateMock: vi.fn(),
}));

const streamStateBase = {
  isRunning: false,
  streamText: '',
  logs: [] as Array<{ time: string; message: string }>,
  startChapter: null,
  currentChapter: null,
  targetChapter: null,
  targetWords: null,
  completedChapters: 0,
  error: null,
  sessionId: null,
  mode: null,
  runMode: 'single' as const,
  fullAutoMode: false,
  stopRequested: false,
  lastSavedChapterId: null,
  lastSavedEventId: null,
  lastCompletedSessionId: null,
};

let streamState = { ...streamStateBase };

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockRefs.navigateMock,
  };
});

vi.mock('../../hooks/useChapterStream', () => ({
  useChapterStream: () => ({
    state: streamState,
    start: mockRefs.streamStartMock,
    stop: mockRefs.streamStopMock,
  }),
}));

vi.mock('../../api/chapters', () => ({
  updateChapter: (...args: unknown[]) => mockRefs.updateChapterMock(...args),
  publishChapter: (...args: unknown[]) => mockRefs.publishChapterMock(...args),
  saveChapterReview: (...args: unknown[]) => mockRefs.saveChapterReviewMock(...args),
}));

vi.mock('antd', async () => {
  const actual = await vi.importActual<typeof import('antd')>('antd');
  return {
    ...actual,
    message: {
      success: mockRefs.messageSuccessMock,
      warning: mockRefs.messageWarningMock,
      error: mockRefs.messageErrorMock,
    },
  };
});

vi.mock('../../components/charts/InsightGraph', () => ({
  InsightGraph: () => <div data-testid="insight-graph" />,
}));

const novel: Novel = {
  id: 1,
  title: '程序员夜航',
  genre: '都市',
  synopsis: '一个现代程序员团队在创业和写作之间来回切换。',
  target_chapters: 12,
  current_chapter: 2,
};

const chapters: Chapter[] = [
  {
    id: 101,
    chapter_number: 1,
    title: '凌晨发布',
    word_count: 1800,
    status: 'published',
    review_status: 'approved',
    raw_content: '第一章原稿',
    final_content: '第一章终稿',
    summary: '项目组第一次上线后熬夜复盘。',
    open_threads: ['埋下监控报警线'],
    consistency_status: { status: 'ok', risks: [], checked_entities: ['林舟'] },
    updated_at: '2026-05-29T11:00:00',
  },
  {
    id: 102,
    chapter_number: 2,
    title: '需求反转',
    word_count: 2200,
    status: 'draft',
    review_status: 'pending',
    raw_content: '第二章原稿',
    final_content: '第二章终稿',
    summary: '客户临时改需求，团队开始分裂。',
    open_threads: ['客户真实动机'],
    consistency_status: { status: 'warning', risks: ['节奏略慢'], checked_entities: ['林舟', '周芷'] },
    updated_at: '2026-05-30T09:30:00',
  },
];

const settings: NovelSettingRecord[] = [
  { setting_type: 'worldview', title: '世界观', content: '现代互联网创业背景。' },
];

const chapterSummaries: ChapterSummaryRecord[] = [
  {
    id: 1,
    chapter: 102,
    chapter_number: 2,
    summary: '客户改需求导致主角面临一次产品与自我表达的冲突。',
    key_events: ['客户否决原方案'],
    open_threads: ['客户真实动机'],
  },
];

const chapterReviews: ChapterReviewRecord[] = [
  {
    id: 1,
    project: 1,
    chapter: 102,
    chapter_number: 2,
    status: 'pending',
    review_notes: '',
    ai_review: '',
    ai_action_items: [],
    modification_rate: 20,
    created_at: '2026-05-30T10:00:00',
    updated_at: '2026-05-30T10:00:00',
  },
];

const storylines: StorylineRecord[] = [
  {
    id: 1,
    name: '创业主线',
    storyline_type: 'main',
    status: 'active',
    description: '主角团队冲刺新产品上线。',
    estimated_chapter_start: 1,
    estimated_chapter_end: 12,
    priority: 1,
  },
];

const plotArcPoints: PlotArcPointRecord[] = [
  {
    id: 1,
    chapter_number: 3,
    point_type: 'turn',
    tension_level: 8,
    description: '主角决定违背客户要求。',
  },
];

const knowledgeFacts: KnowledgeFactRecord[] = [
  {
    id: 1,
    chapter: 102,
    chapter_number: 2,
    subject: '林舟',
    predicate: '负责',
    object: '后端架构',
    source_excerpt: '林舟盯着日志看了一夜',
    confidence: 0.92,
    status: 'active',
  },
];

const foreshadowItems: ForeshadowItemRecord[] = [
  {
    id: 1,
    title: '异常报警线',
    description: '监控报警似乎和客户真实目的有关。',
    introduced_in_chapter_number: 1,
    expected_payoff_chapter: 3,
    status: 'open',
    related_character: '林舟',
  },
];

const styleProfiles: StyleProfileRecord[] = [
  {
    id: 1,
    profile_type: 'chapter_analysis',
    content: '',
    structured_data: {
      chapter_number: 2,
      risk_level: 'medium',
      average_sentence_length: 22,
      dialogue_density: 0.34,
    },
  },
];

const workbenchHighlights: WorkbenchHighlights = {
  focus_chapter_number: 2,
  recommended_focus: '把客户需求反转带来的团队裂痕写实。',
  active_storyline: storylines[0],
  nearest_plot_point: plotArcPoints[0],
  due_foreshadow_items: foreshadowItems,
  continuity_alerts: [
    {
      level: 'warning',
      title: '情绪反应偏弱',
      detail: '主角面对需求反转的反应还不够强。',
    },
  ],
  micro_beats: [
    {
      index: 1,
      label: '会议爆点',
      focus: '冲突升级',
      objective: '把会议上的分歧写出压迫感。',
      target_words: 900,
    },
  ],
  focus_card: {
    chapter_number: 2,
    mission: '让团队分歧从业务问题升级为价值观冲突。',
    conflict: '客户要数据，主角要作品完整性。',
    key_turn: '主角第一次公开反对客户。',
    emotional_note: '压抑和愤怒并行',
    ending_hook: '会后收到匿名威胁邮件。',
    must_keep: ['会议室争执', '异常报警'],
    must_payoff: ['异常报警线'],
    must_fix: ['主角犹豫过少'],
    avoid: ['空泛抒情'],
  },
  quality_snapshot: {
    consistency_status: 'warning',
    consistency_risks: ['节奏略慢'],
    style_risk: 'medium',
    style_tone: '现实紧张',
  },
  workflow_gate: {
    allowed: true,
    status: 'warning',
    summary: '建议先补强主角情绪，再继续后续章节。',
    checked_chapter: {
      id: 102,
      chapter_number: 2,
      title: '需求反转',
      status: 'draft',
      review_status: 'pending',
      modification_rate: 20,
    },
    blocking_reasons: [],
    warnings: [
      {
        code: 'emotion-thin',
        level: 'warning',
        title: '情绪薄弱',
        detail: '主角的愤怒还需要更明确的行为落点。',
      },
    ],
    minimum_modification_rate: 15,
  },
};

const renderWorkspace = (overrides?: Partial<React.ComponentProps<typeof WorkspacePage>>) => {
  const props: React.ComponentProps<typeof WorkspacePage> = {
    selectedNovel: novel,
    selectedChapters: chapters,
    selectedChapterId: 102,
    onSelectChapter: vi.fn(),
    chapterLoading: false,
    aggregatedStats: {
      totalWords: 4000,
      finishedChapters: 1,
      completionRate: 8,
      averageWords: 2000,
      lastUpdate: '2026-05-30',
    },
    settings,
    chapterSummaries,
    chapterReviews,
    storylines,
    plotArcPoints,
    knowledgeFacts,
    foreshadowItems,
    styleProfiles,
    workbenchHighlights,
    onChapterSaved: vi.fn(),
    ...overrides,
  };

  return render(
    <MemoryRouter>
      <WorkspacePage {...props} />
    </MemoryRouter>,
  );
};

const findButtonByText = (label: string) => {
  const target = label.replace(/\s/g, '');
  return screen.getAllByRole('button').find((button) => (
    button.textContent?.replace(/\s/g, '') === target
  ));
};

const requireButtonByText = (label: string) => {
  const button = findButtonByText(label);
  expect(button).toBeTruthy();
  return button as HTMLElement;
};

describe('WorkspacePage', () => {
  beforeEach(() => {
    streamState = { ...streamStateBase };
    mockRefs.streamStartMock.mockReset();
    mockRefs.streamStopMock.mockReset();
    mockRefs.updateChapterMock.mockReset();
    mockRefs.publishChapterMock.mockReset();
    mockRefs.saveChapterReviewMock.mockReset();
    mockRefs.messageSuccessMock.mockReset();
    mockRefs.messageWarningMock.mockReset();
    mockRefs.messageErrorMock.mockReset();
    mockRefs.navigateMock.mockReset();
    mockRefs.updateChapterMock.mockResolvedValue({});
    mockRefs.publishChapterMock.mockResolvedValue({});
    mockRefs.saveChapterReviewMock.mockResolvedValue({
      ...chapterReviews[0],
      status: 'approved',
      review_notes: '结构已经通过。',
      ai_review: '建议加强会议冲突。',
      ai_action_items: ['加重主角肢体反应'],
    });
  });

  test('renders cockpit as writing-first workspace by default', () => {
    renderWorkspace();

    expect(screen.getByRole('main', { name: '正文工作区' })).toBeInTheDocument();
    expect(screen.getByLabelText('章节导航')).toBeInTheDocument();
    expect(screen.getByLabelText('右侧情报区')).toBeInTheDocument();
    expect(screen.queryByText('项目脉冲面板')).not.toBeInTheDocument();
    expect(screen.getByText('AI 输出面板')).toBeInTheDocument();
  });

  test('switches selected chapter from sidebar', () => {
    const onSelectChapter = vi.fn();
    renderWorkspace({ onSelectChapter });

    fireEvent.click(screen.getByText(/第1章/));

    expect(onSelectChapter).toHaveBeenCalledWith(101);
  });

  test('saves manuscript edits through updateChapter', async () => {
    renderWorkspace();

    fireEvent.click(screen.getByRole('tab', { name: '当前正文' }));
    const editor = screen.getByPlaceholderText('当前章节正文会显示在这里，可直接人工润色后保存。');
    fireEvent.change(editor, { target: { value: '第二章终稿，补入更强的情绪动作。' } });
    fireEvent.click(screen.getByRole('button', { name: '保存正文' }));

    await waitFor(() => {
      expect(mockRefs.updateChapterMock).toHaveBeenCalledWith(102, {
        final_content: '第二章终稿，补入更强的情绪动作。',
        publish_status: 'draft',
      });
    });
    expect(mockRefs.messageSuccessMock).toHaveBeenCalledWith('正文已保存');
  });

  test('saves review notes and status through saveChapterReview', async () => {
    renderWorkspace();

    fireEvent.click(screen.getByRole('tab', { name: /质量守护/ }));
    fireEvent.click(screen.getByLabelText('已定稿'));
    fireEvent.change(screen.getByPlaceholderText('记录人工审稿结论、问题位置和修改建议。'), {
      target: { value: '结构已经通过。' },
    });
    fireEvent.click(screen.getByRole('button', { name: '保存审阅' }));

    await waitFor(() => {
      expect(mockRefs.saveChapterReviewMock).toHaveBeenCalledWith(102, {
        status: 'approved',
        review_notes: '结构已经通过。',
      });
    });
    expect(mockRefs.messageSuccessMock).toHaveBeenCalledWith('审阅记录已保存');
  });

  test('publish button stays disabled until chapter is approved', () => {
    renderWorkspace();

    const publishButton = requireButtonByText('发布');
    expect(publishButton).toBeDisabled();
  });

  test('publishes approved chapters', async () => {
    const approvedDraftChapters: Chapter[] = chapters.map((chapter) => (
      chapter.id === 102
        ? { ...chapter, review_status: 'approved' }
        : chapter
    ));

    renderWorkspace({
      selectedChapters: approvedDraftChapters,
      selectedChapterId: 102,
      chapterReviews: [{
        ...chapterReviews[0],
        chapter: 102,
        chapter_number: 2,
        status: 'approved',
      }],
    });

    const publishButton = requireButtonByText('发布');
    fireEvent.click(publishButton);

    await waitFor(() => {
      expect(mockRefs.publishChapterMock).toHaveBeenCalledWith(102);
    });
    expect(mockRefs.messageSuccessMock).toHaveBeenCalledWith('发布成功');
  });

  test('blocks continuous generation when workflow gate disallows it', async () => {
    renderWorkspace({
      workbenchHighlights: {
        ...workbenchHighlights,
        workflow_gate: {
          ...workbenchHighlights.workflow_gate!,
          allowed: false,
          status: 'blocked',
          summary: '必须先完成本章修订才能继续。',
          blocking_reasons: [
            {
              code: 'needs-revision',
              level: 'critical',
              title: '必须修订',
              detail: '人工修改率不足。',
            },
          ],
        },
      },
    });

    const openModalButton = requireButtonByText('开始持续迭代');
    fireEvent.click(openModalButton);
    await waitFor(() => {
      expect(findButtonByText('开始')).toBeTruthy();
    });
    fireEvent.click(requireButtonByText('开始'));

    expect(mockRefs.streamStartMock).not.toHaveBeenCalled();
    expect(mockRefs.messageWarningMock).toHaveBeenCalledWith('必须先完成本章修订才能继续。');
  });

  test('starts continuous generation with full-auto options', async () => {
    renderWorkspace({
      workbenchHighlights: {
        ...workbenchHighlights,
        workflow_gate: {
          ...workbenchHighlights.workflow_gate!,
          allowed: false,
          status: 'blocked',
          summary: '必须先完成本章修订才能继续。',
          blocking_reasons: [
            {
              code: 'review_pending',
              level: 'critical',
              title: '待审',
              detail: '上一章尚未审定。',
            },
          ],
        },
      },
    });

    fireEvent.click(requireButtonByText('开始持续迭代'));
    await waitFor(() => {
      expect(screen.getByText('全自动模式')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('switch'));
    fireEvent.click(requireButtonByText('开始'));

    expect(mockRefs.streamStartMock).toHaveBeenCalledWith(1, {
      mode: 'generate',
      runMode: 'continuous',
      chapterNumber: 3,
      targetChapter: 12,
      targetWords: 3500,
      chapterLimit: 10,
      fullAutoMode: true,
    });
  });

  test('starts single chapter generation when generate next is clicked', () => {
    renderWorkspace();

    fireEvent.click(screen.getByRole('button', { name: '单章生成' }));

    expect(mockRefs.streamStartMock).toHaveBeenCalledWith(1, {
      mode: 'generate',
      runMode: 'single',
      chapterNumber: 3,
    });
  });
});
