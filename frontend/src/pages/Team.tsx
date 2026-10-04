import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Github, ExternalLink, CheckCircle2, Award } from 'lucide-react';

export const Team: React.FC = () => {
  const teamMembers = [
    {
      name: 'Dhanush Kumar',
      role: 'Lead Architect & Systems Engineer',
      focus: 'Autonomous Agents & AST Transformers',
      bio: 'Architected the CodeGuard end-to-end orchestration pipeline, connecting git diff engines, Nebius GPU workers, and headless verification sandboxes.',
      github: 'https://github.com/dhanushkumar-amk',
      badge: 'Core Contributor',
    },
    {
      name: 'Nemotron Autonomous Agent',
      role: 'Synthetic Remediation Engine',
      focus: 'NVIDIA Nemotron-4 340B & Llama-70B',
      bio: 'Analyzes AST context, reasons over DOM hierarchy, and generates unified git diffs targeting authoritative W3C WCAG 2.2 AA rules.',
      github: 'https://build.nvidia.com',
      badge: 'Inference Core',
    },
    {
      name: 'Playwright Sandbox Engine',
      role: 'Deterministic Verification Layer',
      focus: 'Headless Chromium & Axe-Core Engine',
      bio: 'Executes remediated code in containerized micro-environments, verifying that color contrast, keyboard traps, and ARIA trees pass strict tests.',
      github: 'https://playwright.dev',
      badge: 'Sandbox Runtime',
    },
  ];

  const milestones = [
    {
      label: 'NVIDIA HACKATHON 2026',
      title: 'Autonomous Accessibility Challenge',
      desc: 'Conceived and engineered to solve the 97% web accessibility failure rate across the top 1,000,000 websites.',
    },
    {
      label: 'NEBIUS TOKEN FACTORY',
      title: 'Sub-Second GPU Inference',
      desc: 'Powered by Nebius AI Studio with dedicated high-throughput token pipelines for immediate AST analysis and repair.',
    },
    {
      label: 'DETERMINISTIC VERIFICATION',
      title: 'Zero Hallucinations Guarantee',
      desc: 'No patch is delivered without passing live headless browser validation, guaranteeing measurable accessibility score gains.',
    },
  ];

  return (
    <div className="w-full text-left font-sans py-8 md:py-16">
      {/* Top back breadcrumb */}
      <div className="mb-8">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-xs font-mono uppercase tracking-[0.08em] text-muted hover:text-ink transition-colors"
        >
          <ArrowLeft size={13} />
          <span>Back to Home</span>
        </Link>
      </div>

      {/* Hero Header */}
      <div className="max-w-3xl mb-14">
        <div className="inline-flex items-center gap-2 mb-3">
          <span className="text-[11px] font-mono uppercase tracking-[0.08em] text-primary font-semibold">
            ABOUT & CONTRIBUTORS
          </span>
          <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-surface-1 text-muted border border-line flex items-center gap-1">
            <Award size={11} className="text-primary" />
            <span>NVIDIA Hackathon Project</span>
          </span>
        </div>
        <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold text-ink tracking-tight font-sans mb-4">
          Team & Contributors
        </h1>
        <p className="text-base sm:text-lg text-muted leading-relaxed font-sans">
          CodeGuard was built with one unified mission: eliminate accessibility barriers across the open web by turning diagnostic scanning into deterministic, verified code patches.
        </p>
      </div>

      {/* Pillars Strip */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
        {milestones.map((m, idx) => (
          <div key={idx} className="p-6 rounded-[12px] border border-line bg-paper text-left flex flex-col justify-between">
            <div>
              <span className="text-[10px] font-mono uppercase tracking-[0.08em] text-primary font-semibold block mb-2">
                {m.label}
              </span>
              <h3 className="font-bold text-ink text-base mb-2 font-sans tracking-tight">
                {m.title}
              </h3>
              <p className="text-xs text-muted leading-relaxed font-sans">
                {m.desc}
              </p>
            </div>
            <div className="pt-4 mt-4 border-t border-line text-[11px] font-mono text-muted flex items-center gap-1">
              <CheckCircle2 size={12} className="text-emerald-600" />
              <span>Production Proven</span>
            </div>
          </div>
        ))}
      </div>

      {/* Team / Architecture Contributors Grid */}
      <div className="mb-16">
        <div className="max-w-2xl mb-8">
          <span className="text-[11px] font-mono uppercase tracking-[0.08em] text-primary font-semibold block mb-2">
            CORE CONTRIBUTORS
          </span>
          <h2 className="text-2xl sm:text-3xl font-bold text-ink tracking-tight font-sans">
            Engineers & Systems
          </h2>
          <p className="text-sm text-muted leading-relaxed mt-1 font-sans">
            The minds and infrastructure components powering CodeGuard's autonomous AST remediation engine.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {teamMembers.map((member, i) => (
            <div
              key={i}
              className="p-6 rounded-[12px] border border-line bg-paper text-left flex flex-col justify-between hover:border-ink/30 transition-all duration-300"
            >
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="w-10 h-10 rounded-[8px] border border-line bg-surface-1 flex items-center justify-center text-ink font-bold font-mono text-sm">
                    {member.name.charAt(0)}
                  </div>
                  <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-full border border-line bg-surface-1 text-muted">
                    {member.badge}
                  </span>
                </div>

                <h3 className="text-lg font-bold text-ink font-sans tracking-tight mb-1">
                  {member.name}
                </h3>
                <span className="text-xs font-mono text-primary font-medium block mb-3">
                  {member.role}
                </span>

                <p className="text-xs text-muted leading-relaxed font-sans mb-4">
                  {member.bio}
                </p>
              </div>

              <div className="pt-4 border-t border-line flex items-center justify-between text-xs font-mono">
                <span className="text-muted text-[11px] truncate max-w-[170px]">{member.focus}</span>
                <a
                  href={member.github}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-1.5 rounded-[6px] border border-line bg-surface-1 text-ink hover:text-primary hover:border-primary/40 transition-colors"
                >
                  <Github size={14} />
                </a>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Open Source Call to Action Banner */}
      <div className="p-8 md:p-10 rounded-[14px] border border-line bg-surface-1 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 text-left">
        <div className="max-w-xl">
          <span className="text-[11px] font-mono uppercase tracking-[0.08em] text-primary font-semibold block mb-2">
            OPEN SOURCE & COLLABORATIVE
          </span>
          <h3 className="text-xl sm:text-2xl font-bold text-ink tracking-tight font-sans mb-2">
            Join Us in Remediating the Web
          </h3>
          <p className="text-sm text-muted leading-relaxed font-sans">
            CodeGuard is completely open source under permissive licensing. Star the repository, report issues, or contribute new WCAG 2.2 AA rule heuristics.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <a
            href="https://github.com/dhanushkumar-amk/CODEGUARD---NVIDIA-HACKTHON-PROJECT"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-[8px] bg-ink text-paper text-xs font-mono uppercase tracking-[0.08em] hover:bg-ink/90 transition-all cursor-pointer font-semibold shadow-sm"
          >
            <Github size={15} />
            <span>GitHub Repository</span>
            <ExternalLink size={12} />
          </a>
        </div>
      </div>
    </div>
  );
};
