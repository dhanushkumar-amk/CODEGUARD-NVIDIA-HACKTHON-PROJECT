import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldAlert, Cpu, Box } from 'lucide-react';

export const Header: React.FC = () => {
  return (
    <header className="header flex items-center justify-between py-4 border-b border-slate-800/80 mb-6">
      <Link to="/" className="brand flex items-center gap-3 no-underline group">
        <div className="brand-icon w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-600/30 group-hover:bg-indigo-500 transition">
          <ShieldAlert size={22} color="#ffffff" />
        </div>
        <div>
          <div className="brand-title font-bold text-lg text-white tracking-tight flex items-center gap-1.5">
            CodeGuard
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
              v0.1
            </span>
          </div>
          <div className="brand-tagline text-xs text-slate-400">
            AI Accessibility Agent & Remediation Engine
          </div>
        </div>
      </Link>

      <div className="header-badges flex items-center gap-2">
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono bg-slate-900 border border-indigo-500/30 text-indigo-300">
          <Cpu size={13} /> NVIDIA Nemotron
        </span>
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono bg-slate-900 border border-emerald-500/30 text-emerald-300 hidden sm:inline-flex">
          <Box size={13} /> Nebius Sandboxes
        </span>
      </div>
    </header>
  );
};
