import React from 'react';
import { RefreshCw, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { HealthResponse } from '../api/client';

interface ConnectivityStatusProps {
  status: 'idle' | 'loading' | 'success' | 'error';
  data: HealthResponse | null;
  error: string | null;
  onRefresh: () => void;
}

export const ConnectivityStatus: React.FC<ConnectivityStatusProps> = ({
  status,
  data,
  error,
  onRefresh,
}) => {
  return (
    <div className="border border-border bg-background p-4 rounded-control text-left">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          {status === 'loading' && <Loader2 size={16} className="text-primary animate-spin" />}
          {status === 'success' && <CheckCircle2 size={16} className="text-primary" />}
          {status === 'error' && <XCircle size={16} className="text-destructive" />}

          <div>
            <div className="text-xs font-semibold text-foreground">
              {status === 'loading' && 'Checking FastAPI backend connectivity...'}
              {status === 'success' && (
                <span className="flex items-center gap-1.5 font-mono">
                  Backend connected: {JSON.stringify(data)}
                </span>
              )}
              {status === 'error' && 'Backend connection failed'}
            </div>
            <div className="text-[11px] text-muted mt-0.5">
              {status === 'success' && 'FastAPI server is active and responding with status: ok'}
              {status === 'error' && (error || 'Ensure FastAPI backend is running on http://localhost:8000')}
              {status === 'loading' && 'Querying http://localhost:8000/health...'}
            </div>
          </div>
        </div>

        <button
          className="px-3 py-1.5 bg-surface-1 hover:bg-surface-2 border border-border text-foreground text-xs font-medium rounded-control cursor-pointer transition-colors inline-flex items-center gap-1.5 shrink-0"
          onClick={onRefresh}
          disabled={status === 'loading'}
        >
          {status === 'loading' ? (
            <>
              <Loader2 size={13} className="animate-spin" /> Checking...
            </>
          ) : (
            <>
              <RefreshCw size={13} /> Re-check health
            </>
          )}
        </button>
      </div>
    </div>
  );
};
