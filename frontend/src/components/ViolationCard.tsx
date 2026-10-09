import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Compass, ExternalLink } from 'lucide-react';
import { DiagnosedViolation, Violation, ViolationCategory } from '../types';
import { Badge } from './Badge';

export const CATEGORY_LABELS: Record<string, string> = {
  MISSING_ALT_TEXT: 'Missing alt text',
  UNLABELED_FORM_FIELD: 'Unlabeled form field',
  NON_INTERACTIVE_CLICK: 'Non-interactive click',
  EMPTY_LINK_OR_BUTTON: 'Empty link or button',
  LOW_CONTRAST: 'Low contrast',
  HEADING_ORDER: 'Heading order',
  MISSING_LANDMARK: 'Missing landmark',
  KEYBOARD_TRAP: 'Keyboard trap',
  MISSING_LANG: 'Missing lang',
  ARIA_MISUSE: 'ARIA misuse',
  FOCUS_MANAGEMENT: 'Focus management',
  OTHER: 'Other accessibility issue',
};

export function formatCategoryLabel(category?: ViolationCategory | string): string {
  if (!category) return 'Accessibility issue';
  if (CATEGORY_LABELS[category]) return CATEGORY_LABELS[category];

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
  const severityLabel = (violation.severity || 'medium').toLowerCase();

  const leftStripeClass =
    severityLabel === 'critical'
      ? 'border-l-[3px] border-l-coral'
      : ['high', 'serious'].includes(severityLabel)
      ? 'border-l-[3px] border-l-amber'
      : ['medium', 'moderate'].includes(severityLabel)
      ? 'border-l-[3px] border-l-amber'
      : 'border-l-[3px] border-l-[#6C707A]';

  const diagnosed = violation as DiagnosedViolation;
  const hasTechnicalDetails = Boolean(
    diagnosed.root_cause || diagnosed.user_impact || diagnosed.fix_strategy
  );

  return (
    <div className={`border border-line bg-[#FFFFFF] p-4 flex flex-col gap-3 ${leftStripeClass}`}>
      {/* Header row */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={violation.severity as any || 'medium'} size="sm">
            {violation.severity || 'medium'}
          </Badge>

          <span className="font-medium text-sm text-ink">
            {categoryLabel}
          </span>

          {violation.severity_score !== undefined && violation.severity_score !== null && (
            <span className="text-[11px] font-mono text-muted">
              score {violation.severity_score}/10
            </span>
          )}

          {diagnosed.diagnosis_source && (
            <span className="text-[11px] font-mono text-muted">
              {diagnosed.diagnosis_source === 'llm' ? 'Nemotron Ultra' : 'deterministic'}
            </span>
          )}
        </div>

        {onGenerateFix && (
          <button
            onClick={() => onGenerateFix(violation.id)}
            disabled={isFixing}
            className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-control bg-azure hover:bg-azure/90 text-white transition disabled:opacity-50 self-start sm:self-auto shrink-0 cursor-pointer"
          >
            {isFixing ? 'Synthesizing...' : 'Synthesize fix'}
          </button>
        )}
      </div>

      {/* Rule & file path */}
      <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-muted">
        <span>{violation.type}</span>
        {violation.wcag_criterion && (
          <>
            <span className="text-line">&middot;</span>
            <span>{violation.wcag_criterion}</span>
          </>
        )}
        <span className="text-line">&middot;</span>
        <span className="text-ink/70">
          {violation.file}{violation.line ? `:${violation.line}` : ''}
        </span>
      </div>

      {/* Description */}
      <p className="text-xs sm:text-sm text-ink/80 leading-relaxed font-sans">
        {diagnosed.plain_explanation || violation.description}
      </p>

      {/* Code snippet */}
      {violation.context_snippet && (
        <pre className="p-2.5 bg-surface-1 border border-line text-xs font-mono text-ink/80 overflow-x-auto whitespace-pre-wrap">
          {violation.context_snippet}
        </pre>
      )}

      {/* Technical details toggle */}
      {hasTechnicalDetails && (
        <div className="pt-1">
          <button
            type="button"
            onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-azure hover:text-azure/80 transition py-1 focus:outline-none cursor-pointer"
          >
            {showTechnicalDetails ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            <span>{showTechnicalDetails ? 'Hide technical details' : 'Show root-cause & impact'}</span>
          </button>

          {showTechnicalDetails && (
            <div className="mt-2 p-3 bg-surface-1 border border-line flex flex-col gap-2.5 text-xs">
              {diagnosed.affected_element && (
                <div>
                  <span className="font-medium text-muted font-sans">Affected element:</span>
                  <code className="ml-2 font-mono text-[11px] text-ink/80">
                    {diagnosed.affected_element}
                  </code>
                </div>
              )}

              {diagnosed.root_cause && (
                <div>
                  <span className="font-medium text-ink font-sans">Root cause:</span>
                  <p className="text-muted mt-0.5 leading-relaxed font-sans">{diagnosed.root_cause}</p>
                </div>
              )}

              {diagnosed.user_impact && (
                <div>
                  <span className="font-medium text-ink font-sans">User impact:</span>
                  <p className="text-muted mt-0.5 leading-relaxed font-sans">{diagnosed.user_impact}</p>
                </div>
              )}

              {diagnosed.fix_strategy && (
                <div>
                  <span className="font-medium text-ink font-sans">Remediation strategy:</span>
                  <p className="text-azure mt-0.5 leading-relaxed font-sans">{diagnosed.fix_strategy}</p>
                </div>
              )}

              {diagnosed.grounded && diagnosed.grounding_sources && diagnosed.grounding_sources.length > 0 && (
                <div className="pt-1.5 border-t border-line">
                  <span className="font-medium text-emerald font-sans flex items-center gap-1">
                    <Compass size={12} className="shrink-0" /> Grounded in:
                  </span>
                  <div className="flex flex-wrap gap-x-3 gap-y-1 mt-1">
                    {diagnosed.grounding_sources.map((src, idx) => (
                      <a
                        key={idx}
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-azure hover:underline text-xs inline-flex items-center gap-0.5 font-medium"
                      >
                        <span>{src.title}</span>
                        <ExternalLink size={10} className="opacity-70 ml-0.5" />
                      </a>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex items-center gap-3 pt-1 text-[11px] text-muted font-mono border-t border-line">
                <span>Engine: {diagnosed.diagnosis_source === 'llm' ? 'Nemotron Ultra' : 'deterministic'}</span>
                {diagnosed.confidence && <span>&middot; Confidence: {diagnosed.confidence}</span>}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
