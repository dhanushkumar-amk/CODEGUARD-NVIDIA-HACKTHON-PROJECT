import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { ArrowUpRight, Check } from 'lucide-react';
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

      {/* 2. THREE-STAGE PIPELINE CARDS — 3 colored cards replacing the single purple banner */}
      <section className="w-full pb-12 md:pb-24">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* CARD 1: Purple (#8069FF -> #2A1F6B) - Detect & AST Diagnosis */}
          <div
            className="w-full rounded-[16px] p-6 sm:p-7 text-left flex flex-col justify-between border border-white/10"
            style={{
              background: 'linear-gradient(160deg, #8069FF 0%, #2A1F6B 100%)',
            }}
          >
            <div>
              <div className="flex items-center justify-between mb-6">
                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-mono uppercase tracking-[0.08em] font-medium bg-white/15 text-white border border-white/10 select-none">
                  01 &bull; DETECT
                </span>
                <span className="text-[11px] font-mono tracking-[0.08em] text-white/60 uppercase">
                  AST + AXE
                </span>
              </div>

              <div className="font-mono text-[13px] leading-relaxed text-white select-none my-4">
                <div className="text-white/60 mb-2 font-mono">// Button.tsx</div>
                <div className="text-white/95">
                  &lt;button class=&quot;primary&quot;&gt;
                </div>
                <div className="mt-3">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-sans bg-coral/30 text-white border border-coral/50">
                    Contrast 3.1:1 &lt; 4.5:1
                  </span>
                </div>
              </div>
            </div>

            <div className="pt-6 mt-4 border-t border-white/15 flex items-center justify-between text-xs text-white/80 font-sans">
              <span>Deterministic AST parser</span>
              <span className="font-mono text-[11px] text-white/60 uppercase">12 WCAG ISSUES</span>
            </div>
          </div>

          {/* CARD 2: Blue (#2563EB -> #1E1B4B) - Live AI Fix Synthesis */}
          <div
            className="w-full rounded-[16px] p-6 sm:p-7 text-left flex flex-col justify-between border border-white/10"
            style={{
              background: 'linear-gradient(160deg, #2563EB 0%, #1E1B4B 100%)',
            }}
          >
            <div>
              <div className="flex items-center justify-between mb-6">
                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-mono uppercase tracking-[0.08em] font-medium bg-white/15 text-white border border-white/10 select-none">
                  02 &bull; FIX
                </span>
                <button
                  type="button"
                  className="w-7 h-7 rounded-full bg-white/15 hover:bg-white/25 flex items-center justify-center text-white transition-colors cursor-pointer border border-white/10"
                  aria-label="Demo replay"
                >
                  <ArrowUpRight size={14} />
                </button>
              </div>

              <div className="my-2">
                <LiveFixDemo />
              </div>
            </div>

            <div className="pt-6 mt-4 border-t border-white/15 flex items-center justify-between text-xs text-white/80 font-sans">
              <span>Nemotron Ultra unified diff</span>
              <span className="font-mono text-[11px] text-white/60 uppercase">NON-BREAKING</span>
            </div>
          </div>

          {/* CARD 3: Emerald (#10B981 -> #064E3B) - Deterministic Sandbox Verification */}
          <div
            className="w-full rounded-[16px] p-6 sm:p-7 text-left flex flex-col justify-between border border-white/10"
            style={{
              background: 'linear-gradient(160deg, #10B981 0%, #064E3B 100%)',
            }}
          >
            <div>
              <div className="flex items-center justify-between mb-6">
                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-mono uppercase tracking-[0.08em] font-medium bg-white/15 text-white border border-white/10 select-none">
                  03 &bull; VERIFY
                </span>
                <span className="text-[11px] font-mono tracking-[0.08em] text-white/60 uppercase">
                  NEBIUS CLOUD
                </span>
              </div>

              <div className="font-mono text-[13px] leading-relaxed text-white select-none my-4">
                <div className="text-white/60 mb-2 font-mono">// Headless Chromium Sandbox</div>
                <div className="space-y-1.5 text-xs text-white/90 font-mono">
                  <div className="flex items-center gap-1.5 text-emerald-200">
                    <Check size={13} strokeWidth={2.5} />
                    <span>0 WCAG regressions detected</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-white/80">
                    <Check size={13} strokeWidth={2.5} />
                    <span>12/12 unit tests passed</span>
                  </div>
                </div>
                <div className="mt-3">
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-sans bg-emerald/25 text-white border border-emerald/40">
                    <Check size={12} strokeWidth={2.5} />
                    <span>Score: 58% &rarr; 98%</span>
                  </span>
                </div>
              </div>
            </div>

            <div className="pt-6 mt-4 border-t border-white/15 flex items-center justify-between text-xs text-white/80 font-sans">
              <span>Isolated browser sandbox</span>
              <span className="font-mono text-[11px] text-white/60 uppercase">PROVEN FIX</span>
            </div>
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
