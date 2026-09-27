import React, { useEffect, useState, useCallback } from 'react';
import { ConnectivityStatus } from '../components/ConnectivityStatus';
import { checkBackendHealth, HealthResponse } from '../api/client';
import { ShieldCheck, Sparkles, TerminalSquare } from 'lucide-react';

export const HomePage: React.FC = () => {
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('loading');
  const [data, setData] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = useCallback(async () => {
    setStatus('loading');
    setError(null);
    try {
      const response = await checkBackendHealth();
      setData(response);
      setStatus('success');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      setStatus('error');
    }
  }, []);

  useEffect(() => {
    fetchHealth();
  }, [fetchHealth]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2.5rem' }}>
      <section className="hero">
        <div className="hero-pill">
          <Sparkles size={14} color="#818cf8" />
          Autonomous Accessibility Remediation
        </div>
        <h1>
          Protect & Repair with <span className="gradient-text">CodeGuard</span>
        </h1>
        <p>
          Continuous accessibility scanner and automated remediation agent. Powered by{' '}
          <strong style={{ color: '#f8fafc' }}>NVIDIA Nemotron</strong> models via{' '}
          <strong style={{ color: '#f8fafc' }}>Nebius Token Factory</strong>, verified inside{' '}
          <strong style={{ color: '#f8fafc' }}>isolated Nebius sandboxes</strong> with axe-core.
        </p>
      </section>

      <section>
        <ConnectivityStatus
          status={status}
          data={data}
          error={error}
          onRefresh={fetchHealth}
        />
      </section>

      <section className="features-grid">
        <div className="feature-card">
          <div className="card-icon violet">
            <ShieldCheck size={24} />
          </div>
          <h3>1. Automated a11y Scanning</h3>
          <p>
            Scans UI source files (JSX, TSX, Vue, HTML) for WCAG 2.2 AA violations, contrast failures, missing ARIA attributes, and keyboard navigation issues.
          </p>
        </div>

        <div className="feature-card">
          <div className="card-icon cyan">
            <Sparkles size={24} />
          </div>
          <h3>2. Nemotron AI Synthesis</h3>
          <p>
            Leverages NVIDIA Nemotron-4-340B (Ultra) for contextual reasoning and minimal idiomatic code fixes, and Nemotron-Mini (Nano) for rapid triage.
          </p>
        </div>

        <div className="feature-card">
          <div className="card-icon emerald">
            <TerminalSquare size={24} />
          </div>
          <h3>3. Nebius Sandbox Verification</h3>
          <p>
            Executes axe-core checks and project unit test suites within isolated Nebius sandboxes to guarantee zero regressions before submitting PRs.
          </p>
        </div>
      </section>
    </div>
  );
};
