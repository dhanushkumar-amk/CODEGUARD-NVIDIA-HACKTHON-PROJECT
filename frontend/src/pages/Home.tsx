import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { motion } from 'framer-motion';
import {
  Sparkles,
  Search,
  Cpu,
  Wrench,
  ShieldCheck,
  Zap,
  Box,
  CheckCircle2,
} from 'lucide-react';
import { startScan } from '../api/client';
import { HowItWorksStep } from '../components/HowItWorksStep';
import { RepoUrlInput, DEFAULT_DEMO_REPO } from '../components/RepoUrlInput';

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
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
      className="max-w-5xl mx-auto flex flex-col gap-12 py-8 px-2"
    >
      {/* Hero Section */}
      <section className="text-center flex flex-col items-center gap-5">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1, duration: 0.3 }}
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/25 text-xs font-medium text-indigo-300 shadow-sm shadow-indigo-950/40"
        >
          <Sparkles size={14} className="text-indigo-400 animate-pulse" />
          <span>Autonomous WCAG 2.2 AA Remediation Agent</span>
        </motion.div>

        <div className="space-y-3 max-w-3xl">
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-[1.15]">
            Find and Fix Accessibility Issues —{' '}
            <span className="bg-gradient-to-r from-indigo-400 via-purple-300 to-cyan-400 bg-clip-text text-transparent">
              Automatically, Verified
            </span>
          </h1>
          <p className="text-slate-300/90 text-base sm:text-lg max-w-2xl mx-auto leading-relaxed font-normal">
            CodeGuard uses <span className="text-indigo-300 font-medium">NVIDIA Nemotron</span> models to audit frontend code, synthesize non-breaking fixes, and prove compliance in <span className="text-emerald-300 font-medium">isolated execution sandboxes</span>.
          </p>
        </div>
      </section>

      {/* Prominent Scan Input Section */}
      <section className="w-full">
        <RepoUrlInput
          onStartScan={handleStartScan}
          isLoading={isLoading}
          serverError={error}
          onClearError={() => setError(null)}
          demoRepoUrl={DEFAULT_DEMO_REPO}
        />
      </section>

      {/* How It Works Strip (4-Stage Pipeline) */}
      <section className="w-full bg-slate-900/40 border border-slate-800/80 rounded-2xl p-6 sm:p-8 backdrop-blur-md shadow-xl shadow-black/20">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-6 border-b border-slate-800/80 mb-6">
          <div>
            <h2 className="text-base font-semibold text-slate-100 flex items-center gap-2">
              <Zap size={16} className="text-indigo-400" />
              Autonomous Audit Pipeline
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              From raw source code to verified accessibility fixes in four reproducible stages
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono bg-slate-950 border border-slate-800 text-slate-300">
              <CheckCircle2 size={12} className="text-emerald-400" /> Zero False Positives
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 relative">
          <HowItWorksStep
            stepNumber={1}
            title="Scan"
            description="AST parser and axe-core inspect UI components to extract scannable markup chunks and locate violations."
            icon={<Search size={18} />}
            badge="AST + axe-core"
          />

          <HowItWorksStep
            stepNumber={2}
            title="Diagnose"
            description="Nemotron Nano filters benign false alarms, analyzes WCAG rules, and isolates root causes."
            icon={<Cpu size={18} />}
            badge="Nemotron Nano"
          />

          <HowItWorksStep
            stepNumber={3}
            title="Fix"
            description="Nemotron Ultra synthesizes exact, minimal unified diffs preserving design tokens and project styling."
            icon={<Wrench size={18} />}
            badge="Nemotron Ultra"
          />

          <HowItWorksStep
            stepNumber={4}
            title="Verify"
            description="Ephemeral sandboxes spin up Playwright & rerun axe-core to objectively confirm score improvements."
            icon={<ShieldCheck size={18} />}
            badge="Nebius Sandbox"
            isLast={true}
          />
        </div>
      </section>

      {/* Trust & Sponsor Footer Line */}
      <footer className="w-full pt-4 pb-2 border-t border-slate-900/80 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500 font-mono">
        <div className="flex items-center gap-2 text-slate-400">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>System Status: Ready for repository scans</span>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-slate-400 flex items-center gap-1.5">
            <Box size={14} className="text-indigo-400" /> Powered by <strong className="text-slate-200">NVIDIA Nemotron</strong> on <strong className="text-slate-200">Nebius Token Factory</strong>
          </span>
        </div>
      </footer>
    </motion.div>
  );
};
