import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Button } from '../components/Button';

export const NotFound: React.FC = () => {
  return (
    <div className="w-full min-h-[60vh] flex flex-col items-center justify-center text-center font-sans py-24 select-none">
      {/* Subtle tracked mono eyebrow */}
      <span className="text-[11px] font-mono uppercase tracking-[0.12em] text-muted mb-4 block">
        404 &bull; PAGE NOT FOUND
      </span>

      {/* Clean, bold headline */}
      <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold text-ink tracking-tight font-sans mb-3">
        Lost in the codebase
      </h1>

      {/* Quiet, minimal description */}
      <p className="text-sm sm:text-base text-muted font-sans max-w-md leading-relaxed mb-8">
        The page you are looking for does not exist, has been removed, or is temporarily unavailable.
      </p>

      {/* Single clean return button */}
      <Link to="/">
        <Button variant="primary" size="md">
          <span className="flex items-center gap-2">
            <ArrowLeft size={14} />
            <span>RETURN TO SAFETY</span>
          </span>
        </Button>
      </Link>
    </div>
  );
};
