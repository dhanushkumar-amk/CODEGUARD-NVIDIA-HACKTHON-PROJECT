import React from 'react';
import { Link } from 'react-router-dom';
import { Shield } from 'lucide-react';

export const Header: React.FC = () => {
  return (
    <header className="flex items-center justify-between py-4 border-b border-line mb-6 font-sans">
      <Link to="/" className="flex items-center gap-3 no-underline group">
        <div className="w-8 h-8 rounded-control bg-azure flex items-center justify-center">
          <Shield size={18} color="#ffffff" />
        </div>
        <div>
          <div className="font-semibold text-base text-ink tracking-tight flex items-center gap-2">
            CodeGuard
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-control bg-surface-1 text-muted border border-line">
              v0.1
            </span>
          </div>
          <div className="text-xs text-muted">
            AI accessibility agent
          </div>
        </div>
      </Link>

      <div className="flex items-center gap-2">
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-control text-xs font-mono border border-line text-muted bg-surface-1">
          NVIDIA Nemotron
        </span>
        <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-control text-xs font-mono border border-line text-muted bg-surface-1">
          Nebius Sandboxes
        </span>
      </div>
    </header>
  );
};
