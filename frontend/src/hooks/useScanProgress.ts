import { useEffect, useState, useRef } from 'react';
import { WebSocketMessage } from '../types';

export interface UseScanProgressState {
  stage: string;
  progress: number;
  message: string;
  data: Record<string, any> | null;
  isConnected: boolean;
  isCompleted: boolean;
  error: string | null;
  history: WebSocketMessage[];
}

export function useScanProgress(scanId?: string): UseScanProgressState {
  const [stage, setStage] = useState<string>('init');
  const [progress, setProgress] = useState<number>(0);
  const [message, setMessage] = useState<string>('Connecting to CodeGuard pipeline...');
  const [data, setData] = useState<Record<string, any> | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [isCompleted, setIsCompleted] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<WebSocketMessage[]>([]);

  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!scanId) return;

    const WS_BASE_URL =
      import.meta.env.VITE_WS_BASE_URL ||
      (window.location.protocol === 'https:' ? 'wss:' : 'ws:') + `//${window.location.hostname}:8000`;

    const wsUrl = `${WS_BASE_URL}/ws/${scanId}`;
    console.log(`[WebSocket] Connecting to: ${wsUrl}`);

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log(`[WebSocket] Connected for scan: ${scanId}`);
      setIsConnected(true);
      setError(null);
    };

    ws.onmessage = (event) => {
      try {
        const payload: WebSocketMessage = JSON.parse(event.data);
        if (payload.stage) {
          setStage(payload.stage);
          setProgress(payload.progress);
          setMessage(payload.message);
          setData(payload.data || null);
          setHistory((prev) => [...prev, payload]);

          if (payload.stage === 'completed' || payload.progress >= 100) {
            setIsCompleted(true);
          }
        }
      } catch (err) {
        console.error('[WebSocket] Error parsing event data:', err);
      }
    };

    ws.onerror = (evt) => {
      console.error('[WebSocket] Error:', evt);
      setError('WebSocket connection error');
    };

    ws.onclose = () => {
      console.log(`[WebSocket] Connection closed for scan: ${scanId}`);
      setIsConnected(false);
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
    };
  }, [scanId]);

  return {
    stage,
    progress,
    message,
    data,
    isConnected,
    isCompleted,
    error,
    history,
  };
}
