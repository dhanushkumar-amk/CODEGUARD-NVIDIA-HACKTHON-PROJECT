import React from 'react';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
} from 'recharts';

export interface ViolationsPieChartProps {
  statusCounts: {
    fixed_and_verified?: number;
    fixed_not_verified?: number;
    detected_only?: number;
    fix_failed?: number;
    verification_skipped?: number;
  };
  totalViolations: number;
}

// Segments colored exactly emerald/amber/coral/grey matching final_status
export const STATUS_CONFIG: Record<
  string,
  { label: string; color: string; description: string }
> = {
  fixed_and_verified: {
    label: 'Fixed & verified',
    color: '#1F9D55', // emerald
    description: 'Synthesized, applied, and verified in sandbox with 0 regressions',
  },
  fixed_not_verified: {
    label: 'Fixed (unverified)',
    color: '#F2A93C', // amber
    description: 'Fix generated but regression checks failed or timed out',
  },
  detected_only: {
    label: 'Detected only',
    color: '#6C707A', // grey
    description: 'Flagged by static scanner / AST heuristics; pending fix generation',
  },
  fix_failed: {
    label: 'Fix failed',
    color: '#E0562F', // coral
    description: 'Model was unable to synthesize a clean, syntax-valid patch',
  },
  verification_skipped: {
    label: 'Verification skipped',
    color: '#6C707A', // grey
    description: 'Sandbox verification was omitted or deferred',
  },
};

export const ViolationsPieChart: React.FC<ViolationsPieChartProps> = ({
  statusCounts,
  totalViolations,
}) => {
  const chartData = Object.entries(statusCounts)
    .filter(([_, count]) => (count || 0) > 0)
    .map(([statusKey, count]) => {
      const config = STATUS_CONFIG[statusKey] || {
        label: statusKey.replace(/_/g, ' '),
        color: '#6C707A',
      };
      return {
        name: config.label,
        key: statusKey,
        value: count || 0,
        color: config.color,
      };
    });

  if (totalViolations === 0 || chartData.length === 0) {
    return (
      <div
        data-testid="violations-pie-chart-empty"
        className="w-full py-8 text-center border border-line bg-surface-1"
      >
        <span className="text-sm font-medium text-ink">No defects to chart</span>
        <br />
        <span className="text-xs text-muted">
          All WCAG rules passed without actionable violations.
        </span>
      </div>
    );
  }

  return (
    <div
      data-testid="violations-pie-chart"
      className="w-full border border-line bg-paper p-5 flex flex-col sm:flex-row items-center justify-between gap-6"
    >
      {/* Donut */}
      <div className="relative w-44 h-44 sm:w-48 sm:h-48 shrink-0 flex items-center justify-center">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload;
                  const pct = Math.round((data.value / totalViolations) * 100);
                  return (
                    <div className="bg-paper border border-line px-3 py-1.5 rounded-control text-xs font-mono">
                      <div className="font-semibold" style={{ color: data.color }}>
                        {data.name}
                      </div>
                      <div className="text-ink">
                        {data.value} violations ({pct}%)
                      </div>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={72}
              paddingAngle={2}
              dataKey="value"
              strokeWidth={0}
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>

        {/* Center label */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="text-2xl font-bold font-mono text-ink">
            {totalViolations}
          </span>
          <span className="text-[10px] text-muted font-sans">
            total
          </span>
        </div>
      </div>

      {/* Legend: small colored squares + Public Sans labels */}
      <div className="flex-1 w-full flex flex-col gap-1.5 font-sans">
        <div className="text-xs text-muted font-medium mb-1">
          Remediation outcomes
        </div>

        {Object.entries(STATUS_CONFIG).map(([key, config]) => {
          const count = statusCounts[key as keyof typeof statusCounts] || 0;
          if (count === 0 && !['fixed_and_verified', 'fix_failed'].includes(key)) {
            return null;
          }
          const pct = totalViolations > 0 ? Math.round((count / totalViolations) * 100) : 0;

          return (
            <div
              key={key}
              className="flex items-center justify-between py-1.5 px-2 text-xs border-b border-line last:border-b-0"
            >
              <div className="flex items-center gap-2">
                {/* Small colored square */}
                <span
                  className="w-2.5 h-2.5 rounded-[2px] shrink-0"
                  style={{ backgroundColor: config.color }}
                />
                <span className="text-ink font-sans">{config.label}</span>
              </div>

              <div className="flex items-center gap-2 font-mono">
                <span className="font-semibold text-ink">{count}</span>
                <span className="text-muted text-[11px]">({pct}%)</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
