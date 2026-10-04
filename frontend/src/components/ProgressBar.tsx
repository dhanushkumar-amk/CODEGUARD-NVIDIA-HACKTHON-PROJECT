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

  return (
    <div className={`w-full flex flex-col gap-1.5 font-sans ${className}`}>
      {(label || showPercentage) && (
        <div className="flex items-center justify-between text-xs">
          {label && <span className="font-medium text-ink">{label}</span>}
          {showPercentage && (
            <span className="font-mono text-muted">{clampedProgress}%</span>
          )}
        </div>
      )}
      <div className="h-2 w-full bg-surface-2 rounded-control overflow-hidden border border-line">
        <motion.div
          className="h-full rounded-control bg-azure"
          initial={{ width: 0 }}
          animate={{ width: `${clampedProgress}%` }}
          transition={{ ease: 'easeOut', duration: 0.4 }}
        />
      </div>
    </div>
  );
};
