import React from 'react';
import { AlertCircle, ArrowRight, Hash, Star } from 'lucide-react';
import { Violation, ViolationCategory } from '../types';
import { Badge } from './Badge';

export const CATEGORY_LABELS: Record<string, string> = {
  MISSING_ALT_TEXT: 'Missing Alt Text',
  UNLABELED_FORM_FIELD: 'Unlabeled Form Field',
  NON_INTERACTIVE_CLICK: 'Non-Interactive Click',
  EMPTY_LINK_OR_BUTTON: 'Empty Link or Button',
  LOW_CONTRAST: 'Low Contrast',
  HEADING_ORDER: 'Heading Order',
  MISSING_LANDMARK: 'Missing Landmark',
  KEYBOARD_TRAP: 'Keyboard Trap',
  MISSING_LANG: 'Missing Lang',
  ARIA_MISUSE: 'ARIA Misuse',
  FOCUS_MANAGEMENT: 'Focus Management',
  OTHER: 'Other Accessibility Issue',
};

export function formatCategoryLabel(category?: ViolationCategory | string): string {
  if (!category) return 'Accessibility Issue';
  if (CATEGORY_LABELS[category]) return CATEGORY_LABELS[category];

  // Convert SCREAMING_SNAKE_CASE or kebab-case to Title Case
  return category
    .replace(/[_-]/g, ' ')
    .toLowerCase()
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

export interface ViolationCardProps {
  violation: Violation;
  onGenerateFix?: (id: string) => void;
  isFixing?: boolean;
}

export const ViolationCard: React.FC<ViolationCardProps> = ({
  violation,
  onGenerateFix,
  isFixing,
}) => {
  const categoryLabel = formatCategoryLabel(violation.category);
  const severityLabel = violation.severity || 'high';

  return (
    <div className="bg-slate-900/80 border border-slate-800 hover:border-slate-700 rounded-xl p-4 transition flex flex-col gap-3 shadow-lg shadow-black/20">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          {violation.priority_rank && (
            <span className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full text-[11px] font-mono font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
              <Hash size={11} />
              {violation.priority_rank}
            </span>
          )}

          {/* Color-coded severity badge (critical=red, high=orange, medium=yellow, low=gray) */}
          <Badge variant={severityLabel} size="sm">
            {severityLabel}
          </Badge>

          {/* Category readable label */}
          <span className="font-semibold text-sm text-slate-100">
            {categoryLabel}
          </span>

          {violation.severity_score !== undefined && violation.severity_score !== null && (
            <span className="text-[11px] font-mono text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700/50">
              Score: <strong className="text-slate-200">{violation.severity_score}</strong>/10
            </span>
          )}
        </div>

        {onGenerateFix && (
          <button
            onClick={() => onGenerateFix(violation.id)}
            disabled={isFixing}
            className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg bg-indigo-600/90 hover:bg-indigo-600 text-white transition disabled:opacity-50 self-start sm:self-auto shrink-0"
          >
            {isFixing ? 'Synthesizing...' : 'Synthesize Fix'}
            <ArrowRight size={13} />
          </button>
        )}
      </div>

      <div className="flex items-center gap-2 font-mono text-xs text-indigo-400">
        <span>Rule: {violation.type}</span>
        {violation.wcag_criterion && (
          <>
            <span className="text-slate-600">•</span>
            <span className="text-slate-400">{violation.wcag_criterion}</span>
          </>
        )}
      </div>

      <p className="text-xs text-slate-300 leading-relaxed">{violation.description}</p>

      {violation.context_snippet && (
        <pre className="p-2.5 rounded-lg bg-slate-950 border border-slate-800/80 text-xs font-mono text-rose-300/90 overflow-x-auto whitespace-pre-wrap">
          {violation.context_snippet}
        </pre>
      )}

      <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 font-mono mt-1">
        <span className="bg-slate-800/80 px-2 py-1 rounded text-slate-300 border border-slate-700/40">
          {violation.file}
          {violation.line ? `:${violation.line}` : ''}
        </span>
        {violation.selector && (
          <code className="text-indigo-300 bg-indigo-950/40 px-2 py-1 rounded border border-indigo-900/40 truncate max-w-xs">
            {violation.selector}
          </code>
        )}
      </div>
    </div>
  );
};
