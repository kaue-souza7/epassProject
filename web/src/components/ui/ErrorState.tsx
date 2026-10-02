import { AlertCircle, RefreshCw } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import { springSoft } from "../motion/transitions";

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
}

export function ErrorState({
  title = "Erro ao carregar dados",
  message = "Não foi possível carregar as informações. Tente novamente.",
  onRetry,
}: ErrorStateProps) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      className="flex flex-col items-center justify-center py-12 text-center"
      role="alert"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={reduceMotion ? { duration: 0.01 } : springSoft}
    >
      <motion.span
        className="relative mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-danger-50 dark:bg-danger-900/20"
        initial={reduceMotion ? undefined : { scale: 0.6, rotate: -12 }}
        animate={{ scale: 1, rotate: 0 }}
        transition={reduceMotion ? { duration: 0.01 } : springSoft}
      >
        {reduceMotion ? null : (
          <span className="absolute inset-0 rounded-full bg-danger-500/30 animate-ring" />
        )}
        <AlertCircle className="h-6 w-6 text-danger-500 relative" />
      </motion.span>
      <p className="text-base font-semibold text-gray-900 dark:text-gray-100">
        {title}
      </p>
      <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 max-w-md">
        {message}
      </p>
      {onRetry && (
        <motion.button
          type="button"
          onClick={onRetry}
          className="mt-4 inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-primary-500 border border-primary-500 rounded-lg hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-colors"
          whileHover={reduceMotion ? undefined : { scale: 1.04, y: -1 }}
          whileTap={reduceMotion ? undefined : { scale: 0.96 }}
        >
          <motion.span
            animate={reduceMotion ? undefined : { rotate: 360 }}
            transition={reduceMotion ? undefined : { duration: 1, repeat: Infinity, ease: "linear" }}
          >
            <RefreshCw className="h-4 w-4" />
          </motion.span>
          Tentar novamente
        </motion.button>
      )}
    </motion.div>
  );
}
