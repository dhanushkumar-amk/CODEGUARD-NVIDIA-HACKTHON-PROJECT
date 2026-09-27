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
    <div className="connectivity-card">
      <div className="connectivity-header">
        <div className="status-indicator">
          {status === 'loading' && <span className="pulse-dot loading" />}
          {status === 'success' && <span className="pulse-dot success" />}
          {status === 'error' && <span className="pulse-dot error" />}
          {status === 'idle' && <span className="pulse-dot loading" />}

          <div>
            <div className="status-title">
              {status === 'loading' && 'Checking FastAPI backend connectivity...'}
              {status === 'success' && (
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}>
                  <CheckCircle2 size={18} color="#10b981" />
                  Backend Connected: <span className="code-pill">GET /health: {JSON.stringify(data)}</span>
                </span>
              )}
              {status === 'error' && (
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', color: '#f43f5e' }}>
                  <XCircle size={18} color="#f43f5e" />
                  Backend Connection Failed
                </span>
              )}
            </div>
            <div className="status-desc">
              {status === 'success' && 'FastAPI server is active and responding with status: ok'}
              {status === 'error' && (error || 'Ensure FastAPI backend is running on http://localhost:8000')}
              {status === 'loading' && 'Querying http://localhost:8000/health...'}
            </div>
          </div>
        </div>

        <button
          className="retry-btn"
          onClick={onRefresh}
          disabled={status === 'loading'}
          title="Re-check health endpoint"
        >
          {status === 'loading' ? (
            <>
              <Loader2 size={16} className="spin" /> Checking...
            </>
          ) : (
            <>
              <RefreshCw size={16} /> Re-check /health
            </>
          )}
        </button>
      </div>
    </div>
  );
};
