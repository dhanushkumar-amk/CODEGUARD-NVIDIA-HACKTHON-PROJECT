import React, { useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
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
  Sparkles,
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

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="max-w-5xl mx-auto flex flex-col gap-6 py-6 px-2"
    >
      {/* Top Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800/80">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-xs uppercase font-mono text-indigo-400 font-semibold tracking-wider flex items-center gap-1.5">
              <Sparkles size={13} className="text-indigo-400 animate-pulse" />
              Autonomous Remediation Loop
            </span>
            <Badge variant={isConnected ? 'success' : isReconnecting ? 'warning' : 'danger'} size="sm">
              {isConnected ? (
                <span className="flex items-center gap-1">
                  <Wifi size={11} /> Live Stream Connected
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

          <h1 className="text-xl sm:text-2xl font-bold text-white flex items-center gap-2">
            <Shield className="text-indigo-400 shrink-0" size={22} />
            Auditing Scan:&nbsp;
            <span className="font-mono text-indigo-300 text-lg sm:text-xl truncate max-w-xs sm:max-w-md">
              {scanId}
            </span>
          </h1>
        </div>

        {/* Live Counters strip */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <LiveCounter
            value={violationsCount}
            label="Violations"
            variant="rose"
            icon={<AlertTriangle size={14} className="text-rose-400" />}
            testId="violations-counter"
          />
          {currentCost > 0 && (
            <LiveCounter
              value={currentCost}
              label="Model Spend"
              prefix="$"
              decimals={4}
              variant="slate"
              icon={<DollarSign size={13} className="text-indigo-400" />}
              testId="cost-counter"
            />
          )}
        </div>
      </div>

      {/* Stage Timeline Stepper */}
      <StageTimeline currentStage={stage} isCompleted={isCompleted} />

      {/* Main Live Progress Hero Card */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 sm:p-8 backdrop-blur-md shadow-2xl shadow-black/40 flex flex-col gap-6">
        {/* Progress Bar with smooth Framer Motion fill */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="text-slate-400 font-medium flex items-center gap-1.5">
              <Activity size={14} className="text-indigo-400" />
              Overall Pipeline Completion
            </span>
            <span className="text-indigo-300 font-bold" data-testid="progress-percentage">
              {progress}%
            </span>
          </div>

          <div
            data-testid="progress-bar-container"
            className="w-full h-3.5 bg-slate-950 rounded-full overflow-hidden p-0.5 border border-slate-800/80 shadow-inner"
          >
            <motion.div
              data-testid="progress-bar-fill"
              className="h-full rounded-full bg-gradient-to-r from-indigo-500 via-purple-500 to-emerald-400 shadow-md shadow-indigo-500/30"
              initial={{ width: 0 }}
              animate={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
              transition={{ duration: 0.4, ease: 'easeOut' }}
            />
          </div>
        </div>

        {/* Prominent Current Stage Narrative Area */}
        <div className="p-5 sm:p-6 rounded-xl bg-slate-950/80 border border-slate-800/90 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start sm:items-center gap-4">
            <div className="p-2.5 rounded-xl bg-indigo-950/70 border border-indigo-500/40 text-indigo-400 shrink-0 mt-0.5 sm:mt-0 shadow-lg shadow-indigo-950/50">
              {isCompleted ? (
                <CheckCircle2 size={24} className="text-emerald-400" />
              ) : (
                <Loader2 size={24} className="animate-spin text-indigo-400" />
              )}
            </div>

            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-indigo-400">
                  Current Stage
                </span>
                <span className="text-slate-600">&bull;</span>
                <span
                  data-testid="active-stage-label"
                  className="text-sm sm:text-base font-semibold text-slate-100"
                >
                  {displayStageTitle}
                </span>
              </div>

              {/* Live message with smooth opacity/slide transition to eliminate jarring layout shifts */}
              <div className="min-h-[28px] mt-1 flex items-center">
                <AnimatePresence mode="wait">
                  <motion.p
                    key={message}
                    data-testid="live-stage-message"
                    initial={{ opacity: 0, y: 3 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -3 }}
                    transition={{ duration: 0.15 }}
                    className="text-xs sm:text-sm text-slate-300 font-mono"
                  >
                    {message}
                  </motion.p>
                </AnimatePresence>
              </div>
            </div>
          </div>

          {/* Quick action buttons if completed */}
          {isCompleted && (
            <Link to={`/report/${scanId}`} className="shrink-0">
              <Button
                variant="success"
                size="md"
                rightIcon={<ArrowRight size={16} />}
                className="w-full sm:w-auto shadow-lg shadow-emerald-600/30"
              >
                View Audit Report
              </Button>
            </Link>
          )}
        </div>

        {/* Error / Failure State Callout */}
        {error && (
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            data-testid="scan-error-alert"
            className="p-4 sm:p-5 rounded-xl bg-rose-500/10 border border-rose-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
          >
            <div className="flex items-center gap-3 text-rose-300">
              <AlertTriangle size={20} className="shrink-0 text-rose-400" />
              <div>
                <div className="text-xs font-bold uppercase tracking-wider text-rose-400">
                  Audit Execution Interrupted
                </div>
                <div className="text-xs text-rose-200 mt-0.5">{error}</div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={retryConnection}
                leftIcon={<RotateCcw size={13} />}
                className="text-xs border-rose-500/30 hover:bg-rose-500/20 text-rose-200"
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
                  Back to Home
                </Button>
              </Link>
            </div>
          </motion.div>
        )}
      </div>

      {/* Real-time Event Feed */}
      <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-5 backdrop-blur-sm">
        <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-800/80">
          <div className="text-xs font-semibold text-slate-300 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-ping" />
            Live Event Feed
          </div>
          <span className="text-[11px] font-mono text-slate-500">
            {history.length} events logged
          </span>
        </div>

        <div className="flex flex-col gap-2 max-h-56 overflow-y-auto pr-1">
          {history.length === 0 ? (
            <div className="text-xs text-slate-500 italic py-2 text-center">
              Waiting for initial pipeline orchestrator event...
            </div>
          ) : (
            [...history].reverse().map((item, idx) => (
              <div
                key={idx}
                className="flex items-start gap-2.5 p-2 rounded-lg bg-slate-950/50 border border-slate-850 text-xs"
              >
                <div className="mt-1">
                  {item.stage === 'complete' || item.stage === 'completed' ? (
                    <CheckCircle2 size={13} className="text-emerald-400 shrink-0" />
                  ) : (
                    <span className="w-2 h-2 rounded-full bg-indigo-400 inline-block" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-[11px] font-semibold text-slate-300 uppercase">
                      {item.stage} ({item.progress}%)
                    </span>
                    {item.timestamp && (
                      <span className="text-[10px] text-slate-500 font-mono">
                        {new Date(item.timestamp).toLocaleTimeString()}
                      </span>
                    )}
                  </div>
                  <p className="text-slate-400 text-xs mt-0.5 font-mono">{item.message}</p>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </motion.div>
  );
};
