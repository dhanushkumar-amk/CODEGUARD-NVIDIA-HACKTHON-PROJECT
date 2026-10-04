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
    <div className="flex flex-col gap-6 text-left">
      <section className="flex flex-col items-start gap-3">
        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-control bg-surface-1 border border-border text-xs text-foreground">
          <Sparkles size={13} className="text-primary" />
          Autonomous accessibility remediation
        </div>
        <h1 className="text-3xl font-bold text-foreground">
          Protect and repair with CodeGuard
        </h1>
        <p className="text-sm text-muted max-w-2xl leading-relaxed">
          Continuous accessibility scanner and automated remediation agent. Powered by NVIDIA Nemotron models via Nebius Token Factory, verified inside isolated Nebius sandboxes with axe-core.
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

      <section className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="border border-border bg-background p-4 flex flex-col gap-2">
          <div className="text-primary">
            <ShieldCheck size={20} />
          </div>
          <h3 className="text-sm font-semibold text-foreground">1. Automated a11y scanning</h3>
          <p className="text-xs text-muted leading-relaxed">
            Scans UI source files (JSX, TSX, Vue, HTML) for WCAG 2.2 AA violations, contrast failures, missing ARIA attributes, and keyboard navigation issues.
          </p>
        </div>

        <div className="border border-border bg-background p-4 flex flex-col gap-2">
          <div className="text-primary">
            <Sparkles size={20} />
          </div>
          <h3 className="text-sm font-semibold text-foreground">2. Nemotron AI synthesis</h3>
          <p className="text-xs text-muted leading-relaxed">
            Leverages NVIDIA Nemotron models for contextual reasoning and minimal idiomatic code fixes.
          </p>
        </div>

        <div className="border border-border bg-background p-4 flex flex-col gap-2">
          <div className="text-primary">
            <TerminalSquare size={20} />
          </div>
          <h3 className="text-sm font-semibold text-foreground">3. Nebius sandbox verification</h3>
          <p className="text-xs text-muted leading-relaxed">
            Executes axe-core checks within isolated Nebius sandboxes to guarantee zero regressions before submitting PRs.
          </p>
        </div>
      </section>
    </div>
  );
};
