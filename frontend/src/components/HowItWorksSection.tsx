import React from 'react';
import { Search, Wrench, ShieldCheck } from 'lucide-react';

export const HowItWorksSection: React.FC = () => {
  const steps = [
    {
      title: 'Detect',
      icon: <Search size={20} className="text-muted shrink-0" strokeWidth={1.5} />,
      desc: 'Static markup extractors and WCAG rule checks inspect UI components to locate accessibility violations. Nemotron Fast catches additional semantic and contrast defects.',
    },
    {
      title: 'Fix',
      icon: <Wrench size={20} className="text-muted shrink-0" strokeWidth={1.5} />,
      desc: 'Nemotron Ultra synthesizes exact, minimal unified diffs grounded in official WCAG guidance while preserving your codebase conventions and unrelated logic.',
    },
    {
      title: 'Verify',
      icon: <ShieldCheck size={20} className="text-muted shrink-0" strokeWidth={1.5} />,
      desc: 'Isolated verification sandboxes run axe-core audits and your existing test suite to objectively confirm each fix resolves the issue with zero regressions.',
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
