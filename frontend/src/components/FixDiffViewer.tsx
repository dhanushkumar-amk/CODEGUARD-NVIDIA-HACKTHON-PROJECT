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
        return <Badge variant="success" size="sm">high confidence</Badge>;
      case 'medium':
        return <Badge variant="warning" size="sm">medium confidence</Badge>;
      case 'low':
      default:
        return <Badge variant="danger" size="sm">low confidence</Badge>;
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
          let lineStyle = 'text-foreground/70';
          let bgStyle = '';

          if (line.startsWith('+++') || line.startsWith('---')) {
            lineStyle = 'text-muted font-medium';
            bgStyle = 'bg-surface-1';
          } else if (line.startsWith('@@')) {
            lineStyle = 'text-primary font-medium';
            bgStyle = 'bg-primary/5';
          } else if (line.startsWith('+')) {
            lineStyle = 'text-[#2F7A4D]';
            bgStyle = 'bg-[#2F7A4D]/5 border-l-2 border-[#2F7A4D]';
          } else if (line.startsWith('-')) {
            lineStyle = 'text-destructive';
            bgStyle = 'bg-destructive/5 border-l-2 border-destructive';
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
    <div className="border border-border bg-background overflow-hidden">
      {/* Header bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 bg-surface-1 border-b border-border">
        <div className="flex items-center gap-2">
          <FileCode size={14} className="text-muted" />
          <span className="font-mono text-xs font-medium text-foreground">{filePath}</span>
          {lineStart && (
            <span className="text-[11px] font-mono text-muted">
              L{lineStart}
              {lineEnd && lineEnd !== lineStart ? `–${lineEnd}` : ''}
            </span>
          )}
          {status === 'proposed' ? (
            <Badge variant="success" size="sm">proposed fix</Badge>
          ) : (
            <Badge variant="danger" size="sm">unresolved</Badge>
          )}
        </div>

        <div className="flex items-center gap-2">
          {getConfidenceBadge()}

          {original && fixed && (
            <div className="flex items-center border border-border rounded-control p-0.5 text-xs">
              <button
                onClick={() => setViewMode('unified')}
                className={`flex items-center gap-1 px-2 py-1 rounded-control transition text-[11px] ${
                  viewMode === 'unified'
                    ? 'bg-primary text-white'
                    : 'text-muted hover:text-foreground'
                }`}
              >
                <Split size={11} /> Unified
              </button>
              <button
                onClick={() => setViewMode('split')}
                className={`flex items-center gap-1 px-2 py-1 rounded-control transition text-[11px] ${
                  viewMode === 'split'
                    ? 'bg-primary text-white'
                    : 'text-muted hover:text-foreground'
                }`}
              >
                <Columns size={11} /> Split
              </button>
            </div>
          )}

          <button
            onClick={handleCopy}
            className="flex items-center gap-1 px-2.5 py-1 bg-surface-1 hover:bg-surface-2 text-foreground text-xs rounded-control transition border border-border"
          >
            {copied ? <CheckCheck size={12} className="text-[#2F7A4D]" /> : <Copy size={12} />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>

          {onVerifySandbox && status === 'proposed' && (
            <button
              onClick={onVerifySandbox}
              disabled={isVerifying}
              className="flex items-center gap-1.5 px-3 py-1 bg-primary hover:bg-primary/90 text-white text-xs font-medium rounded-control transition disabled:opacity-50"
            >
              {isVerifying ? 'Verifying...' : 'Verify in sandbox'}
            </button>
          )}
        </div>
      </div>

      {/* Explanation */}
      {explanation && (
        <div className="px-4 py-2 bg-surface-1 border-b border-border text-xs text-foreground/80">
          <span className="font-medium text-foreground">Rationale: </span>
          {explanation}
        </div>
      )}

      {/* Failure banner */}
      {status === 'failed' && (
        <div className="px-4 py-2 bg-destructive/5 border-b border-destructive/20 flex items-start gap-2 text-xs text-destructive">
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
          <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-border">
            <div className="p-3 bg-destructive/[0.02]">
              <div className="text-destructive font-medium mb-2 flex items-center justify-between text-xs">
                <span>Original</span>
                {lineStart && <span className="text-muted text-[10px]">L{lineStart}–{lineEnd}</span>}
              </div>
              <pre className="text-foreground/60 overflow-x-auto whitespace-pre-wrap leading-relaxed text-xs">
                {original}
              </pre>
            </div>
            <div className="p-3 bg-[#2F7A4D]/[0.02]">
              <div className="text-[#2F7A4D] font-medium mb-2 flex items-center justify-between text-xs">
                <span className="flex items-center gap-1">
                  <Check size={13} /> Remediated
                </span>
                <span className="text-muted text-[10px]">WCAG 2.2 AA</span>
              </div>
              <pre className="text-foreground/80 overflow-x-auto whitespace-pre-wrap leading-relaxed text-xs">
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
