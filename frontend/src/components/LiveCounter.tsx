import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export interface LiveCounterProps {
  value: number;
  label: string;
  sublabel?: string;
  icon?: React.ReactNode;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  variant?: 'rose' | 'indigo' | 'emerald' | 'amber' | 'slate';
  className?: string;
  testId?: string;
}

export const LiveCounter: React.FC<LiveCounterProps> = ({
  value,
  label,
  sublabel,
  icon,
  prefix = '',
  suffix = '',
  decimals = 0,
  className = '',
  testId = 'live-counter',
}) => {
  const formattedValue = decimals > 0 ? value.toFixed(decimals) : Math.round(value).toString();

  return (
    <div
      data-testid={testId}
      className={`px-3 py-2 border border-border bg-surface-1 flex items-center justify-between gap-3 rounded-control ${className}`}
    >
      <div className="flex items-center gap-2">
        {icon && (
          <div className="text-muted">
            {icon}
          </div>
        )}
        <div>
          <div className="text-[11px] text-muted font-medium">
            {label}
          </div>
          {sublabel && <div className="text-[10px] text-muted/70">{sublabel}</div>}
        </div>
      </div>

      <div className="flex items-baseline font-mono font-semibold tracking-tight">
        {prefix && <span className="text-xs text-muted mr-0.5">{prefix}</span>}
        <AnimatePresence mode="popLayout" initial={false}>
          <motion.span
            key={formattedValue}
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 6 }}
            transition={{ duration: 0.15 }}
            className="text-lg font-bold text-foreground"
          >
            {formattedValue}
          </motion.span>
        </AnimatePresence>
        {suffix && <span className="text-xs text-muted ml-0.5">{suffix}</span>}
      </div>
    </div>
  );
};
