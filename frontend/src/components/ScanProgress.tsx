import React from 'react';
import { motion } from 'framer-motion';
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
    <div className="w-full bg-slate-900/80 border border-slate-800 rounded-xl p-5 backdrop-blur-sm">
      <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">
        Pipeline Execution
      </h3>
      <div className="flex flex-col gap-3">
        {steps.map((step) => (
          <div key={step.id} className="flex items-start gap-3">
            <div className="mt-0.5">
              {step.status === 'completed' && <CheckCircle2 size={18} className="text-emerald-400" />}
              {step.status === 'in_progress' && <Loader2 size={18} className="text-indigo-400 animate-spin" />}
              {step.status === 'pending' && <Circle size={18} className="text-slate-600" />}
              {step.status === 'error' && <Circle size={18} className="text-rose-400" />}
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <span className={`text-sm font-medium ${step.status === 'in_progress' ? 'text-indigo-300' : 'text-slate-200'}`}>
                  {step.label}
                </span>
                <span className="text-xs text-slate-500 capitalize">{step.status.replace('_', ' ')}</span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">{step.description}</p>
              {step.status === 'in_progress' && (
                <motion.div
                  className="h-1 bg-indigo-500/30 rounded-full overflow-hidden mt-2"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                >
                  <motion.div
                    className="h-full bg-indigo-500 rounded-full"
                    animate={{ x: ['-100%', '100%'] }}
                    transition={{ repeat: Infinity, duration: 1.5, ease: 'linear' }}
                    style={{ width: '40%' }}
                  />
                </motion.div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
