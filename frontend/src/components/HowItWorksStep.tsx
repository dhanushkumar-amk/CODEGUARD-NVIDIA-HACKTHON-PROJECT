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
    <div className="relative flex-1 flex flex-col group">
      <div className="flex items-center gap-3 mb-2">
        <div className="w-9 h-9 rounded-lg bg-indigo-950/60 border border-indigo-500/30 flex items-center justify-center text-indigo-400 group-hover:border-indigo-400 group-hover:scale-105 transition-all duration-200 shadow-md shadow-indigo-950/40">
          {icon}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-bold text-slate-500 uppercase tracking-wider">
            0{stepNumber}
          </span>
          <h3 className="text-sm font-semibold text-slate-100 group-hover:text-indigo-300 transition-colors">
            {title}
          </h3>
        </div>
      </div>

      <p className="text-xs text-slate-400 leading-relaxed mb-2.5">
        {description}
      </p>

      {badge && (
        <div className="mt-auto">
          <span className="inline-block text-[11px] font-mono px-2 py-0.5 rounded bg-slate-900/90 border border-slate-800 text-slate-300">
            {badge}
          </span>
        </div>
      )}

      {/* Visual connector line for desktop */}
      {!isLast && (
        <div className="hidden lg:block absolute -right-3 top-4 w-6 h-[1px] bg-gradient-to-r from-slate-700 to-transparent pointer-events-none" />
      )}
    </div>
  );
};
