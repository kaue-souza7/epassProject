import { Outlet } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";

function Orb({
  className,
  delay = 0,
}: {
  className: string;
  delay?: number;
}) {
  return (
    <motion.div
      className={`absolute rounded-full blur-3xl ${className}`}
      animate={{ scale: [1, 1.18, 1], opacity: [0.55, 0.85, 0.55] }}
      transition={{ duration: 9, repeat: Infinity, ease: "easeInOut", delay }}
      aria-hidden="true"
    />
  );
}

export function AuthLayout() {
  const reduceMotion = useReducedMotion();

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 dark:bg-surface-dark p-4 relative overflow-hidden">
      {!reduceMotion && (
        <>
          <Orb className="w-96 h-96 bg-primary-300/50 -top-24 -left-24" />
          <Orb className="w-80 h-80 bg-accent-400/40 bottom-0 right-0" delay={1.6} />
          <Orb className="w-64 h-64 bg-rose-300/40 top-1/3 right-1/4" delay={3.2} />
        </>
      )}

      <motion.div
        className="w-full max-w-5xl flex flex-col lg:flex-row bg-white dark:bg-card-dark rounded-3xl shadow-epass-xl overflow-hidden min-h-[560px] border border-white/60 dark:border-gray-700 relative"
        initial={reduceMotion ? false : { opacity: 0, y: 32, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ type: "spring", stiffness: 240, damping: 26 }}
      >
        <div className="flex-1 flex items-center justify-center p-8 md:p-12">
          <div className="w-full max-w-sm">
            <Outlet />
          </div>
        </div>

        <div className="hidden lg:flex flex-1 items-center justify-center bg-gradient-to-br from-[#FF5B8F] via-rose-300 to-orange-400 p-8 relative overflow-hidden">
          {!reduceMotion && (
            <>
              <motion.div
                className="absolute w-72 h-72 rounded-full bg-white/25 blur-2xl"
                animate={{ x: [-30, 30, -30], y: [20, -20, 20] }}
                transition={{ duration: 11, repeat: Infinity, ease: "easeInOut" }}
                aria-hidden="true"
              />
              <motion.div
                className="absolute w-56 h-56 rounded-full bg-accent-300/40 blur-2xl bottom-8 right-4"
                animate={{ x: [20, -20, 20], y: [-25, 25, -25] }}
                transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
                aria-hidden="true"
              />
            </>
          )}

          <motion.img
            src="/login-image.png"
            alt="Ilustração"
            className="w-full max-w-sm h-auto object-contain drop-shadow-2xl relative"
            initial={reduceMotion ? false : { opacity: 0, x: 40, rotate: 4 }}
            animate={
              reduceMotion
                ? { opacity: 1, x: 0 }
                : { opacity: 1, x: 0, rotate: 0, y: [0, -12, 0] }
            }
            transition={{
              opacity: { duration: 0.7, delay: 0.15 },
              x: { type: "spring", stiffness: 180, damping: 22, delay: 0.15 },
              rotate: { type: "spring", stiffness: 180, damping: 22, delay: 0.15 },
              y: reduceMotion
                ? undefined
                : { duration: 6, repeat: Infinity, ease: "easeInOut", delay: 1 },
            }}
          />
        </div>
      </motion.div>
    </div>
  );
}
