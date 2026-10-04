import React, { useState } from 'react';
import { Eye, Image, FormInput, Sliders, KeyRound, Focus, CheckCircle2, ArrowUpRight } from 'lucide-react';

export const WcagCatalog: React.FC = () => {
  const [activeFilter, setActiveFilter] = useState<'all' | 'perceivable' | 'operable' | 'robust'>('all');

  const rules = [
    {
      id: '1.4.3',
      level: 'AA',
      principle: 'perceivable',
      category: 'Contrast (Minimum)',
      icon: <Eye size={17} strokeWidth={1.75} />,
      description: 'Detects text with contrast ratios below 4.5:1 and recalculates compliant color luminance values.',
      sampleFix: 'text-slate-400 → text-slate-100',
      // 1. Purple
      hoverGradient: 'linear-gradient(145deg, #704BEA 0%, #4322B3 100%)',
    },
    {
      id: '1.1.1',
      level: 'A',
      principle: 'perceivable',
      category: 'Non-Text Content',
      icon: <Image size={17} strokeWidth={1.75} />,
      description: 'Synthesizes contextual alt tags for imagery or marks decorative icons with aria-hidden.',
      sampleFix: '<img src="logo.png" /> → alt="..."',
      // 2. Coral / Orange
      hoverGradient: 'linear-gradient(145deg, #FF5C38 0%, #D83410 100%)',
    },
    {
      id: '3.3.2',
      level: 'A',
      principle: 'operable',
      category: 'Labels or Instructions',
      icon: <FormInput size={17} strokeWidth={1.75} />,
      description: 'Injects explicit <label htmlFor="..."> linkages or programmatic aria attributes to form fields.',
      sampleFix: '<input /> → <label htmlFor="...">',
      // 3. Cyan / Teal
      hoverGradient: 'linear-gradient(145deg, #0891B2 0%, #0E7490 100%)',
    },
    {
      id: '4.1.2',
      level: 'A',
      principle: 'robust',
      category: 'Name, Role, Value',
      icon: <Sliders size={17} strokeWidth={1.75} />,
      description: 'Converts non-semantic clickable elements into accessible native buttons with keyboard listeners.',
      sampleFix: '<div onClick> → <button onClick>',
      // 4. Cobalt / Blue
      hoverGradient: 'linear-gradient(145deg, #2563EB 0%, #1D4ED8 100%)',
    },
    {
      id: '2.1.2',
      level: 'A',
      principle: 'operable',
      category: 'No Keyboard Trap',
      icon: <KeyRound size={17} strokeWidth={1.75} />,
      description: 'Wraps modals in accessible focus traps and binds global Escape key handlers to avoid traps.',
      sampleFix: 'Focus-trap cycle + Escape key',
      // 5. Amber / Gold
      hoverGradient: 'linear-gradient(145deg, #D97706 0%, #B45309 100%)',
    },
    {
      id: '2.4.7',
      level: 'AA',
      principle: 'operable',
      category: 'Focus Visible',
      icon: <Focus size={17} strokeWidth={1.75} />,
      description: 'Replaces outline:none rules with high-contrast, theme-aware focus indicator rings.',
      sampleFix: 'outline:none → focus-visible:ring-2',
      // 6. Emerald / Mint Green
      hoverGradient: 'linear-gradient(145deg, #059669 0%, #047857 100%)',
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
                  : 'bg-paper text-muted border-line hover:text-ink hover:border-ink/40'
              }`}
            >
              {filter.label}
            </button>
          ))}
        </div>
      </div>

      {/* 6 Cards with Smooth Color Hover Animation */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredRules.map((rule) => (
          <div
            key={rule.id}
            className="group relative overflow-hidden p-6 sm:p-7 rounded-[12px] border border-line bg-paper text-left flex flex-col justify-between min-h-[250px] transition-all duration-700 ease-out hover:-translate-y-1 hover:shadow-lg hover:shadow-black/5 hover:border-transparent cursor-pointer select-none"
          >
            {/* Smooth colored background layer — Fades in smoothly and slowly on hover */}
            <div
              className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-700 ease-out pointer-events-none rounded-[12px]"
              style={{ background: rule.hoverGradient }}
            />

            {/* Top section content */}
            <div className="relative z-10">
              {/* Header row */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-[8px] border border-line bg-surface-1 flex items-center justify-center text-ink group-hover:bg-white/20 group-hover:border-white/30 group-hover:text-white transition-all duration-700 ease-out">
                    {rule.icon}
                  </div>
                  <span className="text-[11px] font-mono uppercase tracking-[0.08em] text-muted group-hover:text-white/80 transition-colors duration-700 ease-out">
                    WCAG {rule.id}
                  </span>
                </div>

                {/* Inspect action badge */}
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full border border-line bg-surface-1 text-muted group-hover:bg-white group-hover:text-ink group-hover:border-transparent group-hover:shadow-sm transition-all duration-700 ease-out flex items-center gap-1">
                    <span>Inspect</span>
                    <ArrowUpRight
                      size={11}
                      className="transition-transform duration-700 ease-out group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
                    />
                  </span>
                </div>
              </div>

              {/* Title */}
              <h3 className="text-base sm:text-lg font-bold font-sans text-ink tracking-tight mb-2 group-hover:text-white transition-colors duration-700 ease-out">
                {rule.category}
              </h3>

              {/* Minimal, concise description */}
              <p className="text-xs text-muted leading-relaxed font-sans group-hover:text-white/85 transition-colors duration-700 ease-out">
                {rule.description}
              </p>
            </div>

            {/* Code patch example at bottom */}
            <div className="relative z-10 pt-3 mt-4 border-t border-line group-hover:border-white/20 flex items-center justify-between text-[11px] font-mono text-muted group-hover:text-white/90 transition-all duration-700 ease-out">
              <span className="truncate max-w-[200px] font-medium text-ink/80 group-hover:text-white transition-colors duration-700 ease-out">
                {rule.sampleFix}
              </span>
              <span className="inline-flex items-center gap-1 text-emerald-600 group-hover:text-white font-medium shrink-0 ml-2 transition-colors duration-700 ease-out">
                <CheckCircle2 size={12} className="group-hover:text-white transition-colors duration-700 ease-out" />
                <span className="text-[10px] uppercase tracking-wider">Verified</span>
              </span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};
