import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Alert, Button, Empty, InputNumber, Modal, Progress, Space, Tabs, Tag, Typography } from 'antd';
import { PlayCircleOutlined, StopOutlined } from '@ant-design/icons';
import type { StreamState } from '../../hooks/useChapterStream';
import type {
  Chapter,
  Novel,
  WorkbenchHighlights,
} from './types';

const { Text } = Typography;

interface WritingCenterProps {
  novel: Novel | null;
  selectedChapter: Chapter | null;
  streamState: StreamState;
  highlights?: WorkbenchHighlights;
  onStartContinuous: (targetChapter: number) => void;
  onGenerateNext: () => void;
  onContinueCurrent: () => void;
  onRegenerateCurrent: () => void;
  onStop: () => void;
}

const modeLabel = {
  generate: '生成',
  continue: '续写',
  regenerate: '重写',
} as const;

type CenterTabKey = 'stream' | 'manuscript' | 'logs';

const centerPanelHeightClass = 'h-[min(34rem,calc(100vh-24rem))] min-h-[20rem]';

export const WritingCenter: React.FC<WritingCenterProps> = ({
  novel,
  selectedChapter,
  streamState,
  highlights,
  onStartContinuous,
  onGenerateNext,
  onContinueCurrent,
  onRegenerateCurrent,
  onStop,
}) => {
  const [activeTab, setActiveTab] = useState<CenterTabKey>('stream');
  const [showStartModal, setShowStartModal] = useState(false);
  const [targetChapterDraft, setTargetChapterDraft] = useState<number | null>(null);
  const textAreaRef = useRef<HTMLPreElement>(null);

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

  const handleOpenStartModal = () => {
    setTargetChapterDraft(defaultIterationTarget);
    setShowStartModal(true);
  };

  const handleConfirmStart = () => {
    if (!targetChapterDraft) return;
    onStartContinuous(targetChapterDraft);
    setShowStartModal(false);
  };

  if (!novel) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-slate-400">
        请先在首页选择一本书
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="border-b border-slate-100 px-5 py-4">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div className="min-w-0">
            <div className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Writing Desk</div>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <h2 className="text-xl font-semibold text-slate-800">
                {selectedChapter
                  ? `第 ${selectedChapter.chapter_number} 章 ${selectedChapter.title || ''}`.trim()
                  : `${novel.title} 工作台`}
              </h2>
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
            <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-slate-500">
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

        {streamState.runMode === 'continuous' && streamState.targetChapter ? (
          <div className="mt-4 rounded-[22px] border border-sky-100 bg-sky-50/80 px-4 py-3">
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

      <div className="flex-1 min-h-0 p-4">
        <div className="h-full min-h-0 rounded-[28px] border border-slate-200 bg-slate-50 p-4">
          <Tabs
            activeKey={activeTab}
            onChange={(key) => setActiveTab(key as CenterTabKey)}
            items={[
              {
                key: 'stream',
                label: '实时写作',
                children: (
                  <div className={`${centerPanelHeightClass} flex flex-col overflow-hidden rounded-[24px] border border-slate-200 bg-[#0f172a]`}>
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
                children: selectedContent ? (
                  <div className={`${centerPanelHeightClass} overflow-y-auto rounded-[24px] border border-slate-200 bg-white px-6 py-5`}>
                    <div className="mb-4 text-xs uppercase tracking-[0.2em] text-slate-400">Draft</div>
                    <pre className="whitespace-pre-wrap font-sans text-[15px] leading-8 text-slate-700">
                      {selectedContent}
                    </pre>
                  </div>
                ) : (
                  <div className={`${centerPanelHeightClass} flex items-center justify-center rounded-[24px] border border-dashed border-slate-200 bg-white`}>
                    <Empty description="当前章节还没有正文内容" />
                  </div>
                ),
              },
              {
                key: 'logs',
                label: '流程日志',
                children: (
                  <div className={`${centerPanelHeightClass} overflow-y-auto rounded-[24px] border border-slate-200 bg-white`}>
                    <div className="border-b border-slate-100 px-4 py-3 text-xs font-medium text-slate-500">
                      最新执行日志
                    </div>
                    {streamState.logs.length === 0 ? (
                      <div className="px-4 py-6 text-sm text-slate-400">等待任务启动...</div>
                    ) : (
                      streamState.logs.map((log, index) => (
                        <div
                          key={`${log.time}-${index}`}
                          className="border-b border-slate-100 px-4 py-3 text-sm text-slate-600 last:border-b-0"
                        >
                          <span className="mr-3 text-xs text-slate-400">[{log.time}]</span>
                          {log.message}
                        </div>
                      ))
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
            message="参考 PlotPilot 的托管写作流程"
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
