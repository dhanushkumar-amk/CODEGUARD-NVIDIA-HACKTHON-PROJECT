import React from 'react';
import { motion } from 'framer-motion';

export interface ProgressBarProps {
  progress: number; // 0 to 100
  label?: string;
  showPercentage?: boolean;
  className?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  label,
  showPercentage = true,
  className = '',
}) => {
  const clampedProgress = Math.min(100, Math.max(0, progress));
  const isComplete = clampedProgress === 100;

  return (
    <div className={`w-full flex flex-col gap-2 ${className}`}>
      {(label || showPercentage) && (
        <div className="flex items-center justify-between text-xs">
          {label && <span className="font-medium text-slate-300">{label}</span>}
          {showPercentage && (
            <span className="font-mono font-semibold text-slate-400">{clampedProgress}%</span>
          )}
        </div>
      )}
      <div className="h-2.5 w-full bg-slate-800 rounded-full overflow-hidden p-0.5 border border-slate-700/50">
        <motion.div
          className={`h-full rounded-full transition-all duration-300 ${
            isComplete
              ? 'bg-gradient-to-r from-emerald-500 to-teal-400 shadow-sm shadow-emerald-500/50'
              : 'bg-gradient-to-r from-indigo-500 via-purple-500 to-cyan-400 shadow-sm shadow-indigo-500/50'
          }`}
          initial={{ width: 0 }}
          animate={{ width: `${clampedProgress}%` }}
          transition={{ ease: 'easeOut', duration: 0.4 }}
        />
      </div>
    </div>
  );
};
