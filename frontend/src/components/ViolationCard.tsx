import React from 'react';
import { AlertCircle, ArrowRight } from 'lucide-react';

export interface AccessibilityViolation {
  id: string;
  ruleId: string;
  impact: 'critical' | 'serious' | 'moderate' | 'minor';
  description: string;
  helpUrl: string;
  selector: string;
  filePath: string;
  lineNumber?: number;
}

interface ViolationCardProps {
  violation: AccessibilityViolation;
  onGenerateFix?: (id: string) => void;
  isFixing?: boolean;
}

export const ViolationCard: React.FC<ViolationCardProps> = ({
  violation,
  onGenerateFix,
  isFixing,
}) => {
  const impactColors = {
    critical: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
    serious: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    moderate: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
    minor: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
  };

  return (
    <div className="bg-slate-900/70 border border-slate-800 hover:border-slate-700 rounded-xl p-4 transition">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <AlertCircle size={18} className="text-rose-400 shrink-0" />
          <span className="font-mono text-sm font-semibold text-slate-100">{violation.ruleId}</span>
          <span className={`text-xs px-2 py-0.5 rounded-full border ${impactColors[violation.impact]}`}>
            {violation.impact}
          </span>
        </div>
        {onGenerateFix && (
          <button
            onClick={() => onGenerateFix(violation.id)}
            disabled={isFixing}
            className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg bg-indigo-600/80 hover:bg-indigo-600 text-white transition disabled:opacity-50"
          >
            {isFixing ? 'Synthesizing...' : 'Synthesize Fix'}
            <ArrowRight size={13} />
          </button>
        )}
      </div>

      <p className="text-xs text-slate-300 mt-2">{violation.description}</p>

      <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-400 font-mono">
        <span className="bg-slate-800/80 px-2 py-1 rounded">
          {violation.filePath}{violation.lineNumber ? `:${violation.lineNumber}` : ''}
        </span>
        <code className="text-indigo-300 truncate max-w-xs">{violation.selector}</code>
      </div>
    </div>
  );
};
