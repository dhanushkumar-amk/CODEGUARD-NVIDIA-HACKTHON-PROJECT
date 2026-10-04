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
    'inline-flex items-center justify-center font-mono uppercase tracking-[0.08em] font-medium rounded-[6px] transition-colors focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer select-none';

  const variants = {
    // Primary: solid --primary (#8069FF) background, white text, mono uppercase tracked label, 6px radius, no shadow
    primary:
      'bg-primary hover:bg-[#7057F5] active:bg-[#6045E6] text-white',
    // Secondary: white/paper background, 1px --line border, --ink text, same mono label style, 6px radius
    secondary:
      'bg-paper hover:bg-surface-1 active:bg-surface-2 text-ink border border-line',
    outline:
      'bg-transparent hover:bg-surface-1 active:bg-surface-2 text-ink border border-line',
    danger:
      'bg-coral hover:bg-coral/90 active:bg-coral/80 text-white',
    success:
      'bg-emerald hover:bg-emerald/90 active:bg-emerald/80 text-white',
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
      ) : (
        leftIcon
      )}
      <span>{children}</span>
      {!isLoading && rightIcon}
    </button>
  );
};
