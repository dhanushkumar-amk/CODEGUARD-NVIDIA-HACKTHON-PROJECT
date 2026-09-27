import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

interface ComplianceChartProps {
  scoreBefore: number;
  scoreAfter: number;
}

export const ComplianceChart: React.FC<ComplianceChartProps> = ({
  scoreBefore,
  scoreAfter,
}) => {
  const data = [
    { name: 'Initial Scan', score: scoreBefore, fill: '#f43f5e' },
    { name: 'Remediated & Verified', score: scoreAfter, fill: '#10b981' },
  ];

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-2">
        Accessibility Compliance Score (WCAG 2.2 AA)
      </h3>
      <p className="text-xs text-slate-400 mb-4">
        Comparison of repository score before and after Nemotron remediation & sandbox verification.
      </p>

      <div className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ left: 20, right: 30, top: 10, bottom: 10 }}>
            <XAxis type="number" domain={[0, 100]} stroke="#64748b" />
            <YAxis type="category" dataKey="name" stroke="#94a3b8" width={140} tick={{ fontSize: 12 }} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#0f172a',
                borderColor: '#334155',
                borderRadius: '8px',
                color: '#f8fafc',
              }}
              formatter={(value) => [`${value}%`, 'Score']}
            />
            <Bar dataKey="score" radius={[0, 6, 6, 0]} barSize={28}>
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
