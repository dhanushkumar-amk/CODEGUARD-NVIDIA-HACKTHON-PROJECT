import React, { useState } from 'react';
import { ArrowRight, ChevronDown, ChevronUp, Cpu, FileText, Hash } from 'lucide-react';
import { DiagnosedViolation, Violation, ViolationCategory } from '../types';
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
  violation: Violation | DiagnosedViolation;
  onGenerateFix?: (id: string) => void;
  isFixing?: boolean;
}

export const ViolationCard: React.FC<ViolationCardProps> = ({
  violation,
  onGenerateFix,
  isFixing,
}) => {
  const [showTechnicalDetails, setShowTechnicalDetails] = useState<boolean>(false);
  const categoryLabel = formatCategoryLabel(violation.category);
  const severityLabel = violation.severity || 'high';

  // Cast to DiagnosedViolation to read Phase 14 & 15 fields
  const diagnosed = violation as DiagnosedViolation;
  const hasTechnicalDetails = Boolean(
    diagnosed.root_cause || diagnosed.user_impact || diagnosed.fix_strategy
  );

  return (
    <div className="bg-slate-900/80 border border-slate-800 hover:border-slate-700/80 rounded-xl p-4 sm:p-5 transition flex flex-col gap-3.5 shadow-lg shadow-black/20">
      {/* Top Header Row */}
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

          {diagnosed.diagnosis_source && (
            <span className="inline-flex items-center gap-1 text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700/40">
              {diagnosed.diagnosis_source === 'llm' ? (
                <>
                  <Cpu size={11} className="text-purple-400" />
                  Ultra AI
                </>
              ) : (
                <>
                  <FileText size={11} className="text-slate-400" />
                  Standard
                </>
              )}
            </span>
          )}
        </div>

        {onGenerateFix && (
          <button
            onClick={() => onGenerateFix(violation.id)}
            disabled={isFixing}
            className="flex items-center gap-1.5 text-xs font-medium px-3.5 py-1.5 rounded-lg bg-indigo-600/90 hover:bg-indigo-600 text-white transition disabled:opacity-50 self-start sm:self-auto shrink-0 shadow-sm shadow-indigo-500/20"
          >
            {isFixing ? 'Synthesizing...' : 'Synthesize Fix'}
            <ArrowRight size={13} />
          </button>
        )}
      </div>

      {/* WCAG Rule & File Path info */}
      <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
        <span className="text-indigo-400">Rule: {violation.type}</span>
        {violation.wcag_criterion && (
          <>
            <span className="text-slate-600">•</span>
            <span className="text-slate-400">{violation.wcag_criterion}</span>
          </>
        )}
        <span className="text-slate-600">•</span>
        <span className="bg-slate-800/90 text-slate-300 px-2 py-0.5 rounded text-[11px] border border-slate-700/40">
          {violation.file}{violation.line ? `:${violation.line}` : ''}
        </span>
      </div>

      {/* Prominent Plain English Explanation (Phase 15) */}
      <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/70">
        <p className="text-xs sm:text-sm text-slate-200 leading-relaxed">
          {diagnosed.plain_explanation || violation.description}
        </p>
      </div>

      {/* Offending Code Snippet */}
      {violation.context_snippet && (
        <pre className="p-2.5 rounded-lg bg-slate-950 border border-slate-800/80 text-xs font-mono text-rose-300/90 overflow-x-auto whitespace-pre-wrap">
          {violation.context_snippet}
        </pre>
      )}

      {/* Collapsible Technical Details Section (Phase 14 & 15) */}
      {hasTechnicalDetails && (
        <div className="pt-1">
          <button
            type="button"
            onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-indigo-400 hover:text-indigo-300 transition py-1 focus:outline-none"
          >
            {showTechnicalDetails ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            <span>{showTechnicalDetails ? 'Hide technical details' : 'Show technical root-cause & impact'}</span>
          </button>

          {showTechnicalDetails && (
            <div className="mt-2.5 p-3.5 rounded-lg bg-slate-950/90 border border-slate-800 flex flex-col gap-3 text-xs">
              {diagnosed.affected_element && (
                <div>
                  <span className="font-semibold text-slate-400 block mb-0.5">Affected Component / Selector:</span>
                  <code className="text-indigo-300 font-mono text-[11px] bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                    {diagnosed.affected_element}
                  </code>
                </div>
              )}

              {diagnosed.root_cause && (
                <div>
                  <span className="font-semibold text-slate-300 block mb-0.5">Root Cause:</span>
                  <p className="text-slate-400 leading-relaxed">{diagnosed.root_cause}</p>
                </div>
              )}

              {diagnosed.user_impact && (
                <div>
                  <span className="font-semibold text-slate-300 block mb-0.5">User Impact:</span>
                  <p className="text-slate-400 leading-relaxed">{diagnosed.user_impact}</p>
                </div>
              )}

              {diagnosed.fix_strategy && (
                <div>
                  <span className="font-semibold text-slate-300 block mb-0.5">Remediation Strategy:</span>
                  <p className="text-emerald-400/90 leading-relaxed">{diagnosed.fix_strategy}</p>
                </div>
              )}

              <div className="flex items-center gap-3 pt-1 text-[11px] text-slate-500 font-mono border-t border-slate-850">
                <span>Diagnostic Engine: {diagnosed.diagnosis_source === 'llm' ? 'Nemotron Ultra (550B)' : 'Deterministic Template'}</span>
                {diagnosed.confidence && <span>• Confidence: {diagnosed.confidence.toUpperCase()}</span>}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
