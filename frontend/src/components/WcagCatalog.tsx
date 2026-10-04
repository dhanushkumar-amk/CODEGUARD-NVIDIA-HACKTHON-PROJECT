import React, { useState } from 'react';
import { Eye, Image, FormInput, Sliders, KeyRound, Focus, CheckCircle2 } from 'lucide-react';

export const WcagCatalog: React.FC = () => {
  const [activeFilter, setActiveFilter] = useState<'all' | 'perceivable' | 'operable' | 'robust'>('all');

  const rules = [
    {
      id: '1.4.3',
      level: 'AA',
      principle: 'perceivable',
      category: 'Contrast (Minimum)',
      icon: <Eye size={18} strokeWidth={1.75} />,
      problem: 'Text elements with low luminance contrast ratio (< 4.5:1) against their backgrounds.',
      fix: 'Computes WCAG contrast formulas and adjusts color luminance to guaranteed 4.5:1+ threshold.',
      sampleFix: 'text-slate-400 → text-slate-100 (7.2:1)',
    },
    {
      id: '1.1.1',
      level: 'A',
      principle: 'perceivable',
      category: 'Non-Text Content',
      icon: <Image size={18} strokeWidth={1.75} />,
      problem: 'Images, icons, and SVG graphics missing descriptive alternative text or aria tags.',
      fix: 'Synthesizes contextual alt tags with Nemotron vision reasoning or applies aria-hidden to decorative glyphs.',
      sampleFix: '<img src="logo.png" /> → alt="Company logo"',
    },
    {
      id: '3.3.2',
      level: 'A',
      principle: 'operable',
      category: 'Labels or Instructions',
      icon: <FormInput size={18} strokeWidth={1.75} />,
      problem: 'Form inputs, dropdowns, and textfields without linked programmatic labels.',
      fix: 'Injects explicit <label htmlFor="..."> linkages or aria-label attributes without disturbing layouts.',
      sampleFix: '<input id="email" /> → <label htmlFor="email">Email</label>',
    },
    {
      id: '4.1.2',
      level: 'A',
      principle: 'robust',
      category: 'Name, Role, Value',
      icon: <Sliders size={18} strokeWidth={1.75} />,
      problem: 'Clickable <div> or <span> elements lacking semantic roles and keyboard handlers.',
      fix: 'Refactors into native <button> or injects role="button", tabIndex={0}, and onKeyDown handlers.',
      sampleFix: '<div onClick={fn}> → <button type="button" onClick={fn}>',
    },
    {
      id: '2.1.2',
      level: 'A',
      principle: 'operable',
      category: 'No Keyboard Trap',
      icon: <KeyRound size={18} strokeWidth={1.75} />,
      problem: 'Modals and dialog drawers trapping keyboard focus without an escape path.',
      fix: 'Wraps dialogs in focus traps and binds global Escape key listeners to close overlays cleanly.',
      sampleFix: 'Focus-trap cycle + Escape key listener',
    },
    {
      id: '2.4.7',
      level: 'AA',
      principle: 'operable',
      category: 'Focus Visible',
      icon: <Focus size={18} strokeWidth={1.75} />,
      problem: 'CSS rules stripping default focus outlines (outline: none) with no replacement.',
      fix: 'Restores high-contrast, theme-aware focus indicator rings visible across all browsers.',
      sampleFix: 'outline-none → focus-visible:ring-2 focus-visible:ring-primary',
    },
  ];

  const filteredRules =
    activeFilter === 'all'
      ? rules
      : rules.filter((r) => r.principle === activeFilter);

  return (
    <section className="w-full border-t border-line py-12 md:py-24 text-left font-sans">
      {/* Header and Filter Row */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
        <div className="max-w-xl">
          <span className="text-[11px] font-mono uppercase tracking-[0.08em] text-primary font-semibold block mb-3 select-none">
            STANDARDS COVERAGE
          </span>
          <h2 className="text-2xl sm:text-3xl font-bold font-sans text-ink tracking-tight">
            Targeted WCAG 2.2 AA Criteria
          </h2>
          <p className="text-sm sm:text-base text-muted leading-relaxed mt-2 font-sans">
            Every violation detected by CodeGuard maps directly to authoritative W3C standards, remediated with deterministic unified diffs.
          </p>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-2 flex-wrap text-xs font-mono">
          {(
            [
              { id: 'all', label: 'ALL CRITERIA' },
              { id: 'perceivable', label: 'PERCEIVABLE' },
              { id: 'operable', label: 'OPERABLE' },
              { id: 'robust', label: 'ROBUST' },
            ] as const
          ).map((filter) => (
            <button
              key={filter.id}
              type="button"
              onClick={() => setActiveFilter(filter.id)}
              className={`px-3 py-1.5 rounded-[6px] transition-colors uppercase tracking-[0.08em] text-[11px] cursor-pointer border ${
                activeFilter === filter.id
                  ? 'bg-ink text-paper border-ink'
                  : 'bg-paper text-muted border-line hover:text-ink hover:border-ink/30'
              }`}
            >
              {filter.label}
            </button>
          ))}
        </div>
      </div>

      {/* 6 WCAG Rules Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredRules.map((rule) => (
          <div
            key={rule.id}
            className="group relative p-6 rounded-[8px] border border-line bg-paper hover:bg-surface-1/50 hover:border-ink/30 transition-all duration-300 ease-out hover:-translate-y-1 cursor-pointer flex flex-col justify-between select-none"
          >
            <div>
              {/* Header */}
              <div className="flex items-center justify-between mb-5">
                <div className="w-9 h-9 rounded-[6px] border border-line bg-surface-1 flex items-center justify-center text-ink group-hover:border-primary/40 group-hover:text-primary transition-all duration-300">
                  {rule.icon}
                </div>
                <div className="flex items-center gap-1.5 font-mono text-[11px]">
                  <span className="px-2 py-0.5 rounded-[4px] bg-surface-1 text-muted border border-line">
                    WCAG {rule.id}
                  </span>
                  <span className="px-1.5 py-0.5 rounded-[4px] bg-primary/10 text-primary border border-primary/20 font-semibold">
                    {rule.level}
                  </span>
                </div>
              </div>

              {/* Title */}
              <h3 className="text-base font-bold font-sans text-ink tracking-tight mb-2 group-hover:text-primary transition-colors duration-200">
                {rule.category}
              </h3>

              {/* Problem */}
              <p className="text-xs text-muted leading-relaxed mb-3 font-sans">
                {rule.problem}
              </p>

              {/* Fix narrative */}
              <p className="text-xs text-ink/80 leading-relaxed font-sans mb-4">
                {rule.fix}
              </p>
            </div>

            {/* Code patch example at bottom */}
            <div className="pt-3 border-t border-line flex items-center justify-between text-[11px] font-mono text-muted">
              <span className="truncate max-w-[200px] text-ink/90 font-medium">
                {rule.sampleFix}
              </span>
              <span className="inline-flex items-center gap-1 text-emerald-600 font-medium shrink-0 ml-2">
                <CheckCircle2 size={12} /> Auto-fixed
              </span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};
