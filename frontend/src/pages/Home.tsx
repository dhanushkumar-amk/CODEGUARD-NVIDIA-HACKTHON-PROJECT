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
    <div className="w-full flex flex-col">
      {/* 1. HERO — Single centered column, max-width 640px */}
      <section className="w-full pt-12 md:pt-24 pb-12 md:pb-16 text-center">
        <div className="max-w-[640px] mx-auto flex flex-col items-center text-center">
          {/* 1. Small mono eyebrow label */}
          <span className="text-[11px] font-mono uppercase tracking-[0.08em] text-primary font-semibold block mb-4 select-none">
            ACCESSIBILITY, VERIFIED
          </span>

          {/* 2. Headline */}
          <h1 className="text-3xl sm:text-4xl lg:text-[44px] font-bold font-sans text-ink leading-[1.12] tracking-tight mb-5">
            Every fix, tested before you trust it.
          </h1>

          {/* 3. Subheadline paragraph */}
          <p className="font-sans text-base sm:text-lg leading-relaxed text-muted mb-8">
            CodeGuard scans your repo for accessibility violations, writes fixes with NVIDIA Nemotron, and confirms each one in an isolated sandbox before you merge anything.
          </p>

          {/* 4. Primary + secondary buttons (side by side, centered, gap 12px) & 5. Powered by NVIDIA line (40px spacing above) */}
          <RepoUrlInput
            onStartScan={handleStartScan}
            isLoading={isLoading}
            serverError={error}
            onClearError={() => setError(null)}
            demoRepoUrl={DEFAULT_DEMO_REPO}
          />
        </div>
      </section>

      {/* 2. LIVE DEMO PANEL — Full container width (max-w-[1120px]), below hero with 64px gap */}
      <section className="w-full pb-12 md:pb-24">
        <div
          className="w-full rounded-[16px] p-8 md:p-10 text-left flex flex-col justify-between"
          style={{
            background: 'linear-gradient(160deg, #8069FF 0%, #2A1F6B 100%)',
          }}
        >
          {/* Top row: Pill "LIVE DEMO" + arrow button */}
          <div className="flex items-center justify-between mb-8">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-[11px] font-mono uppercase tracking-[0.08em] font-medium bg-white/15 text-white border border-white/10 select-none">
              LIVE DEMO
            </span>
            <button
              type="button"
              className="w-8 h-8 rounded-full bg-white/15 hover:bg-white/25 flex items-center justify-center text-white transition-colors cursor-pointer border border-white/10"
              aria-label="Demo external link"
            >
              <ArrowUpRight size={16} />
            </button>
          </div>

          {/* LiveFixDemo animation inside */}
          <div className="py-4">
            <LiveFixDemo />
          </div>

          {/* Bottom caption text & mono repo label */}
          <div className="pt-8 mt-6 border-t border-white/15 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <span className="text-xs sm:text-sm text-white/80 font-sans">
              Real-time accessibility verification
            </span>
            <span className="text-[11px] font-mono tracking-[0.08em] text-white/60 uppercase">
              DEMO REPO / REACT
            </span>
          </div>
        </div>
      </section>

      {/* 3. STATS ROW — Section with 96px/48px rhythm, hairline top border only */}
      <StatsRow />

      {/* 4. LOGO/FRAMEWORK STRIP — Section with 96px/48px rhythm, hairline top border */}
      <FrameworkStrip />

      {/* 5. HOW IT WORKS SECTION — Section with 96px/48px rhythm, hairline top border */}
      <HowItWorksSection />
    </div>
  );
};
