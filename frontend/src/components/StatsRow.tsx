import React from 'react';

export interface StatsRowProps {
  violationsFound?: string | number;
  fixesVerified?: string | number;
  complianceScore?: string;
  avgScanTime?: string;
}

export const StatsRow: React.FC<StatsRowProps> = ({
  violationsFound = '12',
  fixesVerified = '12 / 12',
  complianceScore = '98%',
  avgScanTime = '14.2s',
}) => {
  const stats = [
    { label: 'VIOLATIONS FOUND', value: violationsFound },
    { label: 'FIXES VERIFIED', value: fixesVerified },
    { label: 'COMPLIANCE SCORE', value: complianceScore },
    { label: 'AVG SCAN TIME', value: avgScanTime },
  ];

  return (
    <section
      data-testid="stats-row"
      className="w-full border-t border-line py-12 md:py-24"
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-line text-left">
        {stats.map((stat, idx) => (
          <div
            key={idx}
            className="py-6 sm:py-0 px-6 md:px-8 first:sm:pl-0 last:sm:pr-0 flex flex-col gap-6"
          >
            <span className="text-[11px] font-mono uppercase tracking-[0.08em] text-muted">
              {stat.label}
            </span>
            <span className="text-3xl sm:text-4xl font-bold font-sans text-ink tracking-tight">
              {stat.value}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
};
