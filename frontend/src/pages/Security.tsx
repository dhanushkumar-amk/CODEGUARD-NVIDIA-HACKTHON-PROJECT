import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldCheck, Lock, ArrowLeft, ExternalLink, CheckCircle2, AlertTriangle, Mail } from 'lucide-react';

export const Security: React.FC = () => {
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
            TRUST & SAFETY
          </span>
          <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-surface-1 text-muted border border-line">
            Vulnerability Disclosure Program
          </span>
        </div>
        <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold text-ink tracking-tight font-sans mb-4">
          Security Disclosure
        </h1>
        <p className="text-base sm:text-lg text-muted leading-relaxed font-sans">
          We take the security of CodeGuard, our autonomous code remediation pipelines, and the developer repositories we analyze with extreme seriousness.
        </p>
      </div>

      {/* SLA Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
        <div className="p-6 rounded-[12px] border border-line bg-paper text-left flex flex-col justify-between">
          <div>
            <div className="w-8 h-8 rounded-[8px] border border-line bg-surface-1 flex items-center justify-center text-primary mb-4">
              <Mail size={16} />
            </div>
            <h3 className="font-bold text-ink text-base mb-1 font-sans">&lt; 24 Hour Response</h3>
            <p className="text-xs text-muted leading-relaxed font-sans">
              Our core engineering team acknowledges all security disclosures within 24 hours of receipt.
            </p>
          </div>
          <div className="pt-4 mt-4 border-t border-line text-[11px] font-mono text-emerald-600 flex items-center gap-1">
            <CheckCircle2 size={12} />
            <span>Guaranteed Triage</span>
          </div>
        </div>

        <div className="p-6 rounded-[12px] border border-line bg-paper text-left flex flex-col justify-between">
          <div>
            <div className="w-8 h-8 rounded-[8px] border border-line bg-surface-1 flex items-center justify-center text-primary mb-4">
              <Lock size={16} />
            </div>
            <h3 className="font-bold text-ink text-base mb-1 font-sans">Coordinated Disclosure</h3>
            <p className="text-xs text-muted leading-relaxed font-sans">
              We collaborate with reporters on coordinated disclosure schedules before releasing public CVE details.
            </p>
          </div>
          <div className="pt-4 mt-4 border-t border-line text-[11px] font-mono text-emerald-600 flex items-center gap-1">
            <CheckCircle2 size={12} />
            <span>Responsible Embargo</span>
          </div>
        </div>

        <div className="p-6 rounded-[12px] border border-line bg-paper text-left flex flex-col justify-between">
          <div>
            <div className="w-8 h-8 rounded-[8px] border border-line bg-surface-1 flex items-center justify-center text-primary mb-4">
              <ShieldCheck size={16} />
            </div>
            <h3 className="font-bold text-ink text-base mb-1 font-sans">Safe Harbor</h3>
            <p className="text-xs text-muted leading-relaxed font-sans">
              Security researchers acting in good faith under this policy will not be subjected to legal claims.
            </p>
          </div>
          <div className="pt-4 mt-4 border-t border-line text-[11px] font-mono text-emerald-600 flex items-center gap-1">
            <CheckCircle2 size={12} />
            <span>Researcher Protection</span>
          </div>
        </div>
      </div>

      {/* Disclosure Guidelines */}
      <div className="max-w-3xl space-y-10 text-ink font-sans">
        <section className="border-t border-line pt-8">
          <span className="text-[11px] font-mono uppercase tracking-[0.08em] text-primary font-semibold block mb-2">
            01. REPORTING A VULNERABILITY
          </span>
          <h2 className="text-xl font-bold tracking-tight text-ink mb-3">
            How to Submit Findings
          </h2>
          <div className="text-sm text-muted leading-relaxed space-y-3">
            <p>
              If you believe you have discovered a security vulnerability in CodeGuard (including AST transform bypasses, sandbox container breakouts, or credential leakage), please report it directly through one of our private channels:
            </p>
            <div className="p-4 rounded-[10px] border border-line bg-surface-1 space-y-2 font-mono text-xs text-ink">
              <div className="flex items-center justify-between">
                <span>Direct Security Email:</span>
                <span className="text-primary font-bold">security@codeguard.dev</span>
              </div>
              <div className="flex items-center justify-between pt-2 border-t border-line">
                <span>GitHub Security Advisories:</span>
                <a
                  href="https://github.com/dhanushkumar-amk/CODEGUARD---NVIDIA-HACKTHON-PROJECT/security/advisories"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline flex items-center gap-1"
                >
                  <span>Submit Advisory</span>
                  <ExternalLink size={11} />
                </a>
              </div>
            </div>
          </div>
        </section>

        <section className="border-t border-line pt-8">
          <span className="text-[11px] font-mono uppercase tracking-[0.08em] text-primary font-semibold block mb-2">
            02. SCOPE
          </span>
          <h2 className="text-xl font-bold tracking-tight text-ink mb-3">
            Program Scope & Boundaries
          </h2>
          <div className="text-sm text-muted leading-relaxed space-y-3">
            <p>
              The following targets are strictly in-scope for security evaluations:
            </p>
            <ul className="list-disc list-inside space-y-1 pl-2">
              <li>CodeGuard FastAPI backend orchestration routes (`/api/scan`, `/api/verify`).</li>
              <li>Headless Chromium sandbox execution environment isolation.</li>
              <li>Git clone and AST parsing memory safety.</li>
              <li>NVIDIA Nemotron prompt injection or data leakage vulnerabilities.</li>
            </ul>
            <p className="pt-2 text-xs text-muted flex items-center gap-1.5">
              <AlertTriangle size={13} className="text-amber-500 shrink-0" />
              <span>Out of scope: Denial of Service (DoS) attacks against public demo APIs and social engineering.</span>
            </p>
          </div>
        </section>

        <section className="border-t border-line pt-8">
          <span className="text-[11px] font-mono uppercase tracking-[0.08em] text-primary font-semibold block mb-2">
            03. ISSUE TRACKER
          </span>
          <h2 className="text-xl font-bold tracking-tight text-ink mb-3">
            Non-Security Bugs & Feature Requests
          </h2>
          <p className="text-sm text-muted leading-relaxed mb-4">
            For non-sensitive bugs, UI glitches, or feature proposals regarding WCAG rules, please use our public GitHub Issues tracker.
          </p>
          <a
            href="https://github.com/dhanushkumar-amk/CODEGUARD---NVIDIA-HACKTHON-PROJECT/issues"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-[8px] bg-ink text-paper text-xs font-mono uppercase tracking-[0.08em] hover:bg-ink/90 transition-all font-semibold"
          >
            <span>GitHub Issues Tracker</span>
            <ExternalLink size={12} />
          </a>
        </section>
      </div>
    </div>
  );
};
