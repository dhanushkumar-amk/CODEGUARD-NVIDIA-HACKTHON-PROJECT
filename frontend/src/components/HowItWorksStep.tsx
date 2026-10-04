import React from 'react';

export interface HowItWorksStepProps {
  stepNumber: number;
  title: string;
  description: string;
  icon: React.ReactNode;
  badge?: string;
  isLast?: boolean;
}

export const HowItWorksStep: React.FC<HowItWorksStepProps> = ({
  stepNumber,
  title,
  description,
  icon,
  badge,
  isLast = false,
}) => {
  return (
    <div className="relative flex-1 flex flex-col">
      <div className="flex items-center gap-3 mb-2">
        <div className="w-8 h-8 rounded-control border border-border bg-surface-1 flex items-center justify-center text-primary">
          {icon}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-muted">
            {stepNumber}
          </span>
          <h3 className="text-sm font-semibold text-foreground">
            {title}
          </h3>
        </div>
      </div>

      <p className="text-xs text-muted leading-relaxed mb-2">
        {description}
      </p>

      {badge && (
        <div className="mt-auto">
          <span className="inline-block text-[11px] font-mono px-2 py-0.5 rounded-control border border-border text-muted bg-surface-1">
            {badge}
          </span>
        </div>
      )}

      {!isLast && (
        <div className="hidden lg:block absolute -right-3 top-4 w-6 h-px bg-border pointer-events-none" />
      )}
    </div>
  );
};
