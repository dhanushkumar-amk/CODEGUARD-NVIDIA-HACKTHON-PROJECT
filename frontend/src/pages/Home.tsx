import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
  Search,
  Cpu,
  Wrench,
  ShieldCheck,
  CheckCircle2,
} from 'lucide-react';
import { startScan } from '../api/client';
import { HowItWorksStep } from '../components/HowItWorksStep';
import { RepoUrlInput, DEFAULT_DEMO_REPO } from '../components/RepoUrlInput';
import { LiveFixDemo } from '../components/LiveFixDemo';

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
    <div className="max-w-5xl flex flex-col gap-12 py-4 text-left">
      {/* Hero Section: Two-column grid, left-aligned, flat, no gradients or shadows */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-8 lg:gap-12 items-start">
        {/* Left Column */}
        <div className="flex flex-col gap-6">
          <div className="space-y-3">
            <h1 className="text-3xl sm:text-4xl lg:text-[40px] font-bold text-foreground leading-[1.15] tracking-tight">
              Every fix, tested before you trust it.
            </h1>
            <p className="text-[17px] leading-relaxed text-foreground/70">
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

          <div className="pt-4 border-t border-border text-[13px] text-muted">
            Powered by NVIDIA Nemotron on Nebius Token Factory
          </div>
        </div>

        {/* Right Column: LiveFixDemo editor panel */}
        <div className="w-full pt-1">
          <LiveFixDemo />
        </div>
      </section>

      {/* How It Works Section */}
      <section className="w-full border border-border bg-background p-6">
        <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-2 pb-4 border-b border-border mb-6">
          <div>
            <h2 className="text-sm font-semibold text-foreground">
              Remediation pipeline
            </h2>
            <p className="text-xs text-muted mt-0.5">
              From source code to verified accessibility fixes in four stages
            </p>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-muted font-mono">
            <CheckCircle2 size={13} className="text-primary" />
            <span>Deterministic verification</span>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 relative">
          <HowItWorksStep
            stepNumber={1}
            title="Scan"
            description="AST parser and axe-core inspect UI components to extract scannable markup chunks and locate violations."
            icon={<Search size={16} />}
            badge="AST + axe-core"
          />

          <HowItWorksStep
            stepNumber={2}
            title="Diagnose"
            description="Nemotron Nano filters benign false alarms, analyzes WCAG rules, and isolates root causes."
            icon={<Cpu size={16} />}
            badge="Nemotron Nano"
          />

          <HowItWorksStep
            stepNumber={3}
            title="Fix"
            description="Nemotron Ultra synthesizes exact, minimal unified diffs preserving design tokens and project styling."
            icon={<Wrench size={16} />}
            badge="Nemotron Ultra"
          />

          <HowItWorksStep
            stepNumber={4}
            title="Verify"
            description="Ephemeral sandboxes run browser heuristics to objectively confirm accessibility compliance."
            icon={<ShieldCheck size={16} />}
            badge="Nebius Sandbox"
            isLast={true}
          />
        </div>
      </section>

      {/* System Status / Engine line */}
      <footer className="w-full pt-4 border-t border-border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs text-muted font-mono">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-primary" />
          <span>System ready for repository scans</span>
        </div>

        <div>
          <span>Powered by NVIDIA Nemotron on Nebius Token Factory</span>
        </div>
      </footer>
    </div>
  );
};
