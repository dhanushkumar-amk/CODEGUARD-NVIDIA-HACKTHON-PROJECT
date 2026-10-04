import React from 'react';
import { CheckCircle2, Circle, Loader2 } from 'lucide-react';

export type PipelineStepStatus = 'pending' | 'in_progress' | 'completed' | 'error';

export interface PipelineStep {
  id: string;
  label: string;
  description: string;
  status: PipelineStepStatus;
}

interface ScanProgressProps {
  steps: PipelineStep[];
}

export const ScanProgress: React.FC<ScanProgressProps> = ({ steps }) => {
  return (
    <div className="w-full bg-background border border-border p-4">
      <h3 className="text-xs font-semibold text-muted mb-3">
        Pipeline execution
      </h3>
      <div className="flex flex-col gap-2.5">
        {steps.map((step) => (
          <div key={step.id} className="flex items-start gap-2.5">
            <div className="mt-0.5">
              {step.status === 'completed' && <CheckCircle2 size={16} className="text-primary" />}
              {step.status === 'in_progress' && <Loader2 size={16} className="text-primary animate-spin" />}
              {step.status === 'pending' && <Circle size={16} className="text-muted/40" />}
              {step.status === 'error' && <Circle size={16} className="text-destructive" />}
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <span className={`text-xs font-medium ${step.status === 'in_progress' ? 'text-primary' : 'text-foreground'}`}>
                  {step.label}
                </span>
                <span className="text-[11px] text-muted capitalize">{step.status.replace('_', ' ')}</span>
              </div>
              <p className="text-xs text-muted mt-0.5">{step.description}</p>
              {step.status === 'in_progress' && (
                <div className="h-1 bg-surface-2 rounded-control overflow-hidden mt-1.5 border border-border">
                  <div className="h-full bg-primary w-2/5" />
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
