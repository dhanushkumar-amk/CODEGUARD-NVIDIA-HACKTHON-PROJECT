import React from 'react';
import { Link } from 'react-router-dom';
import { Lock, EyeOff, Cpu, CheckCircle2, ArrowLeft, ExternalLink } from 'lucide-react';

export const Privacy: React.FC = () => {
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
            LEGAL & COMPLIANCE
          </span>
          <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-surface-1 text-muted border border-line">
            Effective: October 2026
          </span>
        </div>
        <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold text-ink tracking-tight font-sans mb-4">
          Privacy Policy
        </h1>
        <p className="text-base sm:text-lg text-muted leading-relaxed font-sans">
          CodeGuard is built on a strict zero-retention architecture. Your repository source code is never stored, never indexed for public access, and never used to train foundation models.
        </p>
      </div>

      {/* 3 Core Guarantees Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
        <div className="p-6 rounded-[12px] border border-line bg-paper text-left flex flex-col justify-between">
          <div>
            <div className="w-8 h-8 rounded-[8px] border border-line bg-surface-1 flex items-center justify-center text-primary mb-4">
              <EyeOff size={16} />
            </div>
            <h3 className="font-bold text-ink text-base mb-1 font-sans">Zero Code Retention</h3>
            <p className="text-xs text-muted leading-relaxed font-sans">
              Scanned repositories are processed in ephemeral memory. Cloned working directories are wiped immediately upon scan completion.
            </p>
          </div>
          <div className="pt-4 mt-4 border-t border-line text-[11px] font-mono text-emerald-600 flex items-center gap-1">
            <CheckCircle2 size={12} />
            <span>Ephemeral RAM Execution</span>
          </div>
        </div>

        <div className="p-6 rounded-[12px] border border-line bg-paper text-left flex flex-col justify-between">
          <div>
            <div className="w-8 h-8 rounded-[8px] border border-line bg-surface-1 flex items-center justify-center text-primary mb-4">
              <Cpu size={16} />
            </div>
            <h3 className="font-bold text-ink text-base mb-1 font-sans">No Model Training</h3>
            <p className="text-xs text-muted leading-relaxed font-sans">
              Code snippets transmitted to NVIDIA Nemotron on Nebius Token Factory are strictly used for single-turn inference, never for fine-tuning.
            </p>
          </div>
          <div className="pt-4 mt-4 border-t border-line text-[11px] font-mono text-emerald-600 flex items-center gap-1">
            <CheckCircle2 size={12} />
            <span>Zero Training Ingestion</span>
          </div>
        </div>

        <div className="p-6 rounded-[12px] border border-line bg-paper text-left flex flex-col justify-between">
          <div>
            <div className="w-8 h-8 rounded-[8px] border border-line bg-surface-1 flex items-center justify-center text-primary mb-4">
              <Lock size={16} />
            </div>
            <h3 className="font-bold text-ink text-base mb-1 font-sans">Isolated Sandboxing</h3>
            <p className="text-xs text-muted leading-relaxed font-sans">
              Before patch verification, generated code diffs execute inside isolated, headless Chromium sandboxes with restricted network access.
            </p>
          </div>
          <div className="pt-4 mt-4 border-t border-line text-[11px] font-mono text-emerald-600 flex items-center gap-1">
            <CheckCircle2 size={12} />
            <span>Air-Gapped Verification</span>
          </div>
        </div>
      </div>

      {/* Detailed Policy Sections */}
      <div className="max-w-3xl space-y-12 text-ink font-sans">
        {/* Section 1 */}
        <section className="border-t border-line pt-8">
          <span className="text-[11px] font-mono uppercase tracking-[0.08em] text-primary font-semibold block mb-2">
            01. DATA COLLECTION & INGESTION
          </span>
          <h2 className="text-xl font-bold tracking-tight text-ink mb-3">
            What Information CodeGuard Processes
          </h2>
          <div className="text-sm text-muted leading-relaxed space-y-3">
            <p>
              When you initiate an autonomous accessibility scan via CodeGuard, we ingest only the specific files required for WCAG 2.2 AA analysis (primarily HTML, TSX, JSX, Vue, Svelte, and CSS files).
            </p>
            <ul className="list-disc list-inside space-y-1 pl-2">
              <li>Public or provided repository URLs and specified branch heads.</li>
              <li>Relevant frontend component code fragments containing UI markup and accessibility nodes.</li>
              <li>Anonymized scan performance metrics (execution time, count of detected violations, AST parser latency).</li>
            </ul>
            <p>
              CodeGuard does not request or store repository passwords, SSH private keys, personal contact books, or database secrets.
            </p>
          </div>
        </section>

        {/* Section 2 */}
        <section className="border-t border-line pt-8">
          <span className="text-[11px] font-mono uppercase tracking-[0.08em] text-primary font-semibold block mb-2">
            02. AI INFERENCE PIPELINE
          </span>
          <h2 className="text-xl font-bold tracking-tight text-ink mb-3">
            NVIDIA Nemotron & Nebius Token Factory Infrastructure
          </h2>
          <div className="text-sm text-muted leading-relaxed space-y-3">
            <p>
              Autonomous code remediation is powered by NVIDIA Nemotron-4 / Llama-Nemotron foundation models hosted on high-performance Nebius Token Factory endpoints.
            </p>
            <p>
              During remediation:
            </p>
            <ul className="list-disc list-inside space-y-1 pl-2">
              <li>AST code snippets and WCAG violation context are transmitted via TLS 1.3 encrypted sockets.</li>
              <li>Inference is strictly stateless: prompts are discarded immediately following token generation.</li>
              <li>Nebius infrastructure operates in private enterprise VPCs with zero data caching or persistent logging of source payloads.</li>
            </ul>
          </div>
        </section>

        {/* Section 3 */}
        <section className="border-t border-line pt-8">
          <span className="text-[11px] font-mono uppercase tracking-[0.08em] text-primary font-semibold block mb-2">
            03. SANDBOX ISOLATION
          </span>
          <h2 className="text-xl font-bold tracking-tight text-ink mb-3">
            Deterministic Playwright Sandbox Security
          </h2>
          <div className="text-sm text-muted leading-relaxed space-y-3">
            <p>
              Unlike traditional AI agents that output untested code, CodeGuard executes every generated patch against a headless browser sandbox to prove compliance.
            </p>
            <p>
              To ensure system integrity, sandboxes operate with:
            </p>
            <ul className="list-disc list-inside space-y-1 pl-2">
              <li>Restricted outbound network egress to prevent arbitrary exfiltration.</li>
              <li>Strict execution time limits (max 15 seconds per verification cycle) to protect against infinite loops or resource exhaustion.</li>
              <li>Ephemeral container lifecycles that self-terminate immediately upon report synthesis.</li>
            </ul>
          </div>
        </section>

        {/* Section 4 */}
        <section className="border-t border-line pt-8">
          <span className="text-[11px] font-mono uppercase tracking-[0.08em] text-primary font-semibold block mb-2">
            04. THIRD-PARTY INTEGRATIONS & COOKIES
          </span>
          <h2 className="text-xl font-bold tracking-tight text-ink mb-3">
            External Services & Tracking
          </h2>
          <div className="text-sm text-muted leading-relaxed space-y-3">
            <p>
              CodeGuard does not use third-party marketing cookies, user profiling beacons, or behavioral ad trackers. Local storage is used strictly for storing scan session IDs during active browser sessions.
            </p>
            <p>
              External interactions are limited to:
            </p>
            <ul className="list-disc list-inside space-y-1 pl-2">
              <li>Public Git providers (GitHub, GitLab, Bitbucket) to fetch target repository trees.</li>
              <li>Nebius AI Studio API endpoints for Nemotron inference.</li>
            </ul>
          </div>
        </section>

        {/* Section 5 */}
        <section className="border-t border-line pt-8">
          <span className="text-[11px] font-mono uppercase tracking-[0.08em] text-primary font-semibold block mb-2">
            05. SECURITY CONTACT & DISCLOSURE
          </span>
          <h2 className="text-xl font-bold tracking-tight text-ink mb-3">
            Responsible Disclosure
          </h2>
          <div className="text-sm text-muted leading-relaxed space-y-3">
            <p>
              We welcome security researchers and open-source contributors to inspect our codebase and report any potential vulnerabilities.
            </p>
            <div className="p-4 rounded-[8px] border border-line bg-surface-1 font-mono text-xs text-ink flex items-center justify-between">
              <span>Security Inquiries: security@codeguard.dev</span>
              <a
                href="https://github.com/dhanushkumar-amk/CODEGUARD---NVIDIA-HACKTHON-PROJECT/issues"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline flex items-center gap-1"
              >
                <span>Report on GitHub</span>
                <ExternalLink size={12} />
              </a>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};
