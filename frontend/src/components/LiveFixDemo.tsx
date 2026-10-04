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
      className="w-full text-left flex flex-col justify-center select-none"
    >
      <div className="font-mono text-[13px] sm:text-[14px] leading-relaxed text-white">
        {/* Line 1: Comment */}
        <div className="text-white/60 mb-2.5 font-mono">
          // Header.tsx
        </div>

        {/* Line 2: Code with inline badge */}
        <div className="flex flex-wrap items-center gap-x-2.5 gap-y-2 min-h-[30px]">
          <span className="text-white/95">
            &lt;img src=&quot;logo.png&quot;
            {activeFixed && (
              <motion.span
                initial={shouldReduceMotion ? false : { opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.5, ease: 'easeInOut' }}
                className="bg-emerald/30 border border-emerald/40 px-1.5 py-0.5 rounded-[3px] text-white mx-1 font-mono font-medium"
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
              className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-sans bg-emerald/25 text-white border border-emerald/40"
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
              className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-sans bg-coral/30 text-white border border-coral/50"
            >
              Missing alt text
            </motion.span>
          )}
        </div>
      </div>
    </div>
  );
};
