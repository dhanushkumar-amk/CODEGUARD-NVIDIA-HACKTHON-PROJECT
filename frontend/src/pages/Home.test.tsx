import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Home } from './Home';
import * as api from '../api/client';
import { DEFAULT_DEMO_REPO } from '../components/RepoUrlInput';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('../api/client', () => ({
  startScan: vi.fn(),
}));

describe('Home Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders hero title, description, and use-cases pipeline stages', () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    expect(screen.getByText(/Every fix, tested before you trust it/i)).toBeInTheDocument();
    expect(screen.getByText(/CodeGuard scans your repo for accessibility violations/i)).toBeInTheDocument();
    expect(screen.getByTestId('live-fix-demo')).toBeInTheDocument();
    expect(screen.getByText('Detect')).toBeInTheDocument();
    expect(screen.getByText('Fix')).toBeInTheDocument();
    expect(screen.getByText('Verify')).toBeInTheDocument();
  });

  it('invalid URL shows an inline error and does not call startScan()', async () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    const input = screen.getByTestId('repo-url-input');
    const submitBtn = screen.getByTestId('start-scan-button');

    // Case 1: Empty input
    fireEvent.change(input, { target: { value: '' } });
    fireEvent.click(submitBtn);

    expect(screen.getByTestId('repo-error-banner')).toHaveTextContent(/Repository URL cannot be empty/i);
    expect(api.startScan).not.toHaveBeenCalled();

    // Case 2: Malformed URL
    fireEvent.change(input, { target: { value: 'not-a-valid-url' } });
    fireEvent.click(submitBtn);

    expect(screen.getByTestId('repo-error-banner')).toHaveTextContent(/URL must start with https:\/\/ or http:\/\//i);
    expect(api.startScan).not.toHaveBeenCalled();

    // Case 3: Unsupported domain
    fireEvent.change(input, { target: { value: 'https://mysite.com/some/repo' } });
    fireEvent.click(submitBtn);

    expect(screen.getByTestId('repo-error-banner')).toHaveTextContent(/Supported Git hosts are GitHub, GitLab, and Bitbucket/i);
    expect(api.startScan).not.toHaveBeenCalled();
  });

  it('valid URL calls startScan() and navigates to progress page on success', async () => {
    vi.mocked(api.startScan).mockResolvedValueOnce({ scan_id: 'scan_demo_456' });

    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    const input = screen.getByTestId('repo-url-input');
    const branchInput = screen.getByTestId('repo-branch-input');
    const submitBtn = screen.getByTestId('start-scan-button');

    fireEvent.change(input, { target: { value: 'https://github.com/facebook/react' } });
    fireEvent.change(branchInput, { target: { value: 'main' } });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.startScan).toHaveBeenCalledWith('https://github.com/facebook/react', 'main');
      expect(mockNavigate).toHaveBeenCalledWith('/scan/scan_demo_456');
    });
  });

  it('loading state disables the button and inputs during the API call', async () => {
    let resolveScan!: (val: { scan_id: string }) => void;
    const scanPromise = new Promise<{ scan_id: string }>((resolve) => {
      resolveScan = resolve;
    });
    vi.mocked(api.startScan).mockReturnValueOnce(scanPromise);

    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    const input = screen.getByTestId('repo-url-input');
    const submitBtn = screen.getByTestId('start-scan-button');

    fireEvent.change(input, { target: { value: 'https://github.com/facebook/react' } });
    fireEvent.click(submitBtn);

    // Verify loading state
    expect(submitBtn).toBeDisabled();
    expect(input).toBeDisabled();
    expect(submitBtn).toHaveTextContent(/Scanning.../i);

    // Resolve the promise
    resolveScan({ scan_id: 'scan_789' });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/scan/scan_789');
    });
  });

  it('backend error response displays the error message cleanly to the user', async () => {
    vi.mocked(api.startScan).mockRejectedValueOnce({
      isAxiosError: true,
      response: {
        data: {
          detail: 'Repository "https://github.com/private/repo" not found or is private (HTTP 404).',
        },
      },
    });

    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    const input = screen.getByTestId('repo-url-input');
    const submitBtn = screen.getByTestId('start-scan-button');

    fireEvent.change(input, { target: { value: 'https://github.com/private/repo' } });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByTestId('repo-error-banner')).toHaveTextContent(
        'Repository "https://github.com/private/repo" not found or is private (HTTP 404).'
      );
    });

    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('quick-start "Try our demo repo" button pre-fills the input correctly', () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    );

    const input = screen.getByTestId('repo-url-input') as HTMLInputElement;
    const demoBtn = screen.getByTestId('prefill-demo-btn');

    expect(input.value).toBe('');

    fireEvent.click(demoBtn);

    expect(input.value).toBe(DEFAULT_DEMO_REPO);
    expect(screen.getByText(/Seeded demo repo loaded/i)).toBeInTheDocument();
  });
});
