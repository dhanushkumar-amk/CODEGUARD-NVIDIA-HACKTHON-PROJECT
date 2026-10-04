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
  | 'warning'
  | 'danger'
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

  // Muted severity palette — only used on badges, never decoratively
  const variantStyles: Record<string, string> = {
    critical: 'bg-severity-critical/10 text-severity-critical border-severity-critical/25',
    high: 'bg-severity-high/10 text-severity-high border-severity-high/25',
    serious: 'bg-severity-high/10 text-severity-high border-severity-high/25',
    medium: 'bg-severity-medium/10 text-severity-medium border-severity-medium/25',
    moderate: 'bg-severity-medium/10 text-severity-medium border-severity-medium/25',
    low: 'bg-severity-low/10 text-severity-low border-severity-low/25',
    minor: 'bg-severity-low/10 text-severity-low border-severity-low/25',
    success: 'bg-[#2F7A4D]/10 text-[#2F7A4D] border-[#2F7A4D]/25',
    warning: 'bg-severity-medium/10 text-severity-medium border-severity-medium/25',
    danger: 'bg-destructive/10 text-destructive border-destructive/25',
    info: 'bg-primary/10 text-primary border-primary/25',
    default: 'bg-surface-1 text-muted border-border',
  };

  const currentVariant = variantStyles[normalizedVariant] || variantStyles.default;

  const sizeStyles = {
    sm: 'text-[11px] px-2 py-0.5',
    md: 'text-xs px-2.5 py-0.5',
  };

  return (
    <span
      className={`inline-flex items-center font-medium rounded-control border font-mono ${currentVariant} ${sizeStyles[size]} ${className}`}
    >
      {children}
    </span>
  );
};
