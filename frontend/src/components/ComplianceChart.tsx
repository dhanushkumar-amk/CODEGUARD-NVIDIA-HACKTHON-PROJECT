import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
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
    { name: 'Before', score: scoreBefore, fill: '#6B7280' },
    { name: 'After', score: scoreAfter, fill: '#2F5DA8' },
  ];

  return (
    <div className="bg-background border border-border p-4">
      <h3 className="text-xs font-semibold text-muted mb-3">
        Compliance score comparison
      </h3>
      <div className="h-44">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <XAxis dataKey="name" stroke="#6B7280" fontSize={12} tickLine={false} />
            <YAxis stroke="#6B7280" fontSize={12} domain={[0, 100]} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#FAFAF8',
                borderColor: '#E4E2DD',
                borderRadius: '4px',
                color: '#1C1D21',
                fontSize: '12px',
              }}
            />
            <Bar dataKey="score" radius={[2, 2, 0, 0]}>
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
