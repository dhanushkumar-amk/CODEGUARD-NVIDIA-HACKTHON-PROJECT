import React from 'react';
import { Check, ShieldCheck } from 'lucide-react';

interface FixDiffViewerProps {
  originalCode: string;
  remediatedCode: string;
  filePath: string;
  onVerifySandbox?: () => void;
  isVerifying?: boolean;
}

export const FixDiffViewer: React.FC<FixDiffViewerProps> = ({
  originalCode,
  remediatedCode,
  filePath,
  onVerifySandbox,
  isVerifying,
}) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2.5 bg-slate-950 border-b border-slate-800">
        <span className="font-mono text-xs text-slate-300">{filePath}</span>
        {onVerifySandbox && (
          <button
            onClick={onVerifySandbox}
            disabled={isVerifying}
            className="flex items-center gap-1.5 px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-lg transition disabled:opacity-50"
          >
            <ShieldCheck size={14} />
            {isVerifying ? 'Testing in Sandbox...' : 'Verify in Nebius Sandbox'}
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-slate-800 font-mono text-xs">
        <div className="p-3 bg-rose-950/20">
          <div className="text-rose-400 font-semibold mb-2">Original (Violating)</div>
          <pre className="text-slate-300 overflow-x-auto whitespace-pre-wrap">{originalCode}</pre>
        </div>
        <div className="p-3 bg-emerald-950/20">
          <div className="text-emerald-400 font-semibold mb-2 flex items-center gap-1">
            <Check size={14} /> Nemotron Remediated
          </div>
          <pre className="text-slate-200 overflow-x-auto whitespace-pre-wrap">{remediatedCode}</pre>
        </div>
      </div>
    </div>
  );
};
