import React from 'react';
import { Loader2 } from 'lucide-react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'danger' | 'success';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  leftIcon,
  rightIcon,
  className = '',
  disabled,
  ...props
}) => {
  const baseStyles =
    'group inline-flex items-center justify-center font-mono uppercase tracking-[0.08em] font-medium rounded-[6px] transition-all duration-200 ease-out focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none disabled:shadow-none cursor-pointer select-none';

  const variants = {
    // Primary: solid --primary with tactile lift, subtle ambient glow, and micro-shift
    primary:
      'bg-primary text-white hover:bg-[#725AF8] hover:-translate-y-0.5 hover:shadow-[0_4px_16px_rgba(128,105,255,0.32)] active:translate-y-0 active:bg-[#6045E6] active:shadow-none',
    // Secondary: paper background with subtle lift and border darkening
    secondary:
      'bg-paper text-ink border border-line hover:bg-surface-1 hover:border-ink/30 hover:-translate-y-0.5 active:translate-y-0 active:bg-surface-2',
    outline:
      'bg-transparent text-ink border border-line hover:bg-surface-1 hover:border-ink/30 hover:-translate-y-0.5 active:translate-y-0 active:bg-surface-2',
    danger:
      'bg-coral text-white hover:bg-coral/90 hover:-translate-y-0.5 active:translate-y-0 active:bg-coral/80',
    success:
      'bg-emerald text-white hover:bg-emerald/90 hover:-translate-y-0.5 active:translate-y-0 active:bg-emerald/80',
  };

  const sizes = {
    sm: 'text-[11px] px-3 py-1.5 gap-1.5',
    md: 'text-xs px-4 py-2 gap-2',
    lg: 'text-xs px-5 py-2.5 gap-2.5',
  };

  return (
    <button
      className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <Loader2 className="animate-spin" size={size === 'sm' ? 13 : size === 'lg' ? 18 : 15} />
      ) : leftIcon ? (
        <span className="transition-transform duration-200 group-hover:-translate-x-0.5 inline-flex items-center">
          {leftIcon}
        </span>
      ) : null}
      <span>{children}</span>
      {!isLoading && rightIcon && (
        <span className="transition-transform duration-200 group-hover:translate-x-0.5 inline-flex items-center">
          {rightIcon}
        </span>
      )}
    </button>
  );
};
