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
      className="w-full bg-black/35 backdrop-blur-md rounded-[10px] p-3.5 border border-white/10 flex flex-col justify-between text-left select-none"
    >
      {/* Mini editor top bar */}
      <div className="flex items-center justify-between pb-2 mb-2.5 border-b border-white/10 text-white/50 text-[11px] font-mono">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-red-400/70 inline-block" />
          <span className="w-2 h-2 rounded-full bg-yellow-400/70 inline-block" />
          <span className="w-2 h-2 rounded-full bg-emerald-400/70 inline-block" />
          <span className="ml-1 text-white/70 font-mono">// Header.tsx</span>
        </div>
        <span className="text-[10px] font-mono uppercase tracking-wider text-white/40">TSX</span>
      </div>

      {/* Code line: Clean monospace without awkward wrapping */}
      <div className="py-1 font-mono text-[11px] sm:text-[12px] leading-relaxed text-white whitespace-nowrap overflow-hidden text-ellipsis">
        <span className="text-white/95">
          &lt;img src=&quot;logo.png&quot;
          {activeFixed && (
            <motion.span
              key="alt-prop"
              initial={shouldReduceMotion ? false : { opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.35, ease: 'easeOut' }}
              className="bg-emerald-500/30 border border-emerald-400/40 px-1.5 py-0.5 rounded-[3px] text-emerald-100 mx-1 font-mono font-medium inline-block shadow-sm"
            >
              alt=&quot;Company logo&quot;
            </motion.span>
          )}{' '}
          /&gt;
        </span>
      </div>

      {/* Dedicated status badge row */}
      <div className="mt-2.5 pt-2 border-t border-white/5 flex items-center min-h-[26px]">
        {activeFixed ? (
          <motion.span
            key="verified-badge"
            initial={shouldReduceMotion ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
            className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-sans bg-emerald/30 text-white border border-emerald/50"
          >
            <Check size={11} strokeWidth={2.5} />
            <span>Verified in sandbox</span>
          </motion.span>
        ) : (
          <motion.span
            key="missing-badge"
            initial={shouldReduceMotion ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
            className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-sans bg-coral/30 text-white border border-coral/50"
          >
            Missing alt text
          </motion.span>
        )}
      </div>
    </div>
  );
};
