import React from 'react';

export type BadgeVariant =
  | 'critical'
  | 'high'
  | 'serious'
  | 'medium'
  | 'moderate'
  | 'low'
  | 'minor'
  | 'success'
  | 'info'
  | 'purple'
  | 'default';

export interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant | string;
  className?: string;
  size?: 'sm' | 'md';
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  className = '',
  size = 'md',
}) => {
  const normalizedVariant = variant.toLowerCase();

  // Color coding: critical=red, high=orange, medium=yellow, low=gray
  const variantStyles: Record<string, string> = {
    critical: 'bg-rose-500/15 text-rose-400 border-rose-500/30', // Red
    high: 'bg-orange-500/15 text-orange-400 border-orange-500/30', // Orange
    serious: 'bg-orange-500/15 text-orange-400 border-orange-500/30', // Legacy high
    medium: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30', // Yellow
    moderate: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30', // Legacy medium
    low: 'bg-slate-700/40 text-slate-300 border-slate-600/40', // Gray
    minor: 'bg-slate-700/40 text-slate-300 border-slate-600/40', // Legacy low
    success: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    info: 'bg-indigo-500/15 text-indigo-400 border-indigo-500/30',
    purple: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
    default: 'bg-slate-800 text-slate-300 border-slate-700',
  };

  const currentVariant = variantStyles[normalizedVariant] || variantStyles.default;

  const sizeStyles = {
    sm: 'text-[11px] px-2 py-0.5',
    md: 'text-xs px-2.5 py-1',
  };

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full border tracking-wide uppercase font-mono ${currentVariant} ${sizeStyles[size]} ${className}`}
    >
      {children}
    </span>
  );
};
