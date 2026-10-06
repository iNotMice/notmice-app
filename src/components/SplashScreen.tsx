import React, { useEffect, useRef, useState } from 'react';
import { motion, useReducedMotion } from 'motion/react';
import logo from '../assets/images/logo.jpg';
import { BRAND_NAME } from '../config/site';
import { fill } from '../i18n/fill';
import { useI18n } from '../i18n/I18nProvider';

const HOLD_MS = 1280;
const REDUCED_HOLD_MS = 400;
const EXIT_S = 0.32;

interface SplashScreenProps {
  onDone: () => void;
}

export const SplashScreen: React.FC<SplashScreenProps> = ({ onDone }) => {
  const { m } = useI18n();
  const reduceMotion = useReducedMotion();
  const [leaving, setLeaving] = useState(false);
  const finished = useRef(false);

  const finish = () => {
    if (finished.current) {
      return;
    }
    finished.current = true;
    onDone();
  };

  useEffect(() => {
    if (!leaving) {
      return;
    }
    const exitMs = reduceMotion ? 0 : EXIT_S * 1000;
    const timer = window.setTimeout(finish, exitMs);
    return () => window.clearTimeout(timer);
  }, [leaving, reduceMotion]);

  useEffect(() => {
    const root = document.documentElement;
    const body = document.body;
    const prevRoot = root.style.overflow;
    const prevBody = body.style.overflow;
    root.style.overflow = 'hidden';
    body.style.overflow = 'hidden';
    return () => {
      root.style.overflow = prevRoot;
      body.style.overflow = prevBody;
    };
  }, []);

  useEffect(() => {
    const hold = reduceMotion ? REDUCED_HOLD_MS : HOLD_MS;
    const timer = window.setTimeout(() => setLeaving(true), hold);
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setLeaving(true);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [reduceMotion]);

  return (
    <motion.button
      type="button"
      className="no-print fixed inset-0 z-[80] flex h-full w-full cursor-pointer items-center justify-center border-0 bg-[#f8f9ff] p-0 outline-none"
      aria-label={fill(m.shell.splashAria, { brand: BRAND_NAME })}
      onClick={() => setLeaving(true)}
      initial={{ opacity: 1 }}
      animate={{ opacity: leaving ? 0 : 1 }}
      transition={{ duration: reduceMotion ? 0 : leaving ? EXIT_S : 0 }}
      onAnimationComplete={() => {
        if (leaving) {
          finish();
        }
      }}
    >
      <div className="flex w-[220px] flex-col items-center md:w-[360px]">
        <motion.div
          className="relative mb-5 md:mb-8"
          initial={reduceMotion ? false : { opacity: 0, scale: 0.92 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: reduceMotion ? 0 : 0.45, ease: 'easeOut' }}
        >
          {!reduceMotion && (
            <motion.span
              className="pointer-events-none absolute inset-0 rounded-full border border-[#006194]/30 md:border-2"
              initial={{ scale: 1, opacity: 0.55 }}
              animate={{ scale: 1.45, opacity: 0 }}
              transition={{ duration: 1.25, ease: 'easeOut' }}
            />
          )}
          <img
            alt=""
            className="relative h-16 w-16 rounded-full object-cover ring-2 ring-[#006194]/25 md:h-32 md:w-32 md:ring-[3px]"
            src={logo}
          />
          <span
            className={`absolute -right-0.5 -bottom-0.5 h-3 w-3 rounded-full border-2 border-[#f8f9ff] bg-[#00855b] md:h-4 md:w-4 md:border-[3px] ${
              reduceMotion ? '' : 'animate-pulse'
            }`}
          />
        </motion.div>

        <motion.div
          className="flex flex-col items-center gap-1 md:gap-2"
          initial={reduceMotion ? false : { opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: reduceMotion ? 0 : 0.4, delay: reduceMotion ? 0 : 0.12, ease: 'easeOut' }}
        >
          <span className="font-['Inter'] text-[22px] font-bold tracking-tight text-[#0b1c30] md:text-[44px]">
            {BRAND_NAME}
          </span>
          <span className="font-['JetBrains_Mono'] text-[11px] tracking-wide text-[#565e74] md:text-[15px]">
            {m.shell.researchProtocol}
          </span>
        </motion.div>

        <div className="mt-6 h-px w-full overflow-hidden rounded-full bg-[#dce9ff] md:mt-8 md:h-0.5">
          <motion.div
            className="h-full origin-left bg-[#006194]"
            initial={{ scaleX: reduceMotion ? 1 : 0 }}
            animate={{ scaleX: 1 }}
            transition={{
              duration: reduceMotion ? 0 : HOLD_MS / 1000,
              ease: [0.22, 1, 0.36, 1],
            }}
          />
        </div>
      </div>
    </motion.button>
  );
};
