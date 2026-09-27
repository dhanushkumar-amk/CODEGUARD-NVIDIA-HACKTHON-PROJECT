import React, { useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  CheckCircle2,
  Circle,
  Loader2,
  ArrowRight,
  Shield,
  Wifi,
  WifiOff,
  FileCode,
} from 'lucide-react';
import { useScanProgress } from '../hooks/useScanProgress';
import { Card } from '../components/Card';
import { ProgressBar } from '../components/ProgressBar';
import { Button } from '../components/Button';
import { Badge } from '../components/Badge';

export const ScanProgress: React.FC = () => {
  const { scanId } = useParams<{ scanId: string }>();
  const navigate = useNavigate();

  const { stage, progress, message, isConnected, isCompleted, error, history } =
    useScanProgress(scanId);

  // Auto-navigate to report 1.8 seconds after completion
  useEffect(() => {
    if (isCompleted && scanId) {
      const timer = setTimeout(() => {
        navigate(`/report/${scanId}`);
      }, 1800);
      return () => clearTimeout(timer);
    }
  }, [isCompleted, scanId, navigate]);

  return (
    <div className="max-w-3xl mx-auto flex flex-col gap-6 py-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs uppercase font-mono text-indigo-400 font-semibold tracking-wider">
              Live Pipeline Stream
            </span>
            <Badge variant={isConnected ? 'success' : 'default'} size="sm">
              {isConnected ? (
                <span className="flex items-center gap-1">
                  <Wifi size={11} /> Connected
                </span>
              ) : (
                <span className="flex items-center gap-1">
                  <WifiOff size={11} /> Reconnecting
                </span>
              )}
            </Badge>
          </div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Shield className="text-indigo-400" size={24} />
            Scan ID: <span className="font-mono text-indigo-300">{scanId}</span>
          </h1>
        </div>

        {isCompleted && (
          <Link to={`/report/${scanId}`}>
            <Button variant="success" size="sm" rightIcon={<ArrowRight size={14} />}>
              View Audit Report
            </Button>
          </Link>
        )}
      </div>

      {/* Progress Monitor Card */}
      <Card className="border-indigo-500/20">
        <div className="flex flex-col gap-6">
          <ProgressBar progress={progress} label="Pipeline Execution Progress" />

          {/* Current Stage Indicator */}
          <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              {isCompleted ? (
                <CheckCircle2 size={24} className="text-emerald-400 shrink-0" />
              ) : (
                <Loader2 size={24} className="text-indigo-400 animate-spin shrink-0" />
              )}
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-white capitalize">
                    Stage: {stage}
                  </span>
                  <Badge variant={isCompleted ? 'success' : 'info'} size="sm">
                    {progress}%
                  </Badge>
                </div>
                <p className="text-xs text-slate-300 mt-0.5">{message}</p>
              </div>
            </div>
          </div>

          {error && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-300 text-xs">
              {error}
            </div>
          )}
        </div>
      </Card>

      {/* Execution Timeline History */}
      <Card title="Stage Progression Timeline" subtitle="Real-time events streamed over WebSockets.">
        <div className="flex flex-col gap-3">
          {history.length === 0 ? (
            <div className="text-xs text-slate-500 italic py-2">
              Waiting for initial orchestrator event...
            </div>
          ) : (
            history.map((item, idx) => (
              <div
                key={idx}
                className="flex items-start gap-3 p-2.5 rounded-lg bg-slate-950/40 border border-slate-800/60"
              >
                <div className="mt-0.5">
                  {item.stage === 'completed' ? (
                    <CheckCircle2 size={16} className="text-emerald-400" />
                  ) : item.stage === stage ? (
                    <Loader2 size={16} className="text-indigo-400 animate-spin" />
                  ) : (
                    <Circle size={16} className="text-slate-600" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-xs font-semibold text-slate-200 uppercase">
                      {item.stage} ({item.progress}%)
                    </span>
                    {item.timestamp && (
                      <span className="text-[10px] text-slate-500 font-mono">
                        {new Date(item.timestamp).toLocaleTimeString()}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">{item.message}</p>
                  {item.data && (
                    <div className="mt-1 flex items-center gap-2 text-[11px] font-mono text-indigo-300">
                      <FileCode size={12} />
                      <span>{JSON.stringify(item.data)}</span>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
};
