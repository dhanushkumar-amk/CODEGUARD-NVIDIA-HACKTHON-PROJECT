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
  | 'default';

export interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
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

  const variantStyles: Record<string, string> = {
    critical: 'bg-rose-500/15 text-rose-400 border-rose-500/30',
    high: 'bg-rose-500/15 text-rose-400 border-rose-500/30',
    serious: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
    medium: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
    moderate: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
    low: 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30',
    minor: 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30',
    success: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    info: 'bg-indigo-500/15 text-indigo-400 border-indigo-500/30',
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
