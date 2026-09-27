import React from 'react';
import { ShieldAlert, Cpu, Box } from 'lucide-react';

export const Header: React.FC = () => {
  return (
    <header className="header">
      <div className="brand">
        <div className="brand-icon">
          <ShieldAlert size={24} color="#ffffff" />
        </div>
        <div>
          <div className="brand-title">CodeGuard</div>
          <div className="brand-tagline">AI Accessibility Agent & Remediation Engine</div>
        </div>
      </div>

      <div className="header-badges">
        <span className="badge active">
          <Cpu size={14} /> NVIDIA Nemotron
        </span>
        <span className="badge">
          <Box size={14} /> Nebius Sandboxes
        </span>
      </div>
    </header>
  );
};
