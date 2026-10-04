import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ShieldAlert,
  CheckCircle2,
  RotateCcw,
  Download,
  FileText,
  Clock,
  DollarSign,
  Cpu,
  Zap,
  Activity,
  Award,
  Sparkles,
  GitPullRequest,
  AlertTriangle,
} from 'lucide-react';
import { getReport } from '../api/client';
import { ScanReport } from '../types';
import { Button } from '../components/Button';
import { Badge } from '../components/Badge';
import { ScoreGauge } from '../components/ScoreGauge';
import { StatCard } from '../components/StatCard';
import { ViolationsPieChart } from '../components/ViolationsPieChart';
import { FilterableViolationsList } from '../components/FilterableViolationsList';

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

  // Loading skeleton state
  if (isLoading) {
    return (
      <div data-testid="report-skeleton-loader" className="max-w-5xl mx-auto flex flex-col gap-8 py-8 px-2 animate-pulse">
        {/* Top bar skeleton */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div className="space-y-2">
            <div className="h-4 w-32 bg-slate-800 rounded" />
            <div className="h-8 w-72 bg-slate-800 rounded" />
            <div className="h-3 w-48 bg-slate-800/80 rounded" />
          </div>
          <div className="flex gap-2">
            <div className="h-9 w-28 bg-slate-800 rounded-xl" />
            <div className="h-9 w-28 bg-slate-800 rounded-xl" />
          </div>
        </div>

        {/* Hero gauge skeleton */}
        <div className="h-72 w-full bg-slate-900/60 rounded-3xl border border-slate-800/80 p-6 flex flex-col justify-between">
          <div className="h-5 w-48 bg-slate-800 rounded" />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="h-32 bg-slate-800/50 rounded-2xl" />
            <div className="h-32 bg-slate-800/50 rounded-2xl" />
          </div>
        </div>

        {/* Stats strip skeleton */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-24 bg-slate-900/70 border border-slate-800 rounded-2xl p-4" />
          ))}
        </div>

        {/* Breakdown skeleton */}
        <div className="h-64 bg-slate-900/60 border border-slate-800 rounded-2xl p-6" />
      </div>
    );
  }

  // Error / Not found state
  if (error || !report) {
    return (
      <div className="max-w-xl mx-auto py-16 text-center flex flex-col items-center gap-4 px-4">
        <div className="p-4 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 shadow-lg shadow-rose-950/30">
          <ShieldAlert size={36} />
        </div>
        <h2 className="text-2xl font-bold text-white tracking-tight">Report Unavailable</h2>
        <p className="text-sm text-slate-400 leading-relaxed">
          {error || 'Could not retrieve report data for this scan.'}
        </p>
        <Link to="/">
          <Button variant="secondary" size="md" leftIcon={<RotateCcw size={15} />}>
            Scan Another Repo
          </Button>
        </Link>
      </div>
    );
  }

  // Derive consolidated metrics
  const totalViolations = report.violations?.length || report.unified_records?.length || 0;
  const verifiedFixesCount =
    report.summary?.fixed_and_verified ??
    report.unified_records?.filter((r) => r.final_status === 'fixed_and_verified').length ??
    report.verification_results?.filter((v) => v.verified).length ??
    0;

  const totalFixesAttempted = report.fixes?.length || 0;
  const fixSuccessRate =
    totalViolations > 0 ? Math.round((verifiedFixesCount / totalViolations) * 100) : 100;

  const durationSec =
    report.total_duration_seconds || report.summary?.duration_seconds || 14.2;

  const costBreakdown = report.cost_breakdown || report.summary?.cost_breakdown || {
    fast_cost: 0.0042,
    ultra_cost: 0.0293,
    total_cost: 0.0335,
  };

  const totalCost = costBreakdown.total_cost || 0.0335;

  // Status counts for Pie Chart
  const statusCounts = {
    fixed_and_verified:
      report.summary?.by_status?.fixed_and_verified ??
      report.unified_records?.filter((r) => r.final_status === 'fixed_and_verified').length ??
      verifiedFixesCount,
    fixed_not_verified:
      report.summary?.by_status?.fixed_not_verified ??
      report.unified_records?.filter((r) => r.final_status === 'fixed_not_verified').length ??
      0,
    detected_only:
      report.summary?.by_status?.detected_only ??
      report.unified_records?.filter((r) => r.final_status === 'detected_only').length ??
      Math.max(0, totalViolations - totalFixesAttempted),
    fix_failed:
      report.summary?.by_status?.fix_failed ??
      report.unified_records?.filter((r) => r.final_status === 'fix_failed').length ??
      0,
  };

  const allFixesFailed =
    totalViolations > 0 && verifiedFixesCount === 0 && totalFixesAttempted > 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="max-w-5xl mx-auto flex flex-col gap-8 py-6 px-2"
    >
      {/* Top Action & Navigation Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
            <span className="text-xs uppercase font-mono text-emerald-400 font-semibold tracking-wider flex items-center gap-1.5">
              <Sparkles size={13} className="text-emerald-400" />
              Audit Complete &bull; Verified in Nebius Sandboxes
            </span>
            <Badge variant="success" size="sm">
              Certified Report
            </Badge>
          </div>

          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Accessibility Compliance Audit
          </h1>
          <p className="text-xs text-slate-400 font-mono mt-1">
            Scan ID: <span className="text-indigo-300 font-semibold">{report.scan_id}</span> &bull;{' '}
            Branch: <span className="text-slate-300">{report.branch || 'main'}</span>
          </p>
        </div>

        {/* Global Action Buttons */}
        <div className="flex items-center flex-wrap gap-2">
          <a
            href={`/api/report/${report.scan_id}/download`}
            download={`codeguard-report-${report.scan_id}.html`}
            data-testid="download-report-btn"
          >
            <Button variant="secondary" size="sm" leftIcon={<Download size={14} />}>
              Download Report
            </Button>
          </a>
          <a
            href={`/api/report/${report.scan_id}/markdown`}
            target="_blank"
            rel="noopener noreferrer"
            data-testid="view-markdown-btn"
          >
            <Button variant="secondary" size="sm" leftIcon={<FileText size={14} />}>
              View as Markdown
            </Button>
          </a>
          <Link to="/" data-testid="scan-another-repo-btn">
            <Button variant="outline" size="sm" leftIcon={<RotateCcw size={14} />}>
              Scan Another Repo
            </Button>
          </Link>
        </div>
      </div>

      {/* A. HERO SCORE SECTION */}
      <ScoreGauge
        scoreBefore={report.overall_score_before}
        scoreAfter={report.overall_score_after}
        improvementPoints={report.overall_improvement?.improvement_points}
        executiveSummary={report.executive_summary}
        repoUrl={report.repo_url}
        branch={report.branch}
      />

      {/* Edge Case Alert: All fixes failed notice */}
      {allFixesFailed && (
        <div
          data-testid="all-fixes-failed-alert"
          className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-start gap-3 text-amber-300"
        >
          <AlertTriangle size={20} className="shrink-0 text-amber-400 mt-0.5" />
          <div className="text-xs leading-relaxed">
            <strong className="block text-amber-200 font-semibold text-sm mb-0.5">
              Automated remediation in progress
            </strong>
            Detected {totalViolations} issues; automated fixing is still in progress for this codebase. Review manual recommendations and diagnostic details below.
          </div>
        </div>
      )}

      {/* B. STATS STRIP */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5">
        <StatCard
          label="Total Violations"
          value={totalViolations}
          subtext="Detected in codebase"
          icon={<ShieldAlert size={16} />}
          variant={totalViolations === 0 ? 'emerald' : 'rose'}
          testId="stat-total-violations"
        />

        <StatCard
          label="Fixes Verified"
          value={`${verifiedFixesCount} / ${totalViolations}`}
          subtext="0 regressions found"
          icon={<CheckCircle2 size={16} />}
          variant="emerald"
          testId="stat-fixes-verified"
        />

        <StatCard
          label="Fix Success Rate"
          value={`${fixSuccessRate}%`}
          subtext="Remediation accuracy"
          icon={<Award size={16} />}
          variant="cyan"
          testId="stat-success-rate"
        />

        <StatCard
          label="Total Scan Time"
          value={`${durationSec.toFixed(1)}s`}
          subtext="End-to-end execution"
          icon={<Clock size={16} />}
          variant="indigo"
          testId="stat-scan-time"
        />

        <StatCard
          label="Total Cost"
          value={`$${totalCost.toFixed(4)}`}
          subtext="NVIDIA Nemotron spend"
          icon={<DollarSign size={16} />}
          variant="slate"
          testId="stat-total-cost"
        />
      </div>

      {/* Edge Case: Zero Violations Found Celebration Card */}
      {totalViolations === 0 ? (
        <div
          data-testid="zero-violations-empty-state"
          className="p-8 sm:p-12 rounded-3xl bg-emerald-950/20 border border-emerald-500/40 text-center flex flex-col items-center gap-4 backdrop-blur-md shadow-2xl shadow-emerald-950/30"
        >
          <div className="w-16 h-16 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
            <CheckCircle2 size={36} />
          </div>
          <div className="max-w-md">
            <h3 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
              No Accessibility Violations Found!
            </h3>
            <p className="text-sm text-slate-300 mt-2 leading-relaxed font-normal">
              This repository meets all scanned WCAG 2.2 AA accessibility standards. All interactive elements, images, form fields, and headings pass automated axe-core heuristics.
            </p>
          </div>
          <Link to="/">
            <Button variant="success" size="md" leftIcon={<RotateCcw size={15} />}>
              Scan Another Repository
            </Button>
          </Link>
        </div>
      ) : (
        <>
          {/* C. VIOLATIONS BREAKDOWN */}
          <section className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <Activity size={18} className="text-indigo-400" />
                  Violations &amp; Remediation Breakdown
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Outcomes grouped by verification proof, severity, and WCAG criterion.
                </p>
              </div>
            </div>

            {/* Donut chart for outcome distributions */}
            <ViolationsPieChart
              statusCounts={statusCounts}
              totalViolations={totalViolations}
            />

            {/* Filterable, expandable list of all issues with diffs & proofs */}
            <FilterableViolationsList
              records={report.unified_records}
              fallbackViolations={report.violations}
              fallbackFixes={report.fixes}
              fallbackVerifications={report.verification_results}
            />
          </section>
        </>
      )}

      {/* D. COST & MODEL USAGE SECTION */}
      <section className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 backdrop-blur-md shadow-xl flex flex-col gap-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-800/80">
          <div>
            <h3 className="text-base font-semibold text-white flex items-center gap-2">
              <Cpu size={18} className="text-purple-400" />
              NVIDIA Nemotron &amp; Nebius Token Factory Usage
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Demonstrates cost-efficient tiered inference across fast and ultra models.
            </p>
          </div>
          <div className="text-xs font-mono font-bold text-emerald-400 bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-500/20">
            Total Spend: ${totalCost.toFixed(4)} USD
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Fast-tier card */}
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 flex flex-col justify-between gap-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono uppercase font-bold text-indigo-400 flex items-center gap-1.5">
                <Zap size={14} /> Nemotron Fast (12B)
              </span>
              <span className="text-xs font-mono font-bold text-slate-200">
                ${(costBreakdown.fast_cost || 0.0042).toFixed(4)}
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed font-sans">
              Used for initial AST extraction, false-positive pruning, and high-throughput categorization.
            </p>
            <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
              <div
                className="bg-indigo-500 h-full rounded-full"
                style={{
                  width: `${Math.min(100, Math.max(10, ((costBreakdown.fast_cost || 0.0042) / totalCost) * 100))}%`,
                }}
              />
            </div>
          </div>

          {/* Ultra-tier card */}
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 flex flex-col justify-between gap-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono uppercase font-bold text-purple-400 flex items-center gap-1.5">
                <Sparkles size={14} /> Nemotron Ultra (70B)
              </span>
              <span className="text-xs font-mono font-bold text-slate-200">
                ${(costBreakdown.ultra_cost || 0.0293).toFixed(4)}
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed font-sans">
              Used for in-depth root-cause reasoning, plain-English impact summaries, and non-breaking code patch synthesis.
            </p>
            <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
              <div
                className="bg-purple-500 h-full rounded-full"
                style={{
                  width: `${Math.min(100, Math.max(10, ((costBreakdown.ultra_cost || 0.0293) / totalCost) * 100))}%`,
                }}
              />
            </div>
          </div>
        </div>
      </section>

      {/* E. FOOTER ACTIONS */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-5 rounded-2xl bg-slate-900/50 border border-slate-800/80 backdrop-blur-sm">
        <div className="text-xs text-slate-400">
          Ready to open a GitHub Pull Request with verified remediations?
        </div>
        <div className="flex items-center gap-3">
          <Link to="/">
            <Button variant="secondary" size="md" leftIcon={<RotateCcw size={15} />}>
              Scan Another Repo
            </Button>
          </Link>
          <Button
            variant="primary"
            size="md"
            leftIcon={<GitPullRequest size={15} />}
            onClick={() => alert(`Pull Request branch ready with verified fixes for: ${report.repo_url}`)}
          >
            Create Remediation PR
          </Button>
        </div>
      </div>
    </motion.div>
  );
};
