import React, { useEffect, useState } from 'react';
import { animate } from 'framer-motion';
import { ArrowRight } from 'lucide-react';

export interface ScoreReadoutProps {
  scoreBefore?: number | null;
  scoreAfter?: number | null;
  improvementPoints?: number | null;
  executiveSummary?: string | null;
  repoUrl?: string;
  branch?: string;
}

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

  const isScoreAvailable = scoreBefore != null && scoreAfter != null;

  const calculatedDelta =
    improvementPoints !== undefined && improvementPoints !== null
      ? improvementPoints
      : isScoreAvailable
      ? Math.round(((scoreAfter ?? 0) - (scoreBefore ?? 0)) * 10) / 10
      : null;

  useEffect(() => {
    if (!isScoreAvailable) return;

    const controlsBefore = animate(0, scoreBefore ?? 0, {
      duration: 1.0,
      ease: 'easeOut',
      onUpdate: (latest) => setAnimatedBefore(Math.round(latest)),
    });

    const controlsAfter = animate(0, scoreAfter ?? 0, {
      duration: 1.3,
      ease: 'easeOut',
      onUpdate: (latest) => setAnimatedAfter(Math.round(latest)),
    });

    return () => {
      controlsBefore.stop();
      controlsAfter.stop();
    };
  }, [scoreBefore, scoreAfter, isScoreAvailable]);

  return (
    <div data-testid="hero-score-section" className="border border-line bg-paper p-6 text-left">
      {/* Section label */}
      <div className="text-[11px] font-mono uppercase tracking-[0.08em] text-muted mb-5">
        Compliance score improvement &bull; WCAG 2.2 AA
        {repoUrl && (
          <span className="font-mono ml-2 text-muted normal-case">
            {repoUrl} {branch && `(${branch})`}
          </span>
        )}
      </div>

      {/* Score numerals */}
      <div className="flex items-center gap-6 sm:gap-8 flex-wrap">
        {/* Before score */}
        <div data-testid="score-before-display">
          <div className="text-[11px] font-mono uppercase tracking-[0.08em] text-muted mb-1">
            Before
          </div>
          {isScoreAvailable ? (
            <div className="text-5xl sm:text-6xl font-sans font-bold text-coral tracking-tight leading-none">
              {animatedBefore}<span className="text-3xl sm:text-4xl font-sans text-coral/80">%</span>
            </div>
          ) : (
            <div className="text-2xl sm:text-3xl font-sans font-bold text-muted tracking-tight leading-none">
              Unavailable
            </div>
          )}
        </div>

        {/* Thin primary connecting line with arrow */}
        <div className="flex items-center gap-2 flex-1 min-w-[80px] max-w-[200px] self-center">
          <div className="h-0.5 flex-1 bg-primary" />
          <ArrowRight size={18} className="text-primary shrink-0" strokeWidth={2} />
        </div>

        {/* After score */}
        <div data-testid="score-after-display">
          <div className="text-[11px] font-mono uppercase tracking-[0.08em] text-muted mb-1">
            After
          </div>
          {isScoreAvailable ? (
            <div className="text-5xl sm:text-6xl font-sans font-bold text-emerald tracking-tight leading-none">
              {animatedAfter}<span className="text-3xl sm:text-4xl font-sans text-emerald/80">%</span>
            </div>
          ) : (
            <div className="text-2xl sm:text-3xl font-sans font-bold text-amber tracking-tight leading-none">
              Unverified
            </div>
          )}
        </div>

        {/* Improvement points / Unverified pill */}
        <div
          data-testid="score-improvement-delta"
          className={`px-3 py-1.5 rounded-[6px] font-mono font-bold text-sm sm:text-base self-center ${
            isScoreAvailable
              ? 'bg-emerald/10 border border-emerald/20 text-emerald'
              : 'bg-amber/10 border border-amber/20 text-amber'
          }`}
        >
          {isScoreAvailable
            ? (calculatedDelta! >= 0 ? `+${calculatedDelta}` : calculatedDelta) + ' points'
            : 'Sandbox offline — Fixes unverified'}
        </div>
      </div>

      {/* Executive summary */}
      {executiveSummary && (
        <div
          data-testid="executive-summary-story"
          className="mt-6 pt-4 border-t border-line"
        >
          <div className="text-[11px] font-mono uppercase tracking-[0.08em] text-muted mb-1.5">
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
