import type { LucideIcon } from "lucide-react";
import { clsx } from "clsx";
import { motion, useReducedMotion } from "framer-motion";
import { CountUp } from "../motion";
import { springSoft } from "../motion/transitions";

export type StatTone = "primary" | "success" | "warning" | "danger" | "info" | "default";

const TONE_TEXT: Record<StatTone, string> = {
  primary: "text-primary-500",
  success: "text-success-500",
  warning: "text-warning-500",
  danger: "text-danger-500",
  info: "text-blue-500",
  default: "text-gray-700 dark:text-gray-200",
};

const TONE_GRADIENT: Record<StatTone, string> = {
  primary: "from-primary-500 to-accent-500",
  success: "from-success-500 to-emerald-400",
  warning: "from-warning-500 to-accent-400",
  danger: "from-danger-500 to-rose-400",
  info: "from-blue-500 to-cyan-400",
  default: "from-gray-400 to-gray-300",
};

const TONE_CHIP: Record<StatTone, string> = {
  primary: "bg-primary-50 text-primary-600 dark:bg-primary-900/20 dark:text-primary-300",
  success: "bg-success-50 text-success-600 dark:bg-success-900/20 dark:text-success-500",
  warning: "bg-warning-50 text-warning-600 dark:bg-warning-900/20 dark:text-warning-500",
  danger: "bg-danger-50 text-danger-600 dark:bg-danger-900/20 dark:text-danger-400",
  info: "bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400",
  default: "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300",
};

interface StatCardProps {
  label: string;
  value: number | string | null | undefined;
  icon?: LucideIcon;
  tone?: StatTone;
  hint?: string;
  className?: string;
  index?: number;
  decimals?: number;
  onClick?: () => void;
}

export function StatCard({
  label,
  value,
  icon: Icon,
  tone = "primary",
  hint,
  className,
  index = 0,
  decimals = 0,
  onClick,
}: StatCardProps) {
  const reduceMotion = useReducedMotion();
  const numeric = typeof value === "number" && Number.isFinite(value);

  return (
    <motion.div
      className={clsx(
        "group relative bg-card dark:bg-card-dark rounded-xl border border-gray-200 dark:border-gray-700 shadow-epass overflow-hidden epass-hairline",
        onClick && "cursor-pointer",
        className,
      )}
      initial={reduceMotion ? false : { opacity: 0, y: 18, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ ...springSoft, delay: reduceMotion ? 0 : index * 0.06 }}
      whileHover={
        reduceMotion || !onClick
          ? { y: -3, transition: springSoft }
          : { y: -4, scale: 1.01, transition: springSoft }
      }
      whileTap={reduceMotion ? undefined : { scale: 0.99 }}
      onClick={onClick}
    >
      <motion.span
        className={clsx(
          "absolute inset-x-0 top-0 h-[3px] bg-gradient-to-r",
          TONE_GRADIENT[tone],
        )}
        initial={reduceMotion ? false : { scaleX: 0 }}
        animate={{ scaleX: 1 }}
        transition={{ duration: 0.7, delay: reduceMotion ? 0 : 0.15 + index * 0.06, ease: [0.16, 1, 0.3, 1] }}
        style={{ originX: 0 }}
        aria-hidden="true"
      />

      <div className="flex items-start justify-between gap-3 p-5">
        <div className="min-w-0">
          <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
          <p
            className={clsx(
              "mt-1.5 text-3xl font-extrabold tabular-nums tracking-tight",
              TONE_TEXT[tone],
            )}
          >
            {numeric ? (
              <CountUp value={value} decimals={decimals} />
            ) : (
              value ?? "—"
            )}
          </p>
          {hint && (
            <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">{hint}</p>
          )}
        </div>

        {Icon && (
          <motion.span
            className={clsx(
              "flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl",
              TONE_CHIP[tone],
            )}
            animate={reduceMotion ? undefined : { scale: [1, 1.08, 1] }}
            transition={{
              duration: 2.8,
              repeat: Infinity,
              ease: "easeInOut",
              delay: index * 0.25,
            }}
          >
            <Icon className="h-5 w-5" aria-hidden="true" />
          </motion.span>
        )}
      </div>
    </motion.div>
  );
}
