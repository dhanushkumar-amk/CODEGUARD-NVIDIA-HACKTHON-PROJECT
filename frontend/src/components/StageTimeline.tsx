import React from 'react';
import { motion } from 'framer-motion';
import { CheckCircle2, Loader2, Circle, GitBranch, Search, Filter, Stethoscope, Wrench, ShieldCheck, FileCheck2 } from 'lucide-react';
import { PIPELINE_STEPS, getStepIndexForStage, PipelineStep } from '../constants/stageLabels';

export interface StageTimelineProps {
  currentStage: string;
  isCompleted?: boolean;
}

const STEP_ICONS: Record<string, React.ReactNode> = {
  clone: <GitBranch size={15} />,
  scan: <Search size={15} />,
  classify: <Filter size={15} />,
  diagnose: <Stethoscope size={15} />,
  fix: <Wrench size={15} />,
  verify: <ShieldCheck size={15} />,
  report: <FileCheck2 size={15} />,
};

export const StageTimeline: React.FC<StageTimelineProps> = ({
  currentStage,
  isCompleted = false,
}) => {
  const activeIndex = isCompleted ? PIPELINE_STEPS.length : getStepIndexForStage(currentStage);

  return (
    <div className="w-full bg-slate-900/50 border border-slate-800 rounded-2xl p-4 sm:p-5 backdrop-blur-md shadow-lg shadow-black/20">
      <div className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold mb-3 flex items-center justify-between">
        <span>Pipeline Execution Stepper</span>
        <span className="text-indigo-400">
          Stage {Math.min(activeIndex + 1, PIPELINE_STEPS.length)} of {PIPELINE_STEPS.length}
        </span>
      </div>

      {/* Stepper container */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5 sm:gap-2">
        {PIPELINE_STEPS.map((step: PipelineStep, index: number) => {
          const isDone = index < activeIndex || isCompleted;
          const isActive = index === activeIndex && !isCompleted;
          const isUpcoming = index > activeIndex && !isCompleted;

          return (
            <motion.div
              key={step.id}
              initial={false}
              animate={{
                scale: isActive ? 1.02 : 1,
                opacity: isUpcoming ? 0.45 : 1,
              }}
              transition={{ duration: 0.2 }}
              data-testid={`timeline-step-${step.id}`}
              className={`relative flex flex-col p-2.5 rounded-xl border transition-all ${
                isActive
                  ? 'bg-indigo-950/40 border-indigo-500/70 shadow-md shadow-indigo-950/50 ring-1 ring-indigo-500/30'
                  : isDone
                  ? 'bg-emerald-950/20 border-emerald-500/30 text-slate-300'
                  : 'bg-slate-950/40 border-slate-800/80 text-slate-500'
              }`}
            >
              <div className="flex items-center justify-between mb-1.5">
                <div
                  className={`w-6 h-6 rounded-lg flex items-center justify-center text-xs font-mono font-bold ${
                    isActive
                      ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-600/50'
                      : isDone
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                      : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  {STEP_ICONS[step.id] || (index + 1)}
                </div>

                <div>
                  {isDone ? (
                    <CheckCircle2 size={15} className="text-emerald-400 shrink-0" />
                  ) : isActive ? (
                    <Loader2 size={15} className="text-indigo-400 animate-spin shrink-0" />
                  ) : (
                    <Circle size={13} className="text-slate-600 shrink-0" />
                  )}
                </div>
              </div>

              <div className="min-w-0">
                <div
                  className={`text-xs font-semibold truncate ${
                    isActive ? 'text-indigo-200' : isDone ? 'text-slate-200' : 'text-slate-400'
                  }`}
                >
                  {step.shortLabel}
                </div>
                <div className="text-[10px] text-slate-400 line-clamp-1 mt-0.5">
                  {step.label}
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
};
