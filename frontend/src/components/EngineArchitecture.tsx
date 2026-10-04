import React from 'react';
import { Zap, Cpu, ShieldCheck, GitPullRequest, ArrowUpRight } from 'lucide-react';

export const EngineArchitecture: React.FC = () => {
  const tiers = [
    {
      name: 'Nemotron Fast (12B)',
      tag: 'STAGE 1 • SCREEN',
      icon: <Zap size={18} strokeWidth={1.75} />,
      role: 'AST Syntax & Rule Extraction',
      description:
        'High-throughput parser inspects JSX/HTML trees, eliminates benign false positives, and categorizes WCAG violations in under 1.2s.',
      latency: '< 1.2s latency',
      cost: '$0.0042 / scan',
    },
    {
      name: 'Nemotron Ultra (70B)',
      tag: 'STAGE 2 • REASON',
      icon: <Cpu size={18} strokeWidth={1.75} />,
      role: 'Unified Diff Synthesis',
      description:
        'Deep AI reasoning generates minimal, non-breaking code patches that solve root causes while strictly preserving existing design tokens.',
      latency: 'Context-aware',
      cost: '$0.0293 / scan',
    },
    {
      name: 'Nebius Sandboxes',
      tag: 'STAGE 3 • VERIFY',
      icon: <ShieldCheck size={18} strokeWidth={1.75} />,
      role: 'Isolated Browser Heuristics',
      description:
        'Spins up ephemeral headless Chromium containers to run axe-core and test suites, empirically certifying 0 visual or functional regressions.',
      latency: 'Headless Chromium',
      cost: 'Isolated Runtime',
    },
    {
      name: 'Certified Delivery',
      tag: 'STAGE 4 • SHIP',
      icon: <GitPullRequest size={18} strokeWidth={1.75} />,
      role: 'Automated GitHub PR',
      description:
        'Pushes verified remediation branches directly to GitHub with verifiable before/after scores, executive summaries, and HTML audit logs.',
      latency: 'Direct to Git',
      cost: 'Zero Regressions',
    },
  ];

  return (
    <section className="w-full border-t border-line py-12 md:py-24 text-left font-sans">
      {/* Header row */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
        <div className="max-w-xl">
          <span className="text-[11px] font-mono uppercase tracking-[0.08em] text-primary font-semibold block mb-3 select-none">
            ENGINE ARCHITECTURE
          </span>
          <h2 className="text-2xl sm:text-3xl font-bold font-sans text-ink tracking-tight">
            Dual-LLM Pipeline &amp; Deterministic Sandboxes
          </h2>
          <p className="text-sm sm:text-base text-muted leading-relaxed mt-2 font-sans">
            CodeGuard balances rapid routine screening with deep generative reasoning on NVIDIA Nemotron and isolated browser verification in Nebius AI Cloud.
          </p>
        </div>

        <div className="text-[11px] font-mono uppercase tracking-[0.08em] text-muted shrink-0 pb-1">
          <span>Powered by NVIDIA &bull; Nebius Token Factory</span>
        </div>
      </div>

      {/* 4 Architecture Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {tiers.map((tier) => (
          <div
            key={tier.name}
            className="group relative p-6 rounded-[8px] border border-line bg-paper hover:bg-surface-1/50 hover:border-ink/30 transition-all duration-300 ease-out hover:-translate-y-1 cursor-pointer flex flex-col justify-between select-none"
          >
            <div>
              {/* Header: Icon + Stage Tag */}
              <div className="flex items-center justify-between mb-5">
                <div className="w-9 h-9 rounded-[6px] border border-line bg-surface-1 flex items-center justify-center text-ink group-hover:border-primary/40 group-hover:text-primary transition-all duration-300">
                  {tier.icon}
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] font-mono uppercase tracking-[0.08em] px-2 py-0.5 rounded-[4px] bg-surface-1 text-muted border border-line">
                    {tier.tag}
                  </span>
                  <div className="w-6 h-6 rounded-full border border-line flex items-center justify-center text-muted group-hover:text-ink group-hover:border-ink/40 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-all duration-300">
                    <ArrowUpRight size={12} />
                  </div>
                </div>
              </div>

              {/* Title & Role */}
              <h3 className="text-base font-bold font-sans text-ink tracking-tight mb-1 group-hover:text-primary transition-colors duration-200">
                {tier.name}
              </h3>
              <div className="text-xs font-mono text-muted mb-3">
                {tier.role}
              </div>

              {/* Description */}
              <p className="text-xs text-muted leading-relaxed font-sans">
                {tier.description}
              </p>
            </div>

            {/* Micro specs at bottom */}
            <div className="pt-4 mt-6 border-t border-line flex items-center justify-between text-[11px] font-mono text-muted">
              <span>{tier.latency}</span>
              <span className="text-ink font-medium">{tier.cost}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};
