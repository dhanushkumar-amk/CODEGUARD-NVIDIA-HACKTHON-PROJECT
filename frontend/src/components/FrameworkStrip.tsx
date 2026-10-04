import React from 'react';

export const FrameworkStrip: React.FC = () => {
  const frameworks = [
    {
      name: 'React',
      svg: (
        <svg viewBox="-11.5 -10.23174 23 20.46348" className="h-5 w-5 fill-current">
          <circle cx="0" cy="0" r="2.05" />
          <g stroke="currentColor" strokeWidth="1" fill="none">
            <ellipse rx="11" ry="4.2" />
            <ellipse rx="11" ry="4.2" transform="rotate(60)" />
            <ellipse rx="11" ry="4.2" transform="rotate(120)" />
          </g>
        </svg>
      ),
    },
    {
      name: 'Vue',
      svg: (
        <svg viewBox="0 0 256 221" className="h-4 w-4 fill-current">
          <path d="M204.8 0H256L128 220.8 0 0h97.92L128 51.2 157.44 0h47.36z" />
          <path d="M0 0l128 220.8L256 0h-51.2L128 132.48 49.92 0H0z" opacity="0.6" />
        </svg>
      ),
    },
    {
      name: 'Next.js',
      svg: (
        <svg viewBox="0 0 180 180" className="h-4 w-4 fill-current">
          <mask height="180" id="mask0" maskUnits="userSpaceOnUse" width="180" x="0" y="0" style={{ maskType: 'alpha' }}>
            <circle cx="90" cy="90" fill="black" r="90" />
          </mask>
          <g mask="url(#mask0)">
            <circle cx="90" cy="90" fill="currentColor" r="90" />
            <path d="M149.508 157.52L69.142 54H54V125.97H66.1136V69.3836L139.999 164.845C143.333 162.614 146.509 160.165 149.508 157.52Z" fill="#FDFCF9" />
            <path d="M115 54H127V126H115V54Z" fill="#FDFCF9" />
          </g>
        </svg>
      ),
    },
    {
      name: 'Astro',
      svg: (
        <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
        </svg>
      ),
    },
    {
      name: 'Svelte',
      svg: (
        <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M17 8a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4 4 4 0 0 0 2 3.46L17 15a4 4 0 0 1 0 7H9a4 4 0 0 1-4-4" />
        </svg>
      ),
    },
  ];

  return (
    <div className="w-full flex flex-col gap-3 text-left">
      <span className="text-[11px] font-mono uppercase tracking-[0.08em] text-muted">
        Built to check codebases like
      </span>

      {/* Row of hairline-bordered cells, shared edges like a table */}
      <div className="w-full border border-line grid grid-cols-2 sm:grid-cols-5 divide-y sm:divide-y-0 sm:divide-x divide-line">
        {frameworks.map((fw) => (
          <div
            key={fw.name}
            className="flex items-center justify-center gap-2.5 py-4 px-3 text-muted hover:text-ink transition-colors"
          >
            {fw.svg}
            <span className="font-mono text-xs uppercase tracking-[0.08em] font-medium">
              {fw.name}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
