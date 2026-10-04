import React from 'react';
import { motion } from 'framer-motion';

export interface StatCardProps {
  label: string;
  value: React.ReactNode;
  subtext?: string;
  icon?: React.ReactNode;
  variant?: 'indigo' | 'emerald' | 'rose' | 'amber' | 'cyan' | 'slate';
  testId?: string;
  className?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  subtext,
  icon,
  variant = 'slate',
  testId,
  className = '',
}) => {
  const variantStyles = {
    indigo: {
      border: 'border-indigo-500/30',
      badge: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
      value: 'text-indigo-300',
    },
    emerald: {
      border: 'border-emerald-500/30',
      badge: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
      value: 'text-emerald-400',
    },
    rose: {
      border: 'border-rose-500/30',
      badge: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
      value: 'text-rose-400',
    },
    amber: {
      border: 'border-amber-500/30',
      badge: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
      value: 'text-amber-400',
    },
    cyan: {
      border: 'border-cyan-500/30',
      badge: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
      value: 'text-cyan-300',
    },
    slate: {
      border: 'border-slate-800',
      badge: 'bg-slate-800/80 text-slate-400 border-slate-700/50',
      value: 'text-white',
    },
  };

  const style = variantStyles[variant];

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      data-testid={testId}
      className={`bg-slate-900/80 border ${style.border} rounded-2xl p-4 sm:p-5 backdrop-blur-md shadow-xl shadow-black/20 flex flex-col justify-between gap-3 ${className}`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-mono uppercase tracking-wider text-slate-400 font-medium">
          {label}
        </span>
        {icon && (
          <div className={`p-1.5 rounded-lg border ${style.badge} flex items-center justify-center shrink-0`}>
            {icon}
          </div>
        )}
      </div>

      <div>
        <div className={`text-2xl sm:text-3xl font-extrabold tracking-tight font-mono ${style.value}`}>
          {value}
        </div>
        {subtext && (
          <div className="text-[11px] text-slate-400 mt-1 font-sans">
            {subtext}
          </div>
        )}
      </div>
    </motion.div>
  );
};
