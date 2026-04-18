import { useCallback, useEffect, useState } from 'react';
import { useAuthStore } from '../store/authStore';

const WS_BASE = (() => {
  const base = import.meta.env.VITE_WS_URL || 'ws://localhost:8001/ws/generate-setting';
  return base.replace(/\/ws\/.*$/, '');
})();

export interface StreamState {
  isRunning: boolean;
  streamText: string;
  logs: { time: string; message: string }[];
  startChapter: number | null;
  currentChapter: number | null;
  targetChapter: number | null;
  completedChapters: number;
  error: string | null;
  sessionId: string | null;
  mode: ChapterStreamMode | null;
  runMode: ChapterStreamRunMode;
  stopRequested: boolean;
  lastSavedChapterId: number | null;
  lastSavedEventId: string | null;
  lastCompletedSessionId: string | null;
}

export type ChapterStreamMode = 'generate' | 'continue' | 'regenerate';
export type ChapterStreamRunMode = 'single' | 'continuous';

export interface StartStreamOptions {
  mode?: ChapterStreamMode;
  runMode?: ChapterStreamRunMode;
  chapterNumber?: number | null;
  targetChapter?: number | null;
  chapterTitle?: string | null;
  currentContent?: string;
  continueLength?: number;
}

export interface ActiveStreamRecord {
  projectId: number;
  state: StreamState;
}

const DEFAULT_STATE = (): StreamState => ({
  isRunning: false,
  streamText: '',
  logs: [],
  startChapter: null,
  currentChapter: null,
  targetChapter: null,
  completedChapters: 0,
  error: null,
  sessionId: null,
  mode: null,
  runMode: 'single',
  stopRequested: false,
  lastSavedChapterId: null,
  lastSavedEventId: null,
  lastCompletedSessionId: null,
});

interface StreamEntry {
  ws: WebSocket | null;
  state: StreamState;
  listeners: Set<(s: StreamState) => void>;
}

// Module-level map so streams survive component unmount/remount
const streamMap = new Map<number, StreamEntry>();
const registryListeners = new Set<() => void>();

function notifyRegistryListeners() {
  registryListeners.forEach((listener) => listener());
}

function getEntry(projectId: number): StreamEntry {
  if (!streamMap.has(projectId)) {
    streamMap.set(projectId, { ws: null, state: DEFAULT_STATE(), listeners: new Set() });
  }
  return streamMap.get(projectId)!;
}

function setEntryState(projectId: number, patch: Partial<StreamState>) {
  const entry = streamMap.get(projectId);
  if (!entry) return;
  const previousState = entry.state;
  entry.state = { ...entry.state, ...patch };
  entry.listeners.forEach((fn) => fn(entry.state));
  if (
    previousState.isRunning !== entry.state.isRunning
    || previousState.currentChapter !== entry.state.currentChapter
    || previousState.mode !== entry.state.mode
    || previousState.runMode !== entry.state.runMode
    || previousState.targetChapter !== entry.state.targetChapter
    || previousState.completedChapters !== entry.state.completedChapters
    || previousState.sessionId !== entry.state.sessionId
  ) {
    notifyRegistryListeners();
  }
}

function appendLog(projectId: number, message: string, time?: string) {
  const entry = streamMap.get(projectId);
  if (!entry) return;
  const t = time || new Date().toLocaleTimeString('zh-CN', { hour12: false });
  setEntryState(projectId, {
    logs: [{ time: t, message }, ...entry.state.logs].slice(0, 20),
  });
}

function appendStreamText(projectId: number, chunk: string) {
  const entry = streamMap.get(projectId);
  if (!entry) return;
  setEntryState(projectId, {
    streamText: `${entry.state.streamText}${chunk}`,
  });
}

function appendStreamHeader(projectId: number, chapterNumber: number, targetChapter?: number | null) {
  const entry = streamMap.get(projectId);
  if (!entry) return;
  const header = [
    entry.state.streamText ? '\n\n' : '',
    `\n========== 第 ${chapterNumber} 章`,
    targetChapter ? ` / 目标第 ${targetChapter} 章` : '',
    ' ==========\n\n',
  ].join('');
  setEntryState(projectId, {
    streamText: `${entry.state.streamText}${header}`,
  });
}

function modeLabel(mode: ChapterStreamMode | null | undefined) {
  return (
    {
      generate: '生成',
      continue: '续写',
      regenerate: '重写',
    } as Record<ChapterStreamMode, string>
  )[mode || 'generate'];
}

export function listActiveChapterStreams(): ActiveStreamRecord[] {
  return Array.from(streamMap.entries())
    .filter(([, entry]) => entry.state.isRunning)
    .map(([projectId, entry]) => ({ projectId, state: entry.state }));
}

export function useActiveChapterStreams() {
  const [activeStreams, setActiveStreams] = useState<ActiveStreamRecord[]>(() =>
    listActiveChapterStreams()
  );

  useEffect(() => {
    const refresh = () => setActiveStreams(listActiveChapterStreams());
    registryListeners.add(refresh);
    return () => {
      registryListeners.delete(refresh);
    };
  }, []);

  return activeStreams;
}

export function useChapterStream(projectId: number | null) {
  const [state, setState] = useState<StreamState>(() =>
    projectId != null ? getEntry(projectId).state : DEFAULT_STATE()
  );

  useEffect(() => {
    if (projectId == null) {
      setState(DEFAULT_STATE());
      return;
    }
    const entry = getEntry(projectId);
    setState(entry.state);
    entry.listeners.add(setState);
    return () => {
      entry.listeners.delete(setState);
    };
  }, [projectId]);

  const start = useCallback((pid: number, options?: StartStreamOptions) => {
    const entry = getEntry(pid);
    if (entry.ws) { entry.ws.close(); entry.ws = null; }
    const sessionId = `${pid}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    const mode = options?.mode ?? 'generate';
    const runMode = options?.runMode ?? 'single';
    const currentChapter = options?.chapterNumber ?? null;
    const targetChapter = options?.targetChapter ?? currentChapter;
    setEntryState(pid, {
      ...DEFAULT_STATE(),
      isRunning: true,
      sessionId,
      mode,
      runMode,
      startChapter: currentChapter,
      currentChapter,
      targetChapter: targetChapter ?? null,
    });

    const ws = new WebSocket(`${WS_BASE}/ws/generate-chapter`);
    entry.ws = ws;

    ws.onopen = () => {
      if (entry.ws !== ws) { ws.close(); return; }
      const token = useAuthStore.getState().token;
      ws.send(JSON.stringify({
        action: 'start',
        token: token || '',
        project_id: pid,
        session_id: sessionId,
        mode,
        run_mode: runMode,
        chapter_number: options?.chapterNumber ?? undefined,
        target_chapter: options?.targetChapter ?? undefined,
        chapter_title: options?.chapterTitle ?? undefined,
        current_content: options?.currentContent ?? '',
        continue_length: options?.continueLength ?? undefined,
      }));
      appendLog(
        pid,
        runMode === 'continuous'
          ? `连接已建立，准备持续迭代到第 ${targetChapter ?? '?'} 章...`
          : `连接已建立，正在启动${modeLabel(mode)}...`,
      );
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        const currentSessionId = streamMap.get(pid)?.state.sessionId;
        if (msg.session_id && currentSessionId && msg.session_id !== currentSessionId) {
          return;
        }

        const messageMode = (msg.mode || mode) as ChapterStreamMode;
        const messageRunMode = (msg.run_mode || runMode) as ChapterStreamRunMode;
        const messageChapter = typeof msg.chapter_number === 'number'
          ? msg.chapter_number
          : streamMap.get(pid)?.state.currentChapter;
        const messageTargetChapter = typeof msg.target_chapter === 'number'
          ? msg.target_chapter
          : streamMap.get(pid)?.state.targetChapter;

        if (msg.type === 'chunk') {
          setEntryState(pid, {
            currentChapter: messageChapter ?? null,
            targetChapter: messageTargetChapter ?? null,
            mode: messageMode,
            runMode: messageRunMode,
            startChapter: streamMap.get(pid)?.state.startChapter ?? currentChapter,
          });
          appendStreamText(pid, msg.content);
        } else if (msg.type === 'log') {
          setEntryState(pid, {
            currentChapter: messageChapter ?? null,
            targetChapter: messageTargetChapter ?? null,
            mode: messageMode,
            runMode: messageRunMode,
            startChapter: streamMap.get(pid)?.state.startChapter ?? currentChapter,
          });
          appendLog(pid, msg.message, msg.timestamp);
        } else if (msg.type === 'status') {
          setEntryState(pid, {
            currentChapter: messageChapter ?? null,
            targetChapter: messageTargetChapter ?? null,
            mode: messageMode,
            runMode: messageRunMode,
            startChapter: streamMap.get(pid)?.state.startChapter ?? currentChapter,
          });
          if (msg.status_kind === 'chapter_start' && typeof messageChapter === 'number') {
            appendStreamHeader(pid, messageChapter, messageTargetChapter);
          }
          appendLog(pid, msg.message);
        } else if (msg.type === 'chapter_saved') {
          setEntryState(pid, {
            currentChapter: messageChapter ?? null,
            targetChapter: messageTargetChapter ?? null,
            mode: messageMode,
            runMode: messageRunMode,
            startChapter: streamMap.get(pid)?.state.startChapter ?? currentChapter,
            completedChapters: typeof msg.completed_chapters === 'number'
              ? msg.completed_chapters
              : (streamMap.get(pid)?.state.completedChapters || 0) + 1,
            lastSavedChapterId: msg.chapter_id ?? null,
            lastSavedEventId: msg.save_event_id ?? `${sessionId}-${msg.chapter_id ?? 'saved'}-${Date.now()}`,
            error: null,
            stopRequested: false,
          });
          appendLog(
            pid,
            messageRunMode === 'continuous' && (!messageTargetChapter || msg.chapter_number < messageTargetChapter)
              ? `第 ${msg.chapter_number} 章已归档，继续迭代`
              : `第 ${msg.chapter_number} 章已归档`,
          );
        } else if (msg.type === 'done') {
          const stopReason = String(msg.stop_reason || '');
          const finalMessage = typeof msg.message === 'string' && msg.message
            ? msg.message
            : (
              stopReason === 'target_reached'
                ? `已到达目标章节，第 ${msg.chapter_number ?? messageChapter ?? '?'} 章后自动停止`
                : stopReason === 'stopped'
                  ? '已停止当前生成任务'
                  : `${modeLabel(messageMode)}完成`
            );
          setEntryState(pid, {
            isRunning: false,
            currentChapter: msg.chapter_number ?? null,
            targetChapter: messageTargetChapter ?? null,
            error: null,
            mode: messageMode,
            runMode: messageRunMode,
            startChapter: streamMap.get(pid)?.state.startChapter ?? currentChapter,
            completedChapters: typeof msg.completed_chapters === 'number'
              ? msg.completed_chapters
              : streamMap.get(pid)?.state.completedChapters || 0,
            lastSavedChapterId: msg.chapter_id ?? null,
            lastCompletedSessionId: msg.session_id ?? sessionId,
            stopRequested: false,
          });
          appendLog(pid, finalMessage);
          if (entry.ws === ws) { entry.ws = null; }
          ws.close();
        } else if (msg.type === 'error') {
          setEntryState(pid, {
            isRunning: false,
            error: msg.message,
            currentChapter: messageChapter ?? null,
            targetChapter: messageTargetChapter ?? null,
            mode: messageMode,
            runMode: messageRunMode,
            startChapter: streamMap.get(pid)?.state.startChapter ?? currentChapter,
            stopRequested: false,
          });
          appendLog(pid, `错误：${msg.message}`);
          if (entry.ws === ws) { entry.ws = null; }
          ws.close();
        }
      } catch (e) {
        console.warn('[useChapterStream] parse error', e);
      }
    };

    ws.onerror = () => {
      setEntryState(pid, {
        isRunning: false,
        error: 'WebSocket 连接失败',
        stopRequested: false,
      });
      if (entry.ws === ws) entry.ws = null;
    };

    ws.onclose = () => {
      if (entry.ws === ws) entry.ws = null;
      const e = streamMap.get(pid);
      if (e?.state.isRunning && e.state.sessionId === sessionId) {
        setEntryState(pid, { isRunning: false, stopRequested: false });
      }
    };
  }, []);

  const stop = useCallback((pid: number) => {
    const entry = streamMap.get(pid);
    if (!entry?.ws) return;
    try {
      entry.ws.send(JSON.stringify({ action: 'stop', session_id: entry.state.sessionId }));
      setEntryState(pid, { stopRequested: true });
      appendLog(pid, '已发送停止指令');
    } catch (e) {
      console.warn('[useChapterStream] stop send failed', e);
    }
  }, []);

  const getState = useCallback((pid: number): StreamState => {
    return streamMap.get(pid)?.state ?? DEFAULT_STATE();
  }, []);

  // Cleanup all on page unload
  useEffect(() => {
    const cleanup = () => {
      streamMap.forEach((e) => { e.ws?.close(); });
    };
    window.addEventListener('beforeunload', cleanup);
    return () => window.removeEventListener('beforeunload', cleanup);
  }, []);

  return { state, start, stop, getState };
}
