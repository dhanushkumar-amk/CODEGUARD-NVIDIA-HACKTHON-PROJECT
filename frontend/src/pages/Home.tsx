import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, Sparkles, GitBranch, ArrowRight, Play, CheckCircle } from 'lucide-react';
import { startScan } from '../api/client';
import { Button } from '../components/Button';
import { Card } from '../components/Card';

export const Home: React.FC = () => {
  const navigate = useNavigate();
  const [repoUrl, setRepoUrl] = useState<string>('https://github.com/facebook/react');
  const [branch, setBranch] = useState<string>('main');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoUrl.trim()) return;

    setIsLoading(true);
    setError(null);

    try {
      const { scan_id } = await startScan(repoUrl.trim(), branch.trim() || 'main');
      navigate(`/scan/${scan_id}`);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to initiate repository scan';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto flex flex-col gap-10 py-6">
      {/* Hero Header */}
      <section className="text-center flex flex-col items-center gap-4">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-xs font-medium text-indigo-300">
          <Sparkles size={14} className="text-indigo-400" />
          Autonomous WCAG 2.2 AA Remediation Agent
        </div>
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white">
          Protect & Repair with{' '}
          <span className="bg-gradient-to-r from-indigo-400 via-purple-300 to-cyan-400 bg-clip-text text-transparent">
            CodeGuard
          </span>
        </h1>
        <p className="text-slate-400 text-base sm:text-lg max-w-2xl">
          Automated accessibility auditing powered by{' '}
          <strong className="text-slate-200">NVIDIA Nemotron</strong> models via{' '}
          <strong className="text-slate-200">Nebius Token Factory</strong>, with guaranteed validation
          inside <strong className="text-slate-200">Nebius execution sandboxes</strong>.
        </p>
      </section>

      {/* Main Scan Trigger Card */}
      <Card
        title="Start Accessibility Audit"
        subtitle="Provide a remote Git repository URL to clone, analyze, and synthesize fixes."
        className="border-indigo-500/30 shadow-2xl shadow-indigo-500/10"
      >
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {error && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-300 text-xs">
              {error}
            </div>
          )}

          <div className="flex flex-col sm:flex-row gap-3">
            <div className="flex-1">
              <label htmlFor="repoUrl" className="block text-xs font-medium text-slate-400 mb-1.5">
                Repository HTTPS URL
              </label>
              <input
                id="repoUrl"
                type="url"
                required
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                placeholder="https://github.com/org/repo"
                className="w-full px-4 py-2.5 rounded-lg bg-slate-950 border border-slate-700/80 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-sm font-mono"
              />
            </div>

            <div className="sm:w-36">
              <label htmlFor="branch" className="block text-xs font-medium text-slate-400 mb-1.5">
                Branch
              </label>
              <div className="relative">
                <GitBranch size={15} className="absolute left-3 top-3 text-slate-500" />
                <input
                  id="branch"
                  type="text"
                  value={branch}
                  onChange={(e) => setBranch(e.target.value)}
                  placeholder="main"
                  className="w-full pl-9 pr-3 py-2.5 rounded-lg bg-slate-950 border border-slate-700/80 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-sm font-mono"
                />
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between pt-2">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <ShieldCheck size={16} className="text-emerald-400" />
              <span>Tested safely in ephemeral sandboxes</span>
            </div>
            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={isLoading}
              rightIcon={<ArrowRight size={16} />}
            >
              Start Automated Scan
            </Button>
          </div>
        </form>
      </Card>

      {/* Feature Highlights Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 flex flex-col gap-2">
          <div className="text-indigo-400 font-semibold text-sm flex items-center gap-1.5">
            <Play size={16} /> 1. Deep AST & axe-core Scan
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Scans UI files for WCAG 2.2 AA violations and uses Nemotron Nano to eliminate false alarms.
          </p>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 flex flex-col gap-2">
          <div className="text-purple-400 font-semibold text-sm flex items-center gap-1.5">
            <Sparkles size={16} /> 2. Nemotron Ultra Fixes
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Synthesizes non-breaking, idiomatic code diffs matching existing component design tokens.
          </p>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 flex flex-col gap-2">
          <div className="text-emerald-400 font-semibold text-sm flex items-center gap-1.5">
            <CheckCircle size={16} /> 3. Nebius Sandbox Proof
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Verifies every patch inside isolated environments using Playwright and existing test suites.
          </p>
        </div>
      </div>
    </div>
  );
};
