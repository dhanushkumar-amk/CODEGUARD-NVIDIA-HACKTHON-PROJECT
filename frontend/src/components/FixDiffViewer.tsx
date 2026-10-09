import React, { useState } from 'react';
import { ProposedFix } from '../types';
import {
  AlertTriangle,
  Copy,
  CheckCheck,
  FileCode,
  Check,
  Columns,
  Split,
  Compass,
  ExternalLink,
} from 'lucide-react';
import { Badge } from './Badge';

export interface FixDiffViewerProps {
  fix?: ProposedFix;
  originalCode?: string;
  remediatedCode?: string;
  diff?: string;
  filePath?: string;
  lineStart?: number | null;
  lineEnd?: number | null;
  explanationOfChange?: string;
  confidence?: string;
  status?: string;
  failureReason?: string | null;
  onVerifySandbox?: () => void;
  isVerifying?: boolean;
}

export const FixDiffViewer: React.FC<FixDiffViewerProps> = ({
  fix,
  originalCode: propOriginalCode,
  remediatedCode: propRemediatedCode,
  diff: propDiff,
  filePath: propFilePath,
  lineStart: propLineStart,
  lineEnd: propLineEnd,
  explanationOfChange: propExplanationOfChange,
  confidence: propConfidence,
  status: propStatus,
  failureReason: propFailureReason,
  onVerifySandbox,
  isVerifying,
}) => {
  const filePath = fix?.file || propFilePath || 'Component.tsx';
  const diff = fix?.diff || propDiff || '';
  const original = fix?.original_lines || fix?.original_code || propOriginalCode || '';
  const fixed = fix?.fixed_lines || fix?.remediated_code || propRemediatedCode || '';
  const explanation =
    fix?.explanation_of_change || fix?.explanation || propExplanationOfChange || '';
  const confidence = (fix?.confidence || propConfidence || 'high').toLowerCase();
  const status = (fix?.status || propStatus || 'proposed').toLowerCase();
  const failureReason = fix?.failure_reason || propFailureReason;
  const lineStart = fix?.line_start ?? propLineStart;
  const lineEnd = fix?.line_end ?? propLineEnd;

  const [copied, setCopied] = useState<boolean>(false);
  const [viewMode, setViewMode] = useState<'unified' | 'split'>('unified');

  const handleCopy = () => {
    const textToCopy = fixed || diff || original;
    if (textToCopy) {
      navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const getConfidenceBadge = () => {
    switch (confidence) {
      case 'high':
        return <Badge variant="fixed_and_verified" size="sm">high confidence</Badge>;
      case 'medium':
        return <Badge variant="fixed_not_verified" size="sm">medium confidence</Badge>;
      case 'low':
      default:
        return <Badge variant="fix_failed" size="sm">low confidence</Badge>;
    }
  };

  const renderUnifiedDiff = () => {
    if (!diff) {
      return (
        <div className="p-4 text-xs font-mono text-muted italic">
          No diff patch generated for this violation.
        </div>
      );
    }

    const lines = diff.split('\n');
    return (
      <div>
        {lines.map((line, idx) => {
          let lineStyle = 'text-ink/70';
          let bgStyle = '';

          if (line.startsWith('+++') || line.startsWith('---')) {
            lineStyle = 'text-muted font-medium';
            bgStyle = 'bg-surface-1';
          } else if (line.startsWith('@@')) {
            lineStyle = 'text-azure font-medium';
            bgStyle = 'bg-azure/5';
          } else if (line.startsWith('+')) {
            lineStyle = 'text-emerald';
            bgStyle = 'bg-emerald/10 border-l-2 border-emerald';
          } else if (line.startsWith('-')) {
            lineStyle = 'text-coral';
            bgStyle = 'bg-coral/10 border-l-2 border-coral';
          }

          return (
            <div
              key={idx}
              className={`px-3 py-0.5 flex items-start font-mono text-xs leading-relaxed ${bgStyle}`}
            >
              <span className="select-none text-muted/50 w-8 shrink-0 text-right pr-3 text-[11px]">
                {idx + 1}
              </span>
              <span className={`whitespace-pre overflow-x-auto flex-1 ${lineStyle}`}>{line}</span>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="border border-line bg-[#FFFFFF] overflow-hidden">
      {/* Header bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 bg-surface-1 border-b border-line">
        <div className="flex items-center gap-2">
          <FileCode size={14} className="text-muted" />
          <span className="font-mono text-xs font-medium text-ink">{filePath}</span>
          {lineStart && (
            <span className="text-[11px] font-mono text-muted">
              L{lineStart}
              {lineEnd && lineEnd !== lineStart ? `–${lineEnd}` : ''}
            </span>
          )}
          {status === 'proposed' ? (
            <Badge variant="fixed_and_verified" size="sm">proposed fix</Badge>
          ) : (
            <Badge variant="fix_failed" size="sm">unresolved</Badge>
          )}
        </div>

        <div className="flex items-center gap-2 font-sans">
          {getConfidenceBadge()}

          {original && fixed && (
            <div className="flex items-center border border-line rounded-control p-0.5 text-xs">
              <button
                onClick={() => setViewMode('unified')}
                className={`flex items-center gap-1 px-2 py-1 rounded-control transition text-[11px] cursor-pointer ${
                  viewMode === 'unified'
                    ? 'bg-azure text-white'
                    : 'text-muted hover:text-ink'
                }`}
              >
                <Split size={11} /> Unified
              </button>
              <button
                onClick={() => setViewMode('split')}
                className={`flex items-center gap-1 px-2 py-1 rounded-control transition text-[11px] cursor-pointer ${
                  viewMode === 'split'
                    ? 'bg-azure text-white'
                    : 'text-muted hover:text-ink'
                }`}
              >
                <Columns size={11} /> Split
              </button>
            </div>
          )}

          <button
            onClick={handleCopy}
            className="flex items-center gap-1 px-2.5 py-1 bg-surface-1 hover:bg-surface-2 text-ink text-xs rounded-control transition border border-line cursor-pointer"
          >
            {copied ? <CheckCheck size={12} className="text-emerald" /> : <Copy size={12} />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>

          {onVerifySandbox && status === 'proposed' && (
            <button
              onClick={onVerifySandbox}
              disabled={isVerifying}
              className="flex items-center gap-1.5 px-3 py-1 bg-azure hover:bg-azure/90 text-white text-xs font-medium rounded-control transition disabled:opacity-50 cursor-pointer"
            >
              {isVerifying ? 'Verifying...' : 'Verify in sandbox'}
            </button>
          )}
        </div>
      </div>

      {/* Explanation */}
      {explanation && (
        <div className="px-4 py-2 bg-surface-1 border-b border-line text-xs text-ink/80 font-sans">
          <span className="font-medium text-ink">Rationale: </span>
          {explanation}
        </div>
      )}

      {/* Grounded in WCAG sources */}
      {fix?.grounded && fix.grounding_sources && fix.grounding_sources.length > 0 && (
        <div className="px-4 py-2 bg-emerald/[0.04] border-b border-line text-xs font-sans flex items-center flex-wrap gap-x-2 gap-y-1">
          <span className="font-medium text-emerald flex items-center gap-1">
            <Compass size={12} className="shrink-0" /> Grounded in:
          </span>
          {fix.grounding_sources.map((src, idx) => (
            <a
              key={idx}
              href={src.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-azure hover:underline font-medium inline-flex items-center gap-0.5 text-xs"
            >
              <span>{src.title}</span>
              <ExternalLink size={10} className="inline opacity-70 ml-0.5" />
            </a>
          ))}
        </div>
      )}

      {/* Failure banner */}
      {status === 'failed' && (
        <div className="px-4 py-2 bg-coral/10 border-b border-coral/20 flex items-start gap-2 text-xs text-coral font-sans">
          <AlertTriangle size={13} className="shrink-0 mt-0.5" />
          <div>
            <span className="font-medium">Auto-fix not applied: </span>
            {failureReason ||
              'Code patch generation failed quality/syntax validation.'}
          </div>
        </div>
      )}

      {/* Diff content */}
      <div className="font-mono text-xs overflow-x-auto">
        {viewMode === 'split' && original && fixed ? (
          <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-line">
            <div className="p-3 bg-coral/[0.04]">
              <div className="text-coral font-medium mb-2 flex items-center justify-between text-xs font-sans">
                <span>Original</span>
                {lineStart && <span className="text-muted text-[10px] font-mono">L{lineStart}–{lineEnd}</span>}
              </div>
              <pre className="text-ink/60 overflow-x-auto whitespace-pre-wrap leading-relaxed text-xs font-mono">
                {original}
              </pre>
            </div>
            <div className="p-3 bg-emerald/[0.04]">
              <div className="text-emerald font-medium mb-2 flex items-center justify-between text-xs font-sans">
                <span className="flex items-center gap-1">
                  <Check size={13} /> Remediated
                </span>
                <span className="text-muted text-[10px] font-mono">WCAG 2.2 AA</span>
              </div>
              <pre className="text-ink/80 overflow-x-auto whitespace-pre-wrap leading-relaxed text-xs font-mono">
                {fixed}
              </pre>
            </div>
          </div>
        ) : (
          renderUnifiedDiff()
        )}
      </div>
    </div>
  );
};
