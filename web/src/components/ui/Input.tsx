import { forwardRef, type InputHTMLAttributes } from "react";
import { clsx } from "clsx";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className, id, ...props }, ref) => {
  const inputId = id || label.toLowerCase().replace(/\s+/g, "-");
  return (
    <div className="relative">
      <input
        ref={ref}
        id={inputId}
        className={clsx(
          "w-full px-3 py-3 text-sm bg-transparent border rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-0",
          error
            ? "border-danger-500 focus:ring-danger-500"
            : "border-gray-300 dark:border-gray-600 focus:border-primary-500 focus:ring-primary-500",
          "text-black placeholder:text-gray-400",
          className,
        )}
        {...props}
      />
      <label
        htmlFor={inputId}
        className={clsx(
          "absolute left-3 -translate-y-1/2 pointer-events-none",
          "top-0 text-xs px-1.5 bg-white",
          error ? "text-danger-500" : "text-gray-500 dark:text-gray-400",
        )}
      >
        {label}
      </label>
      {error && <p className="mt-1 text-xs text-danger-500">{error}</p>}
    </div>
  );
});
