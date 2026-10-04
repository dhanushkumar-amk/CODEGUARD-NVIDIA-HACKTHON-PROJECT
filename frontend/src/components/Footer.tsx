import React from 'react';
import { Link } from 'react-router-dom';
import { Shield, Github, ExternalLink, ArrowUpRight } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="w-full border-t border-line mt-20 pt-16 pb-12 text-left font-sans">
      {/* Top row: Operational status & quick summary */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-12 border-b border-line">
        <div className="flex items-center gap-3">
          <Link to="/" className="flex items-center gap-2.5 no-underline group">
            <div className="w-7 h-7 rounded-[6px] bg-primary flex items-center justify-center text-white shrink-0 group-hover:scale-105 transition-transform duration-200">
              <Shield size={16} />
            </div>
            <span className="font-bold text-lg text-ink tracking-tight font-sans">
              CodeGuard
            </span>
          </Link>
          <span className="text-[10px] font-mono uppercase tracking-[0.08em] px-2 py-0.5 rounded-[4px] bg-surface-1 text-muted border border-line">
            v0.1.0-preview
          </span>
        </div>

        {/* Live operational badge */}
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-line bg-surface-1 text-[11px] font-mono">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-ink font-medium uppercase tracking-[0.08em]">All Systems Operational</span>
          <span className="text-muted hidden sm:inline">&bull;</span>
          <span className="text-muted hidden sm:inline">Nebius AI Studio: Healthy</span>
        </div>
      </div>

      {/* Main 4-column link grid */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-8 py-12 border-b border-line text-xs font-sans">
        {/* Col 1: Mission / Info */}
        <div className="col-span-2">
          <span className="text-[11px] font-mono uppercase tracking-[0.08em] text-primary font-semibold block mb-3">
            AUTONOMOUS ACCESSIBILITY
          </span>
          <p className="text-xs text-muted leading-relaxed max-w-sm mb-4">
            CodeGuard transforms digital accessibility from tedious manual audits into deterministic, verified code patches powered by NVIDIA Nemotron-4 on Nebius Token Factory.
          </p>
          <div className="flex items-center gap-3 text-muted text-xs font-mono">
            <a
              href="https://github.com/dhanushkumar-amk/CODEGUARD---NVIDIA-HACKTHON-PROJECT"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[6px] border border-line bg-paper hover:bg-surface-1 hover:text-ink transition-colors text-ink"
            >
              <Github size={13} />
              <span>Star on GitHub</span>
              <ExternalLink size={10} className="text-muted" />
            </a>
          </div>
        </div>

        {/* Col 2: Product */}
        <div>
          <span className="text-[11px] font-mono uppercase tracking-[0.08em] text-ink font-semibold block mb-3">
            PRODUCT
          </span>
          <ul className="space-y-2 text-muted font-sans">
            <li>
              <Link to="/" className="hover:text-ink transition-colors">
                Repository Scanner
              </Link>
            </li>
            <li>
              <Link to="/" className="hover:text-ink transition-colors">
                Autonomous Remediation
              </Link>
            </li>
            <li>
              <Link to="/" className="hover:text-ink transition-colors">
                Deterministic Sandbox
              </Link>
            </li>
            <li>
              <Link to="/" className="hover:text-ink transition-colors">
                Live Fix Engine
              </Link>
            </li>
          </ul>
        </div>

        {/* Col 3: Standards */}
        <div>
          <span className="text-[11px] font-mono uppercase tracking-[0.08em] text-ink font-semibold block mb-3">
            STANDARDS
          </span>
          <ul className="space-y-2 text-muted font-sans">
            <li>
              <a
                href="https://www.w3.org/TR/WCAG22/"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-ink transition-colors inline-flex items-center gap-1"
              >
                <span>WCAG 2.2 AA</span>
                <ArrowUpRight size={10} />
              </a>
            </li>
            <li>
              <a
                href="https://www.section508.gov/"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-ink transition-colors inline-flex items-center gap-1"
              >
                <span>Section 508</span>
                <ArrowUpRight size={10} />
              </a>
            </li>
            <li>
              <a
                href="https://www.ada.gov/"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-ink transition-colors inline-flex items-center gap-1"
              >
                <span>ADA Title III</span>
                <ArrowUpRight size={10} />
              </a>
            </li>
            <li>
              <a
                href="https://www.w3.org/WAI/ARIA/apg/"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-ink transition-colors inline-flex items-center gap-1"
              >
                <span>W3C WAI-ARIA</span>
                <ArrowUpRight size={10} />
              </a>
            </li>
          </ul>
        </div>

        {/* Col 4: Community & Legal */}
        <div>
          <span className="text-[11px] font-mono uppercase tracking-[0.08em] text-ink font-semibold block mb-3">
            GOVERNANCE
          </span>
          <ul className="space-y-2 text-muted font-sans">
            <li>
              <Link to="/team" className="hover:text-ink transition-colors">
                Team & Contributors
              </Link>
            </li>
            <li>
              <Link to="/privacy" className="hover:text-ink transition-colors">
                Privacy Policy
              </Link>
            </li>
            <li>
              <Link to="/terms" className="hover:text-ink transition-colors">
                Terms of Service
              </Link>
            </li>
            <li>
              <Link to="/security" className="hover:text-ink transition-colors">
                Security Disclosure
              </Link>
            </li>
          </ul>
        </div>
      </div>

      {/* Bottom bar */}
      <div className="pt-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 text-[11px] font-mono text-muted">
        <div>
          <span>&copy; {new Date().getFullYear()} CodeGuard &bull; Apache 2.0 / MIT Open Source</span>
        </div>

        {/* Real-world telemetry pill */}
        <div className="flex items-center gap-3 text-[10px] uppercase tracking-wider text-muted">
          <span>Inference: Nemotron-70B</span>
          <span>&bull;</span>
          <span>Provider: Nebius Token Factory</span>
          <span>&bull;</span>
          <span>Sandbox: Chromium Headless</span>
        </div>
      </div>
    </footer>
  );
};
