import React, { useState } from 'react';
import { ProposedFix } from '../types';
import {
  ShieldCheck,
  AlertTriangle,
  Copy,
  CheckCheck,
  Sparkles,
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
  // Normalize props from either `fix` object or individual props
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
        return (
          <Badge variant="success" size="sm">
            High Confidence
          </Badge>
        );
      case 'medium':
        return (
          <Badge variant="warning" size="sm">
            Medium Confidence
          </Badge>
        );
      case 'low':
      default:
        return (
          <Badge variant="critical" size="sm">
            Low Confidence
          </Badge>
        );
    }
  };

  const renderUnifiedDiff = () => {
    if (!diff) {
      return (
        <div className="p-4 text-xs font-mono text-slate-400 italic">
          No diff patch generated for this violation.
        </div>
      );
    }

    const lines = diff.split('\n');
    return (
      <div className="divide-y divide-slate-800/40">
        {lines.map((line, idx) => {
          let lineStyle = 'text-slate-300 bg-transparent';

          if (line.startsWith('+++') || line.startsWith('---')) {
            lineStyle = 'text-slate-400 bg-slate-950/60 font-semibold';
          } else if (line.startsWith('@@')) {
            lineStyle =
              'text-indigo-300 bg-indigo-950/30 border-y border-indigo-900/40 font-semibold';
          } else if (line.startsWith('+')) {
            lineStyle =
              'text-emerald-300 bg-emerald-950/35 border-l-2 border-emerald-500 font-medium';
          } else if (line.startsWith('-')) {
            lineStyle =
              'text-rose-300 bg-rose-950/35 border-l-2 border-rose-500 font-medium';
          }

          return (
            <div
              key={idx}
              className={`px-3 py-1 flex items-start font-mono text-xs leading-relaxed transition-colors hover:bg-slate-800/30 ${lineStyle}`}
            >
              <span className="select-none text-slate-600 w-8 shrink-0 text-right pr-3 font-mono text-[11px]">
                {idx + 1}
              </span>
              <span className="whitespace-pre overflow-x-auto flex-1">{line}</span>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl overflow-hidden shadow-lg transition">
      {/* Header bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 bg-slate-950 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <FileCode size={15} className="text-indigo-400" />
          <span className="font-mono text-xs font-semibold text-slate-200">{filePath}</span>
          {lineStart && (
            <span className="text-[11px] font-mono text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded">
              L{lineStart}
              {lineEnd && lineEnd !== lineStart ? `-${lineEnd}` : ''}
            </span>
          )}
          {status === 'proposed' ? (
            <span className="flex items-center gap-1 text-[11px] text-emerald-400 font-medium bg-emerald-950/40 border border-emerald-800/50 px-2 py-0.5 rounded">
              <Check size={12} /> Proposed Fix
            </span>
          ) : (
            <span className="flex items-center gap-1 text-[11px] text-rose-400 font-medium bg-rose-950/40 border border-rose-800/50 px-2 py-0.5 rounded">
              <AlertTriangle size={12} /> Unresolved / Failed
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {getConfidenceBadge()}

          {/* View toggle (Unified vs Split) if both original & fixed code exist */}
          {original && fixed && (
            <div className="flex items-center bg-slate-850 border border-slate-800 rounded-lg p-0.5 text-xs">
              <button
                onClick={() => setViewMode('unified')}
                className={`flex items-center gap-1 px-2 py-1 rounded transition text-[11px] ${
                  viewMode === 'unified'
                    ? 'bg-indigo-600 text-white font-medium'
                    : 'text-slate-400 hover:text-white'
                }`}
                title="Unified Git Diff View"
              >
                <Split size={12} /> Unified
              </button>
              <button
                onClick={() => setViewMode('split')}
                className={`flex items-center gap-1 px-2 py-1 rounded transition text-[11px] ${
                  viewMode === 'split'
                    ? 'bg-indigo-600 text-white font-medium'
                    : 'text-slate-400 hover:text-white'
                }`}
                title="Side-by-side Split View"
              >
                <Columns size={12} /> Split
              </button>
            </div>
          )}

          <button
            onClick={handleCopy}
            className="flex items-center gap-1 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded-lg transition"
            title="Copy patch to clipboard"
          >
            {copied ? <CheckCheck size={13} className="text-emerald-400" /> : <Copy size={13} />}
            <span>{copied ? 'Copied!' : 'Copy'}</span>
          </button>

          {onVerifySandbox && status === 'proposed' && (
            <button
              onClick={onVerifySandbox}
              disabled={isVerifying}
              className="flex items-center gap-1.5 px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-lg transition disabled:opacity-50"
            >
              <ShieldCheck size={14} />
              {isVerifying ? 'Verifying...' : 'Verify in Sandbox'}
            </button>
          )}
        </div>
      </div>

      {/* Explanation of change banner */}
      {explanation && (
        <div className="px-4 py-2.5 bg-indigo-950/20 border-b border-slate-800 flex items-start gap-2 text-xs text-indigo-200">
          <Sparkles size={14} className="text-indigo-400 shrink-0 mt-0.5" />
          <div className="leading-relaxed">
            <span className="font-semibold text-white">Remediation Rationale: </span>
            {explanation}
          </div>
        </div>
      )}

      {/* Failure reason banner if status === failed */}
      {status === 'failed' && (
        <div className="px-4 py-2.5 bg-rose-950/30 border-b border-rose-900/40 flex items-start gap-2 text-xs text-rose-300">
          <AlertTriangle size={14} className="text-rose-400 shrink-0 mt-0.5" />
          <div className="leading-relaxed">
            <span className="font-semibold text-rose-200">Auto-Fix Not Applied: </span>
            {failureReason ||
              'This defect was detected and diagnosed, but code patch generation failed quality/syntax validation.'}
          </div>
        </div>
      )}

      {/* Main Diff Content Container */}
      <div className="font-mono text-xs overflow-x-auto">
        {viewMode === 'split' && original && fixed ? (
          <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-slate-800">
            <div className="p-3 bg-rose-950/15">
              <div className="text-rose-400 font-semibold mb-2 flex items-center justify-between">
                <span>Original (Violating)</span>
                {lineStart && <span className="text-[10px] text-slate-500 font-mono">Lines {lineStart}-{lineEnd}</span>}
              </div>
              <pre className="text-slate-300 overflow-x-auto whitespace-pre-wrap leading-relaxed">
                {original}
              </pre>
            </div>
            <div className="p-3 bg-emerald-950/15">
              <div className="text-emerald-400 font-semibold mb-2 flex items-center justify-between">
                <span className="flex items-center gap-1">
                  <Check size={14} /> Nemotron Remediated
                </span>
                <span className="text-[10px] text-emerald-500/80 font-mono">WCAG 2.2 AA</span>
              </div>
              <pre className="text-slate-100 overflow-x-auto whitespace-pre-wrap leading-relaxed">
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
