import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Privacy } from './Privacy';
import { Terms } from './Terms';

describe('Legal Pages', () => {
  it('renders Privacy Policy page with zero code retention guarantees', () => {
    render(
      <MemoryRouter>
        <Privacy />
      </MemoryRouter>
    );

    expect(screen.getByRole('heading', { level: 1, name: /Privacy Policy/i })).toBeInTheDocument();
    expect(screen.getByText(/Zero Code Retention/i)).toBeInTheDocument();
    expect(screen.getByText(/No Model Training/i)).toBeInTheDocument();
    expect(screen.getByText(/Isolated Sandboxing/i)).toBeInTheDocument();
    expect(screen.getByText(/Back to Home/i)).toBeInTheDocument();
  });

  it('renders Terms of Service page with usage terms', () => {
    render(
      <MemoryRouter>
        <Terms />
      </MemoryRouter>
    );

    expect(screen.getByRole('heading', { level: 1, name: /Terms of Service/i })).toBeInTheDocument();
    expect(screen.getByText(/Open Source Core/i)).toBeInTheDocument();
    expect(screen.getByText(/Human-in-the-Loop/i)).toBeInTheDocument();
    expect(screen.getByText(/Fair Usage/i)).toBeInTheDocument();
  });
});
