import { clsx } from "clsx";

interface BadgeProps {
  children: string;
  variant?: "success" | "warning" | "danger" | "info" | "default";
}

export function Badge({ children, variant = "default" }: BadgeProps) {
  return (
    <span
      role="status"
      className={clsx(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
        {
          "bg-success-50 text-success-600 dark:bg-success-900/20 dark:text-success-400": variant === "success",
          "bg-warning-50 text-warning-600 dark:bg-warning-900/20 dark:text-warning-400": variant === "warning",
          "bg-danger-50 text-danger-600 dark:bg-danger-900/20 dark:text-danger-400": variant === "danger",
          "bg-primary-50 text-primary-600 dark:bg-primary-900/20 dark:text-primary-400": variant === "info",
          "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400": variant === "default",
        },
      )}
    >
      {children}
    </span>
  );
}
