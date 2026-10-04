import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GitBranch, ArrowRight, AlertCircle, CheckCircle2 } from 'lucide-react';
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
    <div className="w-full flex flex-col gap-4 font-sans text-left">
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        {/* Main Input Row */}
        <div className="flex flex-col sm:flex-row gap-2 p-1.5 rounded-[6px] bg-paper border border-line focus-within:border-primary transition-colors">
          <div className="relative flex-1 flex items-center">
            <input
              id="repo-url-input"
              data-testid="repo-url-input"
              type="text"
              value={repoUrl}
              onChange={handleUrlChange}
              placeholder="https://github.com/owner/repository"
              aria-label="Repository URL"
              disabled={isLoading}
              className="w-full px-3 py-2 bg-transparent text-ink placeholder:text-muted text-sm font-mono focus:outline-none disabled:opacity-60"
            />
          </div>

          {/* Branch selector */}
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-[6px] bg-surface-1 border border-line sm:w-32">
            <GitBranch size={13} className="text-muted shrink-0" />
            <input
              id="repo-branch-input"
              data-testid="repo-branch-input"
              type="text"
              value={branch}
              onChange={handleBranchChange}
              placeholder="branch"
              aria-label="Branch"
              disabled={isLoading}
              className="w-full bg-transparent text-ink text-xs font-mono placeholder:text-muted focus:outline-none disabled:opacity-60"
            />
          </div>
        </div>

        {/* Primary button + Secondary button side by side */}
        <div className="flex items-center gap-3 flex-wrap">
          <Button
            type="submit"
            variant="primary"
            size="md"
            isLoading={isLoading}
            disabled={isLoading}
            data-testid="start-scan-button"
            rightIcon={<ArrowRight size={14} />}
          >
            {isLoading ? 'Scanning...' : 'Start scan'}
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="md"
            onClick={handlePrefillDemo}
            disabled={isLoading}
            data-testid="prefill-demo-btn"
          >
            Try our demo repo
          </Button>

          {isDemoActive && (
            <span className="inline-flex items-center gap-1 text-xs text-ink/70 font-mono">
              <CheckCircle2 size={13} className="text-primary" /> Seeded demo repo loaded
            </span>
          )}
        </div>

        {/* Error message presentation */}
        <AnimatePresence>
          {activeError && (
            <motion.div
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.15 }}
              data-testid="repo-error-banner"
              className="flex items-center gap-2 px-3 py-2 rounded-[6px] bg-coral/10 border border-coral/20 text-coral text-xs font-medium"
            >
              <AlertCircle size={14} className="shrink-0 text-coral" />
              <span>{activeError}</span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Hairline divider with small "Powered by NVIDIA..." label below */}
        <div className="pt-3 border-t border-line flex items-center justify-between text-[11px] font-mono uppercase tracking-[0.08em] text-muted">
          <span>Powered by NVIDIA Nemotron on Nebius Token Factory</span>
        </div>
      </form>
    </div>
  );
};
