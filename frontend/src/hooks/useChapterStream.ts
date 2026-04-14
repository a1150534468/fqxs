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
  currentChapter: number | null;
  error: string | null;
}

const DEFAULT_STATE = (): StreamState => ({
  isRunning: false,
  streamText: '',
  logs: [],
  currentChapter: null,
  error: null,
});

interface StreamEntry {
  ws: WebSocket | null;
  state: StreamState;
  listeners: Set<(s: StreamState) => void>;
}

// Module-level map so streams survive component unmount/remount
const streamMap = new Map<number, StreamEntry>();

function getEntry(projectId: number): StreamEntry {
  if (!streamMap.has(projectId)) {
    streamMap.set(projectId, { ws: null, state: DEFAULT_STATE(), listeners: new Set() });
  }
  return streamMap.get(projectId)!;
}

function setEntryState(projectId: number, patch: Partial<StreamState>) {
  const entry = streamMap.get(projectId);
  if (!entry) return;
  entry.state = { ...entry.state, ...patch };
  entry.listeners.forEach((fn) => fn(entry.state));
}

function appendLog(projectId: number, message: string, time?: string) {
  const entry = streamMap.get(projectId);
  if (!entry) return;
  const t = time || new Date().toLocaleTimeString('zh-CN', { hour12: false });
  setEntryState(projectId, {
    logs: [{ time: t, message }, ...entry.state.logs].slice(0, 20),
  });
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

  const start = useCallback((pid: number) => {
    const entry = getEntry(pid);
    // Close existing connection
    if (entry.ws) { entry.ws.close(); entry.ws = null; }
    setEntryState(pid, { ...DEFAULT_STATE(), isRunning: true });

    const ws = new WebSocket(`${WS_BASE}/ws/generate-chapter`);
    entry.ws = ws;

    ws.onopen = () => {
      if (entry.ws !== ws) { ws.close(); return; }
      const token = useAuthStore.getState().token;
      ws.send(JSON.stringify({ action: 'start', token: token || '', project_id: pid }));
      appendLog(pid, '连接已建立，正在启动写作...');
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'chunk') {
          setEntryState(pid, { streamText: entry.state.streamText + msg.content });
        } else if (msg.type === 'log') {
          appendLog(pid, msg.message, msg.timestamp);
        } else if (msg.type === 'status') {
          appendLog(pid, msg.message);
        } else if (msg.type === 'done') {
          setEntryState(pid, { isRunning: false, currentChapter: msg.chapter_number ?? null });
          appendLog(pid, `写作完成，第 ${msg.chapter_number} 章已保存`);
          if (entry.ws === ws) { entry.ws = null; }
          ws.close();
        } else if (msg.type === 'error') {
          setEntryState(pid, { isRunning: false, error: msg.message });
          appendLog(pid, `错误：${msg.message}`);
          if (entry.ws === ws) { entry.ws = null; }
          ws.close();
        }
      } catch (e) {
        console.warn('[useChapterStream] parse error', e);
      }
    };

    ws.onerror = () => {
      setEntryState(pid, { isRunning: false, error: 'WebSocket 连接失败' });
      if (entry.ws === ws) entry.ws = null;
    };

    ws.onclose = () => {
      if (entry.ws === ws) entry.ws = null;
      const e = streamMap.get(pid);
      if (e?.state.isRunning) setEntryState(pid, { isRunning: false });
    };
  }, []);

  const stop = useCallback((pid: number) => {
    const entry = streamMap.get(pid);
    if (!entry?.ws) return;
    try {
      entry.ws.send(JSON.stringify({ action: 'stop' }));
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
