import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Privacy } from './Privacy';
import { Terms } from './Terms';
import { Team } from './Team';
import { Security } from './Security';
import { NotFound } from './NotFound';

describe('Governance Pages', () => {
  it('renders Team page with contributors and NVIDIA Hackathon context', () => {
    render(
      <MemoryRouter>
        <Team />
      </MemoryRouter>
    );

    expect(screen.getByRole('heading', { level: 1, name: /Team & Contributors/i })).toBeInTheDocument();
    expect(screen.getByText(/Dhanush Kumar/i)).toBeInTheDocument();
    expect(screen.getByText(/NVIDIA HACKATHON 2026/i)).toBeInTheDocument();
  });

  it('renders Privacy Policy page with zero code retention guarantees', () => {
    render(
      <MemoryRouter>
        <Privacy />
      </MemoryRouter>
    );

    expect(screen.getByRole('heading', { level: 1, name: /Privacy Policy/i })).toBeInTheDocument();
    expect(screen.getByText(/Zero Code Retention/i)).toBeInTheDocument();
    expect(screen.getByText(/No Model Training/i)).toBeInTheDocument();
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
  });

  it('renders Security Disclosure page with SLA and reporting instructions', () => {
    render(
      <MemoryRouter>
        <Security />
      </MemoryRouter>
    );

    expect(screen.getByRole('heading', { level: 1, name: /Security Disclosure/i })).toBeInTheDocument();
    expect(screen.getByText(/< 24 Hour Response/i)).toBeInTheDocument();
    expect(screen.getByText(/security@codeguard.dev/i)).toBeInTheDocument();
  });

  it('renders minimal 404 page with return to safety button', () => {
    render(
      <MemoryRouter initialEntries={['/unknown-nonexistent-path']}>
        <NotFound />
      </MemoryRouter>
    );

    expect(screen.getByRole('heading', { level: 1, name: /Lost in the codebase/i })).toBeInTheDocument();
    expect(screen.getByText(/404 • PAGE NOT FOUND/i)).toBeInTheDocument();
    expect(screen.getByText(/RETURN TO SAFETY/i)).toBeInTheDocument();
  });
});
