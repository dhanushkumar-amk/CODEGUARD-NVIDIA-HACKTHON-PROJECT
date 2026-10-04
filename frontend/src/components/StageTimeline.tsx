import React from 'react';
import { CheckCircle2, Loader2, Circle } from 'lucide-react';
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
    <div className="w-full border border-border bg-background p-4">
      <div className="text-xs text-muted font-medium mb-3 flex items-center justify-between">
        <span>Pipeline stages</span>
        <span className="font-mono text-primary">
          {Math.min(activeIndex + 1, PIPELINE_STEPS.length)} of {PIPELINE_STEPS.length}
        </span>
      </div>

      <div className="flex items-start gap-0">
        {PIPELINE_STEPS.map((step: PipelineStep, index: number) => {
          const isDone = index < activeIndex || isCompleted;
          const isActive = index === activeIndex && !isCompleted;
          const isUpcoming = index > activeIndex && !isCompleted;

          return (
            <React.Fragment key={step.id}>
              <div
                data-testid={`timeline-step-${step.id}`}
                className={`flex flex-col items-center flex-1 min-w-0 ${isUpcoming ? 'opacity-40' : ''}`}
              >
                {/* Step indicator */}
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-mono mb-1.5 border ${
                    isActive
                      ? 'border-primary bg-primary/10 text-primary'
                      : isDone
                      ? 'border-[#2F7A4D]/30 bg-[#2F7A4D]/10 text-[#2F7A4D]'
                      : 'border-border bg-surface-1 text-muted'
                  }`}
                >
                  {isDone ? (
                    <CheckCircle2 size={14} />
                  ) : isActive ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : (
                    <Circle size={10} />
                  )}
                </div>

                {/* Step label */}
                <div className="text-center min-w-0 px-1">
                  <div
                    className={`text-[11px] font-medium truncate ${
                      isActive ? 'text-primary' : isDone ? 'text-foreground' : 'text-muted'
                    }`}
                  >
                    {step.shortLabel}
                  </div>
                </div>
              </div>

              {/* Connector line between steps */}
              {index < PIPELINE_STEPS.length - 1 && (
                <div className="flex items-center pt-3.5 -mx-1">
                  <div
                    className={`h-px w-4 sm:w-6 ${
                      index < activeIndex || isCompleted ? 'bg-[#2F7A4D]/40' : 'bg-border'
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
