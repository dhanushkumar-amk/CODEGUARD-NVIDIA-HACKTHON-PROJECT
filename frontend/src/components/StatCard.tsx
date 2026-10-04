import React from 'react';

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
  testId,
  className = '',
}) => {
  return (
    <div
      data-testid={testId}
      className={`border border-border bg-background p-4 flex flex-col justify-between gap-2 ${className}`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs text-muted font-medium">
          {label}
        </span>
        {icon && (
          <div className="text-muted">
            {icon}
          </div>
        )}
      </div>

      <div>
        <div className="text-2xl font-bold tracking-tight font-mono text-foreground">
          {value}
        </div>
        {subtext && (
          <div className="text-[11px] text-muted mt-0.5">
            {subtext}
          </div>
        )}
      </div>
    </div>
  );
};
