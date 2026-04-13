import { useCallback, useRef, useState } from 'react';
import { useAuthStore } from '../store/authStore';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8001/ws/generate-setting';

export interface SettingStreamResult {
  setting_type: string;
  title: string;
  content: string;
  structured_data: Record<string, any>;
  validation_ok: boolean;
}

export function useSettingStream() {
  const [streamingText, setStreamingText] = useState('');
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [structuredData, setStructuredData] = useState<Record<string, any> | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SettingStreamResult | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const accumulatedRef = useRef('');

  const stop = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  const generate = useCallback(
    (params: {
      setting_type: string;
      book_title: string;
      genre?: string;
      context?: string;
      prior_settings?: any[];
    }) => {
      return new Promise<SettingStreamResult | null>((resolve) => {
        // Reset state
        setStreamingText('');
        setStatusMessage(null);
        setStructuredData(null);
        setError(null);
        setResult(null);
        setIsStreaming(true);
        accumulatedRef.current = '';

        // Close previous connection
        if (wsRef.current) {
          wsRef.current.close();
          wsRef.current = null;
        }

        // Track whether this promise has already resolved
        let resolved = false;
        const safeResolve = (value: SettingStreamResult | null) => {
          if (resolved) return;
          resolved = true;
          resolve(value);
        };

        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
          // Check if ws was already replaced (race condition)
          if (wsRef.current !== ws) {
            ws.close();
            safeResolve(null);
            return;
          }
          const token = useAuthStore.getState().token;
          const payload = {
            action: 'generate',
            token: token || '',
            setting_type: params.setting_type,
            book_title: params.book_title,
            genre: params.genre || '',
            context: params.context || '',
            prior_settings: params.prior_settings || [],
          };
          try {
            ws.send(JSON.stringify(payload));
          } catch (e) {
            console.error('[useSettingStream] send() threw:', e);
            setError('发送消息失败');
            setIsStreaming(false);
            safeResolve(null);
          }
        };

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);

            if (msg.type === 'chunk') {
              accumulatedRef.current += msg.content;
              setStreamingText(accumulatedRef.current);
            } else if (msg.type === 'status') {
              setStatusMessage(msg.message);
            } else if (msg.type === 'done') {
              const res: SettingStreamResult = {
                setting_type: msg.setting_type,
                title: msg.title || '',
                content: msg.content || accumulatedRef.current,
                structured_data: msg.structured_data || {},
                validation_ok: msg.validation_ok ?? false,
              };
              setResult(res);
              setStructuredData(res.structured_data);
              setStreamingText(res.content);
              setIsStreaming(false);
              ws.close();
              safeResolve(res);
            } else if (msg.type === 'error') {
              console.error('[useSettingStream] server error:', msg.message);
              setError(msg.message || 'Unknown error');
              setIsStreaming(false);
              ws.close();
              safeResolve(null);
            }
          } catch (e) {
            console.warn('[useSettingStream] parse error:', e);
          }
        };

        ws.onerror = () => {
          setError(`WebSocket 连接失败 (${WS_URL})`);
          setIsStreaming(false);
          safeResolve(null);
        };

        ws.onclose = () => {
          if (wsRef.current === ws) {
            wsRef.current = null;
          }
          // If the promise never resolved (server closed without done/error),
          // resolve now to prevent hanging.
          if (!resolved) {
            setIsStreaming(false);
            if (accumulatedRef.current) {
              const partial: SettingStreamResult = {
                setting_type: params.setting_type,
                title: '',
                content: accumulatedRef.current,
                structured_data: {},
                validation_ok: false,
              };
              safeResolve(partial);
            } else {
              setError('WebSocket 连接异常关闭，未收到数据');
              safeResolve(null);
            }
          }
        };
      });
    },
    [],
  );

  return {
    streamingText,
    statusMessage,
    structuredData,
    isStreaming,
    error,
    result,
    generate,
    stop,
  };
}
