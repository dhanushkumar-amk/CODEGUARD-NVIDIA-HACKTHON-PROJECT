import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { ArrowUpRight, Search, Cpu, ShieldCheck } from 'lucide-react';
import { startScan } from '../api/client';
import { RepoUrlInput, DEFAULT_DEMO_REPO } from '../components/RepoUrlInput';
import { EngineArchitecture } from '../components/EngineArchitecture';
import { WcagCatalog } from '../components/WcagCatalog';
import { HowItWorksSection } from '../components/HowItWorksSection';

export const Home: React.FC = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleStartScan = async (repoUrl: string, branch: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const { scan_id } = await startScan(repoUrl, branch);
      navigate(`/scan/${scan_id}`);
    } catch (err: unknown) {
      let message = 'Failed to initiate repository scan. Please verify the URL and try again.';
      const responseDetail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
      if (typeof responseDetail === 'string') {
        message = responseDetail;
      } else if (Array.isArray(responseDetail) && responseDetail.length > 0) {
        message = (responseDetail[0] as { msg?: string })?.msg || JSON.stringify(responseDetail);
      } else if (axios.isAxiosError(err) && err.message) {
        message = err.message;
      } else if (err instanceof Error) {
        message = err.message;
      }
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  const platformFeatures = [
    {
      icon: <Search size={18} strokeWidth={1.75} />,
      tag: 'STATIC AST ENGINE',
      title: 'Automated WCAG Detection',
      description:
        'Parses React, Next.js, Vue, and Svelte AST trees using axe-core heuristics to pinpoint contrast ratios, unlabeled inputs, and keyboard navigation traps.',
      badge: 'WCAG 2.2 AA Certified',
      metric: '0 False Alarms',
    },
    {
      icon: <Cpu size={18} strokeWidth={1.75} />,
      tag: 'NVIDIA NEMOTRON',
      title: 'Autonomous Code Remediation',
      description:
        'Synthesizes clean, minimal unified diffs addressing root causes while strictly respecting existing design tokens, Tailwind configurations, and component styles.',
      badge: 'Nemotron Ultra 70B',
      metric: 'Non-Breaking Diffs',
    },
    {
      icon: <ShieldCheck size={18} strokeWidth={1.75} />,
      tag: 'NEBIUS SANDBOXES',
      title: 'Deterministic Sandbox Proof',
      description:
        'Spins up ephemeral headless Chromium browser sandboxes to run end-to-end tests and empirically prove zero accessibility regressions before opening a PR.',
      badge: 'Chromium Sandbox',
      metric: '100% Proven Proof',
    },
  ];

  return (
    <div className="w-full flex flex-col">
      {/* 1. HERO — Single centered column, max-width 640px */}
      <section className="w-full pt-12 md:pt-24 pb-12 md:pb-16 text-center">
        <div className="max-w-[640px] mx-auto flex flex-col items-center text-center">
          {/* Small mono eyebrow label */}
          <span className="text-[11px] font-mono uppercase tracking-[0.08em] text-primary font-semibold block mb-4 select-none">
            ACCESSIBILITY, VERIFIED
          </span>

          {/* Headline */}
          <h1 className="text-3xl sm:text-4xl lg:text-[44px] font-bold font-sans text-ink leading-[1.12] tracking-tight mb-5">
            Every fix, tested before you trust it.
          </h1>

          {/* Subheadline paragraph */}
          <p className="font-sans text-base sm:text-lg leading-relaxed text-muted mb-8">
            CodeGuard scans your repo for accessibility violations, writes fixes with NVIDIA Nemotron, and confirms each one in an isolated sandbox before you merge anything.
          </p>

          {/* Input and Buttons */}
          <RepoUrlInput
            onStartScan={handleStartScan}
            isLoading={isLoading}
            serverError={error}
            onClearError={() => setError(null)}
            demoRepoUrl={DEFAULT_DEMO_REPO}
          />
        </div>
      </section>

      {/* 2. CORE CAPABILITIES — Clean, monochrome, hoverable cards with minimal micro-lift */}
      <section className="w-full pb-12 md:pb-24">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {platformFeatures.map((feature) => (
            <div
              key={feature.title}
              className="group relative p-6 sm:p-8 rounded-[8px] border border-line bg-paper text-left flex flex-col justify-between gap-6 transition-all duration-300 ease-out hover:-translate-y-1 hover:border-ink/40 hover:bg-surface-1/50 cursor-pointer select-none"
            >
              <div>
                {/* Header row: Icon box on left, tag and arrow on right */}
                <div className="flex items-center justify-between mb-6">
                  <div className="w-10 h-10 rounded-[6px] border border-line bg-surface-1 flex items-center justify-center text-ink group-hover:border-primary/40 group-hover:text-primary transition-all duration-300">
                    {feature.icon}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono uppercase tracking-[0.08em] px-2 py-0.5 rounded-[4px] bg-surface-1 text-muted border border-line">
                      {feature.tag}
                    </span>
                    <div className="w-7 h-7 rounded-full border border-line flex items-center justify-center text-muted group-hover:text-ink group-hover:border-ink/40 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-all duration-300">
                      <ArrowUpRight size={13} />
                    </div>
                  </div>
                </div>

                {/* Title */}
                <h3 className="text-lg font-bold font-sans text-ink tracking-tight mb-2 group-hover:text-primary transition-colors duration-200">
                  {feature.title}
                </h3>

                {/* Description */}
                <p className="text-sm font-sans text-muted leading-relaxed">
                  {feature.description}
                </p>
              </div>

              {/* Footer hairline divider with micro-metrics */}
              <div className="pt-4 border-t border-line flex items-center justify-between text-[11px] font-mono uppercase tracking-[0.08em] text-muted">
                <span>{feature.badge}</span>
                <span className="text-ink font-medium">{feature.metric}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 3. ENGINE ARCHITECTURE — NVIDIA Nemotron & Nebius Sandboxes */}
      <EngineArchitecture />

      {/* 4. WCAG STANDARDS CATALOG — Real rules and code remediations */}
      <WcagCatalog />

      {/* 5. HOW IT WORKS PIPELINE — Detect • Fix • Verify */}
      <HowItWorksSection />
    </div>
  );
};
