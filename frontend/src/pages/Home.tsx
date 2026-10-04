import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { ArrowUpRight } from 'lucide-react';
import { startScan } from '../api/client';
import { RepoUrlInput, DEFAULT_DEMO_REPO } from '../components/RepoUrlInput';
import { LiveFixDemo } from '../components/LiveFixDemo';
import { StatsRow } from '../components/StatsRow';
import { FrameworkStrip } from '../components/FrameworkStrip';
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

  return (
    <div className="w-full flex flex-col gap-12 sm:gap-16 py-6 text-left">
      {/* HERO SECTION — two column, left-aligned, NOT centered */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center">
        {/* Left Column (7 cols): Bold Public Sans headline, grey subheadline, buttons, powered-by */}
        <div className="lg:col-span-7 flex flex-col gap-6 text-left">
          <div className="space-y-4">
            <h1 className="text-3xl sm:text-4xl lg:text-[44px] font-bold font-sans text-ink leading-[1.12] tracking-tight">
              Every fix, tested before you trust it.
            </h1>
            <p className="font-sans text-base sm:text-lg leading-relaxed text-muted max-w-xl">
              CodeGuard scans your repo for accessibility violations, writes fixes with NVIDIA Nemotron, and confirms each one in an isolated sandbox before you merge anything.
            </p>
          </div>

          <RepoUrlInput
            onStartScan={handleStartScan}
            isLoading={isLoading}
            serverError={error}
            onClearError={() => setError(null)}
            demoRepoUrl={DEFAULT_DEMO_REPO}
          />
        </div>

        {/* Right Column (5 cols): Floating card with dark purple gradient (160deg, #8069FF -> #2A1F6B) */}
        <div className="lg:col-span-5 w-full">
          <div
            className="w-full rounded-[16px] p-6 sm:p-7 text-left flex flex-col justify-between"
            style={{
              background: 'linear-gradient(160deg, #8069FF 0%, #2A1F6B 100%)',
            }}
          >
            {/* Top row: Pill "LIVE DEMO" + arrow button */}
            <div className="flex items-center justify-between mb-6">
              <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-mono uppercase tracking-[0.08em] font-medium bg-white/15 text-white border border-white/10 select-none">
                LIVE DEMO
              </span>
              <button
                type="button"
                className="w-7 h-7 rounded-full bg-white/15 hover:bg-white/25 flex items-center justify-center text-white transition-colors cursor-pointer border border-white/10"
                aria-label="Demo external link"
              >
                <ArrowUpRight size={14} />
              </button>
            </div>

            {/* LiveFixDemo animation with light/white mono text on dark card */}
            <div className="my-2 py-2">
              <LiveFixDemo />
            </div>

            {/* Bottom caption text & mono repo label */}
            <div className="pt-6 mt-4 border-t border-white/15 flex flex-col sm:flex-row sm:items-center justify-between gap-1">
              <span className="text-xs text-white/80 font-sans">
                Real-time accessibility verification
              </span>
              <span className="text-[11px] font-mono tracking-[0.08em] text-white/60 uppercase">
                DEMO REPO / REACT
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* STATS ROW — directly below hero */}
      <StatsRow />

      {/* LOGO STRIP — below StatsRow */}
      <FrameworkStrip />

      {/* USE-CASES SECTION — Detect / Fix / Verify with shared hairlines */}
      <HowItWorksSection />
    </div>
  );
};
