import { useCallback, useRef, useState } from 'react';
import { useAuthStore } from '../store/authStore';

const WS_URL = 'ws://localhost:8001/ws/generate-setting';

export interface SettingStreamResult {
  setting_type: string;
  title: string;
  content: string;
  structured_data: Record<string, any>;
  validation_ok: boolean;
}

export function useSettingStream() {
  const [streamingText, setStreamingText] = useState('');
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
        setStructuredData(null);
        setError(null);
        setResult(null);
        setIsStreaming(true);
        accumulatedRef.current = '';

        // Close previous connection
        if (wsRef.current) {
          wsRef.current.close();
        }

        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
          const token = useAuthStore.getState().token;
          ws.send(
            JSON.stringify({
              action: 'generate',
              token: token || '',
              setting_type: params.setting_type,
              book_title: params.book_title,
              genre: params.genre || '',
              context: params.context || '',
              prior_settings: params.prior_settings || [],
            }),
          );
        };

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);

            if (msg.type === 'chunk') {
              accumulatedRef.current += msg.content;
              setStreamingText(accumulatedRef.current);
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
              resolve(res);
            } else if (msg.type === 'error') {
              setError(msg.message || 'Unknown error');
              setIsStreaming(false);
              ws.close();
              resolve(null);
            }
          } catch {
            // ignore parse errors
          }
        };

        ws.onerror = () => {
          setError('WebSocket connection failed');
          setIsStreaming(false);
          resolve(null);
        };

        ws.onclose = () => {
          if (wsRef.current === ws) {
            wsRef.current = null;
            setIsStreaming(false);
          }
        };
      });
    },
    [],
  );

  return {
    streamingText,
    structuredData,
    isStreaming,
    error,
    result,
    generate,
    stop,
  };
}
