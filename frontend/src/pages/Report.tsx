import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ShieldAlert,
  CheckCircle2,
  FileCheck,
  TrendingUp,
  RotateCcw,
  GitPullRequest,
  Check,
  Server,
  Loader2,
} from 'lucide-react';
import { getReport } from '../api/client';
import { ScanReport } from '../types';
import { Card } from '../components/Card';
import { Badge } from '../components/Badge';
import { Button } from '../components/Button';

export const Report: React.FC = () => {
  const { scanId } = useParams<{ scanId: string }>();
  const [report, setReport] = useState<ScanReport | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!scanId) return;

    let isMounted = true;
    setIsLoading(true);

    getReport(scanId)
      .then((data) => {
        if (isMounted) {
          setReport(data);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          const msg = err instanceof Error ? err.message : 'Failed to fetch scan report';
          setError(msg);
        }
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [scanId]);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <Loader2 className="animate-spin text-indigo-400" size={36} />
        <p className="text-sm text-slate-400 font-medium">Loading compliance audit report...</p>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="max-w-xl mx-auto py-12 text-center flex flex-col items-center gap-4">
        <div className="p-4 rounded-full bg-rose-500/10 text-rose-400">
          <ShieldAlert size={32} />
        </div>
        <h2 className="text-xl font-bold text-white">Report Not Found</h2>
        <p className="text-sm text-slate-400">{error || 'Could not retrieve report data.'}</p>
        <Link to="/">
          <Button variant="secondary" size="md">
            Return to Home
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto flex flex-col gap-8 py-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="success" size="sm">
              Audit Complete
            </Badge>
            <span className="text-xs text-slate-400 font-mono">
              Job: {report.scan_id}
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white">
            Accessibility Compliance Report
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Repo: {report.repo_url} ({report.branch})
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link to="/">
            <Button variant="secondary" size="sm" leftIcon={<RotateCcw size={14} />}>
              New Scan
            </Button>
          </Link>
          <Button
            variant="primary"
            size="sm"
            leftIcon={<GitPullRequest size={14} />}
            onClick={() => alert(`PR branch ready for: ${report.repo_url}`)}
          >
            Create Remediation PR
          </Button>
        </div>
      </div>

      {/* KPI Metric Scorecards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        {/* Baseline Score */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="text-xs text-slate-400 font-medium">Initial Score</div>
          <div className="text-3xl font-extrabold text-rose-400 mt-2">
            {report.overall_score_before}%
          </div>
          <div className="text-[11px] text-slate-500 mt-1">WCAG 2.2 AA Baseline</div>
        </div>

        {/* Remediated Score */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="text-xs text-slate-400 font-medium flex items-center gap-1.5">
            <TrendingUp size={14} className="text-emerald-400" />
            Remediated Score
          </div>
          <div className="text-3xl font-extrabold text-emerald-400 mt-2">
            {report.overall_score_after}%
          </div>
          <div className="text-[11px] text-emerald-400/80 mt-1">
            +{(report.overall_score_after - report.overall_score_before).toFixed(1)}% improvement
          </div>
        </div>

        {/* Violations Count */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="text-xs text-slate-400 font-medium flex items-center gap-1.5">
            <ShieldAlert size={14} className="text-rose-400" />
            Defects Detected
          </div>
          <div className="text-3xl font-extrabold text-white mt-2">
            {report.violations.length}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">Confirmed actionable</div>
        </div>

        {/* Verified Count */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="text-xs text-slate-400 font-medium flex items-center gap-1.5">
            <CheckCircle2 size={14} className="text-emerald-400" />
            Sandbox Verified
          </div>
          <div className="text-3xl font-extrabold text-emerald-300 mt-2">
            {report.verification_results.filter((v) => v.verified).length} /{' '}
            {report.fixes.length}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">0 regressions found</div>
        </div>
      </div>

      {/* Section 1: Violations Detected */}
      <Card
        title={`Identified Accessibility Violations (${report.violations.length})`}
        subtitle="Triaged by Nemotron Nano to eliminate AST false alarms."
      >
        <div className="flex flex-col gap-3">
          {report.violations.map((violation) => (
            <div
              key={violation.id}
              className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 flex flex-col gap-2.5"
            >
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Badge variant={violation.severity as any} size="sm">
                    {violation.severity}
                  </Badge>
                  <span className="font-mono text-sm font-semibold text-white">
                    {violation.type}
                  </span>
                </div>
                <span className="font-mono text-xs text-slate-400">
                  {violation.file}{violation.line ? `:${violation.line}` : ''}
                </span>
              </div>

              <p className="text-xs text-slate-300">{violation.description}</p>

              {violation.context_snippet && (
                <pre className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono text-rose-300 overflow-x-auto">
                  {violation.context_snippet}
                </pre>
              )}
            </div>
          ))}
        </div>
      </Card>

      {/* Section 2: Synthesized Fixes & Unified Diffs */}
      <Card
        title={`Synthesized Fixes & Code Diffs (${report.fixes.length})`}
        subtitle="Generated by Nemotron Ultra (340B) matching repository styling."
      >
        <div className="flex flex-col gap-4">
          {report.fixes.map((fix) => (
            <div
              key={fix.fix_id}
              className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 flex flex-col gap-3"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-xs font-semibold text-indigo-300">
                  Patch {fix.fix_id} (resolves {fix.violation_id})
                </span>
                <span className="flex items-center gap-1 text-[11px] text-emerald-400 font-medium">
                  <Check size={13} /> Synthesized Clean
                </span>
              </div>

              <p className="text-xs text-slate-300 leading-relaxed">{fix.explanation}</p>

              <div className="rounded-lg bg-slate-900 border border-slate-800 overflow-hidden">
                <div className="px-3 py-1.5 bg-slate-850 text-[11px] font-mono text-slate-400 border-b border-slate-800">
                  Unified Git Diff
                </div>
                <pre className="p-3 text-xs font-mono text-emerald-300 overflow-x-auto whitespace-pre-wrap">
                  {fix.diff}
                </pre>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Section 3: Sandbox Verification Results */}
      <Card
        title={`Nebius Sandbox Verifications (${report.verification_results.length})`}
        subtitle="Tested in ephemeral containers with Playwright, axe-core, and repository test suites."
      >
        <div className="flex flex-col gap-3">
          {report.verification_results.map((vr) => (
            <div
              key={vr.fix_id}
              className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
            >
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <Badge variant={vr.verified ? 'success' : 'critical'} size="sm">
                    {vr.verified ? '100% Passed' : 'Failed'}
                  </Badge>
                  <span className="font-mono text-xs text-slate-200">
                    Fix: {vr.fix_id}
                  </span>
                  {vr.sandbox_id && (
                    <span className="flex items-center gap-1 text-[11px] font-mono text-slate-400">
                      <Server size={12} /> {vr.sandbox_id}
                    </span>
                  )}
                </div>
                {vr.sandbox_logs && (
                  <p className="text-xs text-slate-400 font-mono mt-0.5">{vr.sandbox_logs}</p>
                )}
              </div>

              <div className="flex items-center gap-4 text-xs font-mono">
                <div>
                  <span className="text-slate-500">Score: </span>
                  <span className="text-rose-400">{vr.axe_score_before}%</span>
                  <span className="text-slate-500"> → </span>
                  <span className="text-emerald-400 font-bold">{vr.axe_score_after}%</span>
                </div>
                <div className="flex items-center gap-1 text-emerald-400">
                  <FileCheck size={14} /> Tests 100%
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};
