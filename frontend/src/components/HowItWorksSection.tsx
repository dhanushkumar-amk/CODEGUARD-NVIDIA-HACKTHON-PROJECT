import React from 'react';
import { Search, Wrench, ShieldCheck } from 'lucide-react';

export const HowItWorksSection: React.FC = () => {
  const steps = [
    {
      title: 'Detect',
      icon: <Search size={20} className="text-muted shrink-0" strokeWidth={1.5} />,
      desc: 'AST parser and axe-core inspect UI components to extract scannable markup chunks and locate WCAG violations. Nemotron Nano filters benign false alarms and isolates root causes in milliseconds.',
    },
    {
      title: 'Fix',
      icon: <Wrench size={20} className="text-muted shrink-0" strokeWidth={1.5} />,
      desc: 'Nemotron Ultra synthesizes exact, minimal unified diffs preserving your design tokens and codebase conventions. Patches directly address WCAG criteria without touching unrelated business logic.',
    },
    {
      title: 'Verify',
      icon: <ShieldCheck size={20} className="text-muted shrink-0" strokeWidth={1.5} />,
      desc: 'Ephemeral Nebius sandboxes run browser heuristics to objectively confirm accessibility compliance before merging. Every remediation is proven with zero regressions before you trust it.',
    },
  ];

  return (
    <section className="w-full border-t border-line py-12 md:py-24 text-left">
      {/* Top 2-column header row: heading and side paragraph top-aligned */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start mb-12">
        <div>
          <span className="text-[11px] font-mono uppercase tracking-[0.08em] text-primary font-semibold block mb-6">
            HOW IT WORKS
          </span>
          <h2 className="text-2xl sm:text-3xl font-bold font-sans text-ink tracking-tight">
            Issues get fixed on CodeGuard.
          </h2>
        </div>
        <p className="text-base text-muted leading-relaxed font-sans">
          CodeGuard combines automated deterministic AST scanning with NVIDIA Nemotron LLM reasoning and isolated sandbox verification to autonomously find, fix, and prove accessibility compliance across your entire repository.
        </p>
      </div>

      {/* 3-column grid separated by hairline dividers with consistent 32px padding */}
      <div className="w-full border-t border-line grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-line pt-0">
        {steps.map((step) => (
          <div
            key={step.title}
            className="p-8 first:md:pl-0 last:md:pr-0 flex flex-col text-left"
          >
            <div className="flex items-center gap-4 mb-2">
              {step.icon}
              <h3 className="text-lg font-bold font-sans text-ink tracking-tight">
                {step.title}
              </h3>
            </div>
            <p className="text-sm text-muted leading-relaxed font-sans">
              {step.desc}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
};
