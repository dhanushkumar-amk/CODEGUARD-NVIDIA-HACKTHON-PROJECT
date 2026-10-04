import React, { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, AlertTriangle, Loader2, ExternalLink, X, Info } from 'lucide-react';

export type ToastType = 'loading' | 'success' | 'error' | 'info';

export interface ToastData {
  id?: string;
  type: ToastType;
  message: string;
  detail?: string;
  actionUrl?: string;
  actionLabel?: string;
  duration?: number;
}

interface ToastProps {
  toast: ToastData | null;
  onClose: () => void;
}

export const Toast: React.FC<ToastProps> = ({ toast, onClose }) => {
  useEffect(() => {
    if (!toast || toast.type === 'loading') return;

    const timeout = toast.duration ?? (toast.type === 'error' ? 8000 : 5000);
    const timer = setTimeout(() => {
      onClose();
    }, timeout);

    return () => clearTimeout(timer);
  }, [toast, onClose]);

  return (
    <div
      className="fixed bottom-4 right-4 z-50 pointer-events-none max-w-sm w-full px-2"
      data-testid="toast-container"
    >
      <AnimatePresence mode="wait">
        {toast && (
          <motion.div
            key={toast.id || toast.message}
            initial={{ opacity: 0, y: 14, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.96 }}
            transition={{ duration: 0.18, ease: 'easeOut' }}
            className={`pointer-events-auto flex items-start gap-2.5 p-3 rounded-[6px] border text-ink shadow-lg font-sans text-xs bg-paper/95 backdrop-blur-md transition-colors ${
              toast.type === 'success'
                ? 'border-leaf/40 shadow-leaf/5'
                : toast.type === 'error'
                ? 'border-coral/40 shadow-coral/5'
                : 'border-line shadow-black/5'
            }`}
            data-testid={`toast-${toast.type}`}
            role="status"
            aria-live="polite"
          >
            {/* Minimal Icon */}
            <div className="shrink-0 mt-0.5">
              {toast.type === 'loading' && (
                <Loader2 size={14} className="animate-spin text-primary" />
              )}
              {toast.type === 'success' && (
                <CheckCircle2 size={14} className="text-leaf" />
              )}
              {toast.type === 'error' && (
                <AlertTriangle size={14} className="text-coral" />
              )}
              {toast.type === 'info' && (
                <Info size={14} className="text-primary" />
              )}
            </div>

            {/* Message and detail */}
            <div className="flex-1 min-w-0 pr-1">
              <p className="font-semibold text-ink leading-tight truncate">
                {toast.message}
              </p>
              {toast.detail && (
                <p className="text-[11px] text-muted mt-0.5 leading-snug break-words">
                  {toast.detail}
                </p>
              )}

              {/* Action Link if provided */}
              {toast.actionUrl && (
                <a
                  href={toast.actionUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  data-testid="toast-action-link"
                  className="inline-flex items-center gap-1 mt-1.5 text-[11px] font-medium text-primary hover:underline"
                >
                  <span>{toast.actionLabel || 'View on GitHub'}</span>
                  <ExternalLink size={10} />
                </a>
              )}
            </div>

            {/* Close button */}
            {toast.type !== 'loading' && (
              <button
                type="button"
                onClick={onClose}
                data-testid="toast-close-btn"
                className="shrink-0 text-muted hover:text-ink p-0.5 rounded transition-colors"
                aria-label="Dismiss notification"
              >
                <X size={12} />
              </button>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
