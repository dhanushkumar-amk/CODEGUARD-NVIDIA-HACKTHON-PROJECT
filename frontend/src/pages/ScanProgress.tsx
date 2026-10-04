import React, { useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  CheckCircle2,
  Loader2,
  ArrowRight,
  Shield,
  Wifi,
  WifiOff,
  AlertTriangle,
  RotateCcw,
  Home as HomeIcon,
  DollarSign,
  Activity,
} from 'lucide-react';
import { useScanProgress } from '../hooks/useScanProgress';
import { StageTimeline } from '../components/StageTimeline';
import { LiveCounter } from '../components/LiveCounter';
import { Button } from '../components/Button';
import { Badge } from '../components/Badge';
import { getStageDisplayLabel } from '../constants/stageLabels';

export const ScanProgress: React.FC = () => {
  const { scanId } = useParams<{ scanId: string }>();
  const navigate = useNavigate();

  const {
    stage,
    progress,
    message,
    violationsCount,
    currentCost,
    isConnected,
    isReconnecting,
    isCompleted,
    error,
    history,
    retryConnection,
  } = useScanProgress(scanId);

  // Auto-navigate to report page 1.8s after completion to allow users to see 100% state
  useEffect(() => {
    if (isCompleted && scanId) {
      const timer = setTimeout(() => {
        navigate(`/report/${scanId}`);
      }, 1800);
      return () => clearTimeout(timer);
    }
  }, [isCompleted, scanId, navigate]);

  const displayStageTitle = getStageDisplayLabel(stage);
  const isLlmActive =
    stage === 'diagnosing' ||
    stage === 'explaining' ||
    stage === 'generating_fixes' ||
    stage === 'fixing';

  return (
    <div className="max-w-4xl flex flex-col gap-6 py-4 text-left">
      {/* Top Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-3 pb-3 border-b border-line">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-xs font-medium text-muted">
              Autonomous remediation loop
            </span>
            <Badge
              variant={isConnected ? 'fixed_and_verified' : isReconnecting ? 'fixed_not_verified' : 'fix_failed'}
              size="sm"
            >
              {isConnected ? (
                <span className="flex items-center gap-1">
                  <Wifi size={11} /> Live stream connected
                </span>
              ) : isReconnecting ? (
                <span className="flex items-center gap-1">
                  <Loader2 size={11} className="animate-spin" /> Reconnecting...
                </span>
              ) : (
                <span className="flex items-center gap-1">
                  <WifiOff size={11} /> Disconnected
                </span>
              )}
            </Badge>
          </div>

          <h1 className="text-xl sm:text-2xl font-bold text-ink flex items-center gap-2">
            <Shield className="text-azure shrink-0" size={20} />
            <span>Auditing scan:</span>
            <span className="font-mono text-azure text-base sm:text-xl font-medium truncate max-w-xs sm:max-w-md">
              {scanId}
            </span>
          </h1>
        </div>

        {/* Live Counters */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Number ticks up in IBM Plex Mono, small coral dot pulses next to it each time it increments */}
          <LiveCounter
            value={violationsCount}
            label="Violations"
            pulseDot={violationsCount > 0}
            icon={<AlertTriangle size={13} className="text-coral" />}
            testId="violations-counter"
          />
          {currentCost > 0 && (
            <LiveCounter
              value={currentCost}
              label="Model spend"
              prefix="$"
              decimals={4}
              icon={<DollarSign size={13} className="text-azure" />}
              testId="cost-counter"
            />
          )}
        </div>
      </div>

      {/* Stage Timeline Stepper */}
      <StageTimeline currentStage={stage} isCompleted={isCompleted} />

      {/* Main Live Progress Section - Flat, no shadows */}
      <div className="border border-line bg-paper p-5 sm:p-6 flex flex-col gap-5">
        {/* Progress Bar with solid azure primary fill */}
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="text-muted flex items-center gap-1.5 font-sans">
              <Activity size={13} className="text-azure" />
              Overall pipeline progress
            </span>
            <span className="text-ink font-semibold" data-testid="progress-percentage">
              {progress}%
            </span>
          </div>

          <div
            data-testid="progress-bar-container"
            className="w-full h-2.5 bg-surface-2 rounded-control overflow-hidden border border-line"
          >
            <div
              data-testid="progress-bar-fill"
              className="h-full bg-azure transition-all duration-300 ease-out"
              style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
            />
          </div>
        </div>

        {/* Current Stage Narrative Area */}
        <div className="p-4 rounded-control bg-surface-1 border border-line flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start sm:items-center gap-3">
            <div className="p-2 rounded-control bg-paper border border-line shrink-0">
              {isCompleted ? (
                <CheckCircle2 size={20} className="text-emerald" />
              ) : isLlmActive ? (
                <Loader2 size={20} className="animate-spin text-violet" />
              ) : (
                <Loader2 size={20} className="animate-spin text-azure" />
              )}
            </div>

            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs text-muted">
                  Current stage
                </span>
                <span className="text-line">&bull;</span>
                <span
                  data-testid="active-stage-label"
                  className="text-sm font-semibold text-ink"
                >
                  {displayStageTitle}
                </span>

                {/* AI LLM Tag (small violet Nemotron badge) */}
                {isLlmActive && (
                  <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-control text-[10px] font-sans font-medium bg-violet/10 text-violet border border-violet/20">
                    Nemotron
                  </span>
                )}
              </div>

              <p
                data-testid="live-stage-message"
                className="text-xs sm:text-sm text-muted font-mono mt-1"
              >
                {message}
              </p>
            </div>
          </div>

          {/* Quick action button when completed */}
          {isCompleted && (
            <Link to={`/report/${scanId}`} className="shrink-0">
              <Button
                variant="primary"
                size="md"
                rightIcon={<ArrowRight size={15} />}
              >
                View audit report
              </Button>
            </Link>
          )}
        </div>

        {/* Interrupted state callout */}
        {error && (
          <div
            data-testid="scan-error-alert"
            className="p-4 rounded-control bg-coral/10 border border-coral/20 flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-coral"
          >
            <div className="flex items-center gap-2.5">
              <AlertTriangle size={18} className="shrink-0 text-coral" />
              <div>
                <div className="text-xs font-semibold">
                  Audit execution interrupted
                </div>
                <div className="text-xs text-ink/80 mt-0.5">{error}</div>
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <Button
                variant="outline"
                size="sm"
                onClick={retryConnection}
                leftIcon={<RotateCcw size={13} />}
                className="text-xs"
              >
                Retry Stream
              </Button>
              <Link to="/">
                <Button
                  variant="secondary"
                  size="sm"
                  leftIcon={<HomeIcon size={13} />}
                  className="text-xs"
                >
                  Try Again
                </Button>
              </Link>
            </div>
          </div>
        )}
      </div>

      {/* Real-time Event Feed - Flat table/log view */}
      <div className="border border-line bg-paper p-4 sm:p-5">
        <div className="flex items-center justify-between pb-2.5 border-b border-line mb-3">
          <div className="text-xs font-semibold text-ink flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-azure" />
            Live event feed
          </div>
          <span className="text-xs font-mono text-muted">
            {history.length} events logged
          </span>
        </div>

        <div className="flex flex-col max-h-56 overflow-y-auto divide-y divide-line">
          {history.length === 0 ? (
            <div className="text-xs text-muted italic py-3 text-center">
              Waiting for initial pipeline orchestrator event...
            </div>
          ) : (
            [...history].reverse().map((item, idx) => (
              <div
                key={idx}
                className="flex items-start gap-2.5 py-2 text-xs"
              >
                <div className="mt-0.5">
                  {item.stage === 'complete' || item.stage === 'completed' ? (
                    <CheckCircle2 size={13} className="text-emerald shrink-0" />
                  ) : (
                    <span className="w-1.5 h-1.5 rounded-full bg-muted inline-block mt-1" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-xs font-medium text-ink">
                      {item.stage} ({item.progress}%)
                    </span>
                    {item.timestamp && (
                      <span className="text-xs text-muted font-mono">
                        {new Date(item.timestamp).toLocaleTimeString()}
                      </span>
                    )}
                  </div>
                  <p className="text-muted text-xs mt-0.5 font-mono">{item.message}</p>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
