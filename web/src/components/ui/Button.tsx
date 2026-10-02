import type { ButtonHTMLAttributes, ComponentProps, ReactNode } from "react";
import { clsx } from "clsx";
import { motion, useReducedMotion } from "framer-motion";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  children: ReactNode;
}

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  className,
  children,
  disabled,
  ...props
}: ButtonProps) {
  const reduceMotion = useReducedMotion();
  const isDisabled = disabled || loading;

  return (
    <motion.button
      className={clsx(
        "relative inline-flex items-center justify-center font-medium rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none overflow-hidden",
        "transition-colors duration-200 ease-epass active:shadow-epass-sm",
        !isDisabled && !reduceMotion && "hover:shadow-epass-md",
        {
          "bg-primary-500 text-white hover:bg-primary-600 focus:ring-primary-500": variant === "primary",
          "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600": variant === "secondary",
          "border border-primary-500 text-primary-500 hover:bg-primary-50 dark:hover:bg-primary-900/20": variant === "outline",
          "text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700": variant === "ghost",
          "bg-danger-500 text-white hover:bg-danger-600 focus:ring-danger-500": variant === "danger",
        },
        {
          "px-3 py-1.5 text-sm": size === "sm",
          "px-4 py-2 text-sm": size === "md",
          "px-6 py-3 text-base": size === "lg",
        },
        className,
      )}
      disabled={isDisabled}
      aria-busy={loading || undefined}
      whileHover={isDisabled || reduceMotion ? undefined : { y: -1 }}
      whileTap={isDisabled || reduceMotion ? undefined : { scale: 0.96, y: 0 }}
      transition={{ type: "spring", stiffness: 500, damping: 28 }}
      {...(props as ComponentProps<typeof motion.button>)}
    >
      <motion.span
        className="absolute inset-0 bg-white/20"
        style={{ transformOrigin: "left" }}
        initial={{ scaleX: 0 }}
        whileHover={isDisabled || reduceMotion ? undefined : { scaleX: 1 }}
        transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
        aria-hidden="true"
      />
      <motion.span
        className="absolute inset-0 flex items-center justify-center"
        animate={{ opacity: loading ? 1 : 0, scale: loading ? 1 : 0.6 }}
        transition={{ duration: 0.2 }}
        aria-hidden="true"
      >
        <svg
          className="animate-spin h-4 w-4"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
      </motion.span>
      <motion.span
        className="inline-flex items-center"
        animate={{ opacity: loading ? 0 : 1 }}
        transition={{ duration: 0.2 }}
        aria-hidden={loading || undefined}
      >
        {children}
      </motion.span>
    </motion.button>
  );
}
