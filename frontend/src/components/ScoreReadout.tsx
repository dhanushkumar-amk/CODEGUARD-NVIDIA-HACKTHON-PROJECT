import React, { useEffect, useState } from 'react';
import { animate } from 'framer-motion';
import { ArrowRight } from 'lucide-react';

export interface ScoreReadoutProps {
  scoreBefore: number;
  scoreAfter: number;
  improvementPoints?: number;
  executiveSummary?: string | null;
  repoUrl?: string;
  branch?: string;
}

/**
 * ScoreReadout:
 * score_before in coral Source Serif 4 numerals,
 * score_after in emerald Source Serif 4 numerals,
 * connected by a thin azure line/arrow between them,
 * improvement_points shown as a small emerald pill.
 * Source Serif 4 used ONLY for score numerals here.
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

  return (
    <div data-testid="hero-score-section" className="border border-line bg-paper p-6 text-left">
      {/* Section label */}
      <div className="text-xs text-muted font-medium mb-4">
        Compliance score improvement &middot; WCAG 2.2 AA
        {repoUrl && (
          <span className="font-mono ml-2 text-muted">
            {repoUrl} {branch && `(${branch})`}
          </span>
        )}
      </div>

      {/* Score numerals in Source Serif 4 connected by thin azure line/arrow */}
      <div className="flex items-center gap-6 sm:gap-8 flex-wrap">
        {/* Before score: coral Source Serif 4 */}
        <div data-testid="score-before-display">
          <div className="text-xs text-muted mb-1 font-sans">Before</div>
          <div className="text-5xl sm:text-6xl font-serif font-bold text-coral tracking-tight leading-none">
            {animatedBefore}<span className="text-3xl sm:text-4xl font-sans text-coral/80">%</span>
          </div>
        </div>

        {/* Thin azure connecting line with arrow */}
        <div className="flex items-center gap-2 flex-1 min-w-[80px] max-w-[200px] self-center">
          <div className="h-0.5 flex-1 bg-azure" />
          <ArrowRight size={18} className="text-azure shrink-0" strokeWidth={2} />
        </div>

        {/* After score: emerald Source Serif 4 */}
        <div data-testid="score-after-display">
          <div className="text-xs text-muted mb-1 font-sans">After</div>
          <div className="text-5xl sm:text-6xl font-serif font-bold text-emerald tracking-tight leading-none">
            {animatedAfter}<span className="text-3xl sm:text-4xl font-sans text-emerald/80">%</span>
          </div>
        </div>

        {/* Improvement points: small emerald pill */}
        <div
          data-testid="score-improvement-delta"
          className="px-3 py-1.5 rounded-control bg-emerald/10 border border-emerald/20 text-emerald font-mono font-bold text-sm sm:text-base self-center"
        >
          {calculatedDelta >= 0 ? `+${calculatedDelta}` : calculatedDelta} points
        </div>
      </div>

      {/* Executive summary */}
      {executiveSummary && (
        <div
          data-testid="executive-summary-story"
          className="mt-6 pt-4 border-t border-line"
        >
          <div className="text-xs text-muted font-medium mb-1 font-sans">
            Executive summary
          </div>
          <p className="text-sm font-sans text-ink leading-relaxed">
            {executiveSummary}
          </p>
        </div>
      )}
    </div>
  );
};

export { ScoreReadout as ScoreGauge };
