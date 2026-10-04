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
  variant = 'rose',
  className = '',
  testId = 'live-counter',
}) => {
  const formattedValue = decimals > 0 ? value.toFixed(decimals) : Math.round(value).toString();

  const variantStyles = {
    rose: {
      border: 'border-rose-500/30',
      bg: 'bg-rose-500/10',
      badge: 'bg-rose-500/20 text-rose-300 border-rose-500/30',
      text: 'text-rose-400',
      glow: 'shadow-rose-950/30',
    },
    indigo: {
      border: 'border-indigo-500/30',
      bg: 'bg-indigo-500/10',
      badge: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
      text: 'text-indigo-400',
      glow: 'shadow-indigo-950/30',
    },
    emerald: {
      border: 'border-emerald-500/30',
      bg: 'bg-emerald-500/10',
      badge: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
      text: 'text-emerald-400',
      glow: 'shadow-emerald-950/30',
    },
    amber: {
      border: 'border-amber-500/30',
      bg: 'bg-amber-500/10',
      badge: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
      text: 'text-amber-400',
      glow: 'shadow-amber-950/30',
    },
    slate: {
      border: 'border-slate-800',
      bg: 'bg-slate-900/60',
      badge: 'bg-slate-800 text-slate-300 border-slate-700',
      text: 'text-slate-200',
      glow: 'shadow-black/20',
    },
  };

  const style = variantStyles[variant];

  return (
    <div
      data-testid={testId}
      className={`relative px-3.5 py-2.5 rounded-xl border ${style.border} ${style.bg} backdrop-blur-sm shadow-md ${style.glow} flex items-center justify-between gap-3 ${className}`}
    >
      <div className="flex items-center gap-2.5">
        {icon && (
          <div className={`p-1.5 rounded-lg border ${style.badge} flex items-center justify-center`}>
            {icon}
          </div>
        )}
        <div>
          <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-medium">
            {label}
          </div>
          {sublabel && <div className="text-[10px] text-slate-500">{sublabel}</div>}
        </div>
      </div>

      <div className="flex items-baseline font-mono font-bold tracking-tight">
        {prefix && <span className="text-xs text-slate-400 mr-0.5">{prefix}</span>}
        <AnimatePresence mode="popLayout" initial={false}>
          <motion.span
            key={formattedValue}
            initial={{ opacity: 0, y: -8, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.95 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className={`text-lg sm:text-xl font-extrabold ${style.text}`}
          >
            {formattedValue}
          </motion.span>
        </AnimatePresence>
        {suffix && <span className="text-xs text-slate-400 ml-0.5">{suffix}</span>}
      </div>
    </div>
  );
};
