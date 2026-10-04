import React from 'react';

export type BadgeVariant =
  | 'critical'
  | 'high'
  | 'serious'
  | 'medium'
  | 'moderate'
  | 'low'
  | 'minor'
  | 'fixed_and_verified'
  | 'fix_failed'
  | 'fixed_not_verified'
  | 'detected_only'
  | 'success'
  | 'info'
  | 'warning'
  | 'danger'
  | 'violet'
  | 'ai'
  | 'default';

export interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: 'sm' | 'md';
  className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  // Severity badges: solid-but-soft background tints
  critical: 'bg-coral/10 text-coral border border-coral/20',
  serious: 'bg-coral/10 text-coral border border-coral/20',
  high: 'bg-amber/10 text-amber border border-amber/20',
  medium: 'bg-amber/10 text-amber border border-amber/20',
  moderate: 'bg-amber/10 text-amber border border-amber/20',
  low: 'bg-[#6C707A]/10 text-muted border border-line',
  minor: 'bg-[#6C707A]/10 text-muted border border-line',

  // Status badges: directly mapped to emerald, coral, amber
  fixed_and_verified: 'bg-emerald/10 text-emerald border border-emerald/20',
  fix_failed: 'bg-coral/10 text-coral border border-coral/20',
  fixed_not_verified: 'bg-amber/10 text-amber border border-amber/20',
  detected_only: 'bg-[#6C707A]/10 text-muted border border-line',

  // Semantic shortcuts
  success: 'bg-emerald/10 text-emerald border border-emerald/20',
  danger: 'bg-coral/10 text-coral border border-coral/20',
  warning: 'bg-amber/10 text-amber border border-amber/20',
  info: 'bg-azure/10 text-azure border border-azure/20',

  // AI model layer
  violet: 'bg-violet/10 text-violet border border-violet/20',
  ai: 'bg-violet/10 text-violet border border-violet/20',

  default: 'bg-[#6C707A]/10 text-muted border border-line',
};

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  size = 'md',
  className = '',
}) => {
  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-0.5 text-xs';
  const colorClass = variantStyles[variant] || variantStyles.default;

  return (
    <span
      className={`inline-flex items-center gap-1 font-medium rounded-control transition-colors ${sizeClasses} ${colorClass} ${className}`}
    >
      {children}
    </span>
  );
};
