import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GitBranch, ArrowRight, AlertCircle, Sparkles, CheckCircle2 } from 'lucide-react';
import { Button } from './Button';

export interface RepoUrlInputProps {
  onStartScan: (repoUrl: string, branch: string) => Promise<void> | void;
  isLoading?: boolean;
  serverError?: string | null;
  onClearError?: () => void;
  demoRepoUrl?: string;
  defaultBranch?: string;
}

export const DEFAULT_DEMO_REPO = 'https://github.com/dhanushkumar-amk/CODEGUARD---NVIDIA-HACKTHON-PROJECT';

export function validateGitUrl(url: string): string | null {
  const trimmed = url.trim();
  if (!trimmed) {
    return 'Repository URL cannot be empty.';
  }
  if (!trimmed.startsWith('https://') && !trimmed.startsWith('http://')) {
    return 'URL must start with https:// or http://.';
  }
  try {
    const parsed = new URL(trimmed);
    const host = parsed.hostname.toLowerCase();
    const allowedHosts = ['github.com', 'gitlab.com', 'bitbucket.org', 'www.github.com', 'www.gitlab.com'];
    if (!allowedHosts.includes(host)) {
      return 'Supported Git hosts are GitHub, GitLab, and Bitbucket.';
    }
    const parts = parsed.pathname.split('/').filter(Boolean);
    if (parts.length < 2) {
      return 'URL must include both owner and repo (e.g. https://github.com/org/repo).';
    }
    return null;
  } catch {
    return 'Please enter a valid repository URL (e.g. https://github.com/org/repo).';
  }
}

export const RepoUrlInput: React.FC<RepoUrlInputProps> = ({
  onStartScan,
  isLoading = false,
  serverError = null,
  onClearError,
  demoRepoUrl = DEFAULT_DEMO_REPO,
  defaultBranch = 'main',
}) => {
  const [repoUrl, setRepoUrl] = useState<string>('');
  const [branch, setBranch] = useState<string>(defaultBranch);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isDemoActive, setIsDemoActive] = useState<boolean>(false);

  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setRepoUrl(e.target.value);
    if (validationError) setValidationError(null);
    if (serverError && onClearError) onClearError();
    if (isDemoActive) setIsDemoActive(false);
  };

  const handleBranchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setBranch(e.target.value);
  };

  const handlePrefillDemo = () => {
    setRepoUrl(demoRepoUrl);
    setBranch('main');
    setValidationError(null);
    if (onClearError) onClearError();
    setIsDemoActive(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const error = validateGitUrl(repoUrl);
    if (error) {
      setValidationError(error);
      return;
    }

    setValidationError(null);
    onStartScan(repoUrl.trim(), branch.trim() || 'main');
  };

  const activeError = validationError || serverError;

  return (
    <div className="w-full max-w-3xl mx-auto flex flex-col gap-3">
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        {/* Main Input Bar */}
        <div className="flex flex-col sm:flex-row gap-2.5 p-2 rounded-2xl bg-slate-900/90 border border-slate-800 focus-within:border-indigo-500/70 focus-within:ring-2 focus-within:ring-indigo-500/20 shadow-2xl shadow-indigo-950/30 backdrop-blur-sm transition-all">
          <div className="relative flex-1 flex items-center">
            <input
              id="repo-url-input"
              data-testid="repo-url-input"
              type="text"
              value={repoUrl}
              onChange={handleUrlChange}
              placeholder="https://github.com/your-username/your-repo"
              aria-label="Repository URL"
              disabled={isLoading}
              className="w-full px-4 py-3 bg-transparent text-slate-100 placeholder-slate-500 text-sm font-mono focus:outline-none disabled:opacity-60"
            />
          </div>

          {/* Branch selector */}
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-950/70 border border-slate-800/80 sm:w-36">
            <GitBranch size={14} className="text-slate-500 shrink-0" />
            <input
              id="repo-branch-input"
              data-testid="repo-branch-input"
              type="text"
              value={branch}
              onChange={handleBranchChange}
              placeholder="branch"
              aria-label="Branch"
              disabled={isLoading}
              className="w-full bg-transparent text-slate-200 text-xs font-mono focus:outline-none disabled:opacity-60"
            />
          </div>

          {/* Submit Button */}
          <Button
            type="submit"
            variant="primary"
            size="lg"
            isLoading={isLoading}
            disabled={isLoading}
            data-testid="start-scan-button"
            className="sm:w-auto px-6 font-semibold shadow-lg shadow-indigo-600/25"
            rightIcon={<ArrowRight size={16} />}
          >
            {isLoading ? 'Scanning...' : 'Start Scan'}
          </Button>
        </div>

        {/* Error message presentation with subtle spring */}
        <AnimatePresence>
          {activeError && (
            <motion.div
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.15 }}
              data-testid="repo-error-banner"
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-medium"
            >
              <AlertCircle size={15} className="shrink-0 text-rose-400" />
              <span>{activeError}</span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Demo Quick Start & Hints */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-2 px-1 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handlePrefillDemo}
              disabled={isLoading}
              data-testid="prefill-demo-btn"
              className="inline-flex items-center gap-1.5 text-indigo-400 hover:text-indigo-300 transition-colors font-medium cursor-pointer underline-offset-4 hover:underline disabled:opacity-50"
            >
              <Sparkles size={13} className="text-indigo-400" />
              <span>Try our demo repo</span>
            </button>
            <span className="text-slate-600">&bull;</span>
            <span className="text-slate-500">Pre-seeded with 12 WCAG issues</span>
          </div>

          {isDemoActive && (
            <motion.span
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="inline-flex items-center gap-1 text-[11px] text-emerald-400 font-mono"
            >
              <CheckCircle2 size={12} /> Seeded demo repo loaded
            </motion.span>
          )}
        </div>
      </form>
    </div>
  );
};
