import React, { useEffect, useState } from 'react';
import { motion, animate } from 'framer-motion';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from 'recharts';
import { TrendingUp, Sparkles, ShieldAlert, ShieldCheck, ArrowRight } from 'lucide-react';

export interface ScoreGaugeProps {
  scoreBefore: number;
  scoreAfter: number;
  improvementPoints?: number;
  executiveSummary?: string | null;
  repoUrl?: string;
  branch?: string;
}

export const ScoreGauge: React.FC<ScoreGaugeProps> = ({
  scoreBefore,
  scoreAfter,
  improvementPoints,
  executiveSummary,
  repoUrl,
  branch,
}) => {
  const [animatedBefore, setAnimatedBefore] = useState<number>(0);
  const [animatedAfter, setAnimatedAfter] = useState<number>(0);

  const calculatedDelta =
    improvementPoints !== undefined
      ? improvementPoints
      : Math.round((scoreAfter - scoreBefore) * 10) / 10;

  useEffect(() => {
    const controlsBefore = animate(0, scoreBefore, {
      duration: 1.1,
      ease: 'easeOut',
      onUpdate: (latest) => setAnimatedBefore(Math.round(latest * 10) / 10),
    });

    const controlsAfter = animate(0, scoreAfter, {
      duration: 1.4,
      ease: 'easeOut',
      onUpdate: (latest) => setAnimatedAfter(Math.round(latest * 10) / 10),
    });

    return () => {
      controlsBefore.stop();
      controlsAfter.stop();
    };
  }, [scoreBefore, scoreAfter]);

  const chartData = [
    {
      name: 'Before Fixes',
      score: scoreBefore,
      displayLabel: 'Baseline',
      fill: '#f43f5e',
    },
    {
      name: 'After Remediation',
      score: scoreAfter,
      displayLabel: 'Remediated',
      fill: '#10b981',
    },
  ];

  return (
    <div
      data-testid="hero-score-section"
      className="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 sm:p-8 backdrop-blur-md shadow-2xl shadow-black/40 flex flex-col gap-6 relative overflow-hidden"
    >
      {/* Background ambient lighting */}
      <div className="absolute top-0 right-1/4 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none -z-10" />
      <div className="absolute bottom-0 left-1/4 w-96 h-96 bg-emerald-600/10 rounded-full blur-3xl pointer-events-none -z-10" />

      {/* Header Info */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800/80">
        <div>
          <span className="text-xs font-mono uppercase tracking-wider text-indigo-400 font-semibold flex items-center gap-1.5 mb-1">
            <Sparkles size={13} className="text-indigo-400" />
            Core Proof of Work &bull; WCAG 2.2 AA Compliance
          </span>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
            Compliance Score Improvement
          </h2>
          {repoUrl && (
            <p className="text-xs font-mono text-slate-400 mt-0.5 truncate max-w-lg">
              Repository: {repoUrl} {branch && `(${branch})`}
            </p>
          )}
        </div>

        {/* Big Delta Callout */}
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.4, delay: 0.2 }}
          data-testid="score-improvement-delta"
          className="self-start sm:self-center px-4 py-2.5 rounded-2xl bg-gradient-to-r from-emerald-500/20 via-teal-500/15 to-emerald-500/20 border border-emerald-500/40 text-emerald-300 shadow-lg shadow-emerald-950/40 flex items-center gap-2.5"
        >
          <div className="p-1.5 rounded-lg bg-emerald-500/20 border border-emerald-500/40 text-emerald-300">
            <TrendingUp size={18} />
          </div>
          <div>
            <div className="text-[10px] font-mono uppercase font-bold text-emerald-400 tracking-wider">
              Improvement Delta
            </div>
            <div className="text-xl sm:text-2xl font-black font-mono text-emerald-200">
              {calculatedDelta >= 0 ? `+${calculatedDelta}` : calculatedDelta} points
            </div>
          </div>
        </motion.div>
      </div>

      {/* Score Comparison Display Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
        {/* Left Side: Dual Score Big Display Cards */}
        <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Baseline Card */}
          <div
            data-testid="score-before-display"
            className="p-5 rounded-2xl bg-slate-950/70 border border-rose-500/30 flex flex-col justify-between gap-4 shadow-lg shadow-black/30"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-semibold uppercase tracking-wider text-rose-400">
                Baseline Score
              </span>
              <ShieldAlert size={16} className="text-rose-400" />
            </div>

            <div>
              <div className="text-4xl sm:text-5xl font-extrabold font-mono text-rose-400 tracking-tight">
                {animatedBefore}%
              </div>
              <div className="text-xs text-slate-400 mt-1">Pre-Remediation Accessibility</div>
            </div>

            <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden border border-slate-800">
              <motion.div
                className="bg-rose-500 h-full rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${Math.min(100, Math.max(0, scoreBefore))}%` }}
                transition={{ duration: 1, ease: 'easeOut' }}
              />
            </div>
          </div>

          {/* Remediated Card */}
          <div
            data-testid="score-after-display"
            className="p-5 rounded-2xl bg-slate-950/70 border border-emerald-500/40 flex flex-col justify-between gap-4 shadow-xl shadow-emerald-950/20"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-semibold uppercase tracking-wider text-emerald-400">
                Remediated Score
              </span>
              <ShieldCheck size={16} className="text-emerald-400" />
            </div>

            <div>
              <div className="text-4xl sm:text-5xl font-extrabold font-mono text-emerald-400 tracking-tight">
                {animatedAfter}%
              </div>
              <div className="text-xs text-emerald-300/80 mt-1">
                Verified in Nebius Sandboxes
              </div>
            </div>

            <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden border border-slate-800">
              <motion.div
                className="bg-emerald-500 h-full rounded-full shadow-sm shadow-emerald-500/50"
                initial={{ width: 0 }}
                animate={{ width: `${Math.min(100, Math.max(0, scoreAfter))}%` }}
                transition={{ duration: 1.2, ease: 'easeOut' }}
              />
            </div>
          </div>
        </div>

        {/* Right Side: Recharts Bar Comparison Chart */}
        <div className="lg:col-span-5 h-48 sm:h-52 bg-slate-950/60 rounded-2xl p-4 border border-slate-800 flex flex-col justify-between">
          <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider mb-1 flex items-center justify-between">
            <span>Score Delta Chart</span>
            <span className="text-emerald-400 font-bold flex items-center gap-1">
              Before <ArrowRight size={11} /> After
            </span>
          </div>

          <div className="w-full h-40">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                barSize={38}
              >
                <XAxis
                  dataKey="displayLabel"
                  stroke="#94a3b8"
                  fontSize={11}
                  tickLine={false}
                  axisLine={{ stroke: '#334155' }}
                />
                <YAxis
                  domain={[0, 100]}
                  stroke="#94a3b8"
                  fontSize={11}
                  tickLine={false}
                  axisLine={{ stroke: '#334155' }}
                  ticks={[0, 25, 50, 75, 100]}
                />
                <Tooltip
                  cursor={{ fill: 'rgba(255, 255, 255, 0.04)' }}
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload;
                      return (
                        <div className="bg-slate-900 border border-slate-700 px-3 py-1.5 rounded-lg shadow-xl text-xs font-mono">
                          <span className="text-slate-300 font-bold">{data.name}: </span>
                          <span style={{ color: data.fill }} className="font-extrabold">
                            {data.score}%
                          </span>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Bar dataKey="score" radius={[6, 6, 0, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Executive Summary Story Banner (Directly below score visualization) */}
      {executiveSummary && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.3 }}
          data-testid="executive-summary-story"
          className="p-5 sm:p-6 rounded-2xl bg-gradient-to-r from-indigo-950/60 via-slate-900/90 to-purple-950/60 border border-indigo-500/30 shadow-lg shadow-indigo-950/30 flex flex-col gap-2"
        >
          <div className="flex items-center gap-2 text-indigo-400 font-semibold text-xs sm:text-sm uppercase tracking-wider">
            <Sparkles size={16} className="text-indigo-400 shrink-0" />
            <span>Executive Audit Story &amp; Findings</span>
          </div>
          <p className="text-sm sm:text-base text-slate-200 leading-relaxed font-normal">
            {executiveSummary}
          </p>
        </motion.div>
      )}
    </div>
  );
};
