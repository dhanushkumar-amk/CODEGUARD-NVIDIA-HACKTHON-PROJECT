import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { LiveFixDemo } from './LiveFixDemo';

describe('LiveFixDemo Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders initial broken state with comment and missing alt text badge', () => {
    render(<LiveFixDemo />);

    expect(screen.getByText('// Header.tsx')).toBeInTheDocument();
    expect(screen.getByText('Missing alt text')).toBeInTheDocument();
    expect(screen.getByText(/<img src="logo.png" \/>/)).toBeInTheDocument();
  });

  it('transitions to fixed state after delay and crossfade with verified badge and diff highlight', () => {
    render(<LiveFixDemo />);

    // Before timer fires
    expect(screen.getByText('Missing alt text')).toBeInTheDocument();

    // Fast-forward past 1200ms pause + 500ms crossfade
    act(() => {
      vi.advanceTimersByTime(2000);
    });

    expect(screen.getByText('Verified in sandbox')).toBeInTheDocument();
    expect(screen.getByText(/alt="Company logo"/)).toBeInTheDocument();
  });

  it('cycles back to broken state after several seconds', () => {
    render(<LiveFixDemo />);

    // 1200ms pause + 500ms transition -> fixed
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    expect(screen.getByText('Verified in sandbox')).toBeInTheDocument();

    // 3500ms in fixed state -> broken again
    act(() => {
      vi.advanceTimersByTime(3600);
    });
    expect(screen.getByText('Missing alt text')).toBeInTheDocument();
  });
});
