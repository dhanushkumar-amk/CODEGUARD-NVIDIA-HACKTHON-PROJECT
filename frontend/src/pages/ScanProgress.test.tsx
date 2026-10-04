import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ScanProgress } from './ScanProgress';
import * as scanHook from '../hooks/useScanProgress';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('ScanProgress Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('highlights the correct stage and displays friendly label based on incoming messages', () => {
    vi.spyOn(scanHook, 'useScanProgress').mockReturnValue({
      stage: 'scanning',
      progress: 45,
      message: 'Scanned 3/6 chunks — 4 violations found so far',
      data: { violations_found: 4 },
      violationsCount: 4,
      currentCost: 0.0018,
      isConnected: true,
      isReconnecting: false,
      isCompleted: false,
      error: null,
      history: [],
      retryConnection: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={['/scan/scan_abc123']}>
        <Routes>
          <Route path="/scan/:scanId" element={<ScanProgress />} />
        </Routes>
      </MemoryRouter>
    );

    // Timeline step for 'scan' should be highlighted
    const scanStep = screen.getByTestId('timeline-step-scan');
    expect(scanStep).toBeInTheDocument();
    expect(screen.getByTestId('active-stage-label')).toHaveTextContent('Scanning Accessibility Rules');
    expect(screen.getByTestId('live-stage-message')).toHaveTextContent('Scanned 3/6 chunks — 4 violations found so far');

    // Violations counter should display 4
    expect(screen.getByTestId('violations-counter')).toHaveTextContent('4');
  });

  it('progress bar reflects the progress value from messages', () => {
    vi.spyOn(scanHook, 'useScanProgress').mockReturnValue({
      stage: 'fixing',
      progress: 75,
      message: 'Synthesizing WCAG 2.2 AA fixes using Nemotron Ultra',
      data: null,
      violationsCount: 4,
      currentCost: 0.021,
      isConnected: true,
      isReconnecting: false,
      isCompleted: false,
      error: null,
      history: [],
      retryConnection: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={['/scan/scan_progress_test']}>
        <Routes>
          <Route path="/scan/:scanId" element={<ScanProgress />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByTestId('progress-percentage')).toHaveTextContent('75%');
    expect(screen.getByTestId('progress-bar-fill')).toBeInTheDocument();
  });

  it('"complete" stage triggers smooth auto-navigation to the report page', () => {
    vi.spyOn(scanHook, 'useScanProgress').mockReturnValue({
      stage: 'complete',
      progress: 100,
      message: 'All violations remediated and verified in Nebius Sandboxes.',
      data: { fixed_and_verified: 4 },
      violationsCount: 4,
      currentCost: 0.033,
      isConnected: true,
      isReconnecting: false,
      isCompleted: true,
      error: null,
      history: [],
      retryConnection: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={['/scan/scan_auto_nav']}>
        <Routes>
          <Route path="/scan/:scanId" element={<ScanProgress />} />
        </Routes>
      </MemoryRouter>
    );

    // Initial state before timer fires
    expect(mockNavigate).not.toHaveBeenCalled();

    // Fast-forward past the 1.8s pause
    act(() => {
      vi.advanceTimersByTime(2000);
    });

    expect(mockNavigate).toHaveBeenCalledWith('/report/scan_auto_nav');
  });

  it('connection error displays the error state with a retry option', () => {
    const mockRetry = vi.fn();
    vi.spyOn(scanHook, 'useScanProgress').mockReturnValue({
      stage: 'preparing',
      progress: 20,
      message: 'Pipeline disconnected.',
      data: null,
      violationsCount: 0,
      currentCost: 0,
      isConnected: false,
      isReconnecting: false,
      isCompleted: false,
      error: 'Live connection to audit pipeline lost. The scan may have failed or disconnected.',
      history: [],
      retryConnection: mockRetry,
    });

    render(
      <MemoryRouter initialEntries={['/scan/scan_err_test']}>
        <Routes>
          <Route path="/scan/:scanId" element={<ScanProgress />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByTestId('scan-error-alert')).toBeInTheDocument();
    expect(screen.getByText(/Live connection to audit pipeline lost/i)).toBeInTheDocument();

    const retryBtn = screen.getByRole('button', { name: /Retry Stream/i });
    expect(retryBtn).toBeInTheDocument();

    fireEvent.click(retryBtn);
    expect(mockRetry).toHaveBeenCalledTimes(1);

    expect(screen.getByRole('button', { name: /Back to Home/i })).toBeInTheDocument();
  });
});
