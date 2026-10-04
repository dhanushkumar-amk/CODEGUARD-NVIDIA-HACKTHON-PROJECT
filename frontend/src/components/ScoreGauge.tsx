import React, { useEffect, useState } from 'react';
import { animate } from 'framer-motion';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  ReferenceDot,
  YAxis,
} from 'recharts';

export interface ScoreReadoutProps {
  scoreBefore: number;
  scoreAfter: number;
  improvementPoints?: number;
  executiveSummary?: string | null;
  repoUrl?: string;
  branch?: string;
}

/**
 * ScoreReadout replaces ScoreGauge.
 * Large IBM Plex Mono numerals with a thin horizontal sparkline showing
 * before vs after as two marks on one line.
 * One motion moment: the score counts up on page load.
 */
export const ScoreReadout: React.FC<ScoreReadoutProps> = ({
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
      duration: 1.0,
      ease: 'easeOut',
      onUpdate: (latest) => setAnimatedBefore(Math.round(latest)),
    });

    const controlsAfter = animate(0, scoreAfter, {
      duration: 1.3,
      ease: 'easeOut',
      onUpdate: (latest) => setAnimatedAfter(Math.round(latest)),
    });

    return () => {
      controlsBefore.stop();
      controlsAfter.stop();
    };
  }, [scoreBefore, scoreAfter]);

  // Sparkline data: a simple 2-point line from before to after
  const sparklineData = [
    { x: 0, score: scoreBefore },
    { x: 1, score: scoreAfter },
  ];

  return (
    <div data-testid="hero-score-section" className="border border-border bg-background p-6">
      {/* Section label */}
      <div className="text-xs text-muted font-medium mb-4">
        Compliance score improvement &middot; WCAG 2.2 AA
        {repoUrl && (
          <span className="font-mono ml-2 text-muted/70">
            {repoUrl} {branch && `(${branch})`}
          </span>
        )}
      </div>

      {/* Score numerals + sparkline row */}
      <div className="flex items-end gap-8 flex-wrap">
        {/* Before score */}
        <div data-testid="score-before-display">
          <div className="text-xs text-muted mb-1">Before</div>
          <div className="text-5xl sm:text-6xl font-bold font-mono text-foreground/40 tracking-tight leading-none">
            {animatedBefore}<span className="text-3xl sm:text-4xl">%</span>
          </div>
        </div>

        {/* Sparkline: thin horizontal bar with two marks */}
        <div className="flex-1 min-w-[120px] max-w-[280px] h-12 self-center">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={sparklineData} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
              <YAxis domain={[0, 100]} hide />
              <Line
                type="linear"
                dataKey="score"
                stroke="var(--border)"
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
              />
              <ReferenceDot
                x={0}
                y={scoreBefore}
                r={5}
                fill="var(--foreground)"
                fillOpacity={0.25}
                stroke="var(--foreground)"
                strokeWidth={1.5}
                strokeOpacity={0.4}
              />
              <ReferenceDot
                x={1}
                y={scoreAfter}
                r={5}
                fill="var(--primary)"
                stroke="var(--primary)"
                strokeWidth={1.5}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* After score */}
        <div data-testid="score-after-display">
          <div className="text-xs text-muted mb-1">After</div>
          <div className="text-5xl sm:text-6xl font-bold font-mono text-primary tracking-tight leading-none">
            {animatedAfter}<span className="text-3xl sm:text-4xl">%</span>
          </div>
        </div>

        {/* Delta */}
        <div
          data-testid="score-improvement-delta"
          className="px-3 py-2 border border-border bg-surface-1 rounded-control self-center"
        >
          <div className="text-xs text-muted mb-0.5">Delta</div>
          <div className="text-2xl font-bold font-mono text-primary tracking-tight">
            {calculatedDelta >= 0 ? `+${calculatedDelta}` : calculatedDelta}
          </div>
        </div>
      </div>

      {/* Executive summary */}
      {executiveSummary && (
        <div
          data-testid="executive-summary-story"
          className="mt-6 pt-4 border-t border-border"
        >
          <div className="text-xs text-muted font-medium mb-1.5">
            Executive summary
          </div>
          <p className="text-sm text-foreground leading-relaxed">
            {executiveSummary}
          </p>
        </div>
      )}
    </div>
  );
};

// Keep backward-compatible export name
export { ScoreReadout as ScoreGauge };
