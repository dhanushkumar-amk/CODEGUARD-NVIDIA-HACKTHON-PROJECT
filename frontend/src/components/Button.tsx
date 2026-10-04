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
    'inline-flex items-center justify-center font-medium rounded-control transition-colors focus:outline-none focus:ring-2 focus:ring-azure/20 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer';

  const variants = {
    // Primary: solid --azure background, white text, 4px radius, flat (no shadow)
    primary:
      'bg-azure hover:bg-azure/90 text-white active:bg-azure/80',
    // Secondary: --azure text, transparent bg, 1px --azure border
    secondary:
      'text-azure bg-transparent border border-azure hover:bg-azure/5 active:bg-azure/10',
    outline:
      'bg-transparent hover:bg-surface-1 text-ink border border-line active:bg-surface-2',
    danger:
      'bg-coral hover:bg-coral/90 text-white active:bg-coral/80',
    success:
      'bg-emerald hover:bg-emerald/90 text-white active:bg-emerald/80',
  };

  const sizes = {
    sm: 'text-xs px-3 py-1.5 gap-1.5',
    md: 'text-sm px-4 py-2 gap-2',
    lg: 'text-base px-5 py-2.5 gap-2',
  };

  return (
    <button
      className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <Loader2 className="animate-spin" size={size === 'sm' ? 14 : size === 'lg' ? 20 : 16} />
      ) : (
        leftIcon
      )}
      <span>{children}</span>
      {!isLoading && rightIcon}
    </button>
  );
};
