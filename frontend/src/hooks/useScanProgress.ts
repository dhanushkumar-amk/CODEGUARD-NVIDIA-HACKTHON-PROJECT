import { useEffect, useState, useRef, useCallback } from 'react';
import { WebSocketMessage } from '../types';

export interface UseScanProgressState {
  stage: string;
  progress: number;
  message: string;
  data: Record<string, any> | null;
  violationsCount: number;
  currentCost: number;
  isConnected: boolean;
  isReconnecting: boolean;
  isCompleted: boolean;
  error: string | null;
  history: WebSocketMessage[];
  retryConnection: () => void;
}

const MAX_RECONNECT_ATTEMPTS = 4;
const INITIAL_BACKOFF_MS = 1000;

export function useScanProgress(scanId?: string): UseScanProgressState {
  const [stage, setStage] = useState<string>('init');
  const [progress, setProgress] = useState<number>(0);
  const [message, setMessage] = useState<string>('Connecting to CodeGuard pipeline...');
  const [data, setData] = useState<Record<string, any> | null>(null);
  const [violationsCount, setViolationsCount] = useState<number>(0);
  const [currentCost, setCurrentCost] = useState<number>(0);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [isReconnecting, setIsReconnecting] = useState<boolean>(false);
  const [isCompleted, setIsCompleted] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<WebSocketMessage[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef<number>(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isCompletedRef = useRef<boolean>(false);

  const connect = useCallback(() => {
    if (!scanId) return;

    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }

    const WS_BASE_URL =
      import.meta.env.VITE_WS_BASE_URL ||
      (window.location.protocol === 'https:' ? 'wss:' : 'ws:') + `//${window.location.hostname}:8000`;

    const wsUrl = `${WS_BASE_URL}/ws/${scanId}`;
    console.log(`[WebSocket] Connecting to: ${wsUrl}`);

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log(`[WebSocket] Connected for scan: ${scanId}`);
        setIsConnected(true);
        setIsReconnecting(false);
        setError(null);
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const payload: WebSocketMessage = JSON.parse(event.data);

          // Handle error-type messages
          if (payload.stage === 'error' || (payload as any).type === 'error' || (payload as any).error) {
            const errMsg = payload.message || (payload as any).error || 'An error occurred during repository scan.';
            setError(errMsg);
            return;
          }

          if (payload.stage) {
            setStage(payload.stage);
            setProgress(payload.progress);
            setMessage(payload.message);
            setData(payload.data || null);
            setHistory((prev) => [...prev, payload]);

            // Update live running violation counter if present
            if (payload.data) {
              if (typeof payload.data.violations_found === 'number') {
                setViolationsCount(payload.data.violations_found);
              } else if (typeof payload.data.violations_count === 'number') {
                setViolationsCount(payload.data.violations_count);
              }

              // Update live running cost if present
              if (typeof payload.data.current_cost_usd === 'number') {
                setCurrentCost(payload.data.current_cost_usd);
              }
            }

            if (payload.stage === 'complete' || payload.stage === 'completed' || payload.progress >= 100) {
              isCompletedRef.current = true;
              setIsCompleted(true);
            }
          }
        } catch (err) {
          console.error('[WebSocket] Error parsing event data:', err);
        }
      };

      ws.onerror = (evt) => {
        console.warn('[WebSocket] Warning/error on connection:', evt);
      };

      ws.onclose = () => {
        console.log(`[WebSocket] Connection closed for scan: ${scanId}`);
        setIsConnected(false);

        // Do not attempt reconnection if scan already completed successfully
        if (isCompletedRef.current) {
          return;
        }

        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttemptsRef.current += 1;
          setIsReconnecting(true);
          const backoff = INITIAL_BACKOFF_MS * Math.pow(1.5, reconnectAttemptsRef.current - 1);
          console.log(`[WebSocket] Reconnecting in ${backoff}ms (attempt ${reconnectAttemptsRef.current}/${MAX_RECONNECT_ATTEMPTS})...`);
          setMessage(`Connection interrupted. Reconnecting (attempt ${reconnectAttemptsRef.current}/${MAX_RECONNECT_ATTEMPTS})...`);

          reconnectTimerRef.current = setTimeout(() => {
            connect();
          }, backoff);
        } else {
          setIsReconnecting(false);
          setError('Live connection to audit pipeline lost. The scan may have failed or disconnected.');
        }
      };
    } catch (err) {
      console.error('[WebSocket] Instantiation error:', err);
      setError('Unable to open WebSocket connection to audit pipeline.');
    }
  }, [scanId]);

  const retryConnection = useCallback(() => {
    reconnectAttemptsRef.current = 0;
    setError(null);
    setIsReconnecting(false);
    connect();
  }, [connect]);

  useEffect(() => {
    isCompletedRef.current = false;
    connect();

    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (wsRef.current) {
        if (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING) {
          wsRef.current.close();
        }
      }
    };
  }, [connect]);

  return {
    stage,
    progress,
    message,
    data,
    violationsCount,
    currentCost,
    isConnected,
    isReconnecting,
    isCompleted,
    error,
    history,
    retryConnection,
  };
}
