import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Alert, Button, Empty, Input, InputNumber, Modal, Progress, Space, Tabs, Tag, Typography } from 'antd';
import { LeftOutlined, PlayCircleOutlined, RightOutlined, StopOutlined } from '@ant-design/icons';
import type { StreamState } from '../../hooks/useChapterStream';
import type {
  Chapter,
  Novel,
  WorkbenchHighlights,
} from './types';

const { Text } = Typography;

interface WritingCenterProps {
  surface?: 'cockpit' | 'dashboard' | 'intelligence';
  novel: Novel | null;
  selectedChapter: Chapter | null;
  streamState: StreamState;
  highlights?: WorkbenchHighlights;
  canPrevChapter: boolean;
  canNextChapter: boolean;
  onPrevChapter: () => void;
  onNextChapter: () => void;
  onStartContinuous: (targetChapter: number) => void;
  onGenerateNext: () => void;
  onContinueCurrent: () => void;
  onRegenerateCurrent: () => void;
  onSaveChapterContent: (
    chapterId: number,
    content: string,
    options?: { silent?: boolean }
  ) => Promise<void>;
  onStop: () => void;
}

const modeLabel = {
  generate: '生成',
  continue: '续写',
  regenerate: '重写',
} as const;

type CenterTabKey = 'stream' | 'manuscript' | 'logs';

export const WritingCenter: React.FC<WritingCenterProps> = ({
  surface = 'cockpit',
  novel,
  selectedChapter,
  streamState,
  highlights,
  canPrevChapter,
  canNextChapter,
  onPrevChapter,
  onNextChapter,
  onStartContinuous,
  onGenerateNext,
  onContinueCurrent,
  onRegenerateCurrent,
  onSaveChapterContent,
  onStop,
}) => {
  const [activeTab, setActiveTab] = useState<CenterTabKey>('stream');
  const [showStartModal, setShowStartModal] = useState(false);
  const [targetChapterDraft, setTargetChapterDraft] = useState<number | null>(null);
  const [draftContent, setDraftContent] = useState('');
  const [draftBaseline, setDraftBaseline] = useState('');
  const [savingDraft, setSavingDraft] = useState(false);
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null);
  const textAreaRef = useRef<HTMLPreElement>(null);
  const lastChapterIdRef = useRef<number | null>(null);

  useEffect(() => {
    if (textAreaRef.current) {
      textAreaRef.current.scrollTop = textAreaRef.current.scrollHeight;
    }
  }, [streamState.streamText]);

  useEffect(() => {
    if (streamState.isRunning) {
      setActiveTab('stream');
    }
  }, [streamState.isRunning]);

  const nextChapterNumber = (novel?.current_chapter ?? 0) + 1;
  const defaultIterationTarget = useMemo(
    () => Math.max(nextChapterNumber, novel?.target_chapters ?? nextChapterNumber),
    [nextChapterNumber, novel?.target_chapters],
  );

  useEffect(() => {
    setTargetChapterDraft(defaultIterationTarget);
  }, [defaultIterationTarget, novel?.id]);

  const selectedContent = selectedChapter?.final_content || selectedChapter?.raw_content || '';
  const contentDirty = draftContent !== draftBaseline;
  const draftWordCount = useMemo(
    () => draftContent.replace(/\s/g, '').length,
    [draftContent],
  );
  const draftLineCount = useMemo(
    () => (draftContent ? draftContent.split('\n').length : 0),
    [draftContent],
  );
  const draftParagraphCount = useMemo(
    () => (draftContent ? draftContent.split(/\n+/).filter((item) => item.trim()).length : 0),
    [draftContent],
  );
  const estimatedModificationRate = useMemo(() => {
    const original = (selectedChapter?.raw_content || '').replace(/\s/g, '');
    const current = draftContent.replace(/\s/g, '');
    if (!original) return null;

    const compareLength = Math.min(original.length, current.length);
    let sameCount = 0;
    for (let index = 0; index < compareLength; index += 1) {
      if (original[index] === current[index]) {
        sameCount += 1;
      }
    }

    const denominator = Math.max(original.length, current.length, 1);
    return Math.max(0, Math.round((1 - (sameCount / denominator)) * 100));
  }, [draftContent, selectedChapter?.raw_content]);
  const workflowGate = highlights?.workflow_gate;
  const workflowGateAlertType = workflowGate?.status === 'blocked'
    ? 'error'
    : workflowGate?.status === 'warning'
      ? 'warning'
      : 'info';
  const reviewLabel = selectedChapter?.review_status === 'approved'
    ? '已定稿'
    : selectedChapter?.review_status === 'revise'
      ? '需修订'
      : '待审';
  const actionLabel = modeLabel[streamState.mode || 'generate'];

  const streamPlaceholder = highlights?.focus_card?.mission || highlights?.recommended_focus
    || '选择一个章节后可查看正文，也可以直接生成下一章。';
  const loopStartChapter = streamState.startChapter ?? nextChapterNumber;

  const continuousProgressPercent = useMemo(() => {
    if (streamState.runMode !== 'continuous' || !streamState.targetChapter) return 0;
    const totalSteps = Math.max(streamState.targetChapter - loopStartChapter + 1, 1);
    const finishedSteps = Math.min(streamState.completedChapters, totalSteps);
    return Math.min(100, Math.round((finishedSteps / totalSteps) * 100));
  }, [
    loopStartChapter,
    streamState.completedChapters,
    streamState.runMode,
    streamState.targetChapter,
  ]);
  const isCockpit = surface === 'cockpit';
  const panelBodyClass = 'flex h-full min-h-0 flex-col';

  const handleOpenStartModal = () => {
    setTargetChapterDraft(defaultIterationTarget);
    setShowStartModal(true);
  };

  const handleConfirmStart = () => {
    if (!targetChapterDraft) return;
    onStartContinuous(targetChapterDraft);
    setShowStartModal(false);
  };

  useEffect(() => {
    const currentChapterId = selectedChapter?.id ?? null;
    const chapterChanged = currentChapterId !== lastChapterIdRef.current;

    if (chapterChanged) {
      lastChapterIdRef.current = currentChapterId;
      setDraftContent(selectedContent);
      setDraftBaseline(selectedContent);
      setLastSavedAt(null);
      return;
    }

    if (selectedContent !== draftBaseline) {
      setDraftBaseline(selectedContent);
      if (!contentDirty && !savingDraft) {
        setDraftContent(selectedContent);
      }
    }
  }, [
    contentDirty,
    draftBaseline,
    savingDraft,
    selectedChapter?.id,
    selectedContent,
  ]);

  const handleSaveDraft = async (silent?: boolean) => {
    if (!selectedChapter || !contentDirty || savingDraft) return;
    setSavingDraft(true);
    try {
      await onSaveChapterContent(selectedChapter.id, draftContent, { silent });
      setDraftBaseline(draftContent);
      setLastSavedAt(new Date().toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
      }));
    } catch {
      // WorkspacePage already surfaces the error message.
    } finally {
      setSavingDraft(false);
    }
  };

  useEffect(() => {
    if (!selectedChapter || !contentDirty || savingDraft || streamState.isRunning) return undefined;
    const timeoutId = window.setTimeout(() => {
      void handleSaveDraft(true);
    }, 3000);
    return () => window.clearTimeout(timeoutId);
  }, [
    contentDirty,
    draftContent,
    savingDraft,
    selectedChapter,
    streamState.isRunning,
  ]);

  if (!novel) {
    return (
      <div className="flex h-full items-center justify-center bg-[color:var(--app-shell)] text-sm text-slate-400">
        请先在首页选择一本书
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col bg-[color:var(--app-shell)]">
      <div className={`border-b border-[var(--app-divider)] bg-[color:var(--app-surface)] px-5 ${isCockpit ? 'py-3' : 'py-3.5'}`}>
        {workflowGate && workflowGate.status !== 'ok' ? (
          <Alert
            type={workflowGateAlertType}
            showIcon
            className={isCockpit ? 'mb-3' : 'mb-4'}
            title={workflowGate.status === 'blocked' ? '工作流闸门未通过' : '工作流提醒'}
            description={workflowGate.summary}
          />
        ) : null}
        <div className={`flex flex-col ${isCockpit ? 'gap-2.5' : 'gap-3.5'}`}>
          <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
            <div className="min-w-0">
              <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Autopilot</div>
              <div className={`mt-1.5 flex flex-wrap items-center gap-2 ${isCockpit ? 'xl:gap-3' : ''}`}>
                <h2 className={`${isCockpit ? 'text-[1rem]' : 'text-[1.05rem]'} font-semibold text-slate-800`}>
                  {selectedChapter
                    ? `第 ${selectedChapter.chapter_number} 章 ${selectedChapter.title || ''}`.trim()
                    : `${novel.title} · 全托管驾驶`}
                </h2>
                {selectedChapter ? (
                  <Space size={[6, 6]} wrap>
                    <Button
                      size="small"
                      icon={<LeftOutlined />}
                      disabled={!canPrevChapter || streamState.isRunning}
                      onClick={onPrevChapter}
                    >
                      上一章
                    </Button>
                    <Button
                      size="small"
                      icon={<RightOutlined />}
                      disabled={!canNextChapter || streamState.isRunning}
                      onClick={onNextChapter}
                    >
                      下一章
                    </Button>
                  </Space>
                ) : null}
                <Tag color={streamState.isRunning ? 'processing' : 'default'}>
                  {streamState.isRunning
                    ? (
                      streamState.runMode === 'continuous'
                        ? `持续迭代中 · 第 ${streamState.currentChapter ?? highlights?.focus_chapter_number ?? '?'} 章`
                        : `正在${actionLabel}第 ${streamState.currentChapter ?? highlights?.focus_chapter_number ?? '?'} 章`
                    )
                    : '待命'}
                </Tag>
                {highlights?.nearest_plot_point && (
                  <Tag color="purple">
                    最近情节点：第 {highlights.nearest_plot_point.chapter_number} 章
                  </Tag>
                )}
              </div>
              <div className={`mt-1.5 flex flex-wrap items-center ${isCockpit ? 'gap-x-4 gap-y-2 text-[13px]' : 'gap-3 text-sm'} text-slate-500`}>
                <span>
                  目标章节：
                  {streamState.runMode === 'continuous' && streamState.targetChapter
                    ? streamState.targetChapter
                    : (highlights?.focus_chapter_number ?? novel.current_chapter ?? 1)}
                </span>
                <span>当前正文：{selectedContent ? `${selectedContent.length.toLocaleString()} 字` : '暂无正文'}</span>
                {streamState.runMode === 'continuous' && streamState.targetChapter ? (
                  <span>
                    迭代进度：{streamState.completedChapters} / {Math.max(streamState.targetChapter - loopStartChapter + 1, 0)}
                  </span>
                ) : null}
                {selectedChapter ? (
                  <span>
                    人工稿：{savingDraft ? '保存中' : contentDirty ? '有未保存修改' : '已同步'}
                  </span>
                ) : null}
                {selectedChapter ? <span>审阅状态：{reviewLabel}</span> : null}
                {estimatedModificationRate != null ? (
                  <span>
                    预估修改率 {estimatedModificationRate}%
                  </span>
                ) : null}
                {streamState.error && <Text type="danger">{streamState.error}</Text>}
              </div>
            </div>

            <Space wrap size={[8, 8]}>
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                disabled={streamState.isRunning}
                onClick={handleOpenStartModal}
              >
                开始持续迭代
              </Button>
              <Button
                disabled={streamState.isRunning}
                onClick={onGenerateNext}
              >
                单章生成
              </Button>
              <Button
                disabled={streamState.isRunning || !selectedChapter || !selectedContent}
                onClick={onContinueCurrent}
              >
                续写当前章
              </Button>
              <Button
                disabled={streamState.isRunning || !selectedChapter}
                onClick={onRegenerateCurrent}
              >
                重写当前章
              </Button>
              <Button
                danger
                icon={<StopOutlined />}
                disabled={!streamState.isRunning}
                onClick={onStop}
              >
                停止
              </Button>
            </Space>
          </div>

        </div>

        {streamState.runMode === 'continuous' && streamState.targetChapter ? (
          <div className={`${isCockpit ? 'mt-3' : 'mt-4'} rounded-[22px] border border-sky-100 bg-sky-50/80 px-4 py-3`}>
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <div className="text-xs font-medium uppercase tracking-[0.2em] text-sky-500">
                  Continuous Run
                </div>
                <div className="mt-1 text-sm font-medium text-slate-800">
                  从第 {loopStartChapter} 章起连续写到第 {streamState.targetChapter} 章
                </div>
                <div className="mt-1 text-xs text-slate-500">
                  已完成 {streamState.completedChapters} 章
                  {streamState.stopRequested ? '，停止指令已发出，当前章收尾后结束' : ''}
                </div>
              </div>
              <div className="w-full max-w-[18rem]">
                <Progress percent={continuousProgressPercent} showInfo={false} strokeColor="#0ea5e9" />
              </div>
            </div>
          </div>
        ) : null}
      </div>

      <div className={`flex-1 min-h-0 ${isCockpit ? 'p-3.5' : 'p-4'}`}>
        <div className="flex h-full min-h-0 flex-col rounded-[18px] border border-[var(--app-border)] bg-[color:var(--app-surface)] p-4 shadow-[var(--app-shadow-sm)]">
          <Tabs
            className="workspace-tabs workspace-tabs--editor flex-1 min-h-0"
            activeKey={activeTab}
            onChange={(key) => setActiveTab(key as CenterTabKey)}
            items={[
              {
                key: 'stream',
                label: '实时写作',
                children: (
                  <div className={`${panelBodyClass} overflow-hidden rounded-[18px] border border-slate-200 bg-[#0f172a]`}>
                    <div className="flex items-center justify-between border-b border-slate-700 px-4 py-3">
                      <div>
                        <div className="text-sm font-medium text-slate-100">AI 输出面板</div>
                        <div className="text-xs text-slate-400">内容流、阶段日志和中断控制都在这里完成</div>
                      </div>
                      <Tag color={streamState.isRunning ? 'processing' : 'default'} className="mr-0">
                        {streamState.isRunning ? '流式输出中' : '暂无任务'}
                      </Tag>
                    </div>
                    <pre
                      ref={textAreaRef}
                      className="flex-1 overflow-y-auto px-4 py-4 font-sans text-sm leading-7 text-slate-100 whitespace-pre-wrap"
                    >
                      {streamState.streamText || (
                        <span className="text-slate-500">
                          {streamPlaceholder}
                        </span>
                      )}
                    </pre>
                  </div>
                ),
              },
              {
                key: 'manuscript',
                label: '当前正文',
                children: selectedChapter ? (
                  <div className={`${panelBodyClass} overflow-hidden rounded-[18px] border border-slate-200 bg-white`}>
                    <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-4 py-3">
                      <div>
                        <div className="text-sm font-medium text-slate-800">章节编辑器</div>
                        <div className="text-xs text-slate-400">
                          保存到人工审核稿；支持 Ctrl/Cmd + S，停顿 3 秒自动保存
                        </div>
                      </div>
                      <Space size={[8, 8]} wrap>
                        <Tag color={contentDirty ? 'orange' : 'green'} className="mr-0">
                          {contentDirty ? '未保存修改' : '已同步'}
                        </Tag>
                        <Tag color="blue" className="mr-0">
                          {draftWordCount.toLocaleString()} 字
                        </Tag>
                        {lastSavedAt ? (
                          <Tag color="default" className="mr-0">
                            已保存 {lastSavedAt}
                          </Tag>
                        ) : null}
                        <Button
                          type="primary"
                          size="small"
                          disabled={!contentDirty || streamState.isRunning}
                          loading={savingDraft}
                          onClick={() => { void handleSaveDraft(); }}
                        >
                          保存正文
                        </Button>
                      </Space>
                    </div>

                    {streamState.isRunning ? (
                      <div className="border-b border-amber-100 bg-amber-50 px-4 py-2 text-xs text-amber-700">
                        生成任务运行中，正文编辑暂时锁定，避免覆盖流式结果。
                      </div>
                    ) : null}
                    {estimatedModificationRate != null && estimatedModificationRate < 15 ? (
                      <div className="border-b border-rose-100 bg-rose-50 px-4 py-2 text-xs text-rose-700">
                        当前人工稿相对原稿的预估修改率为 {estimatedModificationRate}% ，低于 15%，发布前建议继续人工润色。
                      </div>
                    ) : null}

                    <div className="flex-1 min-h-0 overflow-hidden p-4">
                      <Input.TextArea
                        value={draftContent}
                        disabled={streamState.isRunning}
                        onChange={(event) => setDraftContent(event.target.value)}
                        onKeyDown={(event) => {
                          if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') {
                            event.preventDefault();
                            void handleSaveDraft();
                          }
                        }}
                        className="h-full"
                        style={{ height: '100%', resize: 'none' }}
                        placeholder="当前章节正文会显示在这里，可直接人工润色后保存。"
                      />
                    </div>

                    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 px-4 py-3 text-xs text-slate-500">
                      <Space size={[12, 8]} wrap>
                        <span>字数 {draftWordCount.toLocaleString()}</span>
                        <span>段落 {draftParagraphCount}</span>
                        <span>行数 {draftLineCount}</span>
                        <span>状态 {selectedChapter.status || 'draft'}</span>
                        <span>审核 {reviewLabel}</span>
                        {estimatedModificationRate != null ? (
                          <span>修改率 {estimatedModificationRate}%</span>
                        ) : null}
                      </Space>
                      <span>{lastSavedAt ? `最近保存 ${lastSavedAt}` : '尚未保存人工稿'}</span>
                    </div>
                  </div>
                ) : (
                  <div className={`${panelBodyClass} items-center justify-center rounded-[18px] border border-dashed border-slate-200 bg-white`}>
                    <Empty description="当前章节还没有正文内容" />
                  </div>
                ),
              },
              {
                key: 'logs',
                label: '流程日志',
                children: (
                  <div className={`${panelBodyClass} overflow-hidden rounded-[18px] border border-slate-200 bg-white`}>
                    <div className="shrink-0 border-b border-slate-100 px-4 py-3 text-xs font-medium text-slate-500">
                      最新执行日志
                    </div>
                    {streamState.logs.length === 0 ? (
                      <div className="flex-1 overflow-y-auto px-4 py-6 text-sm text-slate-400">等待任务启动...</div>
                    ) : (
                      <div className="flex-1 overflow-y-auto">
                        {streamState.logs.map((log, index) => (
                          <div
                            key={`${log.time}-${index}`}
                            className="border-b border-slate-100 px-4 py-3 text-sm text-slate-600 last:border-b-0"
                          >
                            <span className="mr-3 text-xs text-slate-400">[{log.time}]</span>
                            {log.message}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ),
              },
            ]}
          />
        </div>
      </div>

      <Modal
        title="开始持续迭代"
        open={showStartModal}
        onOk={handleConfirmStart}
        onCancel={() => setShowStartModal(false)}
        okText="开始"
        cancelText="取消"
        okButtonProps={{
          disabled: !targetChapterDraft || targetChapterDraft < nextChapterNumber,
        }}
      >
        <div className="space-y-4 pt-2">
          <Alert
            type="info"
            showIcon
            description="开始后会持续生成后续章节，直到你手动点停止，或者自动迭代到设定的目标章节。"
          />
          <div className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
            <div>当前已写到：第 {novel.current_chapter ?? 0} 章</div>
            <div className="mt-1">本次将从：第 {nextChapterNumber} 章 开始连续生成</div>
          </div>
          <div>
            <div className="mb-2 text-sm font-medium text-slate-700">自动停止章节</div>
            <InputNumber
              min={nextChapterNumber}
              max={9999}
              value={targetChapterDraft}
              onChange={(value) => setTargetChapterDraft(typeof value === 'number' ? value : nextChapterNumber)}
              className="w-full"
            />
            <div className="mt-2 text-xs text-slate-400">
              达到目标章节后会自动停止；中途点“停止”则在当前章收尾后结束。
            </div>
          </div>
        </div>
      </Modal>
    </div>
  );
};
