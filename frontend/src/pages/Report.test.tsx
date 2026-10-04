import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { Report } from './Report';
import * as api from '../api/client';
import { ScanReport } from '../types';

vi.mock('../api/client', () => ({
  getReport: vi.fn(),
}));

class MockResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
(globalThis as any).ResizeObserver = MockResizeObserver;

vi.mock('recharts', async () => {
  const actual = await vi.importActual<typeof import('recharts')>('recharts');
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div style={{ width: 400, height: 200 }}>{children}</div>
    ),
  };
});

const mockFullReport: ScanReport = {
  scan_id: 'scan_report_123',
  repo_url: 'https://github.com/example/accessible-app',
  branch: 'main',
  status: 'completed',
  overall_score_before: 58.0,
  overall_score_after: 91.0,
  overall_improvement: {
    score_before: 58.0,
    score_after: 91.0,
    improvement_points: 33.0,
  },
  executive_summary:
    'CodeGuard remediated 4 critical accessibility defects, lifting the repository compliance score from 58% to 91% (+33.0 points).',
  violations: [
    {
      id: 'viol_01',
      file: 'src/components/Header.tsx',
      line: 42,
      type: 'color-contrast',
      severity: 'critical',
      description: 'Elements must meet minimum color contrast ratio threshold (3.1:1 found, 4.5:1 required).',
      category: 'LOW_CONTRAST',
      priority_rank: 1,
    },
    {
      id: 'viol_02',
      file: 'src/pages/Login.tsx',
      line: 65,
      type: 'label',
      severity: 'high',
      description: 'Form <input> elements must have associated labels.',
      category: 'UNLABELED_FORM_FIELD',
      priority_rank: 2,
    },
  ],
  fixes: [
    {
      fix_id: 'fix_01',
      violation_id: 'viol_01',
      diff: '--- Header.tsx\n+++ Header.tsx\n- text-slate-400\n+ text-slate-100',
      explanation: 'Changed text color to slate-100 to achieve 7.2:1 contrast ratio.',
      status: 'proposed',
    },
    {
      fix_id: 'fix_02',
      violation_id: 'viol_02',
      diff: '--- Login.tsx\n+++ Login.tsx\n- <input id="email" />\n+ <label htmlFor="email">Email</label><input id="email" />',
      explanation: 'Added explicit label element.',
      status: 'failed',
    },
  ],
  verification_results: [
    {
      fix_id: 'fix_01',
      axe_score_before: 58.0,
      axe_score_after: 100.0,
      verified: true,
      tests_passed: true,
      sandbox_id: 'sb-nebius-01',
      sandbox_logs: 'Passed 0 contrast defects. 12/12 unit tests passed.',
    },
  ],
  unified_records: [
    {
      violation: {
        id: 'viol_01',
        file: 'src/components/Header.tsx',
        line: 42,
        type: 'color-contrast',
        severity: 'critical',
        description: 'Elements must meet minimum color contrast ratio threshold (3.1:1 found, 4.5:1 required).',
        category: 'LOW_CONTRAST',
        priority_rank: 1,
        root_cause: 'Text color has low luminance ratio against slate-900 background.',
        affected_element: 'button.btn-primary',
        user_impact: 'Users with visual impairments cannot distinguish text.',
        fix_strategy: 'Increase text luminance to slate-100.',
        confidence: 'high',
        diagnosis_source: 'llm',
      },
      fix: {
        fix_id: 'fix_01',
        violation_id: 'viol_01',
        diff: '--- Header.tsx\n+++ Header.tsx\n- text-slate-400\n+ text-slate-100',
        explanation: 'Changed text color to slate-100 to achieve 7.2:1 contrast ratio.',
        status: 'proposed',
      },
      verification: {
        fix_id: 'fix_01',
        axe_score_before: 58.0,
        axe_score_after: 100.0,
        verified: true,
        tests_passed: true,
        sandbox_id: 'sb-nebius-01',
        sandbox_logs: 'Passed 0 contrast defects. 12/12 unit tests passed.',
      },
      final_status: 'fixed_and_verified',
    },
    {
      violation: {
        id: 'viol_02',
        file: 'src/pages/Login.tsx',
        line: 65,
        type: 'label',
        severity: 'high',
        description: 'Form <input> elements must have associated labels.',
        category: 'UNLABELED_FORM_FIELD',
        priority_rank: 2,
        root_cause: 'Input tag lacks htmlFor or aria-label.',
        affected_element: 'input#email',
        user_impact: 'Screen readers announce unlabelled textfield.',
        fix_strategy: 'Wrap input with label or add aria-label.',
        confidence: 'high',
        diagnosis_source: 'llm',
      },
      fix: {
        fix_id: 'fix_02',
        violation_id: 'viol_02',
        diff: '--- Login.tsx\n+++ Login.tsx\n- <input id="email" />\n+ <label htmlFor="email">Email</label><input id="email" />',
        explanation: 'Added explicit label element.',
        status: 'failed',
      },
      verification: null,
      final_status: 'fix_failed',
    },
  ],
  summary: {
    total_violations: 2,
    fixed_and_verified: 1,
    fix_failed: 1,
    duration_seconds: 18.4,
  },
  cost_breakdown: {
    fast_cost: 0.0042,
    ultra_cost: 0.0293,
    total_cost: 0.0335,
  },
  timestamp: new Date().toISOString(),
};

describe('Report Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('correctly renders score_before, score_after, and improvement delta values', async () => {
    vi.mocked(api.getReport).mockResolvedValueOnce(mockFullReport);

    render(
      <MemoryRouter initialEntries={['/report/scan_report_123']}>
        <Routes>
          <Route path="/report/:scanId" element={<Report />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('hero-score-section')).toBeInTheDocument();
    });

    // Score delta callout
    expect(screen.getByTestId('score-improvement-delta')).toHaveTextContent('+33 points');

    // Score displays
    expect(screen.getByTestId('score-before-display')).toBeInTheDocument();
    expect(screen.getByTestId('score-after-display')).toBeInTheDocument();

    // Story explanation
    expect(screen.getByTestId('executive-summary-story')).toHaveTextContent(
      /remediated 4 critical accessibility defects/i
    );

    // Stats strip
    expect(screen.getByTestId('stat-total-violations')).toHaveTextContent('2');
    expect(screen.getByTestId('stat-fixes-verified')).toHaveTextContent('1 / 2');
    expect(screen.getByTestId('stat-total-cost')).toHaveTextContent('$0.0335');
  });

  it('filtering violations by final_status correctly shows and hides items', async () => {
    vi.mocked(api.getReport).mockResolvedValueOnce(mockFullReport);

    render(
      <MemoryRouter initialEntries={['/report/scan_report_123']}>
        <Routes>
          <Route path="/report/:scanId" element={<Report />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('filterable-violations-list')).toBeInTheDocument();
    });

    // Initially both items should be visible
    expect(screen.getByTestId('violation-item-viol_01')).toBeInTheDocument();
    expect(screen.getByTestId('violation-item-viol_02')).toBeInTheDocument();

    // Change status filter to 'fixed_and_verified'
    const statusSelect = screen.getByTestId('filter-status-select');
    fireEvent.change(statusSelect, { target: { value: 'fixed_and_verified' } });

    // Item 1 is fixed_and_verified (should stay), Item 2 is fix_failed (should hide)
    expect(screen.getByTestId('violation-item-viol_01')).toBeInTheDocument();
    expect(screen.queryByTestId('violation-item-viol_02')).not.toBeInTheDocument();

    // Change status filter to 'fix_failed'
    fireEvent.change(statusSelect, { target: { value: 'fix_failed' } });
    expect(screen.queryByTestId('violation-item-viol_01')).not.toBeInTheDocument();
    expect(screen.getByTestId('violation-item-viol_02')).toBeInTheDocument();
  });

  it('zero-violations edge case renders the positive celebratory empty state', async () => {
    const zeroViolationReport: ScanReport = {
      ...mockFullReport,
      scan_id: 'scan_clean_app',
      overall_score_before: 100.0,
      overall_score_after: 100.0,
      overall_improvement: {
        score_before: 100.0,
        score_after: 100.0,
        improvement_points: 0.0,
      },
      violations: [],
      fixes: [],
      verification_results: [],
      unified_records: [],
      summary: {
        total_violations: 0,
        fixed_and_verified: 0,
      },
    };

    vi.mocked(api.getReport).mockResolvedValueOnce(zeroViolationReport);

    render(
      <MemoryRouter initialEntries={['/report/scan_clean_app']}>
        <Routes>
          <Route path="/report/:scanId" element={<Report />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('zero-violations-empty-state')).toBeInTheDocument();
    });

    expect(screen.getByText(/No Accessibility Violations Found!/i)).toBeInTheDocument();
    expect(
      screen.getByText(/meets all scanned WCAG 2.2 AA accessibility standards/i)
    ).toBeInTheDocument();
  });

  it('Download and View as Markdown buttons link to the correct endpoints', async () => {
    vi.mocked(api.getReport).mockResolvedValueOnce(mockFullReport);

    render(
      <MemoryRouter initialEntries={['/report/scan_report_123']}>
        <Routes>
          <Route path="/report/:scanId" element={<Report />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('download-report-btn')).toBeInTheDocument();
    });

    const downloadLink = screen.getByTestId('download-report-btn');
    expect(downloadLink).toHaveAttribute('href', '/api/report/scan_report_123/download');

    const markdownLink = screen.getByTestId('view-markdown-btn');
    expect(markdownLink).toHaveAttribute('href', '/api/report/scan_report_123/markdown');

    const scanAnotherLink = screen.getByTestId('scan-another-repo-btn');
    expect(scanAnotherLink).toHaveAttribute('href', '/');
  });
});
