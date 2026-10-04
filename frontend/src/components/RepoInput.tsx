import React, { useState } from 'react';
import { GitBranch, Play } from 'lucide-react';

interface RepoInputProps {
  onStartScan: (repoUrl: string, branch: string) => void;
  isLoading?: boolean;
}

export const RepoInput: React.FC<RepoInputProps> = ({ onStartScan, isLoading }) => {
  const [repoUrl, setRepoUrl] = useState('');
  const [branch, setBranch] = useState('main');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (repoUrl.trim()) {
      onStartScan(repoUrl.trim(), branch.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-2 w-full">
      <input
        type="url"
        placeholder="https://github.com/org/repo"
        value={repoUrl}
        onChange={(e) => setRepoUrl(e.target.value)}
        required
        className="flex-1 px-3 py-2 rounded-control bg-background border border-border text-foreground placeholder:text-muted focus:outline-none focus:border-primary text-sm font-mono"
      />
      <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-control bg-surface-1 border border-border">
        <GitBranch size={14} className="text-muted" />
        <input
          type="text"
          value={branch}
          onChange={(e) => setBranch(e.target.value)}
          placeholder="branch"
          className="w-20 bg-transparent text-foreground text-xs font-mono focus:outline-none"
        />
      </div>
      <button
        type="submit"
        disabled={isLoading}
        className="flex items-center justify-center gap-1.5 px-4 py-2 rounded-control bg-primary hover:bg-primary/90 text-primary-foreground font-medium text-xs transition disabled:opacity-50 cursor-pointer"
      >
        <Play size={14} />
        {isLoading ? 'Scanning...' : 'Scan repo'}
      </button>
    </form>
  );
};
