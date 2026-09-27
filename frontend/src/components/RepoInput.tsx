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
    <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3 w-full">
      <input
        type="url"
        placeholder="https://github.com/org/repo"
        value={repoUrl}
        onChange={(e) => setRepoUrl(e.target.value)}
        required
        className="flex-1 px-4 py-2 rounded-lg bg-slate-900 border border-slate-700 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
      />
      <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-900 border border-slate-700">
        <GitBranch size={16} className="text-slate-400" />
        <input
          type="text"
          value={branch}
          onChange={(e) => setBranch(e.target.value)}
          placeholder="branch"
          className="w-24 bg-transparent text-slate-100 text-sm focus:outline-none"
        />
      </div>
      <button
        type="submit"
        disabled={isLoading}
        className="flex items-center justify-center gap-2 px-6 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium transition disabled:opacity-50 cursor-pointer"
      >
        <Play size={16} />
        {isLoading ? 'Scanning...' : 'Scan Repo'}
      </button>
    </form>
  );
};
