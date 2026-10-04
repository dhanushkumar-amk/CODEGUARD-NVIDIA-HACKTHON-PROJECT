import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, CheckCircle2, FileText, AlertCircle, Scale } from 'lucide-react';

export const Terms: React.FC = () => {
  return (
    <div className="w-full text-left font-sans py-8 md:py-16">
      {/* Top back breadcrumb */}
      <div className="mb-8">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-xs font-mono uppercase tracking-[0.08em] text-muted hover:text-ink transition-colors"
        >
          <ArrowLeft size={13} />
          <span>Back to Home</span>
        </Link>
      </div>

      {/* Hero Header */}
      <div className="max-w-3xl mb-12">
        <div className="inline-flex items-center gap-2 mb-3">
          <span className="text-[11px] font-mono uppercase tracking-[0.08em] text-primary font-semibold">
            LEGAL & USAGE
          </span>
          <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-surface-1 text-muted border border-line">
            Effective: October 2026
          </span>
        </div>
        <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold text-ink tracking-tight font-sans mb-4">
          Terms of Service
        </h1>
        <p className="text-base sm:text-lg text-muted leading-relaxed font-sans">
          These Terms govern the use of CodeGuard, an open-source autonomous accessibility remediation engine built for the NVIDIA AI Challenge.
        </p>
      </div>

      {/* Core Rules Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
        <div className="p-6 rounded-[12px] border border-line bg-paper text-left flex flex-col justify-between">
          <div>
            <div className="w-8 h-8 rounded-[8px] border border-line bg-surface-1 flex items-center justify-center text-primary mb-4">
              <FileText size={16} />
            </div>
            <h3 className="font-bold text-ink text-base mb-1 font-sans">Open Source Core</h3>
            <p className="text-xs text-muted leading-relaxed font-sans">
              CodeGuard software is distributed under the Apache 2.0 / MIT license, enabling transparent inspection and self-hosting.
            </p>
          </div>
          <div className="pt-4 mt-4 border-t border-line text-[11px] font-mono text-emerald-600 flex items-center gap-1">
            <CheckCircle2 size={12} />
            <span>Permissive Licensing</span>
          </div>
        </div>

        <div className="p-6 rounded-[12px] border border-line bg-paper text-left flex flex-col justify-between">
          <div>
            <div className="w-8 h-8 rounded-[8px] border border-line bg-surface-1 flex items-center justify-center text-primary mb-4">
              <AlertCircle size={16} />
            </div>
            <h3 className="font-bold text-ink text-base mb-1 font-sans">Human-in-the-Loop</h3>
            <p className="text-xs text-muted leading-relaxed font-sans">
              Remediated unified diffs are proven in sandboxes, but engineering teams retain responsibility for final production reviews.
            </p>
          </div>
          <div className="pt-4 mt-4 border-t border-line text-[11px] font-mono text-emerald-600 flex items-center gap-1">
            <CheckCircle2 size={12} />
            <span>Review Recommendation</span>
          </div>
        </div>

        <div className="p-6 rounded-[12px] border border-line bg-paper text-left flex flex-col justify-between">
          <div>
            <div className="w-8 h-8 rounded-[8px] border border-line bg-surface-1 flex items-center justify-center text-primary mb-4">
              <Scale size={16} />
            </div>
            <h3 className="font-bold text-ink text-base mb-1 font-sans">Fair Usage</h3>
            <p className="text-xs text-muted leading-relaxed font-sans">
              Public demo APIs are subject to reasonable rate limits to preserve shared GPU compute resources across the community.
            </p>
          </div>
          <div className="pt-4 mt-4 border-t border-line text-[11px] font-mono text-emerald-600 flex items-center gap-1">
            <CheckCircle2 size={12} />
            <span>Resource Protection</span>
          </div>
        </div>
      </div>

      {/* Terms Content */}
      <div className="max-w-3xl space-y-10 text-ink font-sans">
        <section className="border-t border-line pt-8">
          <span className="text-[11px] font-mono uppercase tracking-[0.08em] text-primary font-semibold block mb-2">
            01. SCOPE OF SERVICE
          </span>
          <h2 className="text-xl font-bold tracking-tight text-ink mb-3">
            Autonomous Accessibility Remediation
          </h2>
          <p className="text-sm text-muted leading-relaxed">
            CodeGuard provides automated code scanning, WCAG 2.2 AA violation diagnosis, and synthetic AST patch generation powered by NVIDIA Nemotron-4 foundation models on Nebius Token Factory. CodeGuard is designed to assist software developers in discovering and resolving digital accessibility barriers.
          </p>
        </section>

        <section className="border-t border-line pt-8">
          <span className="text-[11px] font-mono uppercase tracking-[0.08em] text-primary font-semibold block mb-2">
            02. CODE GENERATION & LIABILITY DISCLAIMER
          </span>
          <h2 className="text-xl font-bold tracking-tight text-ink mb-3">
            Deterministic Verification & PR Integration
          </h2>
          <div className="text-sm text-muted leading-relaxed space-y-3">
            <p>
              While CodeGuard executes strict headless browser sandbox tests to verify that generated patches resolve designated WCAG criteria, no automated system can replace human judgment in every scenario.
            </p>
            <p>
              Patches should be reviewed via standard pull request workflows prior to merging into production branches. CodeGuard is provided &ldquo;as is&rdquo;, without warranty of any kind regarding merchantability or fitness for a particular commercial purpose.
            </p>
          </div>
        </section>

        <section className="border-t border-line pt-8">
          <span className="text-[11px] font-mono uppercase tracking-[0.08em] text-primary font-semibold block mb-2">
            03. INTELLECTUAL PROPERTY RIGHTS
          </span>
          <h2 className="text-xl font-bold tracking-tight text-ink mb-3">
            Your Code Remains Your Exclusive Property
          </h2>
          <p className="text-sm text-muted leading-relaxed">
            You retain 100% ownership and copyright over any repository, codebase, or markup submitted for scanning. CodeGuard claims zero ownership over generated unified diffs or patch solutions created during your scan sessions.
          </p>
        </section>

        <section className="border-t border-line pt-8">
          <span className="text-[11px] font-mono uppercase tracking-[0.08em] text-primary font-semibold block mb-2">
            04. RATE LIMITING & COMPUTE ALLOCATION
          </span>
          <h2 className="text-xl font-bold tracking-tight text-ink mb-3">
            Shared GPU Compute Policies
          </h2>
          <p className="text-sm text-muted leading-relaxed">
            To prevent abuse of high-performance NVIDIA inference nodes, automated scrapers, denial-of-service attempts, and bulk concurrent submissions without prior authorization may be throttled. For high-volume CI/CD pipeline deployments, self-hosting our containerized stack via Docker is recommended.
          </p>
        </section>
      </div>
    </div>
  );
};
