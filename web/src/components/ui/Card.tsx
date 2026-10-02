import type { ReactNode } from "react";
import { clsx } from "clsx";
import { motion, useReducedMotion } from "framer-motion";

interface CardProps {
  children: ReactNode;
  className?: string;
  padding?: "none" | "sm" | "md" | "lg";
  interactive?: boolean;
}

export function Card({
  children,
  className,
  padding = "md",
  interactive = false,
}: CardProps) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      className={clsx(
        "bg-card dark:bg-card-dark rounded-xl border border-gray-200 dark:border-gray-700",
        {
          "p-0": padding === "none",
          "p-4": padding === "sm",
          "p-6": padding === "md",
          "p-8": padding === "lg",
        },
        interactive
          ? "shadow-epass transition-shadow duration-300 ease-epass epass-hairline cursor-pointer"
          : "shadow-sm",
        className,
      )}
      whileHover={
        interactive && !reduceMotion
          ? { y: -3, transition: { type: "spring", stiffness: 340, damping: 26 } }
          : undefined
      }
    >
      {children}
    </motion.div>
  );
}
