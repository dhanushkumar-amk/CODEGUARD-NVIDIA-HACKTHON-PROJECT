import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { Check } from 'lucide-react';

export const LiveFixDemo: React.FC = () => {
  const shouldReduceMotion = useReducedMotion();
  const [isFixed, setIsFixed] = useState(false);

  useEffect(() => {
    if (shouldReduceMotion) return;

    let timeoutId: ReturnType<typeof setTimeout>;

    const runLoop = (fixedState: boolean) => {
      const delay = fixedState ? 3500 : 1200;
      timeoutId = setTimeout(() => {
        setIsFixed(!fixedState);
        runLoop(!fixedState);
      }, delay);
    };

    runLoop(false);

    return () => clearTimeout(timeoutId);
  }, [shouldReduceMotion]);

  const activeFixed = shouldReduceMotion || isFixed;

  return (
    <div
      data-testid="live-fix-demo"
      className="border border-border rounded-[6px] bg-[#F4F2EC] p-5 sm:p-6 text-left flex flex-col justify-center min-h-[140px]"
    >
      <div className="font-mono text-[14px] leading-relaxed text-foreground select-none">
        {/* Line 1: Comment */}
        <div className="text-muted/80 mb-2.5">
          // Header.tsx
        </div>

        {/* Line 2: Code line with badge */}
        <div className="min-h-[28px] flex items-center">
          <AnimatePresence mode="wait">
            {activeFixed ? (
              <motion.div
                key="fixed-state"
                initial={shouldReduceMotion ? false : { opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.5, ease: 'easeInOut' }}
                className="flex flex-wrap items-center gap-x-3 gap-y-2"
              >
                <span>
                  &lt;img src=&quot;logo.png&quot;{' '}
                  <span className="bg-[#2F5DA8]/15 px-1 py-0.5 rounded-[2px] text-foreground">
                    alt=&quot;Company logo&quot;
                  </span>{' '}
                  /&gt;
                </span>

                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-sans bg-[#2F5DA8]/10 text-primary">
                  <Check size={12} strokeWidth={2.5} />
                  <span>Verified in sandbox</span>
                </span>
              </motion.div>
            ) : (
              <motion.div
                key="broken-state"
                initial={shouldReduceMotion ? false : { opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.5, ease: 'easeInOut' }}
                className="flex flex-wrap items-center gap-x-3 gap-y-2"
              >
                <span>
                  &lt;img src=&quot;logo.png&quot; /&gt;
                </span>

                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-sans bg-[#B5472A]/10 text-destructive">
                  Missing alt text
                </span>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};
