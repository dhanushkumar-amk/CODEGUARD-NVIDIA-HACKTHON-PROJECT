import React from 'react';

export type StepAccentColor = 'azure' | 'violet' | 'emerald';

export interface HowItWorksStepProps {
  stepNumber: number;
  title: string;
  description: string;
  accentColor?: StepAccentColor;
  icon?: React.ReactNode;
  badge?: string;
  isLast?: boolean;
}

const dotColorClasses: Record<StepAccentColor, string> = {
  azure: 'bg-azure',
  violet: 'bg-violet',
  emerald: 'bg-emerald',
};

export const HowItWorksStep: React.FC<HowItWorksStepProps> = ({
  stepNumber,
  title,
  description,
  accentColor = 'azure',
  badge,
  isLast = false,
}) => {
  const dotClass = dotColorClasses[accentColor] || 'bg-azure';

  return (
    <div className="relative flex-1 flex flex-col text-left">
      <div className="flex items-center gap-2 mb-2">
        {/* Distinct accent dot: small colored circle */}
        <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${dotClass}`} />
        <span className="text-xs font-mono text-muted">
          0{stepNumber}
        </span>
        <h3 className="text-sm font-semibold text-ink">
          {title}
        </h3>
      </div>

      <p className="text-xs text-muted leading-relaxed mb-2.5">
        {description}
      </p>

      {badge && (
        <div className="mt-auto">
          <span className="inline-block text-[11px] font-mono px-2 py-0.5 rounded-control border border-line text-muted bg-surface-1">
            {badge}
          </span>
        </div>
      )}

      {!isLast && (
        <div className="hidden lg:block absolute -right-3 top-2.5 w-6 h-px bg-line pointer-events-none" />
      )}
    </div>
  );
};
