import React from 'react';
import { GitPullRequest, FileCheck, CheckCircle, ShieldAlert } from 'lucide-react';
import { ComplianceChart } from './ComplianceChart';

export interface FinalReportData {
  repoUrl: string;
  totalViolationsFound: number;
  violationsResolved: number;
  unresolvedViolations: number;
  scoreBefore: number;
  scoreAfter: number;
  prUrl?: string;
  prBranch?: string;
}

interface FinalReportProps {
  report: FinalReportData;
  onCreatePullRequest?: () => void;
  isCreatingPR?: boolean;
}

export const FinalReport: React.FC<FinalReportProps> = ({
  report,
  onCreatePullRequest,
  isCreatingPR,
}) => {
  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center gap-2 text-rose-400 text-xs font-semibold mb-1">
            <ShieldAlert size={16} /> Total Violations Detected
          </div>
          <div className="text-2xl font-bold text-slate-100">{report.totalViolationsFound}</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center gap-2 text-emerald-400 text-xs font-semibold mb-1">
            <CheckCircle size={16} /> Verified Resolved in Sandbox
          </div>
          <div className="text-2xl font-bold text-slate-100">{report.violationsResolved}</div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div className="flex items-center gap-2 text-indigo-400 text-xs font-semibold mb-1">
            <FileCheck size={16} /> Final Compliance
          </div>
          <div className="text-2xl font-bold text-slate-100">{report.scoreAfter}%</div>
        </div>
      </div>

      <ComplianceChart scoreBefore={report.scoreBefore} scoreAfter={report.scoreAfter} />

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div>
          <h4 className="text-sm font-semibold text-slate-200">Export Verified Remediations</h4>
          <p className="text-xs text-slate-400">
            Submit a clean GitHub Pull Request with the verified patches and test artifacts.
          </p>
        </div>
        {onCreatePullRequest && (
          <button
            onClick={onCreatePullRequest}
            disabled={isCreatingPR}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs transition disabled:opacity-50"
          >
            <GitPullRequest size={16} />
            {isCreatingPR ? 'Opening Pull Request...' : 'Create Verified Remediation PR'}
          </button>
        )}
      </div>
    </div>
  );
};
