import React from 'react';
import { Check, Loader2, Circle } from 'lucide-react';
import { PIPELINE_STEPS, getStepIndexForStage, PipelineStep } from '../constants/stageLabels';

export interface StageTimelineProps {
  currentStage: string;
  isCompleted?: boolean;
}

export const StageTimeline: React.FC<StageTimelineProps> = ({
  currentStage,
  isCompleted = false,
}) => {
  const activeIndex = isCompleted ? PIPELINE_STEPS.length : getStepIndexForStage(currentStage);

  return (
    <div className="w-full border border-line bg-paper p-4">
      <div className="text-xs text-muted font-medium mb-3 flex items-center justify-between">
        <span>Pipeline stages</span>
        <span className="font-mono text-azure">
          {Math.min(activeIndex + 1, PIPELINE_STEPS.length)} of {PIPELINE_STEPS.length}
        </span>
      </div>

      <div className="flex items-start gap-0">
        {PIPELINE_STEPS.map((step: PipelineStep, index: number) => {
          const isDone = index < activeIndex || isCompleted;
          const isActive = index === activeIndex && !isCompleted;
          const isUpcoming = index > activeIndex && !isCompleted;
          const isLlmStep = step.id === 'diagnose' || step.id === 'fix';

          return (
            <React.Fragment key={step.id}>
              <div
                data-testid={`timeline-step-${step.id}`}
                className={`flex flex-col items-center flex-1 min-w-0 ${isUpcoming ? 'opacity-40' : ''}`}
              >
                {/* Step indicator */}
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-mono mb-1.5 ${
                    isDone
                      ? 'border border-emerald/40 bg-emerald/10 text-emerald'
                      : isActive
                      ? 'border-2 border-azure bg-azure/10 text-azure ring-2 ring-azure/30 ring-offset-1 animate-pulse'
                      : 'border border-line bg-transparent text-muted/30'
                  }`}
                >
                  {isDone ? (
                    <Check size={13} strokeWidth={2.5} />
                  ) : isActive ? (
                    <Loader2 size={13} className="animate-spin" />
                  ) : (
                    <Circle size={8} />
                  )}
                </div>

                {/* Step label */}
                <div className="text-center min-w-0 px-1 flex flex-col items-center">
                  <div
                    className={`text-[11px] font-medium truncate ${
                      isActive ? 'text-azure' : isDone ? 'text-ink' : 'text-muted'
                    }`}
                  >
                    {step.shortLabel}
                  </div>

                  {/* AI LLM call indicator tag (small violet Nemotron badge) */}
                  {isActive && isLlmStep && (
                    <span className="inline-block mt-0.5 px-1 py-0.2 text-[9px] font-sans font-medium rounded-control bg-violet/10 text-violet border border-violet/20">
                      Nemotron
                    </span>
                  )}
                </div>
              </div>

              {/* Connector line between steps */}
              {index < PIPELINE_STEPS.length - 1 && (
                <div className="flex items-center pt-3.5 -mx-1">
                  <div
                    className={`h-px w-4 sm:w-6 ${
                      index < activeIndex || isCompleted ? 'bg-emerald/40' : 'bg-line'
                    }`}
                  />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};
