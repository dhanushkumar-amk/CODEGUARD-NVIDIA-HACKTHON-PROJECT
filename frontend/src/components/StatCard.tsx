import React from 'react';

export interface StatCardProps {
  label: string;
  value: React.ReactNode;
  subtext?: string;
  icon?: React.ReactNode;
  variant?: 'azure' | 'emerald' | 'coral' | 'amber' | 'violet' | 'slate';
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
      className={`border border-line bg-paper p-4 flex flex-col justify-between gap-2 text-left font-sans ${className}`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-[11px] font-mono uppercase tracking-[0.08em] text-muted">
          {label}
        </span>
        {icon && (
          <div className="text-muted shrink-0">
            {icon}
          </div>
        )}
      </div>

      <div>
        <div className="text-2xl sm:text-3xl font-bold font-sans text-ink tracking-tight">
          {value}
        </div>
        {subtext && (
          <div className="text-[11px] text-muted mt-1 font-sans">
            {subtext}
          </div>
        )}
      </div>
    </div>
  );
};
