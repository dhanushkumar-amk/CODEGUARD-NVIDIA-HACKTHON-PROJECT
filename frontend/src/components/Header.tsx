import React from 'react';
import { Link } from 'react-router-dom';
import { Shield } from 'lucide-react';
import { Button } from './Button';

export const Header: React.FC = () => {
  return (
    <header className="w-full flex items-center justify-between py-4 border-b border-line mb-8 font-sans">
      {/* Left: Small logo / wordmark */}
      <Link to="/" className="flex items-center gap-2.5 no-underline group">
        <div className="w-7 h-7 rounded-[6px] bg-primary flex items-center justify-center text-white shrink-0">
          <Shield size={16} />
        </div>
        <div className="flex items-baseline gap-2">
          <span className="font-bold text-base text-ink tracking-tight font-sans">
            CodeGuard
          </span>
          <span className="hidden sm:inline-block text-[10px] font-mono uppercase tracking-[0.08em] px-1.5 py-0.5 rounded-[4px] bg-surface-1 text-muted border border-line">
            v0.1
          </span>
        </div>
      </Link>

      {/* Middle: Tracked mono-label style nav items */}
      <nav className="hidden md:flex items-center gap-6">
        <Link
          to="/"
          className="text-[11px] font-mono uppercase tracking-[0.08em] text-muted hover:text-ink transition-colors"
        >
          DEMO
        </Link>
        <a
          href="https://github.com/dhanushkumar-amk/CODEGUARD---NVIDIA-HACKTHON-PROJECT"
          target="_blank"
          rel="noopener noreferrer"
          className="text-[11px] font-mono uppercase tracking-[0.08em] text-muted hover:text-ink transition-colors"
        >
          DOCS
        </a>
        <a
          href="https://github.com/dhanushkumar-amk/CODEGUARD---NVIDIA-HACKTHON-PROJECT"
          target="_blank"
          rel="noopener noreferrer"
          className="text-[11px] font-mono uppercase tracking-[0.08em] text-muted hover:text-ink transition-colors"
        >
          GITHUB
        </a>
      </nav>

      {/* Right: Primary button */}
      <div className="flex items-center gap-3">
        <Link to="/">
          <Button variant="primary" size="sm">
            START SCAN
          </Button>
        </Link>
      </div>
    </header>
  );
};
