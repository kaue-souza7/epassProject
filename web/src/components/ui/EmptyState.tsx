import type { LucideIcon } from "lucide-react";
import { Inbox } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import { springSoft } from "../motion/transitions";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
}

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
}: EmptyStateProps) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      className="flex flex-col items-center justify-center py-12 text-center"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={reduceMotion ? { duration: 0.01 } : springSoft}
    >
      <motion.span
        className="relative mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-gray-100 dark:bg-gray-800"
        animate={
          reduceMotion
            ? undefined
            : { y: [0, -5, 0], transition: { duration: 3.4, repeat: Infinity, ease: "easeInOut" } }
        }
      >
        <Icon className="h-6 w-6 text-gray-400 dark:text-gray-500" />
      </motion.span>
      <p className="text-base font-medium text-gray-500 dark:text-gray-400">
        {title}
      </p>
      {description && (
        <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
          {description}
        </p>
      )}
      {action && (
        <motion.button
          type="button"
          onClick={action.onClick}
          className="mt-4 text-sm font-medium text-primary-500 hover:text-primary-600 transition-colors"
          whileHover={reduceMotion ? undefined : { scale: 1.05 }}
          whileTap={reduceMotion ? undefined : { scale: 0.95 }}
        >
          {action.label}
        </motion.button>
      )}
    </motion.div>
  );
}
