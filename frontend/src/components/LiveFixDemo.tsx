import React, { useEffect, useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
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

        {/* Line 2: Code with inline badge */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 min-h-[28px]">
          <span>
            &lt;img src=&quot;logo.png&quot;
            {activeFixed && (
              <motion.span
                initial={shouldReduceMotion ? false : { opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.5, ease: 'easeInOut' }}
                className="bg-[#2F5DA8]/15 px-1 py-0.5 rounded-[2px] text-foreground mx-1"
              >
                alt=&quot;Company logo&quot;
              </motion.span>
            )}{' '}
            /&gt;
          </span>

          {activeFixed ? (
            <motion.span
              key="verified-badge"
              initial={shouldReduceMotion ? false : { opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5, ease: 'easeInOut' }}
              className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-sans bg-[#2F5DA8]/10 text-primary"
            >
              <Check size={12} strokeWidth={2.5} />
              <span>Verified in sandbox</span>
            </motion.span>
          ) : (
            <motion.span
              key="missing-badge"
              initial={shouldReduceMotion ? false : { opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5, ease: 'easeInOut' }}
              className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-sans bg-[#B5472A]/10 text-destructive"
            >
              Missing alt text
            </motion.span>
          )}
        </div>
      </div>
    </div>
  );
};
