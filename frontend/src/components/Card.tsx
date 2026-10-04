import React from 'react';

export type CardSeverity = 'critical' | 'high' | 'medium' | 'low' | 'none';

export interface CardProps {
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  headerAction?: React.ReactNode;
  severity?: CardSeverity;
  children: React.ReactNode;
  className?: string;
  bodyClassName?: string;
}

const severityStripeClasses: Record<CardSeverity, string> = {
  critical: 'border-l-[3px] border-l-coral',
  high: 'border-l-[3px] border-l-amber',
  medium: 'border-l-[3px] border-l-amber',
  low: 'border-l-[3px] border-l-[#6C707A]',
  none: '',
};

export const Card: React.FC<CardProps> = ({
  title,
  subtitle,
  headerAction,
  severity = 'none',
  children,
  className = '',
  bodyClassName = '',
}) => {
  const stripeClass = severityStripeClasses[severity] || '';

  return (
    <div
      className={`bg-[#FFFFFF] border border-line overflow-hidden ${stripeClass} ${className}`}
    >
      {(title || subtitle || headerAction) && (
        <div className="px-5 py-4 border-b border-line flex items-center justify-between gap-4">
          <div>
            {title && typeof title === 'string' ? (
              <h3 className="text-sm font-semibold text-ink">{title}</h3>
            ) : (
              title
            )}
            {subtitle && <p className="text-xs text-muted mt-0.5">{subtitle}</p>}
          </div>
          {headerAction && <div>{headerAction}</div>}
        </div>
      )}
      <div className={`p-5 ${bodyClassName}`}>{children}</div>
    </div>
  );
};
