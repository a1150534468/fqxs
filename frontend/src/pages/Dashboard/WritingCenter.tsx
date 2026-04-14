import React, { useEffect, useRef } from 'react';
import { Button, Space, Tag, Typography } from 'antd';
import { PlayCircleOutlined, StopOutlined } from '@ant-design/icons';
import type { StreamState } from '../../hooks/useChapterStream';
import type { Novel } from './types';

const { Text } = Typography;

interface WritingCenterProps {
  novel: Novel | null;
  streamState: StreamState;
  onStart: () => void;
  onStop: () => void;
}

export const WritingCenter: React.FC<WritingCenterProps> = ({
  novel,
  streamState,
  onStart,
  onStop,
}) => {
  const textAreaRef = useRef<HTMLPreElement>(null);

  // Auto-scroll stream output to bottom
  useEffect(() => {
    if (textAreaRef.current) {
      textAreaRef.current.scrollTop = textAreaRef.current.scrollHeight;
    }
  }, [streamState.streamText]);

  if (!novel) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400 text-sm">
        请先在首页选择一本书
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full gap-3">
      {/* Controls */}
      <div className="flex items-center gap-3 px-1">
        <Space>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            disabled={streamState.isRunning}
            onClick={onStart}
          >
            启动写作
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
        <Tag color={streamState.isRunning ? 'processing' : 'default'}>
          {streamState.isRunning
            ? `正在写第 ${streamState.currentChapter ?? '?'} 章...`
            : '空闲'}
        </Tag>
        {streamState.error && (
          <Text type="danger" className="text-xs">{streamState.error}</Text>
        )}
      </div>

      {/* Stream text output */}
      <div className="flex-1 min-h-0 rounded-lg border border-gray-200 bg-gray-50 overflow-hidden">
        <pre
          ref={textAreaRef}
          className="h-full overflow-y-auto p-3 text-sm text-gray-800 whitespace-pre-wrap font-sans leading-relaxed"
        >
          {streamState.streamText || (
            <span className="text-gray-300">启动写作后，章节内容将实时输出在此处...</span>
          )}
        </pre>
      </div>

      {/* Live log panel */}
      <div className="rounded-lg border border-gray-100 bg-white overflow-hidden" style={{ maxHeight: 160 }}>
        <div className="px-3 py-1.5 border-b border-gray-100 bg-gray-50 text-xs text-gray-500 font-medium">
          实时日志
        </div>
        <div className="overflow-y-auto" style={{ maxHeight: 120 }}>
          {streamState.logs.length === 0 ? (
            <div className="px-3 py-2 text-xs text-gray-300">等待任务启动...</div>
          ) : (
            streamState.logs.map((log, i) => (
              <div key={i} className="px-3 py-1 text-xs text-gray-600 border-b border-gray-50 last:border-0">
                <span className="text-gray-400 mr-2">[{log.time}]</span>
                {log.message}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
