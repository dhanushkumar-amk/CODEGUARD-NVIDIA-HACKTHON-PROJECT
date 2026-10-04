import React from 'react';
import { ComplianceChart } from './ComplianceChart';

export interface FinalReportData {
  scanId: string;
  repoUrl: string;
  scoreBefore: number;
  scoreAfter: number;
  violationsCount: number;
  fixedCount: number;
  verifiedCount: number;
}

interface FinalReportProps {
  report: FinalReportData;
}

export const FinalReport: React.FC<FinalReportProps> = ({ report }) => {
  const improvement = report.scoreAfter - report.scoreBefore;

  return (
    <div className="w-full flex flex-col gap-5 text-left">
      <div className="border-b border-border pb-3">
        <h2 className="text-xl font-bold text-foreground">
          Scan complete: compliance report
        </h2>
        <p className="text-xs text-muted font-mono mt-0.5">
          Repository: {report.repoUrl} &bull; Scan ID: {report.scanId}
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="bg-background border border-border p-3.5">
          <div className="text-xs text-muted">Violations detected</div>
          <div className="text-xl font-bold font-mono text-foreground mt-1">
            {report.violationsCount}
          </div>
        </div>
        <div className="bg-background border border-border p-3.5">
          <div className="text-xs text-muted">Fixes synthesized</div>
          <div className="text-xl font-bold font-mono text-primary mt-1">
            {report.fixedCount}
          </div>
        </div>
        <div className="bg-background border border-border p-3.5">
          <div className="text-xs text-muted">Verified in sandbox</div>
          <div className="text-xl font-bold font-mono text-primary mt-1">
            {report.verifiedCount}
          </div>
        </div>
      </div>

      <ComplianceChart scoreBefore={report.scoreBefore} scoreAfter={report.scoreAfter} />

      <div className="bg-surface-1 border border-border p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 rounded-control">
        <div>
          <span className="text-xs text-muted">Score delta</span>
          <div className="text-base font-bold font-mono text-primary">
            {improvement >= 0 ? `+${improvement.toFixed(1)}` : improvement.toFixed(1)} points improvement
          </div>
        </div>
        <button
          onClick={() => window.print()}
          className="px-3.5 py-1.5 bg-background border border-border hover:bg-surface-2 text-foreground text-xs font-medium rounded-control cursor-pointer transition-colors"
        >
          Export / Print report
        </button>
      </div>
    </div>
  );
};
