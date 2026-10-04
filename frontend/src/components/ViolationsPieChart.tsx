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

// Recolored using ONLY the severity/status palette
export const STATUS_CONFIG: Record<
  string,
  { label: string; color: string; description: string }
> = {
  fixed_and_verified: {
    label: 'Fixed & verified',
    color: '#2F7A4D',
    description: 'Synthesized, applied, and verified in sandbox with 0 regressions',
  },
  fixed_not_verified: {
    label: 'Fixed (unverified)',
    color: '#A68B3D',
    description: 'Fix generated but regression checks failed or timed out',
  },
  detected_only: {
    label: 'Detected only',
    color: '#6B7280',
    description: 'Flagged by static scanner / AST heuristics; pending fix generation',
  },
  fix_failed: {
    label: 'Fix failed',
    color: '#B5472A',
    description: 'Model was unable to synthesize a clean, syntax-valid patch',
  },
  verification_skipped: {
    label: 'Verification skipped',
    color: '#9CA3AF',
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
        color: '#9CA3AF',
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
        className="w-full py-8 text-center border border-border bg-surface-1"
      >
        <span className="text-sm font-medium text-foreground">No defects to chart</span>
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
      className="w-full border border-border bg-background p-5 flex flex-col sm:flex-row items-center justify-between gap-6"
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
                    <div className="bg-background border border-border px-3 py-1.5 rounded-control text-xs font-mono">
                      <div className="font-semibold" style={{ color: data.color }}>
                        {data.name}
                      </div>
                      <div className="text-foreground">
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
          <span className="text-2xl font-bold font-mono text-foreground">
            {totalViolations}
          </span>
          <span className="text-[10px] text-muted">
            total
          </span>
        </div>
      </div>

      {/* Legend */}
      <div className="flex-1 w-full flex flex-col gap-1.5">
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
              className="flex items-center justify-between py-1.5 px-2 text-xs border-b border-border last:border-b-0"
            >
              <div className="flex items-center gap-2">
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: config.color }}
                />
                <span className="text-foreground">{config.label}</span>
              </div>

              <div className="flex items-center gap-2 font-mono">
                <span className="font-semibold text-foreground">{count}</span>
                <span className="text-muted text-[11px]">({pct}%)</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
