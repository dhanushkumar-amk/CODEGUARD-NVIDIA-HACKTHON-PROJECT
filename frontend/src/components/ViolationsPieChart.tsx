import React from 'react';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
} from 'recharts';
import { CheckCircle2, AlertTriangle, ShieldX, Eye } from 'lucide-react';

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

export const STATUS_CONFIG: Record<
  string,
  { label: string; color: string; icon: React.ReactNode; description: string }
> = {
  fixed_and_verified: {
    label: 'Fixed & Verified',
    color: '#10b981',
    icon: <CheckCircle2 size={13} className="text-emerald-400" />,
    description: 'Synthesized, applied, and verified in sandbox with 0 regressions',
  },
  fixed_not_verified: {
    label: 'Fixed (Unverified)',
    color: '#f59e0b',
    icon: <AlertTriangle size={13} className="text-amber-400" />,
    description: 'Fix generated but regression checks failed or timed out',
  },
  detected_only: {
    label: 'Detected Only',
    color: '#6366f1',
    icon: <Eye size={13} className="text-indigo-400" />,
    description: 'Flagged by static scanner / AST heuristics; pending fix generation',
  },
  fix_failed: {
    label: 'Fix Failed',
    color: '#f43f5e',
    icon: <ShieldX size={13} className="text-rose-400" />,
    description: 'Model was unable to synthesize a clean, syntax-valid patch',
  },
  verification_skipped: {
    label: 'Verification Skipped',
    color: '#64748b',
    icon: <Eye size={13} className="text-slate-400" />,
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
        color: '#94a3b8',
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
        className="w-full h-56 flex flex-col items-center justify-center text-center p-4 rounded-xl bg-slate-950/40 border border-slate-800"
      >
        <CheckCircle2 size={32} className="text-emerald-400 mb-2" />
        <span className="text-sm font-semibold text-slate-200">No Defects to Chart</span>
        <span className="text-xs text-slate-400 mt-0.5">
          All WCAG rules passed without actionable violations.
        </span>
      </div>
    );
  }

  return (
    <div
      data-testid="violations-pie-chart"
      className="w-full bg-slate-900/80 border border-slate-800 rounded-2xl p-5 backdrop-blur-md shadow-xl flex flex-col sm:flex-row items-center justify-between gap-6"
    >
      {/* Donut Chart */}
      <div className="relative w-48 h-48 sm:w-56 sm:h-56 shrink-0 flex items-center justify-center">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload;
                  const pct = Math.round((data.value / totalViolations) * 100);
                  return (
                    <div className="bg-slate-900 border border-slate-700 px-3 py-1.5 rounded-lg shadow-xl text-xs font-mono">
                      <div className="font-bold" style={{ color: data.color }}>
                        {data.name}
                      </div>
                      <div className="text-slate-300">
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
              innerRadius={55}
              outerRadius={80}
              paddingAngle={4}
              dataKey="value"
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} stroke="#0f172a" strokeWidth={2} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>

        {/* Center label */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="text-2xl sm:text-3xl font-black font-mono text-white">
            {totalViolations}
          </span>
          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
            Total Issues
          </span>
        </div>
      </div>

      {/* Status Legend Breakdown */}
      <div className="flex-1 w-full flex flex-col gap-2.5">
        <div className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold mb-1">
          Remediation Outcomes
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
              className="flex items-center justify-between p-2.5 rounded-xl bg-slate-950/50 border border-slate-850 hover:border-slate-800 transition text-xs"
            >
              <div className="flex items-center gap-2.5">
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: config.color }}
                />
                <span className="font-medium text-slate-200">{config.label}</span>
              </div>

              <div className="flex items-center gap-2 font-mono">
                <span className="font-bold text-slate-100">{count}</span>
                <span className="text-slate-500 text-[11px]">({pct}%)</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
